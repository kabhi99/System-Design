# E-COMMERCE SYSTEM DESIGN
*Chapter 1: Requirements and Scale Estimation*

E-commerce platforms like Amazon, Flipkart, and Shopify handle millions of
products, users, and transactions. This chapter covers the requirements
and scale considerations for designing such a system.

## SECTION 1.1: UNDERSTANDING E-COMMERCE

### WHAT IS AN E-COMMERCE PLATFORM?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  An e-commerce platform enables:                                        |
|                                                                         |
|  BUYERS:                                                                |
|  * Browse and search products                                           |
|  * View product details, reviews, ratings                               |
|  * Add items to cart                                                    |
|  * Checkout and pay                                                     |
|  * Track orders                                                         |
|                                                                         |
|  SELLERS:                                                               |
|  * List products with descriptions, images, prices                      |
|  * Manage inventory                                                     |
|  * Process orders                                                       |
|  * Handle returns                                                       |
|                                                                         |
|  PLATFORM:                                                              |
|  * Facilitate transactions                                              |
|  * Handle payments                                                      |
|  * Manage logistics/shipping                                            |
|  * Provide customer support                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### THE UNIQUE CHALLENGES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY IS E-COMMERCE HARD?                                                |
|                                                                         |
|  1. MASSIVE CATALOG                                                     |
|  ------------------                                                     |
|  Amazon has 350+ million products.                                      |
|  Search must be fast and relevant.                                      |
|  Catalog data comes from millions of sellers.                           |
|                                                                         |
|  2. INVENTORY MANAGEMENT                                                |
|  -------------------------                                              |
|  Real-time inventory across warehouses.                                 |
|  Race conditions: 2 users buy last item.                                |
|  Flash sales: 10,000 users want 100 items.                              |
|                                                                         |
|  3. TRAFFIC SPIKES                                                      |
|  ------------------                                                     |
|  Black Friday: 10-50x normal traffic.                                   |
|  Prime Day, Diwali sales.                                               |
|  System must scale and stay responsive.                                 |
|                                                                         |
|  4. DISTRIBUTED TRANSACTIONS                                            |
|  -----------------------------                                          |
|  Order involves: Inventory, Payment, Shipping, Notification.            |
|  Any step can fail.                                                     |
|  Need consistency across services.                                      |
|                                                                         |
|  5. PERSONALIZATION                                                     |
|  -------------------                                                    |
|  Recommendations based on user behavior.                                |
|  Search results personalized.                                           |
|  Requires ML pipelines at scale.                                        |
|                                                                         |
|  6. FRAUD PREVENTION                                                    |
|  --------------------                                                   |
|  Payment fraud, fake reviews, seller fraud.                             |
|  Real-time detection required.                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.2: FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS                                                |
|                                                                         |
|  1. USER MANAGEMENT                                                     |
|  ---------------------                                                  |
|  * Registration, login (email, phone, social)                           |
|  * Profile management                                                   |
|  * Multiple shipping addresses                                          |
|  * Order history                                                        |
|                                                                         |
|  2. PRODUCT CATALOG                                                     |
|  --------------------                                                   |
|  * Browse by category                                                   |
|  * Search with filters (price, brand, rating)                           |
|  * Product details (description, images, specs)                         |
|  * Reviews and ratings                                                  |
|  * Related products                                                     |
|                                                                         |
|  3. SHOPPING CART                                                       |
|  -----------------                                                      |
|  * Add/remove/update items                                              |
|  * Persist across sessions                                              |
|  * Price updates if product price changes                               |
|  * Apply coupons/discounts                                              |
|                                                                         |
|  4. CHECKOUT                                                            |
|  -----------                                                            |
|  * Shipping address selection                                           |
|  * Delivery options and dates                                           |
|  * Payment methods (cards, UPI, wallets, COD)                           |
|  * Order confirmation                                                   |
|                                                                         |
|  5. ORDER MANAGEMENT                                                    |
|  ---------------------                                                  |
|  * Order tracking                                                       |
|  * Order status updates                                                 |
|  * Cancellation                                                         |
|  * Returns and refunds                                                  |
|                                                                         |
|  6. INVENTORY (Seller side)                                             |
|  ----------------------------                                           |
|  * Stock management                                                     |
|  * Low stock alerts                                                     |
|  * Multi-warehouse inventory                                            |
|                                                                         |
|  7. SELLER PORTAL                                                       |
|  -----------------                                                      |
|  * Product listing                                                      |
|  * Order fulfillment                                                    |
|  * Sales analytics                                                      |
|  * Settlement and payouts                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.3: NON-FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NON-FUNCTIONAL REQUIREMENTS                                            |
|                                                                         |
|  1. AVAILABILITY                                                        |
|  --------------                                                         |
|  * 99.99% uptime                                                        |
|  * Critical: Cart, Checkout, Payment must be highly available           |
|  * Graceful degradation for non-critical features                       |
|                                                                         |
|  2. LATENCY                                                             |
|  ---------                                                              |
|  * Homepage: < 500ms                                                    |
|  * Search results: < 200ms                                              |
|  * Add to cart: < 100ms                                                 |
|  * Checkout page: < 1s                                                  |
|  * Payment processing: < 5s                                             |
|                                                                         |
|  3. CONSISTENCY                                                         |
|  -------------                                                          |
|  * Strong consistency for: Inventory, Payments, Orders                  |
|  * Eventual consistency OK for: Reviews, Recommendations                |
|                                                                         |
|  4. SCALABILITY                                                         |
|  -------------                                                          |
|  * Handle 10x traffic during sales                                      |
|  * Scale to millions of products                                        |
|  * Support thousands of concurrent checkouts                            |
|                                                                         |
|  5. DURABILITY                                                          |
|  -----------                                                            |
|  * Never lose an order or payment                                       |
|  * Replicated storage                                                   |
|  * Regular backups                                                      |
|                                                                         |
|  6. SECURITY                                                            |
|  ----------                                                             |
|  * PCI-DSS for payments                                                 |
|  * User data encryption                                                 |
|  * Fraud detection                                                      |
|  * Rate limiting and DDoS protection                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.4: SCALE ESTIMATION

