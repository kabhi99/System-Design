# E-COMMERCE SYSTEM DESIGN - DEEP DIVE
*Amazon/Flipkart Style Shopping Platform*

### Table of Contents

Part 1: Requirements & Core Challenges
1.1 Functional Requirements
1.2 Non-Functional Requirements
1.3 Capacity Estimation
1.4 Core Design Challenges

Part 2: Data Model & API Contracts
2.1 Database Schema
2.2 API Endpoints

Part 3: High-Level Architecture
3.1 System Architecture Diagram
3.2 Microservices Breakdown
3.3 Technology Choices & Rationale
3.4 Security Model (Authentication & Authorization)
3.5 Database-to-Service Ownership Mapping

Part 4: Product Catalog & Search
4.1 Product Data Model
4.2 Search Architecture (Elasticsearch)
4.3 Faceted Search & Filters
4.4 Autocomplete & Suggestions

Part 5: Shopping Cart
5.1 Cart Architecture
5.2 Cart Storage Strategies
5.3 Cart Merge (Guest > User)
5.4 Price & Availability Sync

Part 6: Inventory Management (The Hard Problem)
6.1 Inventory Challenges
6.2 Inventory Reservation Strategies
6.3 Distributed Locking for Inventory
6.4 Overselling Prevention

Part 7: Checkout & Order Processing
7.1 Checkout Flow
7.2 Payment Integration
7.3 Order State Machine
7.4 Saga Pattern: Orchestration (Central Coordinator)
7.5 Saga Pattern: Choreography (Event-Driven)            < NEW
7.6 Kafka Event Contracts                                 < NEW
7.7 Idempotency Design                                    < NEW
7.8 Saga Recovery Mechanism                               < NEW
7.9 Complete Saga Flow with All Edge Cases               < NEW

Part 8: Pricing & Promotions
8.1 Dynamic Pricing
8.2 Flash Sales Architecture

Part 9: Caching Strategy
Part 10: Notification System
Part 11: Database Architecture
Part 12: Failure Scenarios & Recovery
Part 13: Scaling & Performance
Part 14: Trade-offs & Decisions
Part 15: Interview Follow-ups
Part 16: Theoretical Foundations
16.1 CAP Theorem
16.2 ACID vs BASE
16.3 Consistency Models
16.4 Database Scaling Concepts
16.5 Caching Patterns
16.6 Load Balancing Algorithms
16.7 Rate Limiting Algorithms
16.8 Message Queue Semantics
16.9 Microservices Patterns
16.10 API Design Principles

## A REAL-WORLD PROBLEM

Imagine this scenario:

Black Friday sale starts at midnight.

10 million users flood the site simultaneously.
A hot product (PS5) has only 10,000 units in stock.

User A and User B both add PS5 to cart at the same moment.
Both proceed to checkout.
Both complete payment.

QUESTIONS:
- Who gets the PS5?
- How do we prevent overselling 10,000 units to 50,000 customers?
- When do we "reserve" inventory - at cart add? At checkout? At payment?
- What if User A's payment fails after we reserved their unit?
- How do we handle 10 million concurrent users for 10,000 items?

This is the E-Commerce problem - a classic example of:
- High-read, low-write with extreme contention on hot products
- Inventory management with finite resources
- Distributed transactions across cart, inventory, payment, order
- Eventual consistency vs strong consistency trade-offs
- Traffic spikes (100x-1000x normal load)

## PART 1: REQUIREMENTS & CORE CHALLENGES

### 1.1 FUNCTIONAL REQUIREMENTS

**CUSTOMERS:**
- Browse products by category, brand, price range
- Search products with filters and sorting
- View product details, images, reviews, ratings
- Add products to cart (guest or logged in)
- Manage cart (update quantity, remove items)
- Apply coupons and promotional codes
- Checkout with multiple payment options
- Track order status
- View order history
- Return and refund products
- Write product reviews

**SELLERS/VENDORS:**
- List products with details, images, pricing
- Manage inventory levels
- View orders and fulfill them
- Track sales and revenue
- Manage returns

**ADMIN:**
- Manage product catalog
- Configure promotions and discounts
- Monitor fraud and suspicious activity
- Handle customer support escalations
- Generate reports and analytics

### 1.2 NON-FUNCTIONAL REQUIREMENTS

**SCALE:**
- 100 million monthly active users
- 10 million products in catalog
- 1 million orders per day
- Peak: 10 million concurrent users during sales
- 100,000 orders per hour during flash sales

**PERFORMANCE:**
- Search results: < 200ms
- Product page load: < 500ms
- Add to cart: < 100ms
- Checkout initiation: < 500ms
- Order placement: < 3 seconds
- 99.99% availability (4 nines)

**CONSISTENCY:**
- NO overselling (critical business requirement)
- Inventory must be accurate within seconds
- Order and payment must be atomic
- Price shown = Price charged (no surprises)

**RELIABILITY:**
- Zero lost orders
- Payment failures handled gracefully
- Automatic retry for transient failures
- Data durability across regions

### 1.3 CAPACITY ESTIMATION

```
+-------------------------------------------------------------------------+
|                    TRAFFIC ESTIMATION                                   |
|                                                                         |
|  DAILY ACTIVE USERS:                                                    |
|  * 100M MAU > ~10M DAU (10% daily active)                               |
|                                                                         |
|  PAGE VIEWS:                                                            |
|  * Average 20 page views per user per session                           |
|  * 10M x 20 = 200M page views/day                                       |
|  * Peak: 200M x 0.4 / (4 x 3600) ~ 5,500 requests/second                |
|  * Flash sale peak: 50,000 requests/second                              |
|                                                                         |
|  ORDERS:                                                                |
|  * 1M orders/day                                                        |
|  * Peak hours (6 PM - 10 PM): 40% of orders = 400K in 4 hours           |
|  * Peak TPS: 400K / (4 x 3600) ~ 28 orders/second                       |
|  * Flash sale: 2,000 orders/second                                      |
|                                                                         |
|  SEARCH QUERIES:                                                        |
|  * 50M searches/day                                                     |
|  * Peak: 2,000 searches/second                                          |
|                                                                         |
|  CART OPERATIONS:                                                       |
|  * 5x orders = 5M cart additions/day                                    |
|  * Peak: 150 cart operations/second                                     |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    STORAGE ESTIMATION                                   |
|                                                                         |
|  PRODUCTS:                                                              |
|  * 10M products                                                         |
|  * ~5 KB per product (metadata, description)                            |
|  * Total: 50 GB                                                         |
|                                                                         |
|  PRODUCT IMAGES:                                                        |
|  * 10M products x 5 images x 500 KB = 25 TB                             |
|  * Served via CDN                                                       |
|                                                                         |
|  ORDERS:                                                                |
|  * 1M orders/day x 365 x 5 years = 1.8B orders                          |
|  * ~2 KB per order                                                      |
|  * Total: 3.6 TB                                                        |
|                                                                         |
|  ORDER ITEMS:                                                           |
|  * Average 3 items per order = 5.4B order items                         |
|  * ~500 bytes per item                                                  |
|  * Total: 2.7 TB                                                        |
|                                                                         |
|  USER DATA:                                                             |
|  * 100M users x 2 KB = 200 GB                                           |
|                                                                         |
|  REVIEWS:                                                               |
|  * 500M reviews x 1 KB = 500 GB                                         |
|                                                                         |
|  TOTAL: ~7 TB + 25 TB images                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 1.4 CORE DESIGN CHALLENGES

### CHALLENGE 1: INVENTORY OVERSELLING

```
+-------------------------------------------------------------------------+
|  THE PROBLEM:                                                           |
|                                                                         |
|  PS5 stock: 10,000 units                                                |
|  Flash sale starts                                                      |
|                                                                         |
|  T1: 50,000 users add PS5 to cart                                       |
|  T2: 30,000 users proceed to checkout                                   |
|  T3: 15,000 users complete payment                                      |
|                                                                         |
|  RESULT: We sold 15,000 units but only have 10,000!                     |
|                                                                         |
|  CONSEQUENCES:                                                          |
|  * Customer trust destroyed                                             |
|  * Order cancellations = support nightmare                              |
|  * Potential legal issues (false advertising)                           |
|  * Negative PR during high-visibility event                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CHALLENGE 2: THE CART DILEMMA

```
+-------------------------------------------------------------------------+
|  WHEN TO RESERVE INVENTORY?                                             |
|                                                                         |
|  OPTION A: Reserve at Add-to-Cart                                       |
|  ---------------------------------                                      |
|  Pros: No overselling possible                                          |
|  Cons: Cart abandonment rate is 70%!                                    |
|        Users "hoard" inventory                                          |
|        Items sit reserved but never purchased                           |
|                                                                         |
|  OPTION B: Reserve at Checkout Start                                    |
|  ------------------------------------                                   |
|  Pros: Better inventory utilization                                     |
|  Cons: User might get "out of stock" at checkout (bad UX)               |
|        Still can have abandoned checkouts                               |
|                                                                         |
|  OPTION C: Reserve at Payment (Just-in-time)                            |
|  ---------------------------------------------                          |
|  Pros: Maximum inventory availability                                   |
|  Cons: Risk of overselling if concurrent payments                       |
|        User completes payment but item gone                             |
|                                                                         |
|  SOLUTION: Hybrid approach with soft vs hard reservation                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CHALLENGE 3: DISTRIBUTED TRANSACTIONS

```
+-------------------------------------------------------------------------+
|  A SINGLE ORDER TOUCHES MULTIPLE SERVICES:                              |
|                                                                         |
|  1. Cart Service: Get cart items                                        |
|  2. Inventory Service: Reserve stock                                    |
|  3. Pricing Service: Calculate total with discounts                     |
|  4. Payment Service: Charge customer                                    |
|  5. Order Service: Create order record                                  |
|  6. Notification Service: Send confirmation                             |
|  7. Fulfillment Service: Initiate shipping                              |
|                                                                         |
|  WHAT IF STEP 4 (PAYMENT) FAILS?                                        |
|  * Must release inventory reservation (step 2)                          |
|  * Must NOT create order (step 5)                                       |
|  * This is the SAGA pattern problem                                     |
|                                                                         |
|  WHAT IF STEP 5 (ORDER) FAILS AFTER PAYMENT SUCCESS?                    |
|  * Customer charged but no order!                                       |
|  * Must refund OR retry order creation                                  |
|  * Need idempotency + compensation                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CHALLENGE 4: PRICE CONSISTENCY

```
+-------------------------------------------------------------------------+
|  THE PROBLEM:                                                           |
|                                                                         |
|  T1: User adds item at $99                                              |
|  T2: Price changes to $129 (flash sale ended)                           |
|  T3: User checks out - what price?                                      |
|                                                                         |
|  OPTIONS:                                                               |
|  * Honor cart price ($99) - lose money                                  |
|  * Charge new price ($129) - angry customer                             |
|  * Show warning, ask to re-confirm - friction                           |
|                                                                         |
|  SOLUTION:                                                              |
|  * Price lock for limited time (15-30 minutes)                          |
|  * Clear UI showing "Price guaranteed until X:XX"                       |
|  * Re-validate at checkout, show changes prominently                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 2: DATA MODEL & API CONTRACTS

### 2.1 DATABASE SCHEMA

**USERS TABLE:**

```
+-------------------------------------------------------------------------+
|  CREATE TABLE users (                                                   |
|      user_id BIGINT PRIMARY KEY AUTO_INCREMENT,                         |
|      email VARCHAR(255) UNIQUE NOT NULL,                                |
|      password_hash VARCHAR(255) NOT NULL,                               |
|      first_name VARCHAR(100),                                           |
|      last_name VARCHAR(100),                                            |
|      phone VARCHAR(20),                                                 |
|      status ENUM('ACTIVE', 'SUSPENDED', 'DELETED') DEFAULT 'ACTIVE',    |
|      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                    |
|      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE,          |
|      INDEX idx_email (email),                                           |
|      INDEX idx_status (status)                                          |
|  );                                                                     |
|                                                                         |
|  CREATE TABLE addresses (                                               |
|      address_id BIGINT PRIMARY KEY AUTO_INCREMENT,                      |
|      user_id BIGINT NOT NULL,                                           |
|      address_type ENUM('SHIPPING', 'BILLING') DEFAULT 'SHIPPING',       |
|      street_address VARCHAR(500),                                       |
|      city VARCHAR(100),                                                 |
|      state VARCHAR(100),                                                |
|      postal_code VARCHAR(20),                                           |
|      country VARCHAR(100),                                              |
|      is_default BOOLEAN DEFAULT FALSE,                                  |
|      FOREIGN KEY (user_id) REFERENCES users(user_id),                   |
|      INDEX idx_user_id (user_id)                                        |
|  );                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

**PRODUCTS TABLE:**

```
+-------------------------------------------------------------------------+
|  CREATE TABLE categories (                                              |
|      category_id BIGINT PRIMARY KEY AUTO_INCREMENT,                     |
|      name VARCHAR(255) NOT NULL,                                        |
|      parent_category_id BIGINT,                                         |
|      slug VARCHAR(255) UNIQUE,                                          |
|      level INT DEFAULT 0,                                               |
|      FOREIGN KEY (parent_category_id) REFERENCES categories(category_id) 
|  );                                                                     |
|                                                                         |
|  CREATE TABLE products (                                                |
|      product_id BIGINT PRIMARY KEY AUTO_INCREMENT,                      |
|      seller_id BIGINT NOT NULL,                                         |
|      category_id BIGINT NOT NULL,                                       |
|      name VARCHAR(500) NOT NULL,                                        |
|      description TEXT,                                                  |
|      brand VARCHAR(255),                                                |
|      sku VARCHAR(100) UNIQUE,                                           |
|      base_price DECIMAL(12, 2) NOT NULL,                                |
|      sale_price DECIMAL(12, 2),                                         |
|      currency VARCHAR(3) DEFAULT 'USD',                                 |
|      status ENUM('ACTIVE', 'INACTIVE', 'OUT_OF_STOCK') DEFAULT 'ACTIVE', 
|      avg_rating DECIMAL(3, 2) DEFAULT 0,                                |
|      review_count INT DEFAULT 0,                                        |
|      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                    |
|      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE,          |
|      FOREIGN KEY (category_id) REFERENCES categories(category_id),      |
|      INDEX idx_category (category_id),                                  |
|      INDEX idx_seller (seller_id),                                      |
|      INDEX idx_status (status),                                         |
|      FULLTEXT INDEX idx_search (name, description, brand)               |
|  );                                                                     |
|                                                                         |
|  CREATE TABLE product_images (                                          |
|      image_id BIGINT PRIMARY KEY AUTO_INCREMENT,                        |
|      product_id BIGINT NOT NULL,                                        |
|      image_url VARCHAR(500) NOT NULL,                                   |
|      display_order INT DEFAULT 0,                                       |
|      is_primary BOOLEAN DEFAULT FALSE,                                  |
|      FOREIGN KEY (product_id) REFERENCES products(product_id),          |
|      INDEX idx_product (product_id)                                     |
|  );                                                                     |
|                                                                         |
|  CREATE TABLE product_variants (                                        |
|      variant_id BIGINT PRIMARY KEY AUTO_INCREMENT,                      |
|      product_id BIGINT NOT NULL,                                        |
|      sku VARCHAR(100) UNIQUE,                                           |
|      name VARCHAR(255),           -- e.g., "Red, Large"                 |
|      price_modifier DECIMAL(12, 2) DEFAULT 0,                           |
|      attributes JSON,              -- {"color": "red", "size": "L"}     |
|      FOREIGN KEY (product_id) REFERENCES products(product_id),          |
|      INDEX idx_product (product_id)                                     |
|  );                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

**INVENTORY TABLE:**

```
+----------------------------------------------------------------------------+
|  CREATE TABLE inventory (                                                  |
|      inventory_id BIGINT PRIMARY KEY AUTO_INCREMENT,                       |
|      product_id BIGINT NOT NULL,                                           |
|      variant_id BIGINT,                                                    |
|      warehouse_id BIGINT NOT NULL,                                         |
|      quantity_total INT NOT NULL DEFAULT 0,       -- Physical stock        |
|      quantity_reserved INT NOT NULL DEFAULT 0,    -- Soft reserved         |
|      quantity_available INT GENERATED ALWAYS AS                            |
|          (quantity_total - quantity_reserved) STORED,                      |
|      low_stock_threshold INT DEFAULT 10,                                   |
|      version BIGINT DEFAULT 0,                    -- Optimistic lock       |
|      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE,             |
|      FOREIGN KEY (product_id) REFERENCES products(product_id),             |
|      UNIQUE KEY uk_product_warehouse (product_id, variant_id, warehouse_id),
|      INDEX idx_low_stock (quantity_available, low_stock_threshold)         |
|  );                                                                        |
|                                                                            |
|  CREATE TABLE inventory_reservations (                                     |
|      reservation_id BIGINT PRIMARY KEY AUTO_INCREMENT,                     |
|      inventory_id BIGINT NOT NULL,                                         |
|      order_id BIGINT,                             -- NULL until order      |
|      cart_id VARCHAR(100),                        -- For cart reserv       |
|      quantity INT NOT NULL,                                                |
|      status ENUM('PENDING', 'CONFIRMED', 'RELEASED', 'EXPIRED')            |
|          DEFAULT 'PENDING',                                                |
|      expires_at TIMESTAMP NOT NULL,                                        |
|      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                       |
|      FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id),        |
|      INDEX idx_status_expires (status, expires_at),                        |
|      INDEX idx_cart (cart_id),                                             |
|      INDEX idx_order (order_id)                                            |
|  );                                                                        |
|                                                                            |
+----------------------------------------------------------------------------+
```

**CART TABLE:**

```
+-------------------------------------------------------------------------+
|  CREATE TABLE carts (                                                   |
|      cart_id VARCHAR(100) PRIMARY KEY,            -- UUID or session    |
|      user_id BIGINT,                              -- NULL for guest     |
|      status ENUM('ACTIVE', 'MERGED', 'CONVERTED', 'ABANDONED')          |
|          DEFAULT 'ACTIVE',                                              |
|      currency VARCHAR(3) DEFAULT 'USD',                                 |
|      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                    |
|      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE,          |
|      expires_at TIMESTAMP,                        -- For cleanup        |
|      INDEX idx_user (user_id),                                          |
|      INDEX idx_status (status),                                         |
|      INDEX idx_expires (expires_at)                                     |
|  );                                                                     |
|                                                                         |
|  CREATE TABLE cart_items (                                              |
|      cart_item_id BIGINT PRIMARY KEY AUTO_INCREMENT,                    |
|      cart_id VARCHAR(100) NOT NULL,                                     |
|      product_id BIGINT NOT NULL,                                        |
|      variant_id BIGINT,                                                 |
|      quantity INT NOT NULL DEFAULT 1,                                   |
|      price_at_addition DECIMAL(12, 2) NOT NULL,   -- Snapshot           |
|      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                    |
|      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE,          |
|      FOREIGN KEY (cart_id) REFERENCES carts(cart_id),                   |
|      FOREIGN KEY (product_id) REFERENCES products(product_id),          |
|      UNIQUE KEY uk_cart_product (cart_id, product_id, variant_id),      |
|      INDEX idx_cart (cart_id)                                           |
|  );                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

**ORDERS TABLE:**

