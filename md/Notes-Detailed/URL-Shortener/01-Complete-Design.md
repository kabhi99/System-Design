# URL SHORTENER SYSTEM DESIGN (BITLY / TINYURL)

A COMPLETE CONCEPTUAL GUIDE - NO CODE, PURE THEORY

## SECTION 1: UNDERSTANDING THE PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS A URL SHORTENER?                                               |
|                                                                         |
|  Converts long URLs into short, shareable links                         |
|                                                                         |
|  INPUT:  https://www.example.com/products/electronics/phones/           |
|          iphone-15-pro-max?color=blue&storage=256gb&ref=campaign123     |
|                                                                         |
|  OUTPUT: https://bit.ly/3xY7kLm                                         |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  WHY DO WE NEED IT?                                                     |
|                                                                         |
|  1. CHARACTER LIMITS                                                    |
|     * Twitter/SMS have character limits                                 |
|     * Long URLs consume valuable space                                  |
|                                                                         |
|  2. AESTHETICS                                                          |
|     * Short URLs look cleaner                                           |
|     * Easier to share verbally                                          |
|     * Fit on business cards, posters                                    |
|                                                                         |
|  3. TRACKING & ANALYTICS                                                |
|     * Track click counts                                                |
|     * Geographic distribution of clicks                                 |
|     * Referrer information                                              |
|     * Device/browser analytics                                          |
|                                                                         |
|  4. LINK MANAGEMENT                                                     |
|     * Update destination without changing short URL                     |
|     * Expire links after certain time                                   |
|     * A/B testing with same short URL                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS                                                |
|                                                                         |
|  1. URL SHORTENING                                                      |
|     * Given a long URL, generate a unique short URL                     |
|     * Optional: Allow custom aliases (bit.ly/my-brand)                  |
|     * Optional: Set expiration time                                     |
|                                                                         |
|  2. URL REDIRECTION                                                     |
|     * Given a short URL, redirect to original long URL                  |
|     * Handle expired/deleted URLs gracefully                            |
|                                                                         |
|  3. ANALYTICS (Optional but expected)                                   |
|     * Track number of clicks                                            |
|     * Track when clicks happened                                        |
|     * Geographic and device information                                 |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  NON-FUNCTIONAL REQUIREMENTS                                            |
|                                                                         |
|  1. HIGH AVAILABILITY                                                   |
|     * Service must be always available                                  |
|     * Broken links = lost traffic = lost revenue                        |
|                                                                         |
|  2. LOW LATENCY                                                         |
|     * Redirection must be fast (< 100ms)                                |
|     * Every millisecond of delay = user frustration                     |
|                                                                         |
|  3. SCALABILITY                                                         |
|     * Handle billions of URLs                                           |
|     * Handle millions of redirects per day                              |
|                                                                         |
|  4. UNPREDICTABILITY                                                    |
|     * Short URLs should not be guessable                                |
|     * Security consideration: prevent enumeration                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3: SCALE ESTIMATION (BACK OF ENVELOPE)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TRAFFIC ESTIMATES                                                      |
|                                                                         |
|  Assumptions:                                                           |
|  * 100 million new URLs shortened per month                             |
|  * Read:Write ratio = 100:1 (reads >> writes)                           |
|  * Service runs for 10 years                                            |
|                                                                         |
|  WRITES (URL Creation):                                                 |
|  * 100 million / month                                                  |
|  * 100M / (30 x 24 x 3600) ~ 40 URLs per second                         |
|                                                                         |
|  READS (Redirections):                                                  |
|  * 100:1 ratio means 100 x 40 = 4,000 redirects per second              |
|  * Peak: 5x average = 20,000 redirects per second                       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  STORAGE ESTIMATES                                                      |
|                                                                         |
|  Total URLs over 10 years:                                              |
|  * 100 million x 12 months x 10 years = 12 billion URLs                 |
|                                                                         |
|  Storage per URL:                                                       |
|  * Short URL (7 chars):     7 bytes                                     |
|  * Long URL (avg 200 chars): 200 bytes                                  |
|  * Created timestamp:        8 bytes                                    |
|  * Expiry timestamp:         8 bytes                                    |
|  * User ID:                  8 bytes                                    |
|  * Click count:              4 bytes                                    |
|  * Total:                   ~250 bytes per URL                          |
|                                                                         |
|  Total storage:                                                         |
|  * 12 billion x 250 bytes = 3 TB                                        |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  SHORT URL LENGTH CALCULATION                                           |
|                                                                         |
|  How many characters do we need?                                        |
|                                                                         |
|  Characters available: [a-z, A-Z, 0-9] = 62 characters                  |
|                                                                         |
|  Possible combinations:                                                 |
|  * 6 characters: 62^6 = 56 billion combinations                         |
|  * 7 characters: 62^7 = 3.5 trillion combinations                       |
|                                                                         |
|  For 12 billion URLs, 7 characters is MORE than enough                  |
|  (Even 6 would work, but 7 gives room for growth)                       |
|                                                                         |
|  FINAL ANSWER: 7 character short codes                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SYSTEM COMPONENTS                                                      |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |                         CLIENTS                                   |  |
|  |           (Web, Mobile, API integrations)                         |  |
|  |                          |                                        |  |
|  |                          v                                        |  |
|  |            +-----------------------------+                        |  |
|  |            |      LOAD BALANCER         |                         |  |
|  |            |   (NGINX / AWS ALB)        |                         |  |
|  |            +-------------+---------------+                        |  |
|  |                          |                                        |  |
|  |         +----------------+----------------+                       |  |
|  |         |                |                |                       |  |
|  |         v                v                v                       |  |
|  |    +---------+     +---------+     +---------+                    |  |
|  |    | Server  |     | Server  |     | Server  |                    |  |
|  |    |    1    |     |    2    |     |    3    |                    |  |
|  |    +----+----+     +----+----+     +----+----+                    |  |
|  |         |                |                |                       |  |
|  |         +----------------+----------------+                       |  |
|  |                          |                                        |  |
|  |              +-----------+-----------+                            |  |
|  |              |                       |                            |  |
|  |              v                       v                            |  |
|  |    +-----------------+    +-----------------+                     |  |
|  |    |     CACHE       |    |    DATABASE     |                     |  |
|  |    |    (Redis)      |    |  (PostgreSQL/   |                     |  |
|  |    |                 |    |   Cassandra)    |                     |  |
|  |    |  Hot URLs       |    |  All mappings   |                     |  |
|  |    +-----------------+    +-----------------+                     |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  TWO MAIN FLOWS                                                         |
|                                                                         |
|  FLOW 1: URL SHORTENING (Write Path)                                    |
|  ------------------------------------                                   |
|                                                                         |
|    Client                                                               |
|      |                                                                  |
|      |  POST /shorten                                                   |
|      |  { "long_url": "https://..." }                                   |
|      v                                                                  |
|    Server                                                               |
|      |                                                                  |
|      +-- 1. Validate URL format                                         |
|      |                                                                  |
|      +-- 2. Check if URL already shortened (optional dedup)             |
|      |                                                                  |
|      +-- 3. Generate unique short code                                  |
|      |                                                                  |
|      +-- 4. Store mapping in database                                   |
|      |      short_code > long_url                                       |
|      |                                                                  |
|      +-- 5. Return short URL                                            |
|            { "short_url": "https://bit.ly/xY7kLm" }                     |
|                                                                         |
|                                                                         |
|  FLOW 2: URL REDIRECTION (Read Path)                                    |
|  -----------------------------------                                    |
|                                                                         |
|    Client                                                               |
|      |                                                                  |
|      |  GET /xY7kLm                                                     |
|      v                                                                  |
|    Server                                                               |
|      |                                                                  |
|      +-- 1. Extract short code from URL                                 |
|      |                                                                  |
|      +-- 2. Check cache (Redis)                                         |
|      |      +-- If found: return immediately                            |
|      |                                                                  |
|      +-- 3. If not in cache: query database                             |
|      |      +-- Store result in cache                                   |
|      |                                                                  |
|      +-- 4. If not found: return 404                                    |
|      |                                                                  |
|      +-- 5. Log analytics (async)                                       |
|      |                                                                  |
|      +-- 6. Return 301/302 redirect to long URL                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5: THE CORE PROBLEM - GENERATING UNIQUE SHORT CODES