Let's estimate the scale for a large e-commerce platform.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ASSUMPTIONS (Amazon-scale platform)                                    |
|                                                                         |
|  USERS:                                                                 |
|  * 500 million registered users                                         |
|  * 100 million monthly active users (MAU)                               |
|  * 30 million daily active users (DAU)                                  |
|                                                                         |
|  PRODUCTS:                                                              |
|  * 500 million products                                                 |
|  * 5 million sellers                                                    |
|  * 50 million categories/attributes                                     |
|                                                                         |
|  ORDERS:                                                                |
|  * 5 million orders per day (normal)                                    |
|  * 20 million orders per day (peak sale)                                |
|  * 3 items per order average                                            |
|                                                                         |
|  TRAFFIC:                                                               |
|  * 500 million page views per day                                       |
|  * 100 million search queries per day                                   |
|  * 50 million cart operations per day                                   |
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
|  * 500 million / 86,400 = ~5,800 RPS average                            |
|  * Peak (evening): 3x = ~17,000 RPS                                     |
|  * Sale event: 10x = ~58,000 RPS                                        |
|                                                                         |
|  SEARCH:                                                                |
|  * 100 million / 86,400 = ~1,160 RPS average                            |
|  * Peak: ~3,500 RPS                                                     |
|                                                                         |
|  ORDERS:                                                                |
|  * 5 million / 86,400 = ~58 orders/sec average                          |
|  * Peak: ~175 orders/sec                                                |
|  * Flash sale: 1000+ orders/sec in bursts                               |
|                                                                         |
|  CART OPERATIONS:                                                       |
|  * 50 million / 86,400 = ~580 RPS                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STORAGE CALCULATIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATA STORAGE ESTIMATES                                                 |
|                                                                         |
|  PRODUCTS:                                                              |
|  * 500 million products                                                 |
|  * ~5 KB per product (metadata)                                         |
|  * Total: 500M x 5KB = 2.5 TB                                           |
|                                                                         |
|  PRODUCT IMAGES:                                                        |
|  * 500 million products x 5 images x 500KB = 1.25 PB                    |
|  * (Served via CDN, stored in object storage)                           |
|                                                                         |
|  USERS:                                                                 |
|  * 500 million users x 1 KB = 500 GB                                    |
|                                                                         |
|  ORDERS:                                                                |
|  * 5 million orders/day x 365 x 5 years = 9 billion orders              |
|  * 9 billion x 2 KB = 18 TB                                             |
|                                                                         |
|  REVIEWS:                                                               |
|  * 1 billion reviews x 1 KB = 1 TB                                      |
|                                                                         |
|  TOTAL STRUCTURED DATA: ~25 TB                                          |
|  TOTAL MEDIA: ~1-2 PB                                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.5: SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  E-COMMERCE SCALE SUMMARY                                               |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  USERS                                                           |   |
|  |  -----                                                           |   |
|  |  MAU: 100 million                                                |   |
|  |  DAU: 30 million                                                 |   |
|  |  Peak concurrent: 3 million                                      |   |
|  |                                                                  |   |
|  |  PRODUCTS                                                        |   |
|  |  --------                                                        |   |
|  |  Total: 500 million                                              |   |
|  |  Sellers: 5 million                                              |   |
|  |                                                                  |   |
|  |  TRAFFIC                                                         |   |
|  |  -------                                                         |   |
|  |  Normal: ~6,000 RPS                                              |   |
|  |  Peak: ~60,000 RPS                                               |   |
|  |                                                                  |   |
|  |  ORDERS                                                          |   |
|  |  ------                                                          |   |
|  |  Daily: 5-20 million                                             |   |
|  |  Peak: 200+ orders/second                                        |   |
|  |                                                                  |   |
|  |  STORAGE                                                         |   |
|  |  -------                                                         |   |
|  |  Structured: ~25 TB                                              |   |
|  |  Media: ~1-2 PB                                                  |   |
|  |                                                                  |   |
|  |  KEY CHALLENGES                                                  |   |
|  |  --------------                                                  |   |
|  |  1. Inventory consistency                                        |   |
|  |  2. Search at scale                                              |   |
|  |  3. Flash sale handling                                          |   |
|  |  4. Distributed transactions                                     |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 1