```
+-------------------------------------------------------------------------+
|  CREATE TABLE orders (                                                  |
|      order_id BIGINT PRIMARY KEY AUTO_INCREMENT,                        |
|      order_number VARCHAR(50) UNIQUE NOT NULL,    -- Human readable     |
|      user_id BIGINT NOT NULL,                                           |
|      status ENUM('PENDING', 'CONFIRMED', 'PROCESSING', 'SHIPPED',       |
|                  'DELIVERED', 'CANCELLED', 'REFUNDED') DEFAULT 'PENDING',
|      subtotal DECIMAL(12, 2) NOT NULL,                                  |
|      discount_amount DECIMAL(12, 2) DEFAULT 0,                          |
|      tax_amount DECIMAL(12, 2) DEFAULT 0,                               |
|      shipping_amount DECIMAL(12, 2) DEFAULT 0,                          |
|      total_amount DECIMAL(12, 2) NOT NULL,                              |
|      currency VARCHAR(3) DEFAULT 'USD',                                 |
|      shipping_address_id BIGINT,                                        |
|      billing_address_id BIGINT,                                         |
|      payment_method VARCHAR(50),                                        |
|      payment_status ENUM('PENDING', 'AUTHORIZED', 'CAPTURED',           |
|                          'FAILED', 'REFUNDED') DEFAULT 'PENDING',       |
|      idempotency_key VARCHAR(100) UNIQUE,                               |
|      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                    |
|      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE,          |
|      FOREIGN KEY (user_id) REFERENCES users(user_id),                   |
|      INDEX idx_user (user_id),                                          |
|      INDEX idx_status (status),                                         |
|      INDEX idx_created (created_at)                                     |
|  );                                                                     |
|                                                                         |
|  CREATE TABLE order_items (                                             |
|      order_item_id BIGINT PRIMARY KEY AUTO_INCREMENT,                   |
|      order_id BIGINT NOT NULL,                                          |
|      product_id BIGINT NOT NULL,                                        |
|      variant_id BIGINT,                                                 |
|      seller_id BIGINT NOT NULL,                                         |
|      quantity INT NOT NULL,                                             |
|      unit_price DECIMAL(12, 2) NOT NULL,          -- Price at order     |
|      total_price DECIMAL(12, 2) NOT NULL,                               |
|      status ENUM('PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED',        |
|                  'CANCELLED', 'RETURNED') DEFAULT 'PENDING',            |
|      FOREIGN KEY (order_id) REFERENCES orders(order_id),                |
|      FOREIGN KEY (product_id) REFERENCES products(product_id),          |
|      INDEX idx_order (order_id),                                        |
|      INDEX idx_seller (seller_id)                                       |
|  );                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

**PAYMENTS TABLE:**

```
+-------------------------------------------------------------------------+
|  CREATE TABLE payments (                                                |
|      payment_id BIGINT PRIMARY KEY AUTO_INCREMENT,                      |
|      order_id BIGINT NOT NULL,                                          |
|      amount DECIMAL(12, 2) NOT NULL,                                    |
|      currency VARCHAR(3) DEFAULT 'USD',                                 |
|      payment_method VARCHAR(50) NOT NULL,                               |
|      payment_gateway VARCHAR(50) NOT NULL,        -- Stripe, PayPal     |
|      gateway_transaction_id VARCHAR(255),                               |
|      status ENUM('INITIATED', 'PENDING', 'AUTHORIZED', 'CAPTURED',      |
|                  'FAILED', 'REFUNDED', 'PARTIALLY_REFUNDED')            |
|          DEFAULT 'INITIATED',                                           |
|      idempotency_key VARCHAR(100) UNIQUE NOT NULL,                      |
|      failure_reason TEXT,                                               |
|      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                    |
|      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE,          |
|      FOREIGN KEY (order_id) REFERENCES orders(order_id),                |
|      INDEX idx_order (order_id),                                        |
|      INDEX idx_status (status),                                         |
|      INDEX idx_gateway_txn (gateway_transaction_id)                     |
|  );                                                                     |
|                                                                         |
|  CREATE TABLE refunds (                                                 |
|      refund_id BIGINT PRIMARY KEY AUTO_INCREMENT,                       |
|      payment_id BIGINT NOT NULL,                                        |
|      order_id BIGINT NOT NULL,                                          |
|      amount DECIMAL(12, 2) NOT NULL,                                    |
|      reason VARCHAR(500),                                               |
|      status ENUM('PENDING', 'PROCESSED', 'FAILED') DEFAULT 'PENDING',   |
|      gateway_refund_id VARCHAR(255),                                    |
|      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                    |
|      FOREIGN KEY (payment_id) REFERENCES payments(payment_id),          |
|      FOREIGN KEY (order_id) REFERENCES orders(order_id),                |
|      INDEX idx_payment (payment_id)                                     |
|  );                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.2 API ENDPOINTS

PRODUCT APIs:

```
+-------------------------------------------------------------------------+
|  GET /api/products                                                      |
|  ---------------------                                                  |
|  Query params: category, brand, minPrice, maxPrice, sort, page, size    |
|                                                                         |
|  Response:                                                              |
|  {                                                                      |
|    "products": [                                                        |
|      {                                                                  |
|        "productId": "12345",                                            |
|        "name": "iPhone 15 Pro",                                         |
|        "brand": "Apple",                                                |
|        "price": 999.00,                                                 |
|        "salePrice": 949.00,                                             |
|        "imageUrl": "https://cdn.example.com/iphone15.jpg",              |
|        "rating": 4.5,                                                   |
|        "reviewCount": 1234,                                             |
|        "inStock": true                                                  |
|      }                                                                  |
|    ],                                                                   |
|    "pagination": { "page": 0, "size": 20, "total": 150 },               |
|    "facets": {                                                          |
|      "brands": [{"name": "Apple", "count": 45}, ...],                   |
|      "priceRanges": [{"min": 0, "max": 100, "count": 23}, ...]          |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  GET /api/products/{productId}                                          |
|  -------------------------------                                        |
|  Response: Full product details with variants, images, reviews          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  GET /api/search?q={query}                                              |
|  ---------------------------                                            |
|  Full-text search with autocomplete, spell correction                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

CART APIs:

```
+-------------------------------------------------------------------------+
|  POST /api/cart/items                                                   |
|  ---------------------                                                  |
|  Headers: Authorization (optional), X-Cart-Id (for guest)               |
|                                                                         |
|  Request:                                                               |
|  {                                                                      |
|    "productId": "12345",                                                |
|    "variantId": "v001",                                                 |
|    "quantity": 2                                                        |
|  }                                                                      |
|                                                                         |
|  Response:                                                              |
|  {                                                                      |
|    "cartId": "cart_abc123",                                             |
|    "items": [...],                                                      |
|    "subtotal": 199.98,                                                  |
|    "itemCount": 2                                                       |
|  }                                                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  GET /api/cart                                                          |
|  --------------                                                         |
|  Returns current cart with latest prices and availability               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PUT /api/cart/items/{itemId}                                           |
|  ------------------------------                                         |
|  Update quantity                                                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DELETE /api/cart/items/{itemId}                                        |
|  ---------------------------------                                      |
|  Remove item from cart                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

CHECKOUT APIs:

```
+-------------------------------------------------------------------------+
|  POST /api/checkout/initiate                                            |
|  -----------------------------                                          |
|  Headers: Authorization (required)                                      |
|                                                                         |
|  Request:                                                               |
|  {                                                                      |
|    "cartId": "cart_abc123",                                             |
|    "shippingAddressId": "addr_001",                                     |
|    "billingAddressId": "addr_001"                                       |
|  }                                                                      |
|                                                                         |
|  Response:                                                              |
|  {                                                                      |
|    "checkoutId": "chk_xyz789",                                          |
|    "items": [...],                                                      |
|    "subtotal": 199.98,                                                  |
|    "shipping": 5.99,                                                    |
|    "tax": 18.00,                                                        |
|    "total": 223.97,                                                     |
|    "expiresAt": "2024-12-19T12:30:00Z",                                 |
|    "availablePaymentMethods": ["CARD", "PAYPAL", "UPI"]                 |
|  }                                                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  POST /api/checkout/{checkoutId}/pay                                    |
|  -------------------------------------                                  |
|  Request:                                                               |
|  {                                                                      |
|    "paymentMethod": "CARD",                                             |
|    "paymentToken": "tok_visa_xxx",                                      |
|    "idempotencyKey": "idem_abc123"                                      |
|  }                                                                      |
|                                                                         |
|  Response:                                                              |
|  {                                                                      |
|    "orderId": "ord_12345",                                              |
|    "orderNumber": "ORD-2024-ABC123",                                    |
|    "status": "CONFIRMED",                                               |
|    "paymentStatus": "CAPTURED",                                         |
|    "total": 223.97                                                      |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

ORDER APIs:

```
+-------------------------------------------------------------------------+
|  GET /api/orders                                                        |
|  -----------------                                                      |
|  List user's orders with pagination                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  GET /api/orders/{orderId}                                              |
|  ---------------------------                                            |
|  Order details with items, tracking, payment info                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  POST /api/orders/{orderId}/cancel                                      |
|  -----------------------------------                                    |
|  Cancel order (if cancellation allowed based on status)                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  POST /api/orders/{orderId}/return                                      |
|  -----------------------------------                                    |
|  Initiate return for delivered order                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 3: HIGH-LEVEL ARCHITECTURE

### 3.1 SYSTEM ARCHITECTURE DIAGRAM