```
+--------------------------------------------------------------------------+
|                                                                          |
|  This is the KEY interview discussion point!                             |
|                                                                          |
|  The challenge: Generate unique, short, non-guessable codes              |
|  at scale across multiple servers without collisions.                    |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  APPROACH 1: HASH THE LONG URL                                           |
|                                                                          |
|  Concept:                                                                |
|  * Apply hash function (MD5, SHA256) to long URL                         |
|  * Take first 7 characters of hash                                       |
|                                                                          |
|  Example:                                                                |
|  MD5("https://example.com/long") = "d41d8cd98f00b204..."                 |
|  Short code = "d41d8cd" (first 7 chars)                                  |
|                                                                          |
|  PROBLEM: COLLISIONS                                                     |
|  * Different URLs can produce same first 7 characters                    |
|  * With billions of URLs, collisions are GUARANTEED                      |
|                                                                          |
|  COLLISION HANDLING OPTIONS:                                             |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  Option A: Append counter until unique                             |  |
|  |  hash(url) > collision? > hash(url + "1") > collision?             |  |
|  |            > hash(url + "2") > ... until no collision              |  |
|  |                                                                    |  |
|  |  Option B: Use longer hash portion                                 |  |
|  |  Start with 7 chars, if collision, try 8, 9, etc.                  |  |
|  |                                                                    |  |
|  |  Both require: Check database for each attempt (slow!)             |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  VERDICT: Works but collision handling adds complexity                   |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  APPROACH 2: RANDOM STRING GENERATION                                    |
|                                                                          |
|  Concept:                                                                |
|  * Generate random 7-character string                                    |
|  * Check if it exists in database                                        |
|  * If exists, generate another random string                             |
|                                                                          |
|  PROBLEMS:                                                               |
|  * Still need database check (extra latency)                             |
|  * As database fills up, more collisions, more retries                   |
|  * Race condition: two servers generate same code simultaneously         |
|                                                                          |
|  VERDICT: Simple but doesn't scale well                                  |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  APPROACH 3: COUNTER-BASED (Database Auto-Increment)                     |
|                                                                          |
|  Concept:                                                                |
|  * Database generates auto-increment ID (1, 2, 3, ...)                   |
|  * Convert ID to base62 string                                           |
|                                                                          |
|  Example:                                                                |
|  ID = 12345 > Base62 = "3d7"                                             |
|  ID = 999999999 > Base62 = "15ftgG"                                      |
|                                                                          |
|  Base62 encoding:                                                        |
|  Characters: 0-9 (10) + a-z (26) + A-Z (26) = 62 characters              |
|                                                                          |
|  PROBLEMS:                                                               |
|  * PREDICTABLE! If I see "abc123", next is likely "abc124"               |
|  * Security risk: Easy to enumerate all URLs                             |
|  * Single point of failure (one DB counter)                              |
|                                                                          |
|  VERDICT: Fast, no collisions, but predictable                           |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  APPROACH 4: COUNTER + KEY RANGE (Distributed Counters)  BEST            |
|                                                                          |
|  Concept:                                                                |
|  * Pre-allocate ranges of IDs to each server                             |
|  * Each server generates IDs from its range locally                      |
|  * Convert to base62 when needed                                         |
|                                                                          |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  KEY GENERATION SERVICE (Centralized)                              |  |
|  |                                                                    |  |
|  |    "Give me a range of 1 million IDs"                              |  |
|  |                                                                    |  |
|  |  +------------------------------------------------------------+    |  |
|  |  |                                                            |    |  |
|  |  |  Server 1: Range 1 - 1,000,000                            |     |  |
|  |  |  Server 2: Range 1,000,001 - 2,000,000                    |     |  |
|  |  |  Server 3: Range 2,000,001 - 3,000,000                    |     |  |
|  |  |  ...                                                        |   |  |
|  |  |                                                            |    |  |
|  |  +------------------------------------------------------------+    |  |
|  |                                                                    |  |
|  |  Each server increments locally within its range                   |  |
|  |  When range exhausted, request new range                           |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  BENEFITS:                                                               |
|  * No database check needed (guaranteed unique within range)             |
|  * Very fast (local increment)                                           |
|  * No collisions                                                         |
|  * Horizontally scalable                                                 |
|                                                                          |
|  Still predictable? Combine with:                                        |
|  * Shuffle/scramble the ID before base62 encoding                        |
|  * Use a reversible encoding that looks random                           |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  APPROACH 5: PRE-GENERATED KEYS (Key Database)                           |
|                                                                          |
|  Concept:                                                                |
|  * Pre-generate millions of unique short codes offline                   |
|  * Store in separate "key database"                                      |
|  * When needed, fetch a batch of unused keys                             |
|                                                                          |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  KEY DATABASE                                                      |  |
|  |                                                                    |  |
|  |  +----------------+----------------+                               |  |
|  |  |  USED KEYS     |  UNUSED KEYS   |                               |  |
|  |  |                |                |                               |  |
|  |  |  abc1234       |  xyz9876  <--- Server 1 takes batch            |  |
|  |  |  def5678       |  mno5432       |                               |  |
|  |  |  ghi9012       |  pqr1098       |                               |  |
|  |  |  ...           |  ...           |                               |  |
|  |  +----------------+----------------+                               |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  How it works:                                                           |
|  1. Worker generates keys offline (random or sequential + shuffle)       |
|  2. Server requests batch (e.g., 1000 keys)                              |
|  3. Keys moved from "unused" to "used" atomically                        |
|  4. Server uses keys from local batch                                    |
|  5. When batch depleted, fetch new batch                                 |
|                                                                          |
|  BENEFITS:                                                               |
|  * Zero collisions (pre-verified unique)                                 |
|  * Fast (no generation logic at request time)                            |
|  * Can be truly random (pre-shuffled)                                    |
|                                                                          |
|  DRAWBACKS:                                                              |
|  * Need to pre-generate and maintain key database                        |
|  * Slightly more complex architecture                                    |
|                                                                          |
|  VERDICT: Excellent choice for production systems                        |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 6: DATABASE DESIGN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATABASE SCHEMA                                                        |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  TABLE: url_mappings                                              |  |
|  |                                                                   |  |
|  |  +-----------------+---------------+--------------------------+   |  |
|  |  | Column          | Type          | Description              |   |  |
|  |  +-----------------+---------------+--------------------------+   |  |
|  |  | short_code      | VARCHAR(7)    | Primary Key, indexed    |    |  |
|  |  | long_url        | VARCHAR(2048) | Original URL            |    |  |
|  |  | user_id         | BIGINT        | Who created it          |    |  |
|  |  | created_at      | TIMESTAMP     | Creation time           |    |  |
|  |  | expires_at      | TIMESTAMP     | Optional expiry         |    |  |
|  |  | click_count     | BIGINT        | Number of redirects     |    |  |
|  |  +-----------------+---------------+--------------------------+   |  |
|  |                                                                   |  |
|  |  INDEXES:                                                         |  |
|  |  * Primary: short_code (for redirects)                            |  |
|  |  * Secondary: user_id (for "my URLs" queries)                     |  |
|  |  * Secondary: long_url hash (for duplicate detection)             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  DATABASE CHOICE                                                        |
|                                                                         |
|  OPTION 1: Relational (PostgreSQL, MySQL)                               |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  PROS:                                                            |  |
|  |  * ACID transactions                                              |  |
|  |  * Rich querying for analytics                                    |  |
|  |  * Mature, well-understood                                        |  |
|  |                                                                   |  |
|  |  CONS:                                                            |  |
|  |  * Scaling requires sharding (complex)                            |  |
|  |  * Not as fast for simple key-value lookups                       |  |
|  |                                                                   |  |
|  |  VERDICT: Good for most scales (with read replicas)               |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  OPTION 2: NoSQL (Cassandra, DynamoDB)                                  |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  PROS:                                                            |  |
|  |  * Horizontal scaling built-in                                    |  |
|  |  * Very fast key-value lookups                                    |  |
|  |  * High write throughput                                          |  |
|  |                                                                   |  |
|  |  CONS:                                                            |  |
|  |  * Limited query flexibility                                      |  |
|  |  * Eventually consistent (usually fine for this use case)         |  |
|  |                                                                   |  |
|  |  VERDICT: Best for very high scale (billions of URLs)             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  SHARDING STRATEGY (If needed)                                          |
|                                                                         |
|  Shard by: First character of short_code                                |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Shard A-L: Codes starting with A-L                               |  |
|  |  Shard M-Z: Codes starting with M-Z                               |  |
|  |  Shard 0-9: Codes starting with 0-9                               |  |
|  |                                                                   |  |
|  |  Or use consistent hashing on short_code                          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Why short_code for sharding?                                           |
|  * All reads use short_code (redirects hit exactly one shard)           |
|  * Evenly distributed (random/sequential codes)                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7: CACHING STRATEGY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY CACHING IS CRITICAL                                                |
|                                                                         |
|  * Read:Write ratio is 100:1                                            |
|  * Same popular URLs accessed repeatedly                                |
|  * Database lookup for every redirect is wasteful                       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  CACHING ARCHITECTURE                                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |   Request: GET /xY7kLm                                            |  |
|  |           |                                                       |  |
|  |           v                                                       |  |
|  |   +-----------------------------------------------------------+   |  |
|  |   |              CHECK CACHE (Redis)                          |   |  |
|  |   |                                                           |   |  |
|  |   |   Key: "url:xY7kLm"                                       |   |  |
|  |   |   Value: "https://example.com/very/long/url..."           |   |  |
|  |   |                                                           |   |  |
|  |   +-------------------+---------------------------------------+   |  |
|  |                       |                                           |  |
|  |         +-------------+-------------+                             |  |
|  |         |                           |                             |  |
|  |    CACHE HIT                   CACHE MISS                         |  |
|  |         |                           |                             |  |
|  |         v                           v                             |  |
|  |   Return long URL            Query Database                       |  |
|  |   (< 1ms)                         |                               |  |
|  |                                   |                               |  |
|  |                                   v                               |  |
|  |                            Store in Cache                         |  |
|  |                            (with TTL)                             |  |
|  |                                   |                               |  |
|  |                                   v                               |  |
|  |                            Return long URL                        |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  CACHE EVICTION POLICY                                                  |
|                                                                         |
|  LRU (Least Recently Used) - Best for URL shortener                     |
|                                                                         |
|  Why?                                                                   |
|  * Recently accessed URLs likely to be accessed again                   |
|  * Old/viral URLs eventually drop off                                   |
|  * 80/20 rule: 20% of URLs get 80% of traffic                           |
|                                                                         |
|  Cache size: Calculate based on memory budget                           |
|  Example: 1 million entries x 300 bytes = 300 MB                        |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  CACHE CONSIDERATIONS                                                   |
|                                                                         |
|  1. What if URL is updated/deleted?                                     |
|     * Write-through: Update cache when DB updates                       |
|     * TTL: Cache expires after X hours (slight staleness OK)            |
|     * For URL shortener, URLs rarely change > TTL is fine               |
|                                                                         |
|  2. Cache warming                                                       |
|     * Pre-load popular URLs on startup                                  |
|     * Prevents thundering herd on cold start                            |
|                                                                         |
|  3. Multi-region caching                                                |
|     * CDN caches at edge                                                |
|     * Redis in each region                                              |
|     * Reduces latency for global users                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8: REDIRECTION - 301 vs 302

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HTTP REDIRECT STATUS CODES                                             |
|                                                                         |
|  301 MOVED PERMANENTLY                                                  |
|  -----------------------                                                |
|  * Browser caches the redirect                                          |
|  * Next time, browser goes directly to long URL                         |
|  * Skips your server entirely on subsequent visits                      |
|                                                                         |
|  302 FOUND (Temporary Redirect)                                         |
|  -----------------------------                                          |
|  * Browser does NOT cache                                               |
|  * Every click goes through your server                                 |
|  * Allows tracking every click                                          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  WHICH TO USE?                                                          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  USE 301 (Permanent) when:                                        |  |
|  |  * You don't need analytics                                       |  |
|  |  * You want to reduce server load                                 |  |
|  |  * SEO is important (passes link juice)                           |  |
|  |                                                                   |  |
|  |  USE 302 (Temporary) when:                                        |  |
|  |  * You need to track EVERY click                                  |  |
|  |  * URL might change destination later                             |  |
|  |  * Analytics is a primary feature                                 |  |
|  |                                                                   |  |
|  |  RECOMMENDATION for URL shortener: 302                            |  |
|  |  (Analytics is core feature of services like Bitly)               |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: ANALYTICS SYSTEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT TO TRACK                                                          |
|                                                                         |
|  * Total click count                                                    |
|  * Clicks over time (hourly, daily trends)                              |
|  * Geographic distribution (country, city)                              |
|  * Referrer (where did click come from)                                 |
|  * Device type (mobile, desktop, tablet)                                |
|  * Browser and OS                                                       |
|  * Unique visitors vs total clicks                                      |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ARCHITECTURE FOR ANALYTICS                                             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |   Click Event                                                     |  |
|  |       |                                                           |  |
|  |       |  Don't block redirect!                                    |  |
|  |       |  (async processing)                                       |  |
|  |       |                                                           |  |
|  |       +-----------------> REDIRECT immediately (302)              |  |
|  |       |                                                           |  |
|  |       +-----------------> QUEUE event (Kafka/SQS)                 |  |
|  |                                |                                  |  |
|  |                                v                                  |  |
|  |                      +-----------------+                          |  |
|  |                      |  Analytics      |                          |  |
|  |                      |  Worker         |                          |  |
|  |                      +--------+--------+                          |  |
|  |                               |                                   |  |
|  |                    +----------+----------+                        |  |
|  |                    |                     |                        |  |
|  |                    v                     v                        |  |
|  |           +---------------+     +---------------+                 |  |
|  |           | Real-time     |     | Batch         |                 |  |
|  |           | Counters      |     | Analytics     |                 |  |
|  |           | (Redis)       |     | (Data Lake)   |                 |  |
|  |           +---------------+     +---------------+                 |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  KEY INSIGHT: Never let analytics slow down redirects!                  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  CLICK EVENT DATA                                                       |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Click Event:                                                     |  |
|  |  {                                                                |  |
|  |    "short_code": "xY7kLm",                                        |  |
|  |    "timestamp": "2024-01-15T10:30:00Z",                           |  |
|  |    "ip_address": "1.2.3.4",   (for geo lookup)                    |  |
|  |    "user_agent": "Mozilla...", (for device/browser)               |  |
|  |    "referrer": "https://twitter.com/...",                         |  |
|  |    "country": "US",            (from IP lookup)                   |  |
|  |    "city": "New York"                                             |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10: ADDITIONAL FEATURES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. CUSTOM ALIASES                                                      |
|                                                                         |
|  Allow users to create custom short codes:                              |
|  * bit.ly/my-product-launch                                             |
|  * bit.ly/john-resume                                                   |
|                                                                         |
|  Considerations:                                                        |
|  * Check if custom alias is available                                   |
|  * Validate (no offensive words, min/max length)                        |
|  * May charge premium for custom aliases                                |
|  * Reserve common words (help, about, login)                            |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  2. URL EXPIRATION                                                      |
|                                                                         |
|  Allow URLs to expire after certain time:                               |
|  * Promotional links (expire after campaign)                            |
|  * Temporary sharing (expire in 24 hours)                               |
|                                                                         |
|  Implementation:                                                        |
|  * Store expires_at timestamp                                           |
|  * Check on redirect: if expired, return 410 Gone                       |
|  * Background job to clean up expired URLs                              |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  3. RATE LIMITING                                                       |
|                                                                         |
|  Prevent abuse:                                                         |
|  * Limit URL creation per user/IP                                       |
|  * Free tier: 100 URLs/month                                            |
|  * Paid tier: 10,000 URLs/month                                         |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  4. SPAM/MALWARE DETECTION                                              |
|                                                                         |
|  Prevent malicious use:                                                 |
|  * Check URLs against malware databases (Google Safe Browsing)          |
|  * Block known phishing domains                                         |
|  * Show warning page for suspicious URLs                                |
|  * Allow users to report malicious links                                |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  5. API FOR DEVELOPERS                                                  |
|                                                                         |
|  RESTful API:                                                           |
|  * POST /api/shorten - Create short URL                                 |
|  * GET /api/{code}/stats - Get analytics                                |
|  * DELETE /api/{code} - Delete URL                                      |
|                                                                         |
|  Authentication:                                                        |
|  * API keys for developers                                              |
|  * OAuth for third-party apps                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11: TRADE-OFFS AND DESIGN DECISIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DECISION 1: Same long URL = Same short URL?                            |
|  ---------------------------------------------                          |
|                                                                         |
|  Option A: Always generate new short URL                                |
|  * Simpler implementation                                               |
|  * User A and User B get different short URLs for same long URL         |
|  * Better for user-specific analytics                                   |
|                                                                         |
|  Option B: Return existing short URL if long URL was shortened before   |
|  * Saves storage                                                        |
|  * Requires index on long_url (slower writes)                           |
|  * What about different expiry times?                                   |
|                                                                         |
|  RECOMMENDATION: Option A (simpler, better analytics per user)          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  DECISION 2: How to handle deleted/expired URLs?                        |
|  -------------------------------------------------                      |
|                                                                         |
|  Option A: Return 404 Not Found                                         |
|  * Simple, clear to user                                                |
|                                                                         |
|  Option B: Return 410 Gone                                              |
|  * More semantically correct for "was here, now gone"                   |
|  * Better for SEO                                                       |
|                                                                         |
|  Option C: Redirect to a "URL expired" page                             |
|  * Better user experience                                               |
|  * Opportunity to upsell/show ads                                       |
|                                                                         |
|  RECOMMENDATION: Combination - 410 with custom page                     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  DECISION 3: Short code in path vs subdomain?                           |
|  ---------------------------------------------                          |
|                                                                         |
|  Path style:     bit.ly/xY7kLm                                          |
|  Subdomain:      xY7kLm.bit.ly                                          |
|                                                                         |
|  Path is standard (bit.ly, tinyurl.com)                                 |
|  Subdomain requires wildcard DNS setup                                  |
|                                                                         |
|  RECOMMENDATION: Path style (simpler, standard)                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12: DESIGN ALTERNATIVES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ALTERNATIVE 1: REDIRECT AT CDN vs APPLICATION                          |
|                                                                         |
|  OPTION A: Redirect at Application Server (Standard)                    |
|  Client -> CDN -> Load Balancer -> App Server -> Cache/DB -> 302        |
|                                                                         |
|  Y Full control over redirect logic                                     |
|  Y Analytics on every click                                             |
|  Y Can check expiry, spam, A/B test                                     |
|  X Extra network hop (higher latency)                                   |
|  X App server handles all redirect traffic                              |
|                                                                         |
|  OPTION B: Redirect at CDN Edge (Cloudflare Workers / Lambda@Edge)      |
|  Client -> CDN Edge -> 302 (no origin hit!)                             |
|                                                                         |
|  Y Sub-10ms redirects (edge is closest to user)                         |
|  Y No load on app servers for redirects                                 |
|  Y Massively scalable (CDN handles millions of req/s)                   |
|  X Limited logic at edge (hard to do complex checks)                    |
|  X Analytics must be async (log to Kafka from edge)                     |
|  X Cache invalidation harder (URL update/delete)                        |
|                                                                         |
|  WHEN TO USE WHICH:                                                     |
|  * Small-medium scale: App server (simpler, full control)               |
|  * High scale (1M+ redirects/sec): CDN edge                             |
|  * Bitly/TinyURL: Hybrid (CDN for hot URLs, app for long tail)          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ALTERNATIVE 2: SQL vs NoSQL vs PURE KEY-VALUE                          |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  | Approach       | Latency   | Scale        | Analytics  | Cost   |    |
|  |----------------+-----------+--------------+------------+--------|    |
|  | PostgreSQL     | ~5ms      | Millions     | Rich SQL   | Low    |    |
|  | + read replica |           |              |            |        |    |
|  |                |           |              |            |        |    |
|  | Cassandra /    | ~2ms      | Billions     | Limited    | Medium |    |
|  | DynamoDB       |           |              |            |        |    |
|  |                |           |              |            |        |    |
|  | Redis (primary)| ~0.5ms   | Millions     | None       | High    |    |
|  | + disk backup  |           | (memory cap) |            | (RAM)  |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  TRADE-OFF:                                                             |
|  * PostgreSQL: best if you need analytics queries (GROUP BY, joins)     |
|  * Cassandra: best for massive write throughput + horizontal scale      |
|  * Redis as primary: fastest but expensive (all data in memory)         |
|    Works if dataset fits in memory (~100M URLs x 300B = 30 GB)          |
|  * DynamoDB: serverless, auto-scales, pay-per-request pricing           |
|    Great for unpredictable traffic patterns                             |
|                                                                         |
|  RECOMMENDATION: PostgreSQL + Redis cache for most cases                |
|  At extreme scale: DynamoDB/Cassandra + Redis cache                     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ALTERNATIVE 3: MONOLITH vs MICROSERVICES                               |
|                                                                         |
|  MONOLITH (Recommended for URL shortener):                              |
|  * Simple system -- one service handles create + redirect + analytics   |
|  * Easier to deploy, debug, operate                                     |
|  * URL shortener is NOT complex enough to justify microservices         |
|                                                                         |
|  MICROSERVICES (Only at massive scale):                                 |
|  * URL Service: create/delete/update URLs                               |
|  * Redirect Service: handle redirects (highest traffic)                 |
|  * Analytics Service: process click events                              |
|  * Key Generation Service: manage unique codes                          |
|                                                                         |
|  WHY SPLIT?                                                             |
|  * Redirect Service needs 10x more instances than URL Service           |
|  * Analytics can tolerate delay, redirect cannot                        |
|  * Independent scaling and deployment                                   |
|                                                                         |
|  INTERVIEW TIP: Start with monolith, explain when you'd split           |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ALTERNATIVE 4: SNOWFLAKE ID vs BASE62 vs NANO ID                       |
|                                                                         |
|  Base62 (counter-based):                                                |
|  * Deterministic length based on counter value                          |
|  * Predictable (sequential IDs visible)                                 |
|  * Need to shuffle/scramble for security                                |
|                                                                         |
|  Snowflake ID + Base62:                                                 |
|  * 64-bit ID: timestamp + machine_id + sequence                         |
|  * Distributed, no coordination needed                                  |
|  * But encodes to 11 chars in base62 (longer than ideal 7)              |
|                                                                         |
|  NanoID / KSUID:                                                        |
|  * Cryptographically random, configurable length                        |
|  * No coordination, no collision at 7 chars for millions                |
|  * But need DB uniqueness check (collision possible at scale)           |
|                                                                         |
|  BEST: Counter + key range + scramble (Approach 4 from Section 5)       |
|  Gives you: short (7 chars), unique (guaranteed), non-predictable       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 13: COMMON ISSUES AND FAILURE SCENARIOS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ISSUE 1: HOT KEY PROBLEM                                               |
|                                                                         |
|  Problem:                                                               |
|  A celebrity tweets a short URL. Millions of redirects in seconds.      |
|  All requests hit the SAME cache key and SAME DB row.                   |
|  Redis node holding that key becomes bottleneck.                        |
|                                                                         |
|  Solution:                                                              |
|  * CDN absorbs most traffic (302 redirect cached briefly at edge)       |
|  * Redis read replicas (spread reads across replicas)                   |
|  * Local in-process cache (each app server caches top 1000 URLs)        |
|  * Cache the redirect at CDN with 30-60s TTL                            |
|    (small analytics loss but massive scalability gain)                  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ISSUE 2: KEY GENERATION SERVICE FAILURE                                |
|                                                                         |
|  Problem:                                                               |
|  Central key range allocator goes down. No new ranges can be issued.    |
|  Servers with exhausted ranges can't create new short URLs.             |
|                                                                         |
|  Solution:                                                              |
|  * Allocate large ranges (1M keys) so servers last hours without KGS    |
|  * Run KGS as replicated service (primary + standby with failover)      |
|  * Fallback: servers switch to random generation + DB uniqueness check  |
|  * Pre-fetch next range before current range runs out (buffer)          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ISSUE 3: CACHE STAMPEDE ON COLD START                                  |
|                                                                         |
|  Problem:                                                               |
|  Redis restarts or cache evicts popular entries. Thousands of           |
|  concurrent requests for same URL all miss cache simultaneously.        |
|  All hit DB at once (thundering herd).                                  |
|                                                                         |
|  Solution:                                                              |
|  * Cache warming: preload top 10K URLs on Redis startup                 |
|  * Request coalescing: only 1 thread fetches from DB, others wait       |
|    (singleflight pattern in Go, or distributed lock)                    |
|  * Stale-while-revalidate: serve stale cache while refreshing           |
|  * DB connection pooling with queue (don't overwhelm DB)                |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ISSUE 4: ABUSE AND SPAM                                                |
|                                                                         |
|  Problem:                                                               |
|  Attackers use service to create millions of short URLs pointing        |
|  to phishing/malware sites. Short URLs mask the dangerous destination.  |
|                                                                         |
|  Solution:                                                              |
|  * Rate limiting: per IP (10/min anonymous) and per user (100/hr)       |
|  * URL scanning: Google Safe Browsing API check before creation         |
|  * Domain blocklist: block known malicious domains                      |
|  * Preview page: bit.ly/xY7kLm+ shows destination before redirect       |
|  * Report mechanism: users flag malicious links                         |
|  * CAPTCHA for anonymous URL creation                                   |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ISSUE 5: DATA CONSISTENCY DURING SHARDING                              |
|                                                                         |
|  Problem:                                                               |
|  URL created on Shard A. Read request routed to Shard B.                |
|  Returns 404 for a valid URL. Or: resharding moves data,                |
|  but cache still points to old shard.                                   |
|                                                                         |
|  Solution:                                                              |
|  * Consistent hashing for shard routing (minimizes data movement)       |
|  * short_code determines shard (deterministic -- same code always       |
|    routes to same shard, no ambiguity)                                  |
|  * Cache invalidation during resharding                                 |
|  * Double-write during migration (write to old + new shard)             |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ISSUE 6: ANALYTICS PIPELINE LAG                                        |
|                                                                         |
|  Problem:                                                               |
|  Kafka consumer falls behind during traffic spike. Analytics            |
|  dashboard shows stale data. Click counts are hours behind.             |
|                                                                         |
|  Solution:                                                              |
|  * Separate real-time counters (Redis INCR) from detailed analytics     |
|    User sees "~5M clicks" instantly, detailed breakdown is async        |
|  * Auto-scale Kafka consumers based on lag metric                       |
|  * Partition Kafka by short_code hash (parallel processing)             |
|  * Backpressure: if lag > threshold, sample events (process 1 in 10)    |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ISSUE 7: URL ENUMERATION ATTACK                                        |
|                                                                         |
|  Problem:                                                               |
|  Sequential IDs (abc123, abc124, abc125...) let attacker enumerate      |
|  all short URLs and discover private/sensitive links.                   |
|                                                                         |
|  Solution:                                                              |
|  * Never use plain sequential IDs                                       |
|  * Scramble counter with reversible cipher (e.g., skip32, format-       |
|    preserving encryption) before base62 encoding                        |
|  * Or use pre-generated random keys (Approach 5)                        |
|  * Rate limit lookups: block IPs making sequential requests             |
|  * Return same 404 for "not found" and "doesn't exist" (don't leak)     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 14: INTERVIEW QUICK REFERENCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY TALKING POINTS FOR INTERVIEW                                       |
|                                                                         |
|  1. SCALE                                                               |
|     * 100M URLs/month, 10B over 10 years                                |
|     * 7-character codes (62^7 = 3.5 trillion combinations)              |
|     * Read-heavy (100:1 ratio) > caching critical                       |
|                                                                         |
|  2. SHORT CODE GENERATION (Most important!)                             |
|     * Counter-based with key ranges (distributed, no collision)         |
|     * Or pre-generated keys database                                    |
|     * Base62 encoding for compactness                                   |
|                                                                         |
|  3. ARCHITECTURE                                                        |
|     * Load Balancer > App Servers > Cache > Database                    |
|     * Redis cache for hot URLs                                          |
|     * PostgreSQL or Cassandra for storage                               |
|                                                                         |
|  4. CACHING                                                             |
|     * LRU eviction                                                      |
|     * Read-through pattern                                              |
|     * 80/20 rule: 20% URLs get 80% traffic                              |
|                                                                         |
|  5. REDIRECT                                                            |
|     * 302 for analytics tracking                                        |
|     * 301 for SEO if analytics not needed                               |
|                                                                         |
|  6. ANALYTICS                                                           |
|     * Async processing (don't block redirect)                           |
|     * Queue + workers                                                   |
|     * Real-time counters in Redis                                       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  COMMON FOLLOW-UP QUESTIONS                                             |
|                                                                         |
|  Q: How to prevent collisions?                                          |
|  A: Counter with pre-allocated ranges OR pre-generated key database     |
|                                                                         |
|  Q: How to scale the database?                                          |
|  A: Shard by short_code (first char or consistent hash)                 |
|                                                                         |
|  Q: What if same URL shortened twice?                                   |
|  A: Design choice - can return same or different short URL              |
|                                                                         |
|  Q: How to handle popular URLs?                                         |
|  A: Caching! Popular URLs stay in cache                                 |
|                                                                         |
|  Q: What about security?                                                |
|  A: Rate limiting, spam detection, malware scanning                     |
|                                                                         |
|  Q: 301 vs 302?                                                         |
|  A: 302 for analytics, 301 for SEO                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## ARCHITECTURE DIAGRAM SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|                            CLIENTS                                      |
|                               |                                         |
|                               v                                         |
|                    +-------------------+                                |
|                    |   LOAD BALANCER   |                                |
|                    +---------+---------+                                |
|                              |                                          |
|            +-----------------+-----------------+                        |
|            |                 |                 |                        |
|            v                 v                 v                        |
|       +---------+       +---------+       +---------+                   |
|       | Server  |       | Server  |       | Server  |                   |
|       |    1    |       |    2    |       |    3    |                   |
|       +----+----+       +----+----+       +----+----+                   |
|            |                 |                 |                        |
|            +-----------------+-----------------+                        |
|                              |                                          |
|                +-------------+-------------+                            |
|                |                           |                            |
|                v                           v                            |
|     +-------------------+       +-------------------+                   |
|     |      CACHE        |       |     DATABASE      |                   |
|     |     (Redis)       |       |   (PostgreSQL/    |                   |
|     |                   |       |    Cassandra)     |                   |
|     |  short > long     |       |   URL mappings    |                   |
|     |  (hot URLs)       |       |   (permanent)     |                   |
|     +-------------------+       +-------------------+                   |
|                                                                         |
|                              |                                          |
|                              v                                          |
|                    +-------------------+                                |
|                    |   KEY GENERATOR   |                                |
|                    |    SERVICE        |                                |
|                    |                   |                                |
|                    |  Allocates ID     |                                |
|                    |  ranges to servers|                                |
|                    +-------------------+                                |
|                                                                         |
|                              |                                          |
|                              v                                          |
|                    +-------------------+                                |
|                    |   ANALYTICS       |                                |
|                    |   (Async)         |                                |
|                    |                   |                                |
|                    |   Kafka > Workers |                                |
|                    |   > Data Lake     |                                |
|                    +-------------------+                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

END OF URL SHORTENER SYSTEM DESIGN