```
+-------------------------------------------------------------------------+
|                                                                         |
|                           CLIENTS                                       |
|           +---------+  +---------+  +---------+                         |
|           |   Web   |  | Mobile  |  |  Admin  |                         |
|           |   App   |  |   App   |  |  Panel  |                         |
|           +----+----+  +----+----+  +----+----+                         |
|                |            |            |                              |
|                +------------+------------+                              |
|                             |                                           |
|                             v                                           |
|   +-------------------------------------------------------------+       |
|   |                     CDN (CloudFront/Akamai)                  |      |
|   |              Static assets, product images                   |      |
|   +-------------------------------------------------------------+       |
|                             |                                           |
|                             v                                           |
|   +-------------------------------------------------------------+       |
|   |                    LOAD BALANCER (ALB)                       |      |
|   |                  SSL termination, routing                    |      |
|   +-------------------------------------------------------------+       |
|                             |                                           |
|                             v                                           |
|   +-------------------------------------------------------------+       |
|   |                      API GATEWAY                             |      |
|   |    Rate limiting, Auth, Request validation, Routing          |      |
|   +-------------------------------------------------------------+       |
|                             |                                           |
|        +--------------------+--------------------+                      |
|        |                    |                    |                      |
|        v                    v                    v                      |
|   +---------+         +---------+         +---------+                   |
|   | Product |         |  Cart   |         |  Order  |                   |
|   | Service |         | Service |         | Service |                   |
|   +----+----+         +----+----+         +----+----+                   |
|        |                   |                   |                        |
|        |              +----+----+              |                        |
|        |              |Inventory|              |                        |
|        |              | Service |              |                        |
|        |              +----+----+              |                        |
|        |                   |                   |                        |
|        |              +----+----+              |                        |
|        |              | Payment |              |                        |
|        |              | Service |              |                        |
|        |              +---------+              |                        |
|        |                                       |                        |
|   +----+--------------------------------------+----+                    |
|   |                 MESSAGE QUEUE (Kafka)          |                    |
|   |  Events: OrderCreated, PaymentCompleted, etc.  |                    |
|   +------------------------------------------------+                    |
|              |              |              |                            |
|              v              v              v                            |
|   +----------+  +----------+  +----------+  +----------+                |
|   |Notifica- |  |Analytics |  |  Search  |  |Fulfillment|               |
|   |  tion    |  | Service  |  | Indexer  |  |  Service |                |
|   +----------+  +----------+  +----------+  +----------+                |
|                                                                         |
|   +-------------------------------------------------------------+       |
|   |                      DATA LAYER                              |      |
|   |  +------------+  +------------+  +------------+             |       |
|   |  | PostgreSQL |  |   Redis    |  |Elasticsearch|             |      |
|   |  | (Primary)  |  |  (Cache +  |  |  (Search)  |             |       |
|   |  | Sharded    |  |   Cart)    |  |            |             |       |
|   |  +------------+  +------------+  +------------+             |       |
|   +-------------------------------------------------------------+       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.2 MICROSERVICES BREAKDOWN

```
+-------------------------------------------------------------------------+
|                    SERVICE RESPONSIBILITIES                             |
|                                                                         |
|  PRODUCT SERVICE                                                        |
|  ---------------                                                        |
|  * Product CRUD operations                                              |
|  * Category management                                                  |
|  * Variant management                                                   |
|  * Product images                                                       |
|  * Reviews and ratings                                                  |
|  * Heavily cached (products don't change often)                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SEARCH SERVICE                                                         |
|  --------------                                                         |
|  * Full-text search (Elasticsearch)                                     |
|  * Autocomplete and suggestions                                         |
|  * Faceted filtering                                                    |
|  * Search ranking and relevance                                         |
|  * Spell correction                                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CART SERVICE                                                           |
|  ------------                                                           |
|  * Add/update/remove cart items                                         |
|  * Guest cart management (cookie-based)                                 |
|  * Cart merge on login                                                  |
|  * Price and availability sync                                          |
|  * Cart expiration handling                                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  INVENTORY SERVICE (Critical Path)                                      |
|  ---------------------------------                                      |
|  * Stock level management                                               |
|  * Inventory reservation (soft lock)                                    |
|  * Inventory confirmation (hard lock)                                   |
|  * Low stock alerts                                                     |
|  * Multi-warehouse inventory                                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ORDER SERVICE                                                          |
|  -------------                                                          |
|  * Order creation and management                                        |
|  * Order state machine                                                  |
|  * Order history                                                        |
|  * Cancellation and returns                                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PAYMENT SERVICE                                                        |
|  ---------------                                                        |
|  * Payment gateway integration                                          |
|  * Payment processing                                                   |
|  * Refund handling                                                      |
|  * Idempotency management                                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USER SERVICE                                                           |
|  ------------                                                           |
|  * Registration and authentication                                      |
|  * Profile management                                                   |
|  * Address management                                                   |
|  * Preferences                                                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  NOTIFICATION SERVICE                                                   |
|  --------------------                                                   |
|  * Email notifications                                                  |
|  * SMS notifications                                                    |
|  * Push notifications                                                   |
|  * Async via Kafka                                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PRICING SERVICE                                                        |
|  ---------------                                                        |
|  * Dynamic pricing rules                                                |
|  * Coupon validation                                                    |
|  * Discount calculation                                                 |
|  * Tax calculation                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.3 TECHNOLOGY CHOICES & RATIONALE

```
+-------------------------------------------------------------------------+
|                    DATABASE SELECTION                                   |
|                                                                         |
|  +----------------+-----------------+--------------------------------+  |
|  | Data Type      | Choice          | Why                            |  |
|  +----------------+-----------------+--------------------------------+  |
|  | Transactional  | PostgreSQL      | ACID for orders, payments      |  |
|  | (Orders,       |                 | Strong consistency required    |  |
|  |  Payments)     |                 | Complex queries, joins         |  |
|  +----------------+-----------------+--------------------------------+  |
|  | Shopping Cart  | Redis           | Fast read/write                |  |
|  |                |                 | TTL for cart expiration        |  |
|  |                |                 | Session affinity optional      |  |
|  +----------------+-----------------+--------------------------------+  |
|  | Inventory      | PostgreSQL +    | Strong consistency for stock   |  |
|  | (Critical)     | Redis cache     | Redis for fast availability    |  |
|  |                |                 | DB for source of truth         |  |
|  +----------------+-----------------+--------------------------------+  |
|  | Product Search | Elasticsearch   | Full-text search               |  |
|  |                |                 | Faceted filtering              |  |
|  |                |                 | Autocomplete                   |  |
|  +----------------+-----------------+--------------------------------+  |
|  | Product Catalog| PostgreSQL +    | Relational for categories      |  |
|  |                | Redis cache     | Heavy caching (rarely changes) |  |
|  +----------------+-----------------+--------------------------------+  |
|  | Analytics      | ClickHouse/     | Time-series aggregations       |  |
|  |                | Druid           | Real-time dashboards           |  |
|  +----------------+-----------------+--------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.4 SECURITY MODEL (AUTHENTICATION & AUTHORIZATION)

```
+-------------------------------------------------------------------------+
|                    ACCESS POLICY                                        |
|                                                                         |
|  +--------------------------------+------------+-------------------+    |
|  | Endpoint                       | Auth       | Notes             |    |
|  +--------------------------------+------------+-------------------+    |
|  | GET /api/products              | PUBLIC     | Browse catalog    |    |
|  | GET /api/search                | PUBLIC     | Search products   |    |
|  | GET /api/categories            | PUBLIC     | Category tree     |    |
|  +--------------------------------+------------+-------------------+    |
|  | POST /api/cart/items           | OPTIONAL   | Guest or user     |    |
|  | GET /api/cart                  | OPTIONAL   | Cart by ID/user   |    |
|  +--------------------------------+------------+-------------------+    |
|  | POST /api/checkout/initiate    | USER       | Requires login    |    |
|  | POST /api/checkout/pay         | USER       | Process payment   |    |
|  | GET /api/orders                | USER       | User's orders     |    |
|  | POST /api/orders/{id}/cancel   | USER       | Cancel own order  |    |
|  +--------------------------------+------------+-------------------+    |
|  | POST /api/admin/products       | ADMIN      | Add products      |    |
|  | PUT /api/admin/inventory       | ADMIN      | Update stock      |    |
|  | GET /api/admin/reports         | ADMIN      | Sales reports     |    |
|  +--------------------------------+------------+-------------------+    |
|  | POST /api/seller/products      | SELLER     | List products     |    |
|  | GET /api/seller/orders         | SELLER     | Seller's orders   |    |
|  +--------------------------------+------------+-------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.5 DATABASE-TO-SERVICE OWNERSHIP MAPPING

```
+-------------------------------------------------------------------------+
|                    SERVICE > DATABASE MAPPING                           |
|                                                                         |
|  USER SERVICE > User DB                                                 |
|  -------------------------                                              |
|  Tables: users, addresses, user_preferences                             |
|                                                                         |
|  PRODUCT SERVICE > Product DB                                           |
|  ----------------------------                                           |
|  Tables: products, categories, product_variants, product_images,        |
|          reviews, sellers                                               |
|                                                                         |
|  CART SERVICE > Redis + Cart DB                                         |
|  ------------------------------                                         |
|  Redis: Active carts (fast access)                                      |
|  DB: carts, cart_items (backup, analytics)                              |
|                                                                         |
|  INVENTORY SERVICE > Inventory DB                                       |
|  --------------------------------                                       |
|  Tables: inventory, inventory_reservations, warehouses                  |
|                                                                         |
|  ORDER SERVICE > Order DB                                               |
|  ------------------------                                               |
|  Tables: orders, order_items, order_status_history                      |
|                                                                         |
|  PAYMENT SERVICE > Payment DB                                           |
|  --------------------------                                             |
|  Tables: payments, refunds, payment_methods                             |
|                                                                         |
|  SEARCH SERVICE > Elasticsearch                                         |
|  ------------------------------                                         |
|  Indexes: products_index (denormalized)                                 |
|  Synced via CDC from Product DB                                         |
|                                                                         |
|  KEY PRINCIPLE: No cross-database foreign keys!                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 4: PRODUCT CATALOG & SEARCH

### 4.1 PRODUCT DATA MODEL

```
+-------------------------------------------------------------------------+
|                    PRODUCT HIERARCHY                                    |
|                                                                         |
|   CATEGORY (Electronics)                                                |
|     |                                                                   |
|     +-- SUB-CATEGORY (Mobile Phones)                                    |
|           |                                                             |
|           +-- PRODUCT (iPhone 15 Pro)                                   |
|                 |                                                       |
|                 +-- VARIANT (128GB, Blue)                               |
|                 |     +-- SKU: IPHONE15PRO-128-BLU                      |
|                 |                                                       |
|                 +-- VARIANT (256GB, Blue)                               |
|                 |     +-- SKU: IPHONE15PRO-256-BLU                      |
|                 |                                                       |
|                 +-- VARIANT (256GB, Black)                              |
|                       +-- SKU: IPHONE15PRO-256-BLK                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PRODUCT ATTRIBUTES:                                                    |
|  * Fixed: name, brand, description, base_price                          |
|  * Dynamic: attributes JSON (color, size, material, etc.)               |
|  * Computed: avg_rating, review_count, in_stock                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 4.2 SEARCH ARCHITECTURE (ELASTICSEARCH)

```
+-------------------------------------------------------------------------+
|                    SEARCH INDEX DESIGN                                  |
|                                                                         |
|  {                                                                      |
|    "index": "products",                                                 |
|    "mappings": {                                                        |
|      "properties": {                                                    |
|        "product_id": { "type": "keyword" },                             |
|        "name": {                                                        |
|          "type": "text",                                                |
|          "analyzer": "standard",                                        |
|          "fields": {                                                    |
|            "keyword": { "type": "keyword" },                            |
|            "suggest": { "type": "completion" }                          |
|          }                                                              |
|        },                                                               |
|        "description": { "type": "text" },                               |
|        "brand": { "type": "keyword" },                                  |
|        "category_path": { "type": "keyword" },                          |
|        "price": { "type": "float" },                                    |
|        "sale_price": { "type": "float" },                               |
|        "in_stock": { "type": "boolean" },                               |
|        "rating": { "type": "float" },                                   |
|        "review_count": { "type": "integer" },                           |
|        "attributes": { "type": "nested" },                              |
|        "created_at": { "type": "date" }                                 |
|      }                                                                  |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

DATA SYNC (PostgreSQL > Elasticsearch):

```
+-------------------------------------------------------------------------+
|                    CDC PIPELINE                                         |
|                                                                         |
|  PostgreSQL --> Debezium --> Kafka --> ES Connector --> Elasticsearch   |
|  (Product DB)   (CDC)       (Stream)   (Consumer)       (Search)        |
|                                                                         |
|  FLOW:                                                                  |
|  1. Product inserted/updated in PostgreSQL                              |
|  2. Debezium captures WAL changes                                       |
|  3. Change event published to Kafka topic                               |
|  4. ES Connector consumes and indexes                                   |
|  5. Search index updated (< 5 seconds delay)                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

**CDC SEQUENCE DIAGRAM:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Admin       Product     PostgreSQL    Debezium    Kafka       ES       |
|   |          Service        |            |          |          |        |
|   |            |            |            |          |          |        |
|   |--Update --->           |            |          |          |         |
|   |  product   |            |            |          |          |        |
|   |            |--INSERT --->           |          |          |         |
|   |            |            |            |          |          |        |
|   |            |--COMMIT---->           |          |          |         |
|   |            |            |            |          |          |        |
|   |            |            |--WAL ------>          |          |        |
|   |            |            |  change    |          |          |        |
|   |            |            |            |          |          |        |
|   |            |            |            |--Publish-->         |        |
|   |            |            |            |  event   |          |        |
|   |            |            |            |          |          |        |
|   |            |            |            |          |--Index -->        |
|   |            |            |            |          |  update  |        |
|   |            |            |            |          |          |        |
|   |            |            |            |          |          |  Done  |
|   |            |            |            |          |          |        |
|                                                                         |
|  Total latency: < 5 seconds from DB write to searchable                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

**PRODUCT SEARCH SEQUENCE DIAGRAM:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  User       Frontend      API GW      Search Svc   Elasticsearch        |
|   |           |             |            |              |               |
|   |--Type ---->            |            |              |                |
|   |  "laptop" |            |            |              |                |
|   |           |            |            |              |                |
|   |           |-/suggest--->           |              |                 |
|   |           |  ?q=lap    |            |              |                |
|   |           |            |--Suggest -->              |                |
|   |           |            |            |--Completion-->                |
|   |           |            |            |  query       |                |
|   |           |            |            |<-laptop,     |                |
|   |           |            |            |  laptop bag..|                |
|   |           |            |            |              |                |
|   |<-Autocomplete suggestions----------|              |                 |
|   |                        |            |              |                |
|   |--Submit -->           |            |              |                 |
|   |  search   |            |            |              |                |
|   |           |-/search --->           |              |                 |
|   |           |  ?q=laptop |            |              |                |
|   |           |            |--Search --->              |                |
|   |           |            |            |--Multi-match-->               |
|   |           |            |            |  + aggregations               |
|   |           |            |            |              |                |
|   |           |            |            |<-Results +   |                |
|   |           |            |            |  facets      |                |
|   |           |            |            |              |                |
|   |<-Products + filters----------------|              |                 |
|   |  (Brand: Apple 45,                 |              |                 |
|   |   Dell 38, HP 52...)               |              |                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 4.3 FACETED SEARCH & FILTERS

```
+-------------------------------------------------------------------------+
|                    FACETED SEARCH EXAMPLE                               |
|                                                                         |
|  Search: "laptop"                                                       |
|                                                                         |
|  FILTERS (with counts):                                                 |
|  +-----------------------------------------------------------------+    |
|  | Brand                    | Price Range                          |    |
|  | o Apple (45)            | o Under $500 (23)                    |     |
|  | o Dell (38)             | o $500 - $1000 (67)                  |     |
|  | o HP (52)               | o $1000 - $1500 (45)                 |     |
|  | o Lenovo (41)           | o Over $1500 (15)                    |     |
|  |                          |                                      |    |
|  | RAM                      | Customer Rating                      |    |
|  | o 8 GB (78)             | o 4* & up (120)                      |     |
|  | o 16 GB (56)            | o 3* & up (145)                      |     |
|  | o 32 GB (16)            |                                      |     |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  ELASTICSEARCH AGGREGATION QUERY:                                       |
|  {                                                                      |
|    "aggs": {                                                            |
|      "brands": {                                                        |
|        "terms": { "field": "brand", "size": 20 }                        |
|      },                                                                 |
|      "price_ranges": {                                                  |
|        "range": {                                                       |
|          "field": "price",                                              |
|          "ranges": [                                                    |
|            { "to": 500 },                                               |
|            { "from": 500, "to": 1000 },                                 |
|            { "from": 1000, "to": 1500 },                                |
|            { "from": 1500 }                                             |
|          ]                                                              |
|        }                                                                |
|      }                                                                  |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 5: SHOPPING CART

### 5.1 CART ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                    CART DESIGN DECISIONS                                |
|                                                                         |
|  GUEST CART vs USER CART:                                               |
|  -------------------------                                              |
|  * Guest: Cart ID stored in cookie/localStorage                         |
|  * User: Cart linked to user_id                                         |
|  * On login: Merge guest cart into user cart                            |
|                                                                         |
|  STORAGE OPTIONS:                                                       |
|  ------------------                                                     |
|  Option A: Database only                                                |
|  * Persistent, survives server restarts                                 |
|  * Slower reads/writes                                                  |
|  * Better for analytics                                                 |
|                                                                         |
|  Option B: Redis only                                                   |
|  * Fast reads/writes (< 5ms)                                            |
|  * Lost on Redis failure (acceptable?)                                  |
|  * Set TTL for auto-cleanup                                             |
|                                                                         |
|  Option C: Redis + Database (RECOMMENDED)                               |
|  * Redis for hot path (reads/writes)                                    |
|  * Database as backup, for analytics                                    |
|  * Async sync from Redis > DB                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 5.2 CART STORAGE IN REDIS

```
+-------------------------------------------------------------------------+
|                    REDIS CART STRUCTURE                                 |
|                                                                         |
|  KEY: cart:{cart_id}                                                    |
|  TYPE: Hash                                                             |
|  TTL: 30 days (for guest), infinite (for user)                          |
|                                                                         |
|  HSET cart:abc123                                                       |
|      user_id "user_456"                                                 |
|      created_at "2024-12-19T10:00:00Z"                                  |
|      updated_at "2024-12-19T10:30:00Z"                                  |
|      currency "USD"                                                     |
|                                                                         |
|  KEY: cart:{cart_id}:items                                              |
|  TYPE: Hash (product_id:variant_id > JSON item)                         |
|                                                                         |
|  HSET cart:abc123:items                                                 |
|      "prod_123:var_001" '{"qty":2,"price":99.99,"added":"..."}'         |
|      "prod_456:var_002" '{"qty":1,"price":49.99,"added":"..."}'         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  OPERATIONS:                                                            |
|  ------------                                                           |
|  Add item:     HSET cart:{id}:items {key} {json}                        |
|  Update qty:   HSET cart:{id}:items {key} {updated_json}                |
|  Remove item:  HDEL cart:{id}:items {key}                               |
|  Get cart:     HGETALL cart:{id}:items                                  |
|  Clear cart:   DEL cart:{id} cart:{id}:items                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

**ADD TO CART SEQUENCE DIAGRAM:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  User       Frontend      API GW       Cart Svc      Redis       DB     |
|   |           |             |            |            |          |      |
|   |--Add to -->            |            |            |          |       |
|   |  cart     |            |            |            |          |       |
|   |           |--POST ----->           |            |          |        |
|   |           |  /cart/items           |            |          |        |
|   |           |  {productId,           |            |          |        |
|   |           |   variantId, qty}      |            |          |        |
|   |           |            |            |            |          |       |
|   |           |            |--Add item-->           |          |        |
|   |           |            |            |            |          |       |
|   |           |            |            |--Validate product------>      |
|   |           |            |            |  (exists, in stock)   |       |
|   |           |            |            |<-Valid-----|          |       |
|   |           |            |            |            |          |       |
|   |           |            |            |--HGET ----->          |       |
|   |           |            |            |  cart:id:items        |       |
|   |           |            |            |<-Current items-       |       |
|   |           |            |            |            |          |       |
|   |           |            |            |  (merge if exists)    |       |
|   |           |            |            |            |          |       |
|   |           |            |            |--HSET ----->          |       |
|   |           |            |            |  cart:id:items        |       |
|   |           |            |            |  {key: json}          |       |
|   |           |            |            |            |          |       |
|   |           |            |            |--HSET ----->          |       |
|   |           |            |            |  cart:id              |       |
|   |           |            |            |  updated_at           |       |
|   |           |            |            |            |          |       |
|   |           |            |            |--ASYNC ---------------->      |
|   |           |            |            |  sync to DB (analytics)       |
|   |           |            |            |            |          |       |
|   |           |            |<-Updated cart--         |          |       |
|   |           |<-200 + cart total------|            |          |        |
|   |           |                         |            |          |       |
|   |<-Cart badge updated--|             |            |          |        |
|   |  "Cart (3)"         |             |            |          |         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 5.3 CART MERGE (GUEST > USER)

```
+-------------------------------------------------------------------------+
|                    MERGE SCENARIOS                                      |
|                                                                         |
|  SCENARIO 1: User has no existing cart                                  |
|  -------------------------------------                                  |
|  * Simply associate guest cart with user_id                             |
|  * Update cart metadata                                                 |
|                                                                         |
|  SCENARIO 2: User has existing cart                                     |
|  ----------------------------------                                     |
|  * Merge items from both carts                                          |
|  * Same product? Sum quantities (respect max limit)                     |
|  * Different products? Add all                                          |
|  * Delete guest cart after merge                                        |
|                                                                         |
|  MERGE ALGORITHM:                                                       |
|  -----------------                                                      |
|  1. Get user's existing cart (if any)                                   |
|  2. Get guest cart items                                                |
|  3. For each guest item:                                                |
|     - If exists in user cart: qty = user_qty + guest_qty                |
|     - If new: add to user cart                                          |
|  4. Delete guest cart                                                   |
|  5. Update cart totals                                                  |
|                                                                         |
|  EDGE CASES:                                                            |
|  ------------                                                           |
|  * Product out of stock since added? Remove from cart, notify user      |
|  * Price changed? Update to current price, show warning                 |
|  * Max quantity exceeded? Cap at max, notify user                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

CART MERGE SEQUENCE DIAGRAM (Guest Login):

```
+-------------------------------------------------------------------------+
|                                                                         |
|  User       Frontend      Auth Svc      Cart Svc       Redis            |
|   |           |             |             |              |              |
|   |--Login --->            |             |              |               |
|   |  (with guest_cart_id)  |             |              |               |
|   |           |            |             |              |               |
|   |           |--Authenticate----------->|              |               |
|   |           |            |             |              |               |
|   |           |            |<-JWT + user_id-            |               |
|   |           |            |             |              |               |
|   |           |--Merge cart------------->|              |               |
|   |           |  (guest_id, user_id)     |              |               |
|   |           |            |             |              |               |
|   |           |            |             |--HGETALL ---->               |
|   |           |            |             |  cart:guest:items            |
|   |           |            |             |<-Guest items-|               |
|   |           |            |             |              |               |
|   |           |            |             |--HGETALL ---->               |
|   |           |            |             |  cart:user:items             |
|   |           |            |             |<-User items--|               |
|   |           |            |             |              |               |
|   |           |            |             |  +---------------------+     |
|   |           |            |             |  | MERGE LOGIC:        |     |
|   |           |            |             |  | * Sum quantities    |     |
|   |           |            |             |  | * Check max limits  |     |
|   |           |            |             |  | * Validate products |     |
|   |           |            |             |  +---------------------+     |
|   |           |            |             |              |               |
|   |           |            |             |--HSET (merged)-->            |
|   |           |            |             |  cart:user:items             |
|   |           |            |             |              |               |
|   |           |            |             |--DEL -------->               |
|   |           |            |             |  cart:guest:*                |
|   |           |            |             |              |               |
|   |           |            |             |<-Merged cart-|               |
|   |           |<-Logged in + cart merged-|              |               |
|   |           |                          |              |               |
|   |<-Dashboard + "3 items in cart"------|              |                |
|   |                                      |              |               |
|   |  If conflicts:                       |              |               |
|   |  "We updated some items in your cart"|              |               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 5.4 PRICE & AVAILABILITY SYNC

```
+-------------------------------------------------------------------------+
|                    WHEN TO VALIDATE CART                                |
|                                                                         |
|  OPTION A: On every cart view (Real-time)                               |
|  -----------------------------------------                              |
|  Pros: Always accurate                                                  |
|  Cons: Slow, extra DB calls                                             |
|                                                                         |
|  OPTION B: On checkout initiation (Lazy)                                |
|  ------------------------------------------                             |
|  Pros: Fast cart views                                                  |
|  Cons: Surprise at checkout ("price changed!")                          |
|                                                                         |
|  OPTION C: Hybrid (RECOMMENDED)                                         |
|  ---------------------------------                                      |
|  * Store price_at_addition in cart                                      |
|  * On cart view: Show stored price + "prices may vary"                  |
|  * On checkout: Full validation, show any changes prominently           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  VALIDATION CHECKS AT CHECKOUT:                                         |
|  ---------------------------------                                      |
|  o Product still exists and is active?                                  |
|  o Variant still available?                                             |
|  o Sufficient inventory?                                                |
|  o Price changed? (show warning)                                        |
|  o Quantity within limits?                                              |
|  o Shipping available to address?                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 6: INVENTORY MANAGEMENT (THE HARD PROBLEM)

### 6.1 INVENTORY CHALLENGES

```
+-------------------------------------------------------------------------+
|                    THE OVERSELLING PROBLEM                              |
|                                                                         |
|  TIMELINE:                                                              |
|  ---------                                                              |
|  Stock: 100 units                                                       |
|                                                                         |
|  T1: User A checks stock > 100 available                                |
|  T2: User B checks stock > 100 available                                |
|  T3: User A reserves 100 units                                          |
|  T4: User B reserves 100 units (PROBLEM!)                               |
|                                                                         |
|  Without proper locking, both reservations succeed!                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION REQUIREMENTS:                                                 |
|  -----------------------                                                |
|  1. Atomic check-and-reserve                                            |
|  2. Handle concurrent requests                                          |
|  3. Release failed/expired reservations                                 |
|  4. Scale across multiple servers                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.2 INVENTORY RESERVATION STRATEGIES

```
+-------------------------------------------------------------------------+
|                    STRATEGY 1: RESERVE AT ADD-TO-CART                   |
|                                                                         |
|  User adds to cart > Immediately reserve inventory                      |
|                                                                         |
|  PROS:                                                                  |
|  * Zero overselling possible                                            |
|  * User knows immediately if out of stock                               |
|                                                                         |
|  CONS:                                                                  |
|  * 70% cart abandonment = 70% wasted reservations                       |
|  * Users "hoard" inventory without buying                               |
|  * Need short TTL (5-10 min) and refresh mechanism                      |
|  * High contention on popular items                                     |
|                                                                         |
|  USE CASE: Very limited stock (flash sales, limited editions)           |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    STRATEGY 2: RESERVE AT CHECKOUT                      |
|                                                                         |
|  User clicks "Checkout" > Reserve inventory for X minutes               |
|                                                                         |
|  PROS:                                                                  |
|  * Better inventory utilization                                         |
|  * Only serious buyers get reservation                                  |
|  * Reasonable TTL (10-15 min for payment)                               |
|                                                                         |
|  CONS:                                                                  |
|  * User might get "out of stock" at checkout                            |
|  * Still need TTL handling                                              |
|                                                                         |
|  USE CASE: Standard e-commerce (Amazon, Flipkart)                       |
|  THIS IS THE RECOMMENDED APPROACH                                       |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    STRATEGY 3: RESERVE AT PAYMENT (OPTIMISTIC)          |
|                                                                         |
|  No reservation until payment succeeds > Then deduct stock              |
|                                                                         |
|  PROS:                                                                  |
|  * Maximum inventory availability                                       |
|  * No TTL management needed                                             |
|                                                                         |
|  CONS:                                                                  |
|  * Risk of overselling during payment processing                        |
|  * Need to handle "payment success but no stock" scenario               |
|  * Customer charged but order cancelled = bad UX                        |
|                                                                         |
|  USE CASE: High-volume items with ample stock                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.3 DISTRIBUTED LOCKING FOR INVENTORY

APPROACH 1: DATABASE OPTIMISTIC LOCKING

```
+-------------------------------------------------------------------------+
|                    OPTIMISTIC LOCKING WITH VERSION                      |
|                                                                         |
|  -- Reserve inventory with version check                                |
|  UPDATE inventory                                                       |
|  SET                                                                    |
|      quantity_reserved = quantity_reserved + :qty,                      |
|      version = version + 1                                              |
|  WHERE                                                                  |
|      product_id = :product_id                                           |
|      AND version = :expected_version                                    |
|      AND (quantity_total - quantity_reserved) >= :qty;                  |
|                                                                         |
|  -- Check affected rows                                                 |
|  IF affected_rows = 0:                                                  |
|      -- Either version mismatch (concurrent update)                     |
|      -- Or insufficient stock                                           |
|      RETRY or FAIL                                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROS:                                                                  |
|  * Simple, works with standard SQL                                      |
|  * No external dependencies                                             |
|  * Database handles atomicity                                           |
|                                                                         |
|  CONS:                                                                  |
|  * Retries needed on version conflict                                   |
|  * High contention = high retry rate                                    |
|  * Thundering herd on popular items                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

APPROACH 2: REDIS DISTRIBUTED LOCK

```
+-------------------------------------------------------------------------+
|                    REDIS INVENTORY RESERVATION                          |
|                                                                         |
|  ARCHITECTURE:                                                          |
|  -------------                                                          |
|  * Redis: Fast availability check + atomic reservation                  |
|  * PostgreSQL: Source of truth, final confirmation                      |
|                                                                         |
|  REDIS KEYS:                                                            |
|  ------------                                                           |
|  inventory:{product_id}:available = 100      (available count)          |
|  inventory:{product_id}:reserved  = Hash of reservation_id > qty        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  RESERVATION (Lua Script for atomicity):                                |
|  -----------------------------------------                              |
|                                                                         |
|  local available = tonumber(redis.call('GET', KEYS[1])) or 0            |
|  local qty = tonumber(ARGV[1])                                          |
|  local reservation_id = ARGV[2]                                         |
|  local ttl = tonumber(ARGV[3])                                          |
|                                                                         |
|  if available >= qty then                                               |
|      redis.call('DECRBY', KEYS[1], qty)                                 |
|      redis.call('HSET', KEYS[2], reservation_id, qty)                   |
|      redis.call('EXPIRE', KEYS[2], ttl)                                 |
|      return 1  -- Success                                               |
|  else                                                                   |
|      return 0  -- Insufficient stock                                    |
|  end                                                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  RELEASE RESERVATION:                                                   |
|  ---------------------                                                  |
|                                                                         |
|  local qty = redis.call('HGET', KEYS[2], ARGV[1])                       |
|  if qty then                                                            |
|      redis.call('INCRBY', KEYS[1], qty)                                 |
|      redis.call('HDEL', KEYS[2], ARGV[1])                               |
|      return 1                                                           |
|  end                                                                    |
|  return 0                                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.4 COMPLETE INVENTORY FLOW

```
+-------------------------------------------------------------------------+
|                    CHECKOUT > ORDER INVENTORY FLOW                      |
|                                                                         |
|  User         Cart        Inventory       Payment       Order           |
|    |           |            |               |            |              |
|    |--Checkout-->           |               |            |              |
|    |           |            |               |            |              |
|    |           |--Get items-|               |            |              |
|    |           |            |               |            |              |
|    |           |--Reserve--->               |            |              |
|    |           |   (Lua)    |               |            |              |
|    |           |            |               |            |              |
|    |           |  +---------+--------+     |            |               |
|    |           |  | For each item:   |     |            |               |
|    |           |  | Check available  |     |            |               |
|    |           |  | Decrement count  |     |            |               |
|    |           |  | Store reservation|     |            |               |
|    |           |  +---------+--------+     |            |               |
|    |           |            |               |            |              |
|    |           |<-Reserved (15 min)-       |            |               |
|    |<-Checkout page, timer--|               |            |              |
|    |           |            |               |            |              |
|    |--Pay---------------------------------->            |               |
|    |           |            |               |            |              |
|    |           |            |  +-----------+-----+      |               |
|    |           |            |  |Process payment  |      |               |
|    |           |            |  +-----------+-----+      |               |
|    |           |            |              |            |               |
|    |           |            |<-Success-----|            |               |
|    |           |            |               |            |              |
|    |           |            |--Confirm reservation------>               |
|    |           |            |   (DB update)             |               |
|    |           |            |               |            |              |
|    |           |            |              |<-Order created             |
|    |           |            |               |            |              |
|    |<-Order confirmation--------------------------------|               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  KEY POINTS:                                                            |
|  ------------                                                           |
|  1. SOFT RESERVATION in Redis (reversible)                              |
|  2. Timer starts - user has 15 minutes                                  |
|  3. Payment processed                                                   |
|  4. HARD CONFIRMATION in PostgreSQL (permanent)                         |
|  5. Redis reservation released (stock already deducted in DB)           |
|                                                                         |
+-------------------------------------------------------------------------+
```

**RESERVATION EXPIRATION HANDLING:**

```
+-------------------------------------------------------------------------+
|                    EXPIRATION CLEANUP                                   |
|                                                                         |
|  OPTION 1: TTL-based (Redis handles it)                                 |
|  -----------------------------------------                              |
|  * Set TTL on reservation hash                                          |
|  * Problem: Can't increment available count on expiry                   |
|                                                                         |
|  OPTION 2: Background job (RECOMMENDED)                                 |
|  ------------------------------------------                             |
|  * Scheduler runs every 30 seconds                                      |
|  * Find expired reservations                                            |
|  * Release each: increment available, delete reservation                |
|                                                                         |
|  @Scheduled(fixedRate = 30000)                                          |
|  public void cleanupExpiredReservations() {                             |
|      List<Reservation> expired = findExpired(Instant.now());            |
|      for (Reservation r : expired) {                                    |
|          try {                                                          |
|              releaseReservation(r.getProductId(), r.getId());           |
|          } catch (Exception e) {                                        |
|              log.error("Failed to release: " + r.getId(), e);           |
|          }                                                              |
|      }                                                                  |
|  }                                                                      |
|                                                                         |
|  OPTION 3: Lazy cleanup on next access                                  |
|  -----------------------------------------                              |
|  * Check reservation validity on read                                   |
|  * Release if expired                                                   |
|  * Simpler but may have stale count                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 7: CHECKOUT & ORDER PROCESSING

### 7.1 CHECKOUT FLOW

```
+-------------------------------------------------------------------------+
|                    CHECKOUT STATE MACHINE                               |
|                                                                         |
|        +------------+                                                   |
|        |   CART     |                                                   |
|        +-----+------+                                                   |
|              | User clicks "Checkout"                                   |
|              v                                                          |
|        +------------+                                                   |
|        | VALIDATING | <--- Check stock, prices, shipping                |
|        +-----+------+                                                   |
|              |                                                          |
|     +--------+--------+                                                 |
|     |        |        |                                                 |
|     v        v        v                                                 |
|  +------+ +------+ +-----------+                                        |
|  |FAILED| |ERROR | | RESERVED  | <--- Inventory locked                  |
|  |(OOS) | |      | |           |      Timer: 15 min                     |
|  +------+ +------+ +-----+-----+                                        |
|                          |                                              |
|                          | User submits payment                         |
|                          v                                              |
|                    +------------+                                       |
|                    |  PAYING    |                                       |
|                    +-----+------+                                       |
|                          |                                              |
|              +-----------+-----------+                                  |
|              |           |           |                                  |
|              v           v           v                                  |
|        +----------+ +--------+ +-----------+                            |
|        | PAYMENT  | |TIMEOUT | | CONFIRMED |                            |
|        | FAILED   | |        | |           |                            |
|        +----+-----+ +---+----+ +-----------+                            |
|             |           |                                               |
|             +-----+-----+                                               |
|                   | Release reservation                                 |
|                   v                                                     |
|             +----------+                                                |
|             | RELEASED |                                                |
|             +----------+                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

**CHECKOUT SEQUENCE DIAGRAM:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  User        Frontend      API GW      Cart       Inventory    Pricing  |
|   |            |             |          |            |           |      |
|   |--Click ---->            |          |            |           |       |
|   |  Checkout  |            |          |            |           |       |
|   |            |--Checkout-->          |            |           |       |
|   |            |  Request   |          |            |           |       |
|   |            |            |--Get ---->            |           |       |
|   |            |            |  Cart    |            |           |       |
|   |            |            |<-Items---|            |           |       |
|   |            |            |          |            |           |       |
|   |            |            |----------Reserve------>           |       |
|   |            |            |          |            |           |       |
|   |            |            |          |  +---------+--------+  |       |
|   |            |            |          |  | Lua Script:      |  |       |
|   |            |            |          |  | Check available  |  |       |
|   |            |            |          |  | Decrement count  |  |       |
|   |            |            |          |  | Store reservation|  |       |
|   |            |            |          |  +---------+--------+  |       |
|   |            |            |          |            |           |       |
|   |            |            |<------Reserved (15 min)-----------|       |
|   |            |            |          |            |           |       |
|   |            |            |----------Calculate total---------->       |
|   |            |            |<---------Subtotal + tax + ship----|       |
|   |            |            |          |            |           |       |
|   |            |<-Checkout page (items, total, timer)--         |       |
|   |<-Show payment form------|          |            |           |       |
|   |                         |          |            |           |       |
|   |  Timer: 14:59...        |          |            |           |       |
|   |                         |          |            |           |       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.2 PAYMENT INTEGRATION

```
+-------------------------------------------------------------------------+
|                    PAYMENT FLOW                                         |
|                                                                         |
|  STEP 1: CREATE PAYMENT INTENT                                          |
|  ------------------------------                                         |
|  * Generate idempotency key                                             |
|  * Create payment record (status: INITIATED)                            |
|  * Call payment gateway to create intent                                |
|                                                                         |
|  STEP 2: CAPTURE PAYMENT                                                |
|  ------------------------                                               |
|  * User completes payment on gateway                                    |
|  * Gateway sends webhook (or we poll)                                   |
|  * Verify payment amount matches order                                  |
|                                                                         |
|  STEP 3: CONFIRM ORDER                                                  |
|  ----------------------                                                 |
|  * Update payment status: CAPTURED                                      |
|  * Confirm inventory reservation                                        |
|  * Create order (status: CONFIRMED)                                     |
|  * Send confirmation notification                                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  IDEMPOTENCY:                                                           |
|  ------------                                                           |
|  * Generate key: checkout_{checkoutId}_{timestamp}                      |
|  * Store in payment record                                              |
|  * Gateway uses key to dedupe requests                                  |
|  * Safe to retry on timeout                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

**PAYMENT SEQUENCE DIAGRAM:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  User       Frontend     Order Svc    Payment Svc   Stripe      DB      |
|   |           |             |             |           |          |      |
|   |--Submit -->            |             |           |          |       |
|   |  payment  |            |             |           |          |       |
|   |           |--Pay ------>            |           |          |        |
|   |           |  request   |             |           |          |       |
|   |           |            |--Verify ---->           |          |       |
|   |           |            |  reservation|           |          |       |
|   |           |            |<-Valid -----|           |          |       |
|   |           |            |             |           |          |       |
|   |           |            |--Process --->           |          |       |
|   |           |            |  payment    |           |          |       |
|   |           |            |             |           |          |       |
|   |           |            |             |--Create -->          |       |
|   |           |            |             |  payment  |          |       |
|   |           |            |             |  record   |--INSERT-->       |
|   |           |            |             |           |          |       |
|   |           |            |             |--Charge -->          |       |
|   |           |            |             |  (idempotency key)   |       |
|   |           |            |             |           |          |       |
|   |           |            |             |<-Success -|          |       |
|   |           |            |             |  txn_id   |          |       |
|   |           |            |             |           |          |       |
|   |           |            |             |--UPDATE -------------->      |
|   |           |            |             |  CAPTURED |          |       |
|   |           |            |             |           |          |       |
|   |           |            |<-Payment ---|           |          |       |
|   |           |            |  success    |           |          |       |
|   |           |            |             |           |          |       |
|   |           |            |--Create order---------------------->       |
|   |           |            |--Confirm inventory----------------->       |
|   |           |            |--Publish OrderCreated event        |       |
|   |           |            |             |           |          |       |
|   |           |<-Order ----|             |           |          |       |
|   |           |  confirmed |             |           |          |       |
|   |<-Success -|            |             |           |          |       |
|   |  page     |            |             |           |          |       |
|                                                                         |
+-------------------------------------------------------------------------+
```

**PAYMENT FAILURE SEQUENCE:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  User       Frontend     Order Svc    Payment Svc   Stripe    Inventory |
|   |           |             |             |           |          |      |
|   |--Submit -->            |             |           |          |       |
|   |  payment  |            |             |           |          |       |
|   |           |--Pay ------>            |           |          |        |
|   |           |            |--Process --->           |          |       |
|   |           |            |             |--Charge -->          |       |
|   |           |            |             |           |          |       |
|   |           |            |             |<-DECLINED-|          |       |
|   |           |            |             |  insufficient_funds  |       |
|   |           |            |             |           |          |       |
|   |           |            |<-Payment ---|           |          |       |
|   |           |            |  FAILED     |           |          |       |
|   |           |            |             |           |          |       |
|   |           |            |-------------Release reservation---->       |
|   |           |            |             |           |          |       |
|   |           |            |             |           |<-Released|       |
|   |           |            |             |           |          |       |
|   |           |<-Error ----|             |           |          |       |
|   |           |  message   |             |           |          |       |
|   |<-"Payment-|            |             |           |          |       |
|   |  failed"  |            |             |           |          |       |
|   |           |            |             |           |          |       |
|   |  (User can retry with different card)           |          |        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.3 ORDER STATE MACHINE

```
+-------------------------------------------------------------------------+
|                    ORDER LIFECYCLE                                      |
|                                                                         |
|    +---------+                                                          |
|    | PENDING | <--- Order created, awaiting payment                     |
|    +----+----+                                                          |
|         |                                                               |
|    +----+----+                                                          |
|    |         |                                                          |
|    v         v                                                          |
| +------+ +-----------+                                                  |
| |FAILED| | CONFIRMED | <--- Payment success                             |
| +------+ +-----+-----+                                                  |
|                |                                                        |
|                v                                                        |
|          +-----------+                                                  |
|          |PROCESSING | <--- Warehouse picking/packing                   |
|          +-----+-----+                                                  |
|                |                                                        |
|                v                                                        |
|          +-----------+                                                  |
|          |  SHIPPED  | <--- Handed to courier                           |
|          +-----+-----+                                                  |
|                |                                                        |
|       +--------+--------+                                               |
|       |        |        |                                               |
|       v        v        v                                               |
|  +--------++---------++------------+                                    |
|  |RETURNED||DELIVERED||  CANCELLED |                                    |
|  +--------++----+----++------------+                                    |
|                 |                                                       |
|                 v                                                       |
|           +----------+                                                  |
|           | REFUNDED | (if return approved)                             |
|           +----------+                                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  VALID TRANSITIONS:                                                     |
|  * PENDING > CONFIRMED, FAILED, CANCELLED                               |
|  * CONFIRMED > PROCESSING, CANCELLED                                    |
|  * PROCESSING > SHIPPED, CANCELLED                                      |
|  * SHIPPED > DELIVERED, RETURNED                                        |
|  * DELIVERED > RETURNED (within return window)                          |
|  * RETURNED > REFUNDED                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

**ORDER RETURN & REFUND SEQUENCE DIAGRAM:**

```
+---------------------------------------------------------------------------+
|                                                                           |
|  User       Frontend     Order Svc    Inventory   Payment    Notify       |
|   |           |            |            |           |          |          |
|   |--Request ->           |            |           |          |           |
|   |  return   |            |            |           |          |          |
|   |           |--POST ----->           |           |          |           |
|   |           |  /orders/{id}/return   |           |          |           |
|   |           |            |            |           |          |          |
|   |           |            |--Validate--|           |          |          |
|   |           |            |  order is  |           |          |          |
|   |           |            |  DELIVERED |           |          |          |
|   |           |            |            |           |          |          |
|   |           |            |--Check ----|           |          |          |
|   |           |            |  return    |           |          |          |
|   |           |            |  window    |           |          |          |
|   |           |            |            |           |          |          |
|   |           |            |--Create ---|           |          |          |
|   |           |            |  return    |           |          |          |
|   |           |            |  request   |           |          |          |
|   |           |            |  (PENDING) |           |          |          |
|   |           |            |            |           |          |          |
|   |           |<-Return ID + instructions--         |          |          |
|   |<-"Ship item back to..."--|          |           |          |          |
|   |                         |            |           |          |         |
|  ===============================================================          |
|  |  WAREHOUSE RECEIVES ITEM, INSPECTS, APPROVES RETURN       |            |
|  ===============================================================          |
|                             |            |           |          |         |
|       (Admin)--Approve ----->           |           |          |          |
|                return       |            |           |          |         |
|                             |            |           |          |         |
|                             |--Update --->           |          |         |
|                             |  order:    |           |          |         |
|                             |  RETURNED  |           |          |         |
|                             |            |           |          |         |
|                             |--Restore -->           |          |         |
|                             |  inventory |           |          |         |
|                             |            |--INCREMENT |          |        |
|                             |            |  stock     |          |        |
|                             |            |           |          |         |
|                             |-----------Initiate refund---->    |         |
|                             |            |           |          |         |
|                             |            |           |--Refund  |         |
|                             |            |           |  to      |         |
|                             |            |           |  gateway |         |
|                             |            |           |          |         |
|                             |<----------Refund success----|    |          |
|                             |            |           |          |         |
|                             |--Update order: REFUNDED|          |         |
|                             |            |           |          |         |
|                             |--------------------------Notify -->         |
|                             |            |           |          |         |
|   |<-"Refund of $XX processed"-----------------------|   Email  |         |
|   |  (3-5 business days)    |           |           |          |          |
|                                                                           |
+---------------------------------------------------------------------------+
```

### 7.4 SAGA PATTERN FOR DISTRIBUTED TRANSACTIONS

```
+-------------------------------------------------------------------------+
|                    ORDER SAGA (ORCHESTRATION)                           |
|                                                                         |
|  Orchestrator (Order Service) coordinates:                              |
|                                                                         |
|  +---------------------------------------------------------------+      |
|  |                      HAPPY PATH                               |      |
|  |                                                               |      |
|  |  1. Reserve inventory     -------->  Inventory Service       |       |
|  |  2. Process payment       -------->  Payment Service         |       |
|  |  3. Create order          -------->  Order Service           |       |
|  |  4. Confirm inventory     -------->  Inventory Service       |       |
|  |  5. Send notification     -------->  Notification Service    |       |
|  |  6. Clear cart            -------->  Cart Service            |       |
|  |                                                               |      |
|  +---------------------------------------------------------------+      |
|                                                                         |
|  +---------------------------------------------------------------+      |
|  |                    COMPENSATION (Payment Fails)               |      |
|  |                                                               |      |
|  |  1. Reserve inventory     Y Success                         |        |
|  |  2. Process payment       X FAILED                          |        |
|  |                                                               |      |
|  |  COMPENSATE:                                                 |       |
|  |  > Release inventory reservation                             |       |
|  |  > Return error to user                                     |        |
|  |                                                               |      |
|  +---------------------------------------------------------------+      |
|                                                                         |
|  +---------------------------------------------------------------+      |
|  |              COMPENSATION (Order Creation Fails)              |      |
|  |                                                               |      |
|  |  1. Reserve inventory     Y Success                         |        |
|  |  2. Process payment       Y Success                         |        |
|  |  3. Create order          X FAILED                          |        |
|  |                                                               |      |
|  |  COMPENSATE:                                                 |       |
|  |  > Refund payment                                           |        |
|  |  > Release inventory reservation                             |       |
|  |  > Notify user: "Sorry, refund initiated"                  |         |
|  |                                                               |      |
|  +---------------------------------------------------------------+      |
|                                                                         |
+-------------------------------------------------------------------------+
```

SAGA ORCHESTRATION SEQUENCE DIAGRAM (Happy Path):

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Orchestrator    Inventory     Payment      Order       Notification    |
|  (Order Svc)      Service      Service     Service       Service        |
|       |             |            |           |              |           |
|       |--Reserve---->           |           |              |            |
|       |  inventory  |            |           |              |           |
|       |             |            |           |              |           |
|       |<-Reserved---|           |           |              |            |
|       |  (sagaId)   |            |           |              |           |
|       |             |            |           |              |           |
|       |-------------Process----->           |              |            |
|       |             |  payment   |           |              |           |
|       |             |            |           |              |           |
|       |<------------Success-----|           |              |            |
|       |             |  (paymentId)          |              |            |
|       |             |            |           |              |           |
|       |-------------------------Create------>              |            |
|       |             |            |  order    |              |           |
|       |             |            |           |              |           |
|       |<------------------------Created-----|              |            |
|       |             |            |  (orderId)|              |           |
|       |             |            |           |              |           |
|       |--Confirm---->           |           |              |            |
|       |  inventory  |            |           |              |           |
|       |             |            |           |              |           |
|       |<-Confirmed--|           |           |              |            |
|       |             |            |           |              |           |
|       |-------------------------------------Send confirmation-->        |
|       |             |            |           |              |           |
|       |             |            |           |              | Email     |
|       |             |            |           |              | sent      |
|       |                                                                 |
|       |  SAGA COMPLETED Y                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

SAGA COMPENSATION SEQUENCE DIAGRAM (Payment Fails):

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Orchestrator    Inventory     Payment      Order       Notification    |
|  (Order Svc)      Service      Service     Service       Service        |
|       |             |            |           |              |           |
|       |--Reserve---->           |           |              |            |
|       |  inventory  |            |           |              |           |
|       |<-Reserved---|           |           |              |            |
|       |             |            |           |              |           |
|       |-------------Process----->           |              |            |
|       |             |  payment   |           |              |           |
|       |             |            |           |              |           |
|       |<------------FAILED------|           |              |            |
|       |             |  (card declined)      |              |            |
|       |             |            |           |              |           |
|       |  ======================================================         |
|       |  |  COMPENSATION TRIGGERED                         |            |
|       |  ======================================================         |
|       |             |            |           |              |           |
|       |--Release---->           |           |              |            |
|       |  reservation|            |           |              |           |
|       |             |            |           |              |           |
|       |<-Released---|           |           |              |            |
|       |             |            |           |              |           |
|       |  SAGA COMPENSATED X                                             |
|       |  Return error to user                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

SAGA COMPENSATION SEQUENCE (Order Creation Fails After Payment):

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Orchestrator    Inventory     Payment      Order       Notification    |
|       |             |            |           |              |           |
|       |--Reserve---->           |           |              |            |
|       |<-Reserved---|           |           |              |            |
|       |             |            |           |              |           |
|       |-------------Process----->           |              |            |
|       |<------------Success-----|           |              |            |
|       |             |            |           |              |           |
|       |-------------------------Create------>              |            |
|       |             |            |           |              |           |
|       |<------------------------FAILED------|              |            |
|       |             |            |  (DB error)             |            |
|       |             |            |           |              |           |
|       |  ======================================================         |
|       |  |  COMPENSATION (Reverse Order)                   |            |
|       |  ======================================================         |
|       |             |            |           |              |           |
|       |-------------Refund------>           |              |            |
|       |             |            |           |              |           |
|       |<------------Refunded----|           |              |            |
|       |             |            |           |              |           |
|       |--Release---->           |           |              |            |
|       |<-Released---|           |           |              |            |
|       |             |            |           |              |           |
|       |------------------------------------- Notify user -->            |
|       |             |            |           |              |           |
|       |             |            |           |     "Sorry, |            |
|       |             |            |           |      refund |            |
|       |             |            |           |   initiated"|            |
|       |                                                                 |
|       |  SAGA COMPENSATED X                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

**SAGA IMPLEMENTATION:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  @Service                                                               |
|  public class CheckoutSagaOrchestrator {                                |
|                                                                         |
|      public OrderResult executeCheckout(CheckoutRequest request) {      |
|          String sagaId = UUID.randomUUID().toString();                  |
|          SagaState state = new SagaState(sagaId);                       |
|                                                                         |
|          try {                                                          |
|              // Step 1: Reserve inventory                               |
|              ReservationResult reservation = inventoryService           |
|                  .reserve(request.getItems(), sagaId);                  |
|              state.markCompleted(INVENTORY_RESERVED);                   |
|                                                                         |
|              // Step 2: Process payment                                 |
|              PaymentResult payment = paymentService                     |
|                  .processPayment(request.getPayment(), sagaId);         |
|              state.markCompleted(PAYMENT_PROCESSED);                    |
|                                                                         |
|              // Step 3: Create order                                    |
|              Order order = orderService                                 |
|                  .createOrder(request, reservation, payment);           |
|              state.markCompleted(ORDER_CREATED);                        |
|                                                                         |
|              // Step 4: Confirm inventory (make permanent)              |
|              inventoryService.confirmReservation(sagaId);               |
|              state.markCompleted(INVENTORY_CONFIRMED);                  |
|                                                                         |
|              // Step 5: Publish events (async)                          |
|              eventPublisher.publish(new OrderConfirmedEvent(order));    |
|                                                                         |
|              return OrderResult.success(order);                         |
|                                                                         |
|          } catch (Exception e) {                                        |
|              // Compensate in reverse order                             |
|              compensate(state, sagaId);                                 |
|              throw e;                                                   |
|          }                                                              |
|      }                                                                  |
|                                                                         |
|      private void compensate(SagaState state, String sagaId) {          |
|          if (state.isCompleted(PAYMENT_PROCESSED)) {                    |
|              paymentService.refund(sagaId);                             |
|          }                                                              |
|          if (state.isCompleted(INVENTORY_RESERVED)) {                   |
|              inventoryService.releaseReservation(sagaId);               |
|          }                                                              |
|      }                                                                  |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.5 SAGA PATTERN: CHOREOGRAPHY (ALTERNATIVE)

```
+-------------------------------------------------------------------------+
|                    ORCHESTRATION VS CHOREOGRAPHY                        |
|                                                                         |
|  +------------------+---------------------+------------------------+    |
|  | Aspect           | Orchestration       | Choreography           |    |
|  +------------------+---------------------+------------------------+    |
|  | Coordinator      | Central (Order Svc) | None (Event-driven)    |    |
|  +------------------+---------------------+------------------------+    |
|  | Coupling         | Orchestrator knows  | Services are loosely   |    |
|  |                  | all services        | coupled via events     |    |
|  +------------------+---------------------+------------------------+    |
|  | Single point     | Yes (orchestrator)  | No                     |    |
|  | of failure       |                     |                        |    |
|  +------------------+---------------------+------------------------+    |
|  | Visibility       | Easy (central log)  | Hard (distributed)     |    |
|  +------------------+---------------------+------------------------+    |
|  | Complexity       | In orchestrator     | Distributed            |    |
|  +------------------+---------------------+------------------------+    |
|  | Scalability      | Limited by coord    | Better (no bottleneck) |    |
|  +------------------+---------------------+------------------------+    |
|  | Debugging        | Easier              | Harder                 |    |
|  +------------------+---------------------+------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+
```

CHOREOGRAPHY PATTERN (Event-Driven):

```
+-------------------------------------------------------------------------+
|                    CHOREOGRAPHY SAGA FLOW                               |
|                                                                         |
|  Each service listens for events and publishes new events.              |
|  No central coordinator - services react to events.                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HAPPY PATH:                                                            |
|                                                                         |
|  [Cart Service]                                                         |
|       |                                                                 |
|       | Publish: CheckoutInitiated                                      |
|       v                                                                 |
|  ======================== KAFKA ==========================              |
|       |                                                                 |
|       v                                                                 |
|  [Inventory Service]  --> Listens: CheckoutInitiated                    |
|       |                   Reserves stock                                |
|       |                   Publishes: InventoryReserved                  |
|       v                                                                 |
|  ======================== KAFKA ==========================              |
|       |                                                                 |
|       v                                                                 |
|  [Payment Service]    --> Listens: InventoryReserved                    |
|       |                   Processes payment                             |
|       |                   Publishes: PaymentCompleted                   |
|       v                                                                 |
|  ======================== KAFKA ==========================              |
|       |                                                                 |
|       v                                                                 |
|  [Order Service]      --> Listens: PaymentCompleted                     |
|       |                   Creates order                                 |
|       |                   Publishes: OrderCreated                       |
|       v                                                                 |
|  ======================== KAFKA ==========================              |
|       |                                                                 |
|       +--> [Inventory Service] --> Confirms reservation                 |
|       |                            Publishes: InventoryConfirmed        |
|       |                                                                 |
|       +--> [Notification Service] --> Sends confirmation email          |
|       |                                                                 |
|       +--> [Cart Service] --> Clears cart                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

CHOREOGRAPHY COMPENSATION (Payment Fails):

```
+-------------------------------------------------------------------------+
|                    COMPENSATION FLOW                                    |
|                                                                         |
|  [Payment Service]                                                      |
|       |                                                                 |
|       | Payment failed!                                                 |
|       | Publishes: PaymentFailed {sagaId, reason}                       |
|       v                                                                 |
|  ======================== KAFKA ==========================              |
|       |                                                                 |
|       v                                                                 |
|  [Inventory Service]  --> Listens: PaymentFailed                        |
|       |                   Releases reservation                          |
|       |                   Publishes: InventoryReleased                  |
|       v                                                                 |
|  ======================== KAFKA ==========================              |
|       |                                                                 |
|       v                                                                 |
|  [Notification Svc]   --> Listens: PaymentFailed                        |
|                           Notifies user: "Payment failed"               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  KEY PRINCIPLE:                                                         |
|  Each service knows what to do when it sees a failure event.            |
|  No central coordinator needed - but harder to debug!                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

**WHEN TO USE WHICH:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USE ORCHESTRATION WHEN:                                                |
|  -------------------------                                              |
|  * Need clear visibility into saga state                                |
|  * Complex compensation logic                                           |
|  * Fewer services involved (3-5)                                        |
|  * Team prefers centralized control                                     |
|  * E-commerce checkout < RECOMMENDED                                    |
|                                                                         |
|  USE CHOREOGRAPHY WHEN:                                                 |
|  -------------------------                                              |
|  * Services are truly independent                                       |
|  * High scalability needed                                              |
|  * Simple compensation (mostly idempotent)                              |
|  * Organization has strong event-driven culture                         |
|  * Example: Notification pipelines, analytics                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.6 KAFKA EVENT CONTRACTS

```
+-------------------------------------------------------------------------+
|                    EVENT TOPICS                                         |
|                                                                         |
|  TOPIC: checkout.events                                                 |
|  TOPIC: inventory.events                                                |
|  TOPIC: payment.events                                                  |
|  TOPIC: order.events                                                    |
|  TOPIC: notification.events                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

EVENT SCHEMAS (Avro/JSON):

```
+-------------------------------------------------------------------------+
|                    CHECKOUT INITIATED EVENT                             |
|                                                                         |
|  {                                                                      |
|    "eventType": "CHECKOUT_INITIATED",                                   |
|    "eventId": "evt_abc123",                                             |
|    "sagaId": "saga_xyz789",                                             |
|    "timestamp": "2024-12-19T10:30:00Z",                                 |
|    "payload": {                                                         |
|      "userId": "user_456",                                              |
|      "cartId": "cart_abc",                                              |
|      "items": [                                                         |
|        {                                                                |
|          "productId": "prod_123",                                       |
|          "variantId": "var_001",                                        |
|          "quantity": 2,                                                 |
|          "unitPrice": 99.99                                             |
|        }                                                                |
|      ],                                                                 |
|      "totalAmount": 199.98,                                             |
|      "shippingAddressId": "addr_001"                                    |
|    },                                                                   |
|    "metadata": {                                                        |
|      "correlationId": "corr_123",                                       |
|      "source": "cart-service",                                          |
|      "version": "1.0"                                                   |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    INVENTORY RESERVED EVENT                             |
|                                                                         |
|  {                                                                      |
|    "eventType": "INVENTORY_RESERVED",                                   |
|    "eventId": "evt_def456",                                             |
|    "sagaId": "saga_xyz789",                                             |
|    "timestamp": "2024-12-19T10:30:01Z",                                 |
|    "payload": {                                                         |
|      "reservationId": "res_789",                                        |
|      "items": [                                                         |
|        {                                                                |
|          "productId": "prod_123",                                       |
|          "warehouseId": "wh_001",                                       |
|          "quantityReserved": 2                                          |
|        }                                                                |
|      ],                                                                 |
|      "expiresAt": "2024-12-19T10:45:01Z"                                |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    PAYMENT COMPLETED EVENT                              |
|                                                                         |
|  {                                                                      |
|    "eventType": "PAYMENT_COMPLETED",                                    |
|    "eventId": "evt_ghi789",                                             |
|    "sagaId": "saga_xyz789",                                             |
|    "timestamp": "2024-12-19T10:32:00Z",                                 |
|    "payload": {                                                         |
|      "paymentId": "pay_123",                                            |
|      "amount": 199.98,                                                  |
|      "currency": "USD",                                                 |
|      "paymentMethod": "CARD",                                           |
|      "gatewayTransactionId": "ch_stripe_abc",                           |
|      "status": "CAPTURED"                                               |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    PAYMENT FAILED EVENT                                 |
|                                                                         |
|  {                                                                      |
|    "eventType": "PAYMENT_FAILED",                                       |
|    "eventId": "evt_fail123",                                            |
|    "sagaId": "saga_xyz789",                                             |
|    "timestamp": "2024-12-19T10:32:00Z",                                 |
|    "payload": {                                                         |
|      "paymentId": "pay_123",                                            |
|      "failureReason": "INSUFFICIENT_FUNDS",                             |
|      "failureCode": "card_declined",                                    |
|      "retryable": true                                                  |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    ORDER CREATED EVENT                                  |
|                                                                         |
|  {                                                                      |
|    "eventType": "ORDER_CREATED",                                        |
|    "eventId": "evt_ord456",                                             |
|    "sagaId": "saga_xyz789",                                             |
|    "timestamp": "2024-12-19T10:32:05Z",                                 |
|    "payload": {                                                         |
|      "orderId": "ord_12345",                                            |
|      "orderNumber": "ORD-2024-ABC123",                                  |
|      "userId": "user_456",                                              |
|      "status": "CONFIRMED",                                             |
|      "totalAmount": 199.98,                                             |
|      "items": [...],                                                    |
|      "shippingAddress": {...}                                           |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

**EVENT CONSUMPTION PATTERNS:**

```
+-------------------------------------------------------------------------+
|                    AT-LEAST-ONCE DELIVERY                               |
|                                                                         |
|  Kafka guarantees at-least-once delivery.                               |
|  This means: SAME EVENT MAY BE DELIVERED MULTIPLE TIMES!                |
|                                                                         |
|  CONSUMER REQUIREMENTS:                                                 |
|  -----------------------                                                |
|  1. Must be IDEMPOTENT (process same event twice = same result)         |
|  2. Track processed event IDs                                           |
|  3. Use database transaction with event processing                      |
|                                                                         |
|  CONSUMER GROUP SETUP:                                                  |
|  ----------------------                                                 |
|  * inventory-service-group > processes inventory.events                 |
|  * payment-service-group > processes payment.events                     |
|  * Each service has dedicated consumer group                            |
|  * Partitioning by sagaId for ordering within saga                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.7 IDEMPOTENCY DESIGN

```
+-------------------------------------------------------------------------+
|                    WHY IDEMPOTENCY MATTERS                              |
|                                                                         |
|  SCENARIOS WHERE DUPLICATES HAPPEN:                                     |
|  ------------------------------------                                   |
|  1. Network timeout > Client retries                                    |
|  2. Kafka redelivery (at-least-once)                                    |
|  3. User double-clicks button                                           |
|  4. Service restart mid-processing                                      |
|                                                                         |
|  WITHOUT IDEMPOTENCY:                                                   |
|  ---------------------                                                  |
|  * Customer charged twice                                               |
|  * Inventory reserved twice                                             |
|  * Duplicate orders created                                             |
|  * Duplicate emails sent                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

**IDEMPOTENCY STRATEGIES:**

```
+-------------------------------------------------------------------------+
|                    STRATEGY 1: IDEMPOTENCY KEY                          |
|                                                                         |
|  Client generates unique key for each logical operation.                |
|  Server stores key and returns cached result on duplicate.              |
|                                                                         |
|  FLOW:                                                                  |
|  ------                                                                 |
|  1. Client generates key: checkout_{userId}_{timestamp}_{random}        |
|  2. Sends request with Idempotency-Key header                           |
|  3. Server checks: Key exists in DB?                                    |
|     - YES: Return cached response                                       |
|     - NO: Process request, store key + response                         |
|                                                                         |
|  IMPLEMENTATION:                                                        |
|  ----------------                                                       |
|  CREATE TABLE idempotency_keys (                                        |
|      idempotency_key VARCHAR(100) PRIMARY KEY,                          |
|      request_hash VARCHAR(64),        -- Hash of request body           |
|      response_body TEXT,                                                |
|      response_status INT,                                               |
|      created_at TIMESTAMP,                                              |
|      expires_at TIMESTAMP,                                              |
|      INDEX idx_expires (expires_at)                                     |
|  );                                                                     |
|                                                                         |
|  -- Cleanup old keys                                                    |
|  DELETE FROM idempotency_keys WHERE expires_at < NOW();                 |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    STRATEGY 2: NATURAL IDEMPOTENCY                      |
|                                                                         |
|  Use business logic that is naturally idempotent.                       |
|                                                                         |
|  EXAMPLES:                                                              |
|  ---------                                                              |
|  IDEMPOTENT:                                                            |
|  * SET status = 'CONFIRMED' (same result if run twice)                  |
|  * SET quantity = 5 (absolute value)                                    |
|                                                                         |
|  NOT IDEMPOTENT:                                                        |
|  * quantity = quantity + 1 (increments each time)                       |
|  * INSERT INTO orders (...) (creates duplicate)                         |
|                                                                         |
|  MAKE IT IDEMPOTENT:                                                    |
|  * INSERT ... ON CONFLICT DO NOTHING                                    |
|  * UPDATE ... WHERE status != 'CONFIRMED'                               |
|  * Use unique constraint on order_number                                |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    STRATEGY 3: EVENT ID DEDUPLICATION                   |
|                                                                         |
|  For Kafka consumers, track processed event IDs.                        |
|                                                                         |
|  CREATE TABLE processed_events (                                        |
|      event_id VARCHAR(100) PRIMARY KEY,                                 |
|      processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                  |
|      INDEX idx_processed_at (processed_at)                              |
|  );                                                                     |
|                                                                         |
|  CONSUMER LOGIC:                                                        |
|  ----------------                                                       |
|  @Transactional                                                         |
|  public void processEvent(Event event) {                                |
|      // Check if already processed                                      |
|      if (processedEventRepo.existsById(event.getEventId())) {           |
|          log.info("Duplicate event, skipping: " + event.getEventId());   
|          return;                                                        |
|      }                                                                  |
|                                                                         |
|      // Process event                                                   |
|      handleEvent(event);                                                |
|                                                                         |
|      // Mark as processed (in same transaction!)                        |
|      processedEventRepo.save(new ProcessedEvent(event.getEventId()));   |
|  }                                                                      |
|                                                                         |
|  CRITICAL: Insert and business logic in SAME transaction!               |
|                                                                         |
+-------------------------------------------------------------------------+
```

**IDEMPOTENCY FOR EACH SERVICE:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INVENTORY SERVICE:                                                     |
|  -------------------                                                    |
|  * Reserve: Check if reservation exists for sagaId                      |
|  * If exists: Return existing reservation (idempotent)                  |
|  * Use: UNIQUE(saga_id, product_id) constraint                          |
|                                                                         |
|  PAYMENT SERVICE:                                                       |
|  -----------------                                                      |
|  * Idempotency key sent to payment gateway                              |
|  * Gateway returns same result for same key                             |
|  * Store payment result locally for our idempotency                     |
|                                                                         |
|  ORDER SERVICE:                                                         |
|  ---------------                                                        |
|  * Generate order_number from sagaId (deterministic)                    |
|  * UNIQUE constraint on order_number                                    |
|  * INSERT ... ON CONFLICT DO UPDATE SET updated_at = NOW()              |
|                                                                         |
|  NOTIFICATION SERVICE:                                                  |
|  ----------------------                                                 |
|  * Track sent notifications by (saga_id, notification_type)             |
|  * Skip if already sent                                                 |
|  * Sending twice is annoying but not catastrophic                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.8 SAGA RECOVERY MECHANISM

```
+-------------------------------------------------------------------------+
|                    WHAT CAN GO WRONG                                    |
|                                                                         |
|  1. SERVICE CRASH MID-SAGA                                              |
|     Orchestrator crashes after reserving inventory, before payment      |
|     > Inventory stuck reserved forever                                  |
|                                                                         |
|  2. NETWORK PARTITION                                                   |
|     Payment succeeds but response never received                        |
|     > Order not created, customer charged                               |
|                                                                         |
|  3. DATABASE FAILURE                                                    |
|     Order DB down during order creation                                 |
|     > Payment captured but no order record                              |
|                                                                         |
|  4. STUCK SAGA                                                          |
|     Saga in progress > 30 minutes                                       |
|     > Something is wrong, needs intervention                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

**SAGA STATE PERSISTENCE:**

```
+-------------------------------------------------------------------------+
|                    SAGA STATE TABLE                                     |
|                                                                         |
|  CREATE TABLE saga_state (                                              |
|      saga_id VARCHAR(100) PRIMARY KEY,                                  |
|      saga_type VARCHAR(50) NOT NULL,       -- 'CHECKOUT', 'REFUND'      |
|      status ENUM('STARTED', 'IN_PROGRESS', 'COMPLETED',                 |
|                  'COMPENSATING', 'FAILED') NOT NULL,                    |
|      current_step VARCHAR(50),                                          |
|      payload JSON,                          -- Original request         |
|      completed_steps JSON,                  -- ["INVENTORY", "PAYMENT"]  
|      error_message TEXT,                                                |
|      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                    |
|      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE,          |
|      INDEX idx_status (status),                                         |
|      INDEX idx_created (created_at)                                     |
|  );                                                                     |
|                                                                         |
|  CREATE TABLE saga_step_log (                                           |
|      log_id BIGINT PRIMARY KEY AUTO_INCREMENT,                          |
|      saga_id VARCHAR(100) NOT NULL,                                     |
|      step_name VARCHAR(50) NOT NULL,                                    |
|      step_status ENUM('STARTED', 'COMPLETED', 'FAILED',                 |
|                       'COMPENSATED') NOT NULL,                          |
|      step_data JSON,                        -- Response/error data      |
|      executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                   |
|      FOREIGN KEY (saga_id) REFERENCES saga_state(saga_id),              |
|      INDEX idx_saga (saga_id)                                           |
|  );                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

**RECOVERY MECHANISMS:**

```
+-------------------------------------------------------------------------+
|                    RECOVERY JOB (Scheduled)                             |
|                                                                         |
|  @Scheduled(fixedRate = 60000)  // Every minute                         |
|  public void recoverStuckSagas() {                                      |
|                                                                         |
|      // Find sagas stuck > 15 minutes                                   |
|      List<SagaState> stuckSagas = sagaRepo.findStuck(                   |
|          Status.IN_PROGRESS,                                            |
|          Instant.now().minusMinutes(15)                                 |
|      );                                                                 |
|                                                                         |
|      for (SagaState saga : stuckSagas) {                                |
|          try {                                                          |
|              recoverSaga(saga);                                         |
|          } catch (Exception e) {                                        |
|              log.error("Recovery failed for: " + saga.getSagaId());     |
|              alertOps(saga);  // Manual intervention needed             |
|          }                                                              |
|      }                                                                  |
|  }                                                                      |
|                                                                         |
|  private void recoverSaga(SagaState saga) {                             |
|      // Determine last successful step                                  |
|      String lastStep = saga.getCurrentStep();                           |
|                                                                         |
|      switch (lastStep) {                                                |
|          case "INVENTORY_RESERVED":                                     |
|              // Try to continue with payment                            |
|              // Or compensate if too old                                |
|              if (saga.isExpired()) {                                    |
|                  compensateSaga(saga);                                  |
|              } else {                                                   |
|                  retryFromStep(saga, "PAYMENT");                        |
|              }                                                          |
|              break;                                                     |
|                                                                         |
|          case "PAYMENT_COMPLETED":                                      |
|              // Payment done, must complete order                       |
|              retryFromStep(saga, "CREATE_ORDER");                       |
|              break;                                                     |
|                                                                         |
|          case "PAYMENT_FAILED":                                         |
|              // Compensation should have happened                       |
|              compensateSaga(saga);                                      |
|              break;                                                     |
|      }                                                                  |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

**RECONCILIATION JOB:**

```
+-------------------------------------------------------------------------+
|                    CROSS-SERVICE RECONCILIATION                         |
|                                                                         |
|  @Scheduled(cron = "0 0 * * * *")  // Every hour                        |
|  public void reconcile() {                                              |
|                                                                         |
|      // 1. Find orphaned inventory reservations                         |
|      //    Reserved > 30 min, no corresponding order                    |
|      List<Reservation> orphaned = inventoryService                      |
|          .findExpiredWithoutOrder();                                    |
|      for (Reservation r : orphaned) {                                   |
|          inventoryService.release(r);                                   |
|          log.warn("Released orphaned reservation: " + r.getId());       |
|      }                                                                  |
|                                                                         |
|      // 2. Find payments without orders                                 |
|      //    Payment SUCCESS but no ORDER record                          |
|      List<Payment> orphanedPayments = paymentService                    |
|          .findSuccessfulWithoutOrder(Duration.ofHours(1));              |
|      for (Payment p : orphanedPayments) {                               |
|          // Either create order OR refund                               |
|          if (canCreateOrder(p)) {                                       |
|              orderService.createFromPayment(p);                         |
|          } else {                                                       |
|              paymentService.refund(p, "Reconciliation: no order");      |
|          }                                                              |
|      }                                                                  |
|                                                                         |
|      // 3. Find orders without confirmed inventory                      |
|      List<Order> unconfirmedInventory = orderService                    |
|          .findWithPendingInventory();                                   |
|      for (Order o : unconfirmedInventory) {                             |
|          inventoryService.confirmForOrder(o.getOrderId());              |
|      }                                                                  |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.9 COMPLETE SAGA FLOW WITH ALL EDGE CASES

```
+-------------------------------------------------------------------------+
|                    PRODUCTION-READY SAGA FLOW                           |
|                                                                         |
|  @Service                                                               |
|  @Transactional                                                         |
|  public class CheckoutSagaOrchestrator {                                |
|                                                                         |
|      public OrderResult checkout(CheckoutRequest request) {             |
|          String sagaId = generateSagaId(request);                       |
|                                                                         |
|          // Step 0: Check idempotency                                   |
|          SagaState existing = sagaRepo.findById(sagaId);                |
|          if (existing != null && existing.isCompleted()) {              |
|              return OrderResult.fromExisting(existing);                 |
|          }                                                              |
|                                                                         |
|          // Step 1: Create saga record                                  |
|          SagaState saga = createSaga(sagaId, request);                  |
|                                                                         |
|          try {                                                          |
|              // Step 2: Reserve inventory                               |
|              updateSagaStep(saga, "RESERVE_INVENTORY", "STARTED");      |
|              ReservationResult reservation = inventoryService           |
|                  .reserve(request.getItems(), sagaId);                  |
|              updateSagaStep(saga, "RESERVE_INVENTORY", "COMPLETED");    |
|                                                                         |
|              // Step 3: Process payment                                 |
|              updateSagaStep(saga, "PROCESS_PAYMENT", "STARTED");        |
|              PaymentResult payment = paymentService                     |
|                  .charge(request.getPayment(), sagaId);                 |
|                                                                         |
|              if (!payment.isSuccess()) {                                |
|                  updateSagaStep(saga, "PROCESS_PAYMENT", "FAILED");     |
|                  throw new PaymentFailedException(payment.getError());  |
|              }                                                          |
|              updateSagaStep(saga, "PROCESS_PAYMENT", "COMPLETED");      |
|                                                                         |
|              // Step 4: Create order                                    |
|              updateSagaStep(saga, "CREATE_ORDER", "STARTED");           |
|              Order order = orderService.create(request, payment);       |
|              updateSagaStep(saga, "CREATE_ORDER", "COMPLETED");         |
|                                                                         |
|              // Step 5: Confirm inventory                               |
|              updateSagaStep(saga, "CONFIRM_INVENTORY", "STARTED");      |
|              inventoryService.confirm(sagaId);                          |
|              updateSagaStep(saga, "CONFIRM_INVENTORY", "COMPLETED");    |
|                                                                         |
|              // Step 6: Async operations (fire and forget)              |
|              eventPublisher.publish(new OrderCreatedEvent(order));      |
|              cartService.clearAsync(request.getCartId());               |
|                                                                         |
|              // Mark saga complete                                      |
|              saga.setStatus(Status.COMPLETED);                          |
|              saga.setOrderId(order.getOrderId());                       |
|              sagaRepo.save(saga);                                       |
|                                                                         |
|              return OrderResult.success(order);                         |
|                                                                         |
|          } catch (InsufficientInventoryException e) {                   |
|              // No compensation needed - nothing happened               |
|              saga.setStatus(Status.FAILED);                             |
|              saga.setError(e.getMessage());                             |
|              sagaRepo.save(saga);                                       |
|              throw e;                                                   |
|                                                                         |
|          } catch (PaymentFailedException e) {                           |
|              // Compensate: Release inventory                           |
|              compensateInventory(sagaId);                               |
|              saga.setStatus(Status.COMPENSATED);                        |
|              saga.setError(e.getMessage());                             |
|              sagaRepo.save(saga);                                       |
|              throw e;                                                   |
|                                                                         |
|          } catch (OrderCreationException e) {                           |
|              // Compensate: Refund + Release inventory                  |
|              compensatePayment(sagaId);                                 |
|              compensateInventory(sagaId);                               |
|              saga.setStatus(Status.COMPENSATED);                        |
|              saga.setError(e.getMessage());                             |
|              sagaRepo.save(saga);                                       |
|              throw e;                                                   |
|                                                                         |
|          } catch (Exception e) {                                        |
|              // Unknown error - log and compensate                      |
|              log.error("Saga failed: " + sagaId, e);                    |
|              compensateAll(saga);                                       |
|              saga.setStatus(Status.FAILED);                             |
|              saga.setError("Unexpected: " + e.getMessage());            |
|              sagaRepo.save(saga);                                       |
|              throw e;                                                   |
|          }                                                              |
|      }                                                                  |
|                                                                         |
|      private void compensateAll(SagaState saga) {                       |
|          List<String> completedSteps = saga.getCompletedSteps();        |
|                                                                         |
|          // Compensate in reverse order                                 |
|          if (completedSteps.contains("CONFIRM_INVENTORY")) {            |
|              // Can't un-confirm, but inventory already deducted        |
|              log.warn("Inventory confirmed, cannot fully compensate");  |
|          }                                                              |
|          if (completedSteps.contains("CREATE_ORDER")) {                 |
|              orderService.cancel(saga.getOrderId());                    |
|          }                                                              |
|          if (completedSteps.contains("PROCESS_PAYMENT")) {              |
|              paymentService.refund(saga.getSagaId());                   |
|          }                                                              |
|          if (completedSteps.contains("RESERVE_INVENTORY")) {            |
|              inventoryService.release(saga.getSagaId());                |
|          }                                                              |
|      }                                                                  |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 8: PRICING & PROMOTIONS

### 8.1 DYNAMIC PRICING

```
+-------------------------------------------------------------------------+
|                    PRICING FACTORS                                      |
|                                                                         |
|  * Demand: High demand > higher price                                   |
|  * Competition: Match competitor prices                                 |
|  * Time: Time-limited sales, happy hours                                |
|  * Inventory: Low stock > higher price (or lower to clear)              |
|  * User segment: Premium members get better prices                      |
|  * Location: Regional pricing                                           |
|                                                                         |
|  PRICE CALCULATION ORDER:                                               |
|  -------------------------                                              |
|  1. Base price (from product)                                           |
|  2. Dynamic adjustments (demand, time)                                  |
|  3. Promotional price (sale price)                                      |
|  4. Coupon discount                                                     |
|  5. Member discount                                                     |
|  6. Final price                                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 8.2 FLASH SALES ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                    FLASH SALE CHALLENGES                                |
|                                                                         |
|  SCENARIO:                                                              |
|  * Sale starts at 12:00 PM                                              |
|  * 1 million users waiting                                              |
|  * 10,000 items available at 50% off                                    |
|  * All users click "Buy" at exactly 12:00:00                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION: MULTI-LAYER DEFENSE                                          |
|                                                                         |
|  LAYER 1: Virtual Waiting Room                                          |
|  -----------------------------                                          |
|  * Queue users before sale starts                                       |
|  * Random shuffle to prevent bots advantage                             |
|  * Release users in batches (1000 per minute)                           |
|  * Show position and estimated time                                     |
|                                                                         |
|  LAYER 2: Pre-warm Everything                                           |
|  ----------------------------                                           |
|  * Scale up services 30 min before                                      |
|  * Pre-load product data into cache                                     |
|  * Pre-create inventory counters in Redis                               |
|                                                                         |
|  LAYER 3: Inventory Token System                                        |
|  ---------------------------------                                      |
|  * Pre-generate 10,000 "purchase tokens"                                |
|  * User gets token > guaranteed purchase                                |
|  * Token has TTL (5 minutes to complete)                                |
|  * No token > "Sold out"                                                |
|                                                                         |
|  LAYER 4: Rate Limiting                                                 |
|  -----------------------                                                |
|  * Per-user: 1 request per second                                       |
|  * Per-IP: 10 requests per second                                       |
|  * Global: Cap concurrent checkouts                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 9: CACHING STRATEGY

```
+-------------------------------------------------------------------------+
|                    CACHING LAYERS                                       |
|                                                                         |
|  +--------------------+-------------+--------------+-----------------+  |
|  | Data               | Cache       | TTL          | Invalidation    |  |
|  +--------------------+-------------+--------------+-----------------+  |
|  | Product catalog    | Redis       | 1 hour       | On product edit |  |
|  +--------------------+-------------+--------------+-----------------+  |
|  | Product details    | Redis       | 30 min       | On product edit |  |
|  +--------------------+-------------+--------------+-----------------+  |
|  | Category tree      | Redis       | 6 hours      | On change       |  |
|  +--------------------+-------------+--------------+-----------------+  |
|  | Inventory count    | Redis       | Real-time    | On reservation  |  |
|  | (available)        |             |              |                 |  |
|  +--------------------+-------------+--------------+-----------------+  |
|  | Shopping cart      | Redis       | 30 days      | On cart change  |  |
|  +--------------------+-------------+--------------+-----------------+  |
|  | User session       | Redis       | 24 hours     | On logout       |  |
|  +--------------------+-------------+--------------+-----------------+  |
|  | Search results     | Elasticsearch| In-memory   | On product change| |
|  +--------------------+-------------+--------------+-----------------+  |
|  | Static assets      | CDN         | 1 year       | URL versioning  |  |
|  +--------------------+-------------+--------------+-----------------+  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CACHE-ASIDE PATTERN:                                                   |
|  ---------------------                                                  |
|  1. Check cache first                                                   |
|  2. Cache miss > Query DB                                               |
|  3. Store in cache with TTL                                             |
|  4. Return data                                                         |
|                                                                         |
|  WRITE-THROUGH FOR INVENTORY:                                           |
|  -----------------------------                                          |
|  1. Update DB                                                           |
|  2. Update cache immediately                                            |
|  3. Critical data - cache must be consistent                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 10: NOTIFICATION SYSTEM

```
+-------------------------------------------------------------------------+
|                    NOTIFICATION TYPES                                   |
|                                                                         |
|  +--------------+-----------------------------------------------------+ |
|  | Channel      | Use Cases                                          |  |
|  +--------------+-----------------------------------------------------+ |
|  | Email        | Order confirmation, shipping updates, invoices     |  |
|  |              | Password reset, promotional campaigns              |  |
|  +--------------+-----------------------------------------------------+ |
|  | SMS          | OTP, delivery alerts, order updates                |  |
|  +--------------+-----------------------------------------------------+ |
|  | Push         | Flash sale alerts, price drops, delivery updates   |  |
|  +--------------+-----------------------------------------------------+ |
|  | In-App       | Real-time order tracking, cart reminders           |  |
|  +--------------+-----------------------------------------------------+ |
|                                                                         |
|  ASYNC VIA KAFKA:                                                       |
|  -----------------                                                      |
|  Order Service > Kafka (order.events) > Notification Consumers          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 11: DATABASE ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                    SHARDING STRATEGY                                    |
|                                                                         |
|  ORDERS: Shard by user_id                                               |
|  -------------------------                                              |
|  * User always sees all their orders                                    |
|  * Most queries are user-centric                                        |
|  * Consistent hashing for distribution                                  |
|                                                                         |
|  PRODUCTS: Single database (replication)                                |
|  ----------------------------------------                               |
|  * 10M products fits in one DB                                          |
|  * Read replicas for scale                                              |
|  * Heavy caching reduces load                                           |
|                                                                         |
|  INVENTORY: Shard by product_id                                         |
|  -------------------------------                                        |
|  * All operations for a product on one shard                            |
|  * Avoids distributed transactions for stock                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  READ REPLICAS:                                                         |
|  ---------------                                                        |
|  * Products: 5 read replicas                                            |
|  * Orders: 3 read replicas per shard                                    |
|  * Write to primary, read from replicas                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 12: FAILURE SCENARIOS & RECOVERY

```
+-------------------------------------------------------------------------+
|                    FAILURE HANDLING                                     |
|                                                                         |
|  PAYMENT GATEWAY TIMEOUT:                                               |
|  -------------------------                                              |
|  * Retry with exponential backoff                                       |
|  * Same idempotency key (safe to retry)                                 |
|  * After N retries, mark PENDING for reconciliation                     |
|  * Background job queries gateway for status                            |
|                                                                         |
|  INVENTORY SERVICE DOWN:                                                |
|  -------------------------                                              |
|  * Circuit breaker opens                                                |
|  * Show "Unable to process" error                                       |
|  * Cart preserved, user can retry                                       |
|  * DO NOT proceed without inventory check                               |
|                                                                         |
|  REDIS FAILURE:                                                         |
|  --------------                                                         |
|  * Fallback to database for cart                                        |
|  * Fallback to DB pessimistic locking for inventory                     |
|  * Slower but functional                                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  RECONCILIATION JOBS:                                                   |
|  ---------------------                                                  |
|  * Pending payments > 1 hour > Query gateway, update status             |
|  * Reserved inventory > 30 min without order > Release                  |
|  * Order CONFIRMED but no payment > Flag for review                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 13: SCALING & PERFORMANCE

```
+-------------------------------------------------------------------------+
|                    SCALING STRATEGIES                                   |
|                                                                         |
|  HORIZONTAL SCALING:                                                    |
|  --------------------                                                   |
|  * API servers: Stateless, scale on CPU/request rate                    |
|  * Workers: Scale on queue depth                                        |
|                                                                         |
|  AUTO-SCALING TRIGGERS:                                                 |
|  ------------------------                                               |
|  * CPU > 70% for 2 min > Scale up                                       |
|  * CPU < 30% for 10 min > Scale down                                    |
|  * Request latency p99 > 500ms > Scale up                               |
|                                                                         |
|  PRE-SCALING FOR EVENTS:                                                |
|  -------------------------                                              |
|  * Flash sale: 10x capacity 30 min before                               |
|  * Black Friday: 50x capacity, start day before                         |
|  * Pre-warm caches                                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CDN FOR PRODUCT IMAGES:                                                |
|  -------------------------                                              |
|  * 25 TB of images served from CDN                                      |
|  * Edge locations reduce latency                                        |
|  * Cache-Control: max-age=31536000, immutable                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 14: TRADE-OFFS & DECISIONS

```
+-------------------------------------------------------------------------+
|                    KEY DESIGN DECISIONS                                 |
|                                                                         |
|  DECISION 1: Inventory Reservation Strategy                             |
|  -------------------------------------------                            |
|  Chose: Reserve at checkout (not add-to-cart)                           |
|  Trade-off:                                                             |
|  + Better inventory utilization (70% cart abandonment)                  |
|  + Less infrastructure for cart-level reservations                      |
|  - User might see "out of stock" at checkout                            |
|                                                                         |
|  DECISION 2: Cart Storage                                               |
|  --------------------------                                             |
|  Chose: Redis primary + DB backup                                       |
|  Trade-off:                                                             |
|  + Fast cart operations (< 5ms)                                         |
|  + Cart survives Redis restart (DB backup)                              |
|  - Complexity of dual storage                                           |
|                                                                         |
|  DECISION 3: Saga vs 2PC for Distributed Transactions                   |
|  -----------------------------------------------------                  |
|  Chose: Saga with orchestration                                         |
|  Trade-off:                                                             |
|  + No distributed locks (better performance)                            |
|  + Services stay independent                                            |
|  - Eventual consistency (brief window of inconsistency)                 |
|  - Compensation logic complexity                                        |
|                                                                         |
|  DECISION 4: Search Technology                                          |
|  -----------------------------                                          |
|  Chose: Elasticsearch                                                   |
|  Trade-off:                                                             |
|  + Full-text search, facets, autocomplete                               |
|  + Horizontal scaling                                                   |
|  - Additional infrastructure                                            |
|  - Data sync complexity (CDC)                                           |
|                                                                         |
|  DECISION 5: Strong vs Eventual Consistency                             |
|  -------------------------------------------                            |
|  Chose: Strong for inventory, eventual for others                       |
|  Trade-off:                                                             |
|  + No overselling (critical business requirement)                       |
|  + Product data can be slightly stale (OK for browsing)                 |
|  - Inventory operations slightly slower                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 15: INTERVIEW FOLLOW-UPS

### 15.1 COMMON INTERVIEW QUESTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q1: How do you prevent overselling?                                    |
|  -----------------------------------                                    |
|  A: Multi-layer approach:                                               |
|     1. Redis atomic reservation (Lua script for check + decrement)      |
|     2. Database optimistic lock as backup verification                  |
|     3. Short TTL on reservations (15 min)                               |
|     4. Background job to release expired reservations                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q2: When do you reserve inventory?                                     |
|  -----------------------------------                                    |
|  A: At checkout initiation, not at add-to-cart.                         |
|     Why: 70% cart abandonment would waste inventory.                    |
|     Exception: Flash sales with limited stock - reserve at cart.        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q3: How do you handle cart for guest users?                            |
|  -----------------------------------------                              |
|  A: Cart ID in cookie, stored in Redis with 30-day TTL.                 |
|     On login: Merge guest cart into user cart.                          |
|     Same product > sum quantities (up to max limit).                    |
|     Different products > add all.                                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q4: What if payment succeeds but order creation fails?                 |
|  ----------------------------------------------------                   |
|  A: Saga compensation pattern:                                          |
|     1. Log the failure with all details                                 |
|     2. Trigger automatic refund                                         |
|     3. Release inventory reservation                                    |
|     4. Notify user: "Sorry, booking failed. Refund initiated."          |
|     5. Reconciliation job catches any missed cases                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q5: How do you handle flash sales with 1M concurrent users?            |
|  --------------------------------------------------------               |
|  A: Multiple strategies:                                                |
|     1. Virtual waiting room with random shuffle                         |
|     2. Pre-generated inventory tokens (guarantee purchase)              |
|     3. Pre-scale infrastructure (10x-50x)                               |
|     4. Rate limiting per user/IP                                        |
|     5. CDN for static content                                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q6: How do you ensure price consistency?                               |
|  --------------------------------------                                 |
|  A: Price snapshot at cart addition + validation at checkout.           |
|     If price changed:                                                   |
|     - Small change: Proceed, charge new price, notify user              |
|     - Big change: Show warning, require re-confirmation                 |
|     - Price drop: Automatically give better price                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q7: How do you design the search system?                               |
|  --------------------------------------                                 |
|  A: Elasticsearch with:                                                 |
|     - Full-text search on product name, description                     |
|     - Faceted filtering (brand, price, rating)                          |
|     - Autocomplete with completion suggester                            |
|     - CDC pipeline from PostgreSQL for sync                             |
|     - < 5 second delay for updates                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q8: How do you handle inventory across multiple warehouses?            |
|  ---------------------------------------------------------              |
|  A: Inventory table has warehouse_id column.                            |
|     Product availability = SUM(available) across warehouses.            |
|     At checkout: Reserve from nearest warehouse.                        |
|     Fallback: Reserve from any warehouse with stock.                    |
|     Show estimated delivery based on warehouse location.                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q9: What's your database sharding strategy?                            |
|  -----------------------------------------                              |
|  A: Different strategies per data type:                                 |
|     - Orders: Shard by user_id (user-centric queries)                   |
|     - Inventory: Shard by product_id (avoid distributed locks)          |
|     - Products: No sharding (10M fits, use read replicas)               |
|     - Consistent hashing for even distribution                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q10: How do you handle payment gateway failures?                       |
|  ---------------------------------------------                          |
|  A: Resilient payment flow:                                             |
|     1. Retry with exponential backoff (same idempotency key)            |
|     2. After N retries: Mark PENDING, hold reservation                  |
|     3. Background job polls gateway for status                          |
|     4. Multi-gateway fallback (Stripe fails > use PayPal)               |
|     5. Circuit breaker to fail fast on gateway outage                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.2 DEEP DIVE QUESTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q11: Walk me through the complete checkout flow                        |
|  -------------------------------------------------                      |
|                                                                         |
|  A: Step-by-step:                                                       |
|                                                                         |
|  1. USER CLICKS CHECKOUT                                                |
|     * Validate cart (items exist, in stock, prices)                     |
|     * Return any warnings (price changed, low stock)                    |
|                                                                         |
|  2. RESERVE INVENTORY (Redis Lua Script)                                |
|     * For each item: atomic check + decrement available                 |
|     * Store reservation with 15-min TTL                                 |
|     * If any fails: Release all, return error                           |
|                                                                         |
|  3. DISPLAY CHECKOUT PAGE                                               |
|     * Show items, prices, shipping options                              |
|     * Timer: "Complete in 14:59..."                                     |
|     * User enters payment info                                          |
|                                                                         |
|  4. PROCESS PAYMENT                                                     |
|     * Generate idempotency key                                          |
|     * Create payment record (status: INITIATED)                         |
|     * Call payment gateway                                              |
|     * Handle response (success/failure/timeout)                         |
|                                                                         |
|  5. CREATE ORDER (if payment success)                                   |
|     * Create order record (status: CONFIRMED)                           |
|     * Create order_items                                                |
|     * Confirm inventory (permanent deduction in DB)                     |
|     * Clear cart                                                        |
|                                                                         |
|  6. POST-ORDER                                                          |
|     * Publish OrderConfirmed event to Kafka                             |
|     * Send confirmation email/SMS                                       |
|     * Update analytics                                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q12: Design the inventory reservation Lua script                       |
|  -------------------------------------------------                      |
|                                                                         |
|  A: Atomic multi-item reservation:                                      |
|                                                                         |
|  -- KEYS: [product1:available, product2:available, ...]                 |
|  -- ARGV: [qty1, qty2, ..., reservation_id, ttl]                        |
|                                                                         |
|  local n = (#KEYS)                                                      |
|  local reservation_id = ARGV[n + 1]                                     |
|  local ttl = tonumber(ARGV[n + 2])                                      |
|                                                                         |
|  -- Phase 1: Check all items have sufficient stock                      |
|  for i = 1, n do                                                        |
|      local available = tonumber(redis.call('GET', KEYS[i])) or 0        |
|      local qty = tonumber(ARGV[i])                                      |
|      if available < qty then                                            |
|          return {err = 'INSUFFICIENT_STOCK', item = i}                  |
|      end                                                                |
|  end                                                                    |
|                                                                         |
|  -- Phase 2: Reserve all items (only if Phase 1 passed)                 |
|  for i = 1, n do                                                        |
|      redis.call('DECRBY', KEYS[i], ARGV[i])                             |
|      -- Store reservation for cleanup                                   |
|      redis.call('HSET', 'reservations:' .. reservation_id,              |
|                 KEYS[i], ARGV[i])                                       |
|  end                                                                    |
|  redis.call('EXPIRE', 'reservations:' .. reservation_id, ttl)           |
|                                                                         |
|  return {ok = true}                                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Q13: How do you handle high-cardinality product variants?              |
|  -------------------------------------------------------                |
|                                                                         |
|  A: Example: T-shirt with 5 colors x 4 sizes = 20 variants              |
|                                                                         |
|  DATA MODEL:                                                            |
|  * Product: Base product info                                           |
|  * Variant: Each combination (color + size)                             |
|  * Inventory: Per variant (SKU level)                                   |
|                                                                         |
|  UI OPTIMIZATION:                                                       |
|  * Don't load all variants upfront                                      |
|  * User selects color > Load size availability                          |
|  * API: GET /products/123/variants?color=red                            |
|                                                                         |
|  INVENTORY TRACKING:                                                    |
|  * Product-level: aggregate for display ("In Stock")                    |
|  * Variant-level: actual reservation/purchase                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.3 HOMEWORK ASSIGNMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. Design the returns/refund system                                    |
|     * Return eligibility rules (window, condition)                      |
|     * Return shipping label generation                                  |
|     * Refund processing (full, partial)                                 |
|     * Inventory restocking                                              |
|                                                                         |
|  2. Design the recommendation engine                                    |
|     * "Customers also bought"                                           |
|     * Personalized recommendations                                      |
|     * Collaborative vs content-based filtering                          |
|                                                                         |
|  3. Design the seller dashboard                                         |
|     * Product listing management                                        |
|     * Order fulfillment workflow                                        |
|     * Sales analytics                                                   |
|     * Inventory alerts                                                  |
|                                                                         |
|  4. Design the review and rating system                                 |
|     * Verified purchase reviews                                         |
|     * Review moderation                                                 |
|     * Helpfulness voting                                                |
|     * Aggregate rating calculation                                      |
|                                                                         |
|  5. Design the wishlist feature                                         |
|     * Multiple wishlists per user                                       |
|     * Price drop notifications                                          |
|     * Back-in-stock alerts                                              |
|     * Share wishlist                                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 16: THEORETICAL FOUNDATIONS

### 16.1 CAP THEOREM

```
+-------------------------------------------------------------------------+
|                    CAP THEOREM EXPLAINED                                |
|                                                                         |
|  In a distributed system, you can only guarantee TWO of THREE:          |
|                                                                         |
|                         CONSISTENCY                                     |
|                            /\                                           |
|                           /  \                                          |
|                          /    \                                         |
|                         / CP   \                                        |
|                        /        \                                       |
|                       /    CA    \                                      |
|                      /____________\                                     |
|            AVAILABILITY --- AP --- PARTITION                            |
|                                    TOLERANCE                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CONSISTENCY (C):                                                       |
|  -----------------                                                      |
|  * Every read receives the most recent write or an error                |
|  * All nodes see the same data at the same time                         |
|  * Strong consistency = linearizability                                 |
|                                                                         |
|  AVAILABILITY (A):                                                      |
|  ------------------                                                     |
|  * Every request receives a (non-error) response                        |
|  * No guarantee that it contains the most recent write                  |
|  * System remains operational 100% of the time                          |
|                                                                         |
|  PARTITION TOLERANCE (P):                                               |
|  -------------------------                                              |
|  * System continues to operate despite network partitions               |
|  * Messages between nodes can be lost or delayed                        |
|  * In distributed systems, P is NON-NEGOTIABLE                          |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    CAP TRADE-OFFS IN PRACTICE                           |
|                                                                         |
|  +-------------+------------------------+----------------------------+  |
|  | Choice      | What You Get           | Examples                   |  |
|  +-------------+------------------------+----------------------------+  |
|  | CP          | Consistency +          | MongoDB (strong read),     |  |
|  |             | Partition Tolerance    | HBase, Redis Cluster,      |  |
|  |             | (sacrifice availability| Zookeeper, etcd            |  |
|  |             | during partition)      |                            |  |
|  +-------------+------------------------+----------------------------+  |
|  | AP          | Availability +         | Cassandra, DynamoDB,       |  |
|  |             | Partition Tolerance    | CouchDB, Riak              |  |
|  |             | (sacrifice consistency |                            |  |
|  |             | during partition)      |                            |  |
|  +-------------+------------------------+----------------------------+  |
|  | CA          | Consistency +          | Single-node RDBMS          |  |
|  |             | Availability           | (PostgreSQL, MySQL)        |  |
|  |             | (no partition tolerance| NOT truly distributed!     |  |
|  |             | = not distributed)     |                            |  |
|  +-------------+------------------------+----------------------------+  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  E-COMMERCE IMPLICATIONS:                                               |
|  -------------------------                                              |
|                                                                         |
|  INVENTORY (CP choice):                                                 |
|  * Need strong consistency to prevent overselling                       |
|  * Accept brief unavailability during partitions                        |
|  * "Sorry, try again" is better than overselling                        |
|                                                                         |
|  PRODUCT CATALOG (AP choice):                                           |
|  * Eventual consistency is acceptable                                   |
|  * Better to show slightly stale data than nothing                      |
|  * Cache heavily, sync eventually                                       |
|                                                                         |
|  SHOPPING CART (AP choice):                                             |
|  * Eventual consistency OK (merge on conflicts)                         |
|  * Availability more important than perfect consistency                 |
|  * "Last write wins" or "union merge" strategies                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 16.2 ACID vs BASE

```
+-------------------------------------------------------------------------+
|                    ACID PROPERTIES                                      |
|                                                                         |
|  Traditional relational databases guarantee ACID:                       |
|                                                                         |
|  ATOMICITY:                                                             |
|  -----------                                                            |
|  * All operations in a transaction succeed or ALL fail                  |
|  * No partial updates                                                   |
|  * "All or nothing"                                                     |
|                                                                         |
|  Example:                                                               |
|  BEGIN TRANSACTION;                                                     |
|    UPDATE accounts SET balance = balance - 100 WHERE id = 1;            |
|    UPDATE accounts SET balance = balance + 100 WHERE id = 2;            |
|  COMMIT;  -- Both happen, or neither happens                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CONSISTENCY:                                                           |
|  -------------                                                          |
|  * Database moves from one valid state to another                       |
|  * All constraints, triggers, cascades are respected                    |
|  * Data integrity is maintained                                         |
|                                                                         |
|  Example:                                                               |
|  * Foreign key constraints prevent orphan records                       |
|  * CHECK constraints prevent invalid values                             |
|  * UNIQUE constraints prevent duplicates                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ISOLATION:                                                             |
|  -----------                                                            |
|  * Concurrent transactions don't interfere with each other              |
|  * Each transaction sees a consistent snapshot                          |
|  * Isolation levels: READ UNCOMMITTED > READ COMMITTED >                |
|                      REPEATABLE READ > SERIALIZABLE                     |
|                                                                         |
|  ISOLATION LEVELS:                                                      |
|  +------------------+------------+-------------+-------------------+    |
|  | Level            | Dirty Read | Non-Repeat  | Phantom Read      |    |
|  +------------------+------------+-------------+-------------------+    |
|  | READ UNCOMMITTED | Possible   | Possible    | Possible          |    |
|  | READ COMMITTED   | Prevented  | Possible    | Possible          |    |
|  | REPEATABLE READ  | Prevented  | Prevented   | Possible          |    |
|  | SERIALIZABLE     | Prevented  | Prevented   | Prevented         |    |
|  +------------------+------------+-------------+-------------------+    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DURABILITY:                                                            |
|  ------------                                                           |
|  * Once committed, data survives crashes, power failures                |
|  * Written to persistent storage (disk)                                 |
|  * WAL (Write-Ahead Logging) ensures recoverability                     |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    BASE PROPERTIES                                      |
|                                                                         |
|  NoSQL and distributed databases often follow BASE:                     |
|                                                                         |
|  BASICALLY AVAILABLE:                                                   |
|  ---------------------                                                  |
|  * System guarantees availability (per CAP)                             |
|  * May return stale data, but always responds                           |
|  * Partial failures don't cause total system failure                    |
|                                                                         |
|  SOFT STATE:                                                            |
|  ------------                                                           |
|  * State of the system may change over time                             |
|  * Even without input (due to eventual consistency)                     |
|  * Data may expire, replicas may sync                                   |
|                                                                         |
|  EVENTUALLY CONSISTENT:                                                 |
|  -----------------------                                                |
|  * Given enough time, all replicas will converge                        |
|  * No guarantee of immediate consistency                                |
|  * Reads may return stale data temporarily                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ACID vs BASE COMPARISON:                                               |
|                                                                         |
|  +------------------+---------------------+-------------------------+   |
|  | Aspect           | ACID                | BASE                    |   |
|  +------------------+---------------------+-------------------------+   |
|  | Consistency      | Strong              | Eventual                |   |
|  +------------------+---------------------+-------------------------+   |
|  | Availability     | May be sacrificed   | Prioritized             |   |
|  +------------------+---------------------+-------------------------+   |
|  | Scalability      | Vertical (limited)  | Horizontal (easier)     |   |
|  +------------------+---------------------+-------------------------+   |
|  | Data Model       | Rigid schema        | Flexible schema         |   |
|  +------------------+---------------------+-------------------------+   |
|  | Use Case         | Banking, inventory  | Social feeds, analytics |   |
|  +------------------+---------------------+-------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 16.3 CONSISTENCY MODELS

```
+-------------------------------------------------------------------------+
|                    CONSISTENCY SPECTRUM                                 |
|                                                                         |
|  STRONGEST <---------------------------------------------> WEAKEST      |
|                                                                         |
|  +-----------+-----------+------------+----------+-----------------+    |
|  |Lineariz-  |Sequential | Causal     | Eventual | No Consistency  |    |
|  |ability    |Consistency| Consistency|Consistency| (Chaos)        |    |
|  +-----------+-----------+------------+----------+-----------------+    |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    CONSISTENCY MODELS EXPLAINED                         |
|                                                                         |
|  LINEARIZABILITY (Strongest):                                           |
|  -----------------------------                                          |
|  * Operations appear to execute instantaneously                         |
|  * Global total order of all operations                                 |
|  * Any read returns the most recent write                               |
|  * As if there's a single copy of data                                  |
|                                                                         |
|  Example: Single-leader database with synchronous replication           |
|  Cost: High latency, limited scalability                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SEQUENTIAL CONSISTENCY:                                                |
|  -------------------------                                              |
|  * Operations from each client appear in order                          |
|  * All clients see same order of operations                             |
|  * But order may not match real-time order                              |
|                                                                         |
|  Client A: Write(x=1), Write(x=2)                                       |
|  Client B: Read(x) > might see 1 then 2, never 2 then 1                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CAUSAL CONSISTENCY:                                                    |
|  ---------------------                                                  |
|  * Causally related operations seen in same order by all                |
|  * Concurrent (unrelated) operations may be seen differently            |
|                                                                         |
|  If A causes B, everyone sees A before B                                |
|  If A and B are independent, order may vary                             |
|                                                                         |
|  Example: "Reply" must come after "Original post"                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EVENTUAL CONSISTENCY:                                                  |
|  -----------------------                                                |
|  * Given no new updates, all replicas converge                          |
|  * No guarantee on how long convergence takes                           |
|  * Reads may return stale data                                          |
|                                                                         |
|  Example: DNS propagation (24-48 hours)                                 |
|  Good for: High availability, read-heavy workloads                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  READ-YOUR-WRITES:                                                      |
|  -------------------                                                    |
|  * User always sees their own writes                                    |
|  * May not see others' writes immediately                               |
|  * Implementation: Sticky sessions, read from leader                    |
|                                                                         |
|  MONOTONIC READS:                                                       |
|  -----------------                                                      |
|  * Once you read a value, you never see older value                     |
|  * Time doesn't go backward for a client                                |
|  * Implementation: Version vectors, session tokens                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 16.4 DATABASE SCALING CONCEPTS

```
+-------------------------------------------------------------------------+
|                    VERTICAL vs HORIZONTAL SCALING                       |
|                                                                         |
|  VERTICAL SCALING (Scale Up):                                           |
|  -----------------------------                                          |
|  * Add more CPU, RAM, Storage to single server                          |
|  * Simpler (no code changes)                                            |
|  * Has upper limit (hardware constraints)                               |
|  * Single point of failure                                              |
|  * Expensive at scale                                                   |
|                                                                         |
|  +---------+         +-----------------+                                |
|  | Small   |   >     |    BIGGER       |                                |
|  | Server  |         |    SERVER       |                                |
|  +---------+         +-----------------+                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HORIZONTAL SCALING (Scale Out):                                        |
|  ------------------------------                                         |
|  * Add more servers                                                     |
|  * Requires distributed architecture                                    |
|  * Theoretically unlimited                                              |
|  * Built-in redundancy                                                  |
|  * More complex (data distribution, coordination)                       |
|                                                                         |
|  +---------+         +-------+ +-------+ +-------+                      |
|  | Server  |   >     |Server | |Server | |Server |                      |
|  +---------+         +-------+ +-------+ +-------+                      |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    REPLICATION                                          |
|                                                                         |
|  PURPOSE:                                                               |
|  * High availability (failover)                                         |
|  * Read scalability (read replicas)                                     |
|  * Geographic distribution (lower latency)                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SINGLE-LEADER (Master-Slave):                                          |
|  ------------------------------                                         |
|                                                                         |
|       Writes ----> +--------+                                           |
|                    | LEADER |                                           |
|       Reads  ----> |(Master)|                                           |
|                    +---+----+                                           |
|              +---------+---------+                                      |
|              v         v         v                                      |
|         +--------++--------++--------+                                  |
|  Reads> |Follower||Follower||Follower| <Reads                           |
|         +--------++--------++--------+                                  |
|                                                                         |
|  * All writes go to leader                                              |
|  * Leader replicates to followers                                       |
|  * Followers serve reads                                                |
|  * Failover: Promote follower to leader                                 |
|                                                                         |
|  REPLICATION LAG:                                                       |
|  * Async replication: Followers may be behind                           |
|  * Sync replication: Slower, but consistent                             |
|  * Semi-sync: At least one follower confirmed                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  MULTI-LEADER:                                                          |
|  --------------                                                         |
|                                                                         |
|  +--------+ <----------------> +--------+                               |
|  |Leader 1|     Bi-sync        |Leader 2|                               |
|  |(US-East)|                   |(EU-West)|                              |
|  +---+----+                    +---+----+                               |
|      |                             |                                    |
|  +---+---+                     +---+---+                                |
|  |Replicas|                    |Replicas|                               |
|  +-------+                     +-------+                                |
|                                                                         |
|  * Multiple leaders accept writes                                       |
|  * Conflict resolution needed (LWW, vector clocks)                      |
|  * Good for geo-distributed systems                                     |
|  * Complex to implement correctly                                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  LEADERLESS (Dynamo-style):                                             |
|  ---------------------------                                            |
|                                                                         |
|  +--------+ +--------+ +--------+                                       |
|  | Node 1 | | Node 2 | | Node 3 |                                       |
|  +---+----+ +---+----+ +---+----+                                       |
|      |         |         |                                              |
|      +---------+---------+                                              |
|                |                                                        |
|         Client writes to                                                |
|         W nodes (quorum)                                                |
|                                                                         |
|  QUORUM: W + R > N                                                      |
|  * N = total replicas                                                   |
|  * W = write quorum (nodes that must ack write)                         |
|  * R = read quorum (nodes queried for read)                             |
|                                                                         |
|  Example: N=3, W=2, R=2                                                 |
|  * Write to 2 nodes, read from 2 nodes                                  |
|  * Guaranteed overlap > see latest write                                |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    SHARDING (PARTITIONING)                              |
|                                                                         |
|  PURPOSE:                                                               |
|  * Distribute data across multiple databases                            |
|  * Scale writes (each shard handles subset)                             |
|  * Handle data that doesn't fit on one server                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SHARDING STRATEGIES:                                                   |
|                                                                         |
|  1. RANGE-BASED:                                                        |
|  -----------------                                                      |
|  * Shard by key range: user_id 1-1M, 1M-2M, etc.                        |
|  * Good for range queries                                               |
|  * Risk: Hotspots if data skewed                                        |
|                                                                         |
|  +-----------+-----------+-----------+                                  |
|  | Shard 1   | Shard 2   | Shard 3   |                                  |
|  | A-H       | I-P       | Q-Z       |                                  |
|  +-----------+-----------+-----------+                                  |
|                                                                         |
|  2. HASH-BASED:                                                         |
|  ---------------                                                        |
|  * shard = hash(key) % num_shards                                       |
|  * Even distribution                                                    |
|  * Range queries require scatter-gather                                 |
|                                                                         |
|  hash("user_123") % 4 = 2  > Shard 2                                    |
|                                                                         |
|  3. CONSISTENT HASHING:                                                 |
|  ------------------------                                               |
|  * Minimize data movement when adding/removing nodes                    |
|  * Used in DynamoDB, Cassandra, Redis Cluster                           |
|                                                                         |
|        Node A                                                           |
|           o                                                             |
|      /         \                                                        |
|     /           \                                                       |
|    o             o                                                      |
|  Node D         Node B                                                  |
|     \           /                                                       |
|      \         /                                                        |
|           o                                                             |
|        Node C                                                           |
|                                                                         |
|  Keys map to points on ring > assigned to next node clockwise           |
|                                                                         |
|  4. DIRECTORY-BASED:                                                    |
|  ---------------------                                                  |
|  * Lookup service maps key > shard                                      |
|  * Most flexible                                                        |
|  * Directory can be bottleneck                                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CHOOSING SHARD KEY:                                                    |
|                                                                         |
|  Good: user_id (even distribution, natural partition)                   |
|  Bad: timestamp (all writes go to latest shard > hotspot)               |
|  Bad: country (US has way more data than Luxembourg)                    |
|                                                                         |
|  CROSS-SHARD QUERIES:                                                   |
|  * JOIN across shards is expensive                                      |
|  * Design to minimize cross-shard operations                            |
|  * Denormalize if needed                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 16.5 CACHING PATTERNS

```
+--------------------------------------------------------------------------+
|                    CACHE-ASIDE (LAZY LOADING)                            |
|                                                                          |
|  Application controls the cache:                                         |
|                                                                          |
|  READ:                                                                   |
|  1. Check cache                                                          |
|  2. Cache hit > return data                                              |
|  3. Cache miss > query DB > store in cache > return                      |
|                                                                          |
|  +---------+     1. Get      +---------+                                 |
|  |   App   | <--------------> |  Cache  |                                |
|  +----+----+     2. Miss      +---------+                                |
|       |                                                                  |
|       | 3. Query DB                                                      |
|       v                                                                  |
|  +---------+     4. Store     +---------+                                |
|  |   DB    | -----------------> |  Cache  |                              |
|  +---------+                  +---------+                                |
|                                                                          |
|  WRITE: Update DB, invalidate cache (or update)                          |
|                                                                          |
|  PROS: Only requested data cached, simple                                |
|  CONS: Cache miss penalty, potential stale data                          |
|                                                                          |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
|                    WRITE-THROUGH                                         |
|                                                                          |
|  Cache is always updated with DB:                                        |
|                                                                          |
|  WRITE:                                                                  |
|  1. Write to cache                                                       |
|  2. Cache synchronously writes to DB                                     |
|  3. Return success                                                       |
|                                                                          |
|  +---------+    Write     +---------+    Write     +---------+           |
|  |   App   | ------------> |  Cache  | ------------> |   DB    |         |
|  +---------+              +---------+              +---------+           |
|                                                                          |
|  PROS: Cache always consistent with DB                                   |
|  CONS: Write latency (double write), write-heavy = not ideal             |
|                                                                          |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
|                    WRITE-BEHIND (WRITE-BACK)                             |
|                                                                          |
|  Async write to DB:                                                      |
|                                                                          |
|  WRITE:                                                                  |
|  1. Write to cache                                                       |
|  2. Return success immediately                                           |
|  3. Async: flush to DB in batches                                        |
|                                                                          |
|  +---------+    Write     +---------+   Async      +---------+           |
|  |   App   | ------------> |  Cache  | ~~~~~~~~~~> |   DB    |           |
|  +---------+    (fast)    +---------+   (batch)   +---------+            |
|                                                                          |
|  PROS: Low write latency, batching reduces DB load                       |
|  CONS: Risk of data loss (cache crash before flush)                      |
|                                                                          |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
|                    READ-THROUGH                                          |
|                                                                          |
|  Cache handles DB interaction:                                           |
|                                                                          |
|  +---------+    Read      +---------+    Load      +---------+           |
|  |   App   | ------------> |  Cache  | ------------> |   DB    |         |
|  +---------+              +---------+   (on miss)  +---------+           |
|                                                                          |
|  * App only talks to cache                                               |
|  * Cache auto-loads from DB on miss                                      |
|  * Simpler app code                                                      |
|                                                                          |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
|                    CACHE INVALIDATION STRATEGIES                         |
|                                                                          |
|  TTL (Time To Live):                                                     |
|  ---------------------                                                   |
|  * Data expires after fixed time                                         |
|  * Simple, but may serve stale data                                      |
|  * Good for: Session data, API rate limits                               |
|                                                                          |
|  Event-Based Invalidation:                                               |
|  --------------------------                                              |
|  * On data change, explicitly invalidate/update cache                    |
|  * More complex, but always fresh                                        |
|  * Good for: Product catalog, user profiles                              |
|                                                                          |
|  Version-Based:                                                          |
|  ---------------                                                         |
|  * Include version in cache key: product:123:v5                          |
|  * On update, increment version                                          |
|  * Old cache entries expire naturally                                    |
|                                                                          |
|  ---------------------------------------------------------------------   |
|                                                                          |
|  CACHE EVICTION POLICIES:                                                |
|                                                                          |
|  LRU (Least Recently Used):                                              |
|  * Evict items not accessed recently                                     |
|  * Good general-purpose policy                                           |
|                                                                          |
|  LFU (Least Frequently Used):                                            |
|  * Evict items accessed least often                                      |
|  * Good for stable access patterns                                       |
|                                                                          |
|  FIFO (First In First Out):                                              |
|  * Evict oldest items                                                    |
|  * Simple, but not access-aware                                          |
|                                                                          |
|  Random:                                                                 |
|  * Random eviction                                                       |
|  * Surprisingly effective, O(1)                                          |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 16.6 LOAD BALANCING ALGORITHMS

```
+-------------------------------------------------------------------------+
|                    LOAD BALANCING ALGORITHMS                            |
|                                                                         |
|  1. ROUND ROBIN:                                                        |
|  -----------------                                                      |
|  Request 1 > Server A                                                   |
|  Request 2 > Server B                                                   |
|  Request 3 > Server C                                                   |
|  Request 4 > Server A  (cycle repeats)                                  |
|                                                                         |
|  Pros: Simple, fair distribution                                        |
|  Cons: Ignores server capacity/load                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  2. WEIGHTED ROUND ROBIN:                                               |
|  --------------------------                                             |
|  Server A (weight 3): Gets 3 requests per cycle                         |
|  Server B (weight 1): Gets 1 request per cycle                          |
|                                                                         |
|  Use when servers have different capacities                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  3. LEAST CONNECTIONS:                                                  |
|  -----------------------                                                |
|  Route to server with fewest active connections                         |
|                                                                         |
|  Server A: 5 connections                                                |
|  Server B: 2 connections  < Next request goes here                      |
|  Server C: 8 connections                                                |
|                                                                         |
|  Good for: Long-lived connections, varying request times                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  4. LEAST RESPONSE TIME:                                                |
|  --------------------------                                             |
|  Route to server with lowest average response time                      |
|                                                                         |
|  Server A: 50ms avg                                                     |
|  Server B: 30ms avg  < Next request goes here                           |
|  Server C: 45ms avg                                                     |
|                                                                         |
|  Adapts to real server performance                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  5. IP HASH:                                                            |
|  ------------                                                           |
|  server = hash(client_ip) % num_servers                                 |
|                                                                         |
|  Same client always goes to same server                                 |
|  Good for: Session affinity (sticky sessions)                           |
|  Bad: Uneven if client distribution skewed                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  6. RANDOM:                                                             |
|  -----------                                                            |
|  Randomly select a server                                               |
|  Simple, statistically even over time                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  7. RESOURCE-BASED:                                                     |
|  -------------------                                                    |
|  Route based on server metrics (CPU, memory)                            |
|  Requires health checks / agent on each server                          |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    LAYER 4 vs LAYER 7 LOAD BALANCING                    |
|                                                                         |
|  LAYER 4 (Transport):                                                   |
|  ---------------------                                                  |
|  * Operates at TCP/UDP level                                            |
|  * Forwards packets based on IP + Port                                  |
|  * Very fast (no packet inspection)                                     |
|  * No application awareness                                             |
|  * Examples: AWS NLB, HAProxy (TCP mode)                                |
|                                                                         |
|  LAYER 7 (Application):                                                 |
|  -----------------------                                                |
|  * Operates at HTTP level                                               |
|  * Can inspect headers, cookies, URL path                               |
|  * Content-based routing                                                |
|  * SSL termination                                                      |
|  * More overhead but more features                                      |
|  * Examples: AWS ALB, Nginx, HAProxy (HTTP mode)                        |
|                                                                         |
|  Example L7 routing:                                                    |
|  * /api/*     > API servers                                             |
|  * /static/*  > CDN                                                     |
|  * /admin/*   > Admin servers                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 16.7 RATE LIMITING ALGORITHMS

```
+-------------------------------------------------------------------------+
|                    TOKEN BUCKET                                         |
|                                                                         |
|  CONCEPT:                                                               |
|  * Bucket holds tokens (max capacity = bucket size)                     |
|  * Tokens added at fixed rate (e.g., 10/second)                         |
|  * Request consumes 1 token                                             |
|  * No token = request rejected                                          |
|                                                                         |
|         +---------------+                                               |
|         | o o o o o o o | < Bucket (capacity: 10)                       |
|         |   o o o       |                                               |
|         +-------+-------+                                               |
|                 |                                                       |
|    Tokens added |  Tokens consumed                                      |
|    at rate R    |  per request                                          |
|                 v                                                       |
|                                                                         |
|  PROS:                                                                  |
|  * Allows bursts (up to bucket size)                                    |
|  * Smooth rate limiting over time                                       |
|  * Memory efficient (just counter + timestamp)                          |
|                                                                         |
|  IMPLEMENTATION:                                                        |
|  tokens = min(bucket_size, tokens + (now - last_update) * rate)         |
|  if tokens >= 1:                                                        |
|      tokens -= 1                                                        |
|      allow_request()                                                    |
|  else:                                                                  |
|      reject_request()                                                   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    LEAKY BUCKET                                         |
|                                                                         |
|  CONCEPT:                                                               |
|  * Requests enter bucket (queue)                                        |
|  * Processed at fixed rate (leak rate)                                  |
|  * Bucket overflow = request rejected                                   |
|                                                                         |
|         +---------------+ < Requests enter                              |
|         | v v v v v v v |                                               |
|         |   Queue       | < Bucket (max size)                           |
|         |               |                                               |
|         +-------+-------+                                               |
|                 |                                                       |
|                 v Leak at fixed rate                                    |
|            (process requests)                                           |
|                                                                         |
|  PROS:                                                                  |
|  * Strict output rate (no bursts)                                       |
|  * Smooths out traffic                                                  |
|                                                                         |
|  CONS:                                                                  |
|  * No burst allowance                                                   |
|  * Old requests wait in queue                                           |
|                                                                         |
|  Use: When you need absolutely constant rate (API calls to external)    |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    FIXED WINDOW COUNTER                                 |
|                                                                         |
|  CONCEPT:                                                               |
|  * Divide time into fixed windows (e.g., 1 minute each)                 |
|  * Count requests per window                                            |
|  * Reset counter at window boundary                                     |
|                                                                         |
|  Window 1        Window 2        Window 3                               |
|  [0:00-1:00]     [1:00-2:00]     [2:00-3:00]                            |
|   Count: 50       Count: 45       Count: 30                             |
|   Limit: 100      Limit: 100      Limit: 100                            |
|                                                                         |
|  PROS:                                                                  |
|  * Very simple                                                          |
|  * Memory efficient (one counter per window)                            |
|                                                                         |
|  CONS:                                                                  |
|  * Burst at window edge: 100 at 0:59, 100 at 1:00 = 200 in 2 seconds    |
|                                                                         |
|    0:58   0:59 | 1:00   1:01                                            |
|      v     v   |   v     v                                              |
|      50    50  |  50    50  = 200 requests in 2 seconds!                |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    SLIDING WINDOW LOG                                   |
|                                                                         |
|  CONCEPT:                                                               |
|  * Store timestamp of each request                                      |
|  * Count requests in last N seconds                                     |
|  * Remove expired timestamps                                            |
|                                                                         |
|  Log: [1:00:01, 1:00:15, 1:00:30, 1:00:45]                              |
|  Now: 1:01:00                                                           |
|  Window: Last 60 seconds                                                |
|  Count: 4 requests in window                                            |
|                                                                         |
|  PROS:                                                                  |
|  * Accurate rate limiting                                               |
|  * No edge burst problem                                                |
|                                                                         |
|  CONS:                                                                  |
|  * Memory intensive (store all timestamps)                              |
|  * Slow at scale                                                        |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    SLIDING WINDOW COUNTER                               |
|                                                                         |
|  CONCEPT (Hybrid):                                                      |
|  * Combine fixed window + sliding                                       |
|  * Weight previous window by overlap                                    |
|                                                                         |
|  Previous window: 50 requests                                           |
|  Current window:  20 requests                                           |
|  Position in current window: 40%                                        |
|                                                                         |
|  Estimated count = (50 x 60%) + (20 x 100%) = 30 + 20 = 50              |
|                                                                         |
|  PROS:                                                                  |
|  * Memory efficient (just 2 counters)                                   |
|  * Good approximation                                                   |
|  * Smooths window edge bursts                                           |
|                                                                         |
|  This is what Redis rate limiters typically use                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 16.8 MESSAGE QUEUE SEMANTICS

```
+-------------------------------------------------------------------------+
|                    DELIVERY GUARANTEES                                  |
|                                                                         |
|  AT-MOST-ONCE:                                                          |
|  ---------------                                                        |
|  * Message delivered 0 or 1 times                                       |
|  * No retries on failure                                                |
|  * Fire and forget                                                      |
|                                                                         |
|  Producer > Queue > Consumer                                            |
|                  X (lost)                                               |
|                                                                         |
|  Use: Metrics, logs (loss acceptable)                                   |
|  Implementation: No acks, no persistence                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  AT-LEAST-ONCE:                                                         |
|  ----------------                                                       |
|  * Message delivered 1 or more times                                    |
|  * Retry until acknowledged                                             |
|  * May cause duplicates                                                 |
|                                                                         |
|  Producer > Queue > Consumer                                            |
|                  > Consumer (retry)                                     |
|                  > Consumer (retry again)                               |
|                  Y ACK                                                  |
|                                                                         |
|  Use: Most use cases (with idempotent consumers)                        |
|  Implementation: ACKs + retries + persistence                           |
|                                                                         |
|  CONSUMER MUST BE IDEMPOTENT:                                           |
|  * Same message processed twice = same result                           |
|  * Use idempotency key to dedupe                                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXACTLY-ONCE:                                                          |
|  ---------------                                                        |
|  * Message delivered exactly 1 time                                     |
|  * Hardest to achieve                                                   |
|  * Requires coordination between producer, queue, consumer              |
|                                                                         |
|  IMPLEMENTATION OPTIONS:                                                |
|  1. Idempotent producer + at-least-once + idempotent consumer           |
|     (effectively exactly-once)                                          |
|  2. Transactional outbox pattern                                        |
|  3. Kafka transactions (EOS)                                            |
|                                                                         |
|  Use: Financial transactions, inventory                                 |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    ORDERING GUARANTEES                                  |
|                                                                         |
|  NO ORDERING:                                                           |
|  -------------                                                          |
|  * Messages may arrive in any order                                     |
|  * Highest throughput                                                   |
|  * SQS Standard                                                         |
|                                                                         |
|  FIFO (Partition-level):                                                |
|  ------------------------                                               |
|  * Order preserved within partition/shard                               |
|  * Different partitions = no order guarantee                            |
|  * Kafka partitions, SQS FIFO                                           |
|                                                                         |
|  Kafka: Messages with same key > same partition > ordered               |
|                                                                         |
|  TOTAL ORDERING:                                                        |
|  -----------------                                                      |
|  * Global order across all messages                                     |
|  * Very limited throughput (single writer)                              |
|  * Rarely needed                                                        |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    PUSH vs PULL                                         |
|                                                                         |
|  PUSH (Queue pushes to consumer):                                       |
|  ---------------------------------                                      |
|  Queue --message--> Consumer                                            |
|                                                                         |
|  * Low latency                                                          |
|  * Consumer can be overwhelmed                                          |
|  * Need flow control                                                    |
|  * Example: WebSockets, RabbitMQ push                                   |
|                                                                         |
|  PULL (Consumer pulls from queue):                                      |
|  ----------------------------------                                     |
|  Queue <--poll---- Consumer                                             |
|                                                                         |
|  * Consumer controls rate                                               |
|  * Can batch messages                                                   |
|  * Polling overhead                                                     |
|  * Example: Kafka, SQS                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 16.9 MICROSERVICES PATTERNS

```
+-------------------------------------------------------------------------+
|                    SERVICE COMMUNICATION PATTERNS                       |
|                                                                         |
|  SYNCHRONOUS (Request-Response):                                        |
|  ------------------------------                                         |
|                                                                         |
|  Service A --HTTP/gRPC--> Service B                                     |
|           <--response----                                               |
|                                                                         |
|  * Caller waits for response                                            |
|  * Simple, familiar                                                     |
|  * Tight coupling                                                       |
|  * Cascading failures risk                                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ASYNCHRONOUS (Event-Driven):                                           |
|  -----------------------------                                          |
|                                                                         |
|  Service A --event--> Message Queue --event--> Service B                |
|         (fire & forget)                                                 |
|                                                                         |
|  * Loose coupling                                                       |
|  * Better fault isolation                                               |
|  * Higher complexity                                                    |
|  * Eventual consistency                                                 |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    CIRCUIT BREAKER                                      |
|                                                                         |
|  Prevents cascading failures when downstream service is unhealthy:      |
|                                                                         |
|  STATES:                                                                |
|                                                                         |
|  +---------+  Failures exceed  +----------+  Timeout   +-----------+    |
|  | CLOSED  | ---threshold----> |   OPEN   | ---------> |HALF-OPEN  |    |
|  |(normal) |                   |(fail fast)|           | (testing) |    |
|  +----+----+                   +-----+----+           +-----+-----+     |
|       |                              |                      |           |
|       |<---------Success-------------+------Failure---------+           |
|                                                                         |
|  CLOSED:    Normal operation, requests pass through                     |
|  OPEN:      Fast-fail all requests (return error immediately)           |
|  HALF-OPEN: Allow limited requests to test if service recovered         |
|                                                                         |
|  Example (Resilience4j):                                                |
|  @CircuitBreaker(name = "inventory")                                    |
|  public Stock checkInventory(String productId) {                        |
|      return inventoryService.getStock(productId);                       |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    BULKHEAD PATTERN                                     |
|                                                                         |
|  Isolate failures by partitioning resources:                            |
|                                                                         |
|  WITHOUT BULKHEAD:                                                      |
|  -----------------                                                      |
|  +-------------------------------------+                                |
|  |           Thread Pool (100)         |                                |
|  |  Service A, B, C share all threads  | < One slow service blocks all  |
|  +-------------------------------------+                                |
|                                                                         |
|  WITH BULKHEAD:                                                         |
|  ---------------                                                        |
|  +----------+ +----------+ +----------+                                 |
|  |Service A | |Service B | |Service C |                                 |
|  | Pool(30) | | Pool(40) | | Pool(30) | < Isolation                     |
|  +----------+ +----------+ +----------+                                 |
|                                                                         |
|  If Service A is slow, only its 30 threads blocked                      |
|  B and C continue working normally                                      |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    SAGA PATTERN (Recap)                                 |
|                                                                         |
|  Manage distributed transactions without 2PC:                           |
|                                                                         |
|  ORCHESTRATION:                                                         |
|  ---------------                                                        |
|  * Central coordinator manages workflow                                 |
|  * Coordinator calls each service                                       |
|  * On failure, calls compensating actions                               |
|                                                                         |
|  +------------+                                                         |
|  |Orchestrator|--1.Reserve inventory                                    |
|  |            |--2.Process payment                                      |
|  |            |--3.Create order                                         |
|  |            |--(on fail: compensate in reverse)                       |
|  +------------+                                                         |
|                                                                         |
|  CHOREOGRAPHY:                                                          |
|  --------------                                                         |
|  * No central coordinator                                               |
|  * Services react to events                                             |
|  * Each service knows what to do next                                   |
|                                                                         |
|  Inventory --InventoryReserved--> Payment --PaymentCompleted--> Order   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    SIDECAR PATTERN                                      |
|                                                                         |
|  Deploy helper functionality alongside main service:                    |
|                                                                         |
|  +-------------------------------------+                                |
|  |              POD                    |                                |
|  |  +---------------+ +-------------+ |                                 |
|  |  |   Main App    | |   Sidecar   | |                                 |
|  |  | (Your Service)| |  (Envoy/    | |                                 |
|  |  |               | |   Istio)    | |                                 |
|  |  +---------------+ +-------------+ |                                 |
|  +-------------------------------------+                                |
|                                                                         |
|  SIDECAR RESPONSIBILITIES:                                              |
|  * Service discovery                                                    |
|  * Load balancing                                                       |
|  * TLS termination                                                      |
|  * Metrics collection                                                   |
|  * Rate limiting                                                        |
|  * Circuit breaking                                                     |
|                                                                         |
|  Main app stays simple, sidecar handles cross-cutting concerns          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 16.10 API DESIGN PRINCIPLES

```
+-------------------------------------------------------------------------+
|                    REST API BEST PRACTICES                              |
|                                                                         |
|  RESOURCE NAMING:                                                       |
|  -----------------                                                      |
|  * Use nouns, not verbs: /products not /getProducts                     |
|  * Plural for collections: /users, /orders                              |
|  * Hierarchical: /users/123/orders                                      |
|                                                                         |
|  HTTP METHODS:                                                          |
|  --------------                                                         |
|  GET     /products        List products                                 |
|  GET     /products/123    Get single product                            |
|  POST    /products        Create product                                |
|  PUT     /products/123    Replace product                               |
|  PATCH   /products/123    Partial update                                |
|  DELETE  /products/123    Delete product                                |
|                                                                         |
|  STATUS CODES:                                                          |
|  --------------                                                         |
|  200 OK              Success                                            |
|  201 Created         Resource created                                   |
|  204 No Content      Success, no body (DELETE)                          |
|  400 Bad Request     Invalid input                                      |
|  401 Unauthorized    Authentication required                            |
|  403 Forbidden       Not allowed                                        |
|  404 Not Found       Resource doesn't exist                             |
|  409 Conflict        Conflict (duplicate, version mismatch)             |
|  422 Unprocessable   Validation failed                                  |
|  429 Too Many Req    Rate limited                                       |
|  500 Server Error    Internal error                                     |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    API VERSIONING                                       |
|                                                                         |
|  URL PATH (Most common):                                                |
|  ------------------------                                               |
|  /api/v1/products                                                       |
|  /api/v2/products                                                       |
|                                                                         |
|  QUERY PARAMETER:                                                       |
|  -----------------                                                      |
|  /api/products?version=1                                                |
|                                                                         |
|  HEADER:                                                                |
|  --------                                                               |
|  Accept: application/vnd.myapi.v1+json                                  |
|  X-API-Version: 1                                                       |
|                                                                         |
|  RECOMMENDATION:                                                        |
|  * URL path is most explicit and cacheable                              |
|  * Support N-1 versions (current + previous)                            |
|  * Deprecation notice before removal                                    |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    PAGINATION                                           |
|                                                                         |
|  OFFSET-BASED (Simple):                                                 |
|  -----------------------                                                |
|  GET /products?limit=20&offset=40                                       |
|                                                                         |
|  Response:                                                              |
|  {                                                                      |
|    "data": [...],                                                       |
|    "total": 1000,                                                       |
|    "limit": 20,                                                         |
|    "offset": 40                                                         |
|  }                                                                      |
|                                                                         |
|  CONS: Slow for large offsets (DB scans), inconsistent with changes     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CURSOR-BASED (Recommended):                                            |
|  -----------------------------                                          |
|  GET /products?limit=20&cursor=eyJpZCI6MTIzfQ==                         |
|                                                                         |
|  Response:                                                              |
|  {                                                                      |
|    "data": [...],                                                       |
|    "next_cursor": "eyJpZCI6MTQzfQ==",                                   |
|    "has_more": true                                                     |
|  }                                                                      |
|                                                                         |
|  PROS: Consistent, efficient (index scan), works with real-time data    |
|                                                                         |
|  Cursor = encoded last seen ID (base64 of {"id": 123})                  |
|  Query: WHERE id > cursor_id ORDER BY id LIMIT 20                       |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    IDEMPOTENCY                                          |
|                                                                         |
|  Same request multiple times = same result                              |
|                                                                         |
|  NATURALLY IDEMPOTENT:                                                  |
|  ---------------------                                                  |
|  GET, PUT, DELETE are naturally idempotent                              |
|  GET /products/123 - always returns same product                        |
|  PUT /products/123 - replaces with same data                            |
|  DELETE /products/123 - already deleted = no change                     |
|                                                                         |
|  NOT NATURALLY IDEMPOTENT:                                              |
|  --------------------------                                             |
|  POST - creates new resource each time                                  |
|  PATCH - might append                                                   |
|                                                                         |
|  MAKING POST IDEMPOTENT:                                                |
|  -------------------------                                              |
|  Client sends idempotency key:                                          |
|                                                                         |
|  POST /payments                                                         |
|  Idempotency-Key: abc-123-def-456                                       |
|                                                                         |
|  Server:                                                                |
|  1. Check if key exists in Redis/DB                                     |
|  2. If exists, return cached response                                   |
|  3. If not, process and store response with key                         |
|  4. TTL on key (24 hours)                                               |
|                                                                         |
|  Client can safely retry on timeout                                     |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    REST vs GraphQL vs gRPC                              |
|                                                                         |
|  +------------+-------------------+-----------------+----------------+  |
|  | Aspect     | REST              | GraphQL         | gRPC           |  |
|  +------------+-------------------+-----------------+----------------+  |
|  | Protocol   | HTTP              | HTTP            | HTTP/2         |  |
|  +------------+-------------------+-----------------+----------------+  |
|  | Format     | JSON              | JSON            | Protobuf       |  |
|  +------------+-------------------+-----------------+----------------+  |
|  | Contract   | OpenAPI (opt)     | Schema (req)    | Proto (req)    |  |
|  +------------+-------------------+-----------------+----------------+  |
|  | Fetching   | Over/under fetch  | Exact fields    | Defined types  |  |
|  +------------+-------------------+-----------------+----------------+  |
|  | Caching    | HTTP caching      | Complex         | No HTTP cache  |  |
|  +------------+-------------------+-----------------+----------------+  |
|  | Use case   | Public APIs,      | Flexible client | Internal,      |  |
|  |            | simple CRUD       | needs, mobile   | high perf      |  |
|  +------------+-------------------+-----------------+----------------+  |
|                                                                         |
|  CHOOSE:                                                                |
|  * REST: Simple, cacheable, public APIs                                 |
|  * GraphQL: Complex queries, mobile apps (minimize requests)            |
|  * gRPC: Service-to-service, streaming, high performance                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF DOCUMENT

