# NEWS FEED SYSTEM DESIGN (TWITTER / FACEBOOK)
*Complete Design: Requirements, Architecture, and Interview Guide*

A news feed is the constantly updating list of stories in the middle of a
user's home page. It includes status updates, photos, videos, links, app
activity, and likes from people, pages, and groups that a user follows.

## SECTION 1: SCOPING THE PROBLEM WITH THE INTERVIEWER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INTERVIEWER-CANDIDATE DIALOGUE                                         |
|  (establishing scope before diving into design)                         |
|                                                                         |
|  CANDIDATE: Is this a social media news feed like Facebook/Twitter,     |
|    or a content aggregator like Google News or Reddit?                  |
|                                                                         |
|  INTERVIEWER: Social media feed. Users see posts from people and        |
|    pages they follow. Think Facebook or Twitter home timeline.          |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: What content types should the feed support? Just text,      |
|    or also images, videos, and links?                                   |
|                                                                         |
|  INTERVIEWER: All of them - text, images, videos, and shared links.     |
|    But focus the design on feed generation and delivery, not media      |
|    transcoding.                                                         |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: Should the feed be ranked (by relevance) or purely          |
|    chronological (most recent first)?                                   |
|                                                                         |
|  INTERVIEWER: Ranked by relevance with recency as a strong signal.      |
|    This is a key differentiator - the ranking pipeline is worth         |
|    discussing in detail.                                                |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: What scale are we targeting? How many users, how many       |
|    posts per day?                                                       |
|                                                                         |
|  INTERVIEWER: 500M DAU, average 1000 friends/followees. About           |
|    10M new posts per day. Each user checks their feed ~10 times/day.    |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: How should we handle celebrities with millions of           |
|    followers? A celebrity posting triggers massive fan-out.             |
|                                                                         |
|  INTERVIEWER: Great question. The "celebrity problem" is the core       |
|    challenge here. Propose an approach and we'll discuss trade-offs.    |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: Should I handle push notifications for new feed items,      |
|    or just the feed generation/retrieval?                               |
|                                                                         |
|  INTERVIEWER: Focus on feed generation and retrieval. Mention           |
|    notifications briefly but don't deep-dive.                           |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  AGREED SCOPE:                                                          |
|                                                                         |
|  * Social media news feed (Facebook/Twitter style)                      |
|  * Text, images, videos, links as content types                         |
|  * Relevance-ranked with recency signal                                 |
|  * 500M DAU, 1000 avg friends, 10M posts/day, 5B feed reads/day         |
|  * Celebrity problem: users with millions of followers                  |
|  * Deep dive: fan-out strategy + ranking pipeline                       |
|  * Notifications mentioned briefly, not deep-dived                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: UNDERSTANDING THE PROBLEM

### WHAT IS A NEWS FEED?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A News Feed aggregates and displays content from connections:          |
|                                                                         |
|  USER EXPERIENCE:                                                       |
|  1. Open app / website                                                  |
|  2. See a personalized feed of posts from followed users                |
|  3. Scroll through ranked/chronological content                         |
|  4. Interact: like, comment, share, bookmark                            |
|  5. Create new posts (text, images, videos, links)                      |
|  6. Discover trending content and suggested users                       |
|                                                                         |
|  CORE CHALLENGE:                                                        |
|  Given 500M daily active users, each following hundreds of accounts,    |
|  generate a personalized feed for every user in under 500ms.            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY IS THIS HARD TO BUILD?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  KEY CHALLENGES:                                                         |
|                                                                          |
|  1. MASSIVE SCALE                                                        |
|  ----------------                                                        |
|  500M DAU, 1B posts/day, 10B feed reads/day.                             |
|  Each feed request can fan out to hundreds of followed users.            |
|                                                                          |
|  2. LOW LATENCY REQUIREMENT                                              |
|  ----------------------------                                            |
|  Feed must load in <500ms. Users are impatient.                          |
|  Pre-computation vs on-the-fly generation tradeoff.                      |
|                                                                          |
|  3. PERSONALIZATION                                                      |
|  ------------------                                                      |
|  Not just chronological -- must rank by relevance.                       |
|  Different users see different content from same author.                 |
|                                                                          |
|  4. CELEBRITY PROBLEM                                                    |
|  ---------------------                                                   |
|  A user with 100M followers posts something.                             |
|  Writing to 100M feeds is extremely expensive.                           |
|                                                                          |
|  5. CONSISTENCY vs AVAILABILITY                                          |
|  ------------------------------                                          |
|  New posts should appear quickly but system must never go down.          |
|  Eventual consistency is acceptable for feeds.                           |
|                                                                          |
|  6. MIXED MEDIA                                                          |
|  ---------------                                                         |
|  Posts contain text, images, videos, links, polls, etc.                  |
|  Each type requires different storage and rendering.                     |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 1.2: REQUIREMENTS

### FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS:                                               |
|                                                                         |
|  1. POST CREATION                                                       |
|     * Create text posts (up to 280 chars for Twitter-like)              |
|     * Attach images (up to 4), videos (up to 1), links                  |
|     * Tag other users, add hashtags                                     |
|     * Edit posts within a time window                                   |
|     * Delete own posts                                                  |
|                                                                         |
|  2. NEWS FEED GENERATION                                                |
|     * Display posts from followed users                                 |
|     * Ranked by relevance OR chronological (user choice)                |
|     * Paginated (infinite scroll)                                       |
|     * Real-time updates for new posts                                   |
|                                                                         |
|  3. SOCIAL GRAPH                                                        |
|     * Follow / Unfollow users                                           |
|     * View followers / following lists                                  |
|     * Suggested users to follow                                         |
|                                                                         |
|  4. INTERACTIONS                                                        |
|     * Like / Unlike posts                                               |
|     * Comment on posts (threaded comments)                              |
|     * Share / Retweet posts                                             |
|     * Bookmark posts for later                                          |
|                                                                         |
|  5. NOTIFICATIONS                                                       |
|     * Notify when someone likes/comments on your post                   |
|     * Notify when followed by someone                                   |
|     * Notify for mentions and tags                                      |
|                                                                         |
|  6. SEARCH                                                              |
|     * Search posts by keywords, hashtags                                |
|     * Search users by name, handle                                      |
|     * Trending topics                                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### NON-FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NON-FUNCTIONAL REQUIREMENTS:                                           |
|                                                                         |
|  1. LOW LATENCY                                                         |
|     * Feed generation: <500ms (p99)                                     |
|     * Post creation: <1s                                                |
|     * Like/Comment: <200ms                                              |
|                                                                         |
|  2. HIGH AVAILABILITY                                                   |
|     * 99.99% uptime (52 min downtime / year)                            |
|     * Graceful degradation during failures                              |
|     * Multi-region deployment                                           |
|                                                                         |
|  3. EVENTUAL CONSISTENCY                                                |
|     * Posts can take a few seconds to appear in followers' feeds        |
|     * Like counts may be slightly stale (acceptable)                    |
|     * Strong consistency for user's own timeline                        |
|                                                                         |
|  4. SCALABILITY                                                         |
|     * Horizontal scaling for all components                             |
|     * Handle viral posts (sudden 1000x traffic spike)                   |
|     * Auto-scaling based on load                                        |
|                                                                         |
|  5. DURABILITY                                                          |
|     * Zero data loss for posts and interactions                         |
|     * Multi-region replication for disaster recovery                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: KEY TERMINOLOGY

```
+-------------------------------------------------------------------------+
||                                                                        |
||  NEWS FEED                                                             |
||  The constantly updating stream of posts on a user's home page,        |
||  aggregated from accounts they follow. Also called "timeline."         |
||                                                                        |
||  FAN-OUT ON WRITE (PUSH MODEL)                                         |
||  When a user posts, content is immediately pushed to every             |
||  follower's feed cache. Fast reads but costly for popular users.       |
||                                                                        |
||  FAN-OUT ON READ (PULL MODEL)                                          |
||  Feed is assembled on-the-fly at request time by pulling recent        |
||  posts from each followed user. Cheap writes but slower reads.         |
||                                                                        |
||  HYBRID FAN-OUT                                                        |
||  Combines push and pull: regular users fan out on write, while         |
||  celebrity posts (millions of followers) are fetched on demand.        |
||                                                                        |
||  SOCIAL GRAPH                                                          |
||  The data structure mapping follow/friend relationships between        |
||  users. Determines whose posts appear in a user's feed.                |
||                                                                        |
||  TIMELINE                                                              |
||  A user's pre-computed feed stored in cache (e.g., Redis).             |
||  Ordered by relevance or chronologically per user preference.          |
||                                                                        |
||  RANKING                                                               |
||  ML-driven scoring of posts by predicted engagement. Considers         |
||  affinity, recency, content type, and interaction history.             |
||                                                                        |
||  FEED GENERATION                                                       |
||  Background process that merges posts from followed accounts,          |
||  applies ranking, and writes the result to the user's feed cache.      |
||                                                                        |
||  HOT KEY / CELEBRITY PROBLEM                                           |
||  A user with millions of followers posts, requiring fan-out on         |
||  write to update millions of caches -- extreme write amplification.    |
||                                                                        |
||  CACHE INVALIDATION                                                    |
||  Removing or updating stale feed entries when posts are deleted,       |
||  edited, or when follow relationships change.                          |
||                                                                        |
||  DENORMALIZATION                                                       |
||  Storing redundant post data in each follower's feed cache to          |
||  avoid expensive joins at read time. Trades storage for speed.         |
||                                                                        |
+-------------------------------------------------------------------------+
```

## SECTION 3: SCALE ESTIMATION

### BACK-OF-ENVELOPE CALCULATIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USER BASE:                                                             |
|  * Total users: 1 Billion                                               |
|  * Daily Active Users (DAU): 500 Million                                |
|  * Average follows per user: 200                                        |
|  * Celebrity users (>1M followers): ~50,000                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TRAFFIC ESTIMATES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WRITE TRAFFIC (Post Creation):                                         |
|  * 1 Billion posts/day                                                  |
|  * 1B / 86,400 = ~11,574 posts/second                                   |
|  * Peak (2x): ~23,000 posts/second                                      |
|                                                                         |
|  READ TRAFFIC (Feed Reads):                                             |
|  * 10 Billion feed reads/day                                            |
|  * 10B / 86,400 = ~115,740 reads/second                                 |
|  * Peak (3x): ~350,000 reads/second                                     |
|  * Read:Write ratio = 10:1                                              |
|                                                                         |
|  SOCIAL GRAPH OPERATIONS:                                               |
|  * Follow/Unfollow: ~50M/day = ~580/second                              |
|  * Like operations: ~5B/day = ~57,870/second                            |
|  * Comments: ~500M/day = ~5,787/second                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STORAGE ESTIMATES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  POST STORAGE:                                                          |
|  * Average post size (text + metadata): ~1 KB                           |
|  * 1B posts/day x 1KB = 1 TB/day                                        |
|  * Per year: 365 TB                                                     |
|  * With replication (3x): ~1 PB/year                                    |
|                                                                         |
|  MEDIA STORAGE:                                                         |
|  * 20% of posts have images: 200M images/day                            |
|  * Average image: 500 KB                                                |
|  * Image storage/day: 200M x 500KB = 100 TB/day                         |
|  * 5% of posts have videos: 50M videos/day                              |
|  * Average video: 10 MB                                                 |
|  * Video storage/day: 50M x 10MB = 500 TB/day                           |
|                                                                         |
|  FEED CACHE:                                                            |
|  * Cache feed for each active user                                      |
|  * 500M users x 200 post IDs x 8 bytes = ~800 GB                        |
|  * With metadata: ~5 TB cache needed                                    |
|                                                                         |
|  SOCIAL GRAPH:                                                          |
|  * 1B users x 200 avg follows = 200B edges                              |
|  * Each edge: ~16 bytes (2 user IDs)                                    |
|  * Total: 200B x 16B = ~3.2 TB                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### BANDWIDTH ESTIMATES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INCOMING (Writes):                                                     |
|  * Posts: 11,574/s x 1KB = ~12 MB/s                                     |
|  * Images: 2,300/s x 500KB = ~1.15 GB/s                                 |
|  * Videos: 580/s x 10MB = ~5.8 GB/s                                     |
|  * Total incoming: ~7 GB/s                                              |
|                                                                         |
|  OUTGOING (Reads):                                                      |
|  * Feed reads: 115,740/s                                                |
|  * Each feed page: ~50 KB (post metadata + thumbnails)                  |
|  * Total outgoing: ~5.8 GB/s (text + metadata)                          |
|  * With media: ~50 GB/s (served via CDN)                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

### SYSTEM OVERVIEW

```
+--------------------------------------------------------------------------+
|                                                                          |
|                        HIGH-LEVEL ARCHITECTURE                           |
|                                                                          |
|  +----------+     +-----------+     +-------------------+                |
|  |  Client  |---->|   Load    |---->|   API Gateway     |                |
|  |  (App/   |     |  Balancer |     |  (Auth, Rate      |                |
|  |   Web)   |     |           |     |   Limit, Route)   |                |
|  +----------+     +-----------+     +-------------------+                |
|                                              |                           |
|                    +-------------------------+----------+                |
|                    |              |           |          |               |
|                    v              v           v          v               |
|             +-----------+  +---------+  +--------+ +--------+            |
|             |   Post    |  |  Feed   |  | Social | | Search |            |
|             |  Service  |  | Service |  | Graph  | | Service|            |
|             +-----------+  +---------+  +--------+ +--------+            |
|                    |              |           |          |               |
|                    v              v           v          v               |
|             +-----------+  +---------+  +--------+ +--------+            |
|             | Post DB   |  | Feed    |  |Graph DB| | Search |            |
|             | (MySQL/   |  | Cache   |  |(Neo4j/ | | Index  |            |
|             |  Postgres)|  | (Redis) |  | Adj.   | | (ES)   |            |
|             +-----------+  +---------+  | List)  | +--------+            |
|                                         +--------+                       |
|                                                                          |
|  SUPPORTING SERVICES:                                                    |
|  +-------------+  +---------------+  +-------------+  +----------+       |
|  | Notification|  | Media Service |  |  Analytics  |  |  Fan-out |       |
|  | Service     |  | (Upload/CDN)  |  |  Service    |  |  Service |       |
|  +-------------+  +---------------+  +-------------+  +----------+       |
|                                                                          |
+--------------------------------------------------------------------------+
```

### REQUEST FLOW FOR POSTING

```
+--------------------------------------------------------------------------+
|                                                                          |
|  WHAT HAPPENS WHEN A USER CREATES A POST?                                |
|                                                                          |
|  User creates post                                                       |
|       |                                                                  |
|       v                                                                  |
|  +-------------+                                                         |
|  | API Gateway | --- Auth check, rate limit                              |
|  +-------------+                                                         |
|       |                                                                  |
|       v                                                                  |
|  +-------------+                                                         |
|  | Post Service| --- Validate content, check for spam                    |
|  +-------------+                                                         |
|       |                                                                  |
|       +-----> Store post in Post DB (synchronous)                        |
|       |                                                                  |
|       +-----> Upload media to Object Store (async)                       |
|       |                                                                  |
|       +-----> Publish event to Message Queue                             |
|                    |                                                     |
|                    +----> Fan-out Service (write to follower feeds)      |
|                    |                                                     |
|                    +----> Notification Service (notify mentioned users)  |
|                    |                                                     |
|                    +----> Search Indexer (index for search)              |
|                    |                                                     |
|                    +----> Analytics (track post creation metrics)        |
|                                                                          |
+--------------------------------------------------------------------------+
```

### REQUEST FLOW FOR READING FEED

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT HAPPENS WHEN A USER OPENS THEIR FEED?                             |
|                                                                         |
|  User opens app                                                         |
|       |                                                                 |
|       v                                                                 |
|  +-------------+                                                        |
|  | API Gateway | --- Auth, rate limit                                   |
|  +-------------+                                                        |
|       |                                                                 |
|       v                                                                 |
|  +-------------+                                                        |
|  | Feed Service| --- Check feed cache for pre-computed feed             |
|  +-------------+                                                        |
|       |                                                                 |
|       +---> Cache HIT: Return cached feed (fast path, <50ms)            |
|       |                                                                 |
|       +---> Cache MISS: Generate feed on-the-fly (slow path)            |
|                  |                                                      |
|                  +---> Get followed user IDs from Social Graph          |
|                  |                                                      |
|                  +---> Fetch recent posts for each followed user        |
|                  |                                                      |
|                  +---> Merge, rank, and paginate                        |
|                  |                                                      |
|                  +---> Cache the result, return to user                 |
|                                                                         |
|  For subsequent pages: use cursor-based pagination with post_id         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5: FAN-OUT STRATEGIES (THE CORE PROBLEM)

### FAN-OUT ON WRITE (PUSH MODEL)

```
+--------------------------------------------------------------------------+
|                                                                          |
|  FAN-OUT ON WRITE (Push Model):                                          |
|                                                                          |
|  When a user publishes a post, immediately push it to all                |
|  followers' feed caches.                                                 |
|                                                                          |
|  User A posts                                                            |
|       |                                                                  |
|       v                                                                  |
|  +-------------+     +----------------+                                  |
|  | Post Service|---->| Fan-out Service|                                  |
|  +-------------+     +----------------+                                  |
|                            |                                             |
|              +-------------+-------------+                               |
|              |             |             |                               |
|              v             v             v                               |
|      +-----------+  +-----------+  +-----------+                         |
|      |Follower 1 |  |Follower 2 |  |Follower N |                         |
|      |Feed Cache |  |Feed Cache |  |Feed Cache |                         |
|      +-----------+  +-----------+  +-----------+                         |
|                                                                          |
|  PROS:                                                                   |
|  + Feed read is very fast (pre-computed)                                 |
|  + Simple feed retrieval (just read from cache)                          |
|  + Real-time: followers see post immediately                             |
|                                                                          |
|  CONS:                                                                   |
|  * Celebrity problem: user with 100M followers = 100M writes             |
|  * Wasted work for inactive users (may never read feed)                  |
|  * High write amplification                                              |
|  * Slow post publishing for high-follower users                          |
|                                                                          |
|  BEST FOR: Users with < 10,000 followers (majority of users)             |
|                                                                          |
+--------------------------------------------------------------------------+
```

### FAN-OUT ON READ (PULL MODEL)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FAN-OUT ON READ (Pull Model):                                          |
|                                                                         |
|  Do nothing on post creation. When a user reads their feed,             |
|  fetch posts from all followed users in real-time.                      |
|                                                                         |
|  User B reads feed                                                      |
|       |                                                                 |
|       v                                                                 |
|  +-------------+                                                        |
|  | Feed Service|                                                        |
|  +-------------+                                                        |
|       |                                                                 |
|       +---> Get list of followed users [u1, u2, u3, ..., u200]          |
|       |                                                                 |
|       +---> For each user, fetch their recent posts                     |
|       |         |                                                       |
|       |         +---> u1: [post_a, post_b]                              |
|       |         +---> u2: [post_c]                                      |
|       |         +---> u3: [post_d, post_e, post_f]                      |
|       |         +---> ...                                               |
|       |                                                                 |
|       +---> Merge all posts, sort/rank, return top N                    |
|                                                                         |
|  PROS:                                                                  |
|  + No write amplification                                               |
|  + Works well for celebrity users                                       |
|  + No wasted work for inactive users                                    |
|                                                                         |
|  CONS:                                                                  |
|  * Slow feed reads (must fetch from many sources)                       |
|  * High read latency, especially for users following many accounts      |
|  * Difficult to rank without fetching everything first                  |
|                                                                         |
|  BEST FOR: Celebrity/hot users with millions of followers               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HYBRID APPROACH (THE SOLUTION)

```
+--------------------------------------------------------------------------+
|                                                                          |
|  HYBRID FAN-OUT (What Twitter/Facebook Actually Uses):                   |
|                                                                          |
|  Combine both approaches based on user type:                             |
|                                                                          |
|  CLASSIFICATION:                                                         |
|  * Normal users (<10K followers): Fan-out on WRITE                       |
|  * Celebrity users (>10K followers): Fan-out on READ                     |
|                                                                          |
|  HOW IT WORKS:                                                           |
|                                                                          |
|  1. Normal user posts --> Push to all followers' caches                  |
|  2. Celebrity posts --> Store in celebrity post cache only               |
|  3. When user reads feed:                                                |
|     a. Fetch pre-computed feed from cache (normal user posts)            |
|     b. Fetch celebrity posts from celebrity cache                        |
|     c. Merge both, rank, return                                          |
|                                                                          |
|  +------------------+                                                    |
|  | User reads feed  |                                                    |
|  +------------------+                                                    |
|           |                                                              |
|     +-----+-----+                                                        |
|     |           |                                                        |
|     v           v                                                        |
|  +--------+  +------------------+                                        |
|  | Feed   |  | Celebrity Post   |                                        |
|  | Cache  |  | Cache (per user) |                                        |
|  +--------+  +------------------+                                        |
|     |           |                                                        |
|     +-----+-----+                                                        |
|           |                                                              |
|           v                                                              |
|     +----------+                                                         |
|     |  Merge & |                                                         |
|     |  Rank    |                                                         |
|     +----------+                                                         |
|           |                                                              |
|           v                                                              |
|     Return feed                                                          |
|                                                                          |
|  This limits fan-out writes to a manageable level while                  |
|  keeping feed reads fast for 99% of cases.                               |
|                                                                          |
+--------------------------------------------------------------------------+
```

### CELEBRITY / HOT USER PROBLEM IN DETAIL

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE CELEBRITY PROBLEM:                                                 |
|                                                                         |
|  SCENARIO:                                                              |
|  * Celebrity with 100M followers posts                                  |
|  * Fan-out on write: 100M cache insertions needed                       |
|  * At 100K writes/sec: takes ~17 minutes to fan out                     |
|  * Some followers see post 17 min after others!                         |
|                                                                         |
|  SOLUTIONS:                                                             |
|                                                                         |
|  1. HYBRID MODEL (described above)                                      |
|     Celebrities use fan-out on read                                     |
|                                                                         |
|  2. TIERED FAN-OUT                                                      |
|     * Immediate: Push to active users online right now                  |
|     * Deferred: Push to recently active users                           |
|     * On-demand: Pull for inactive users when they come online          |
|                                                                         |
|  3. CACHE-ASIDE FOR CELEBRITY POSTS                                     |
|     * Maintain a separate "celebrity timeline" cache                    |
|     * Each user's feed = their cache + celebrity timeline merge         |
|     * Celebrity cache: ~50K celebrities x 100 posts x 8B = ~40 MB       |
|                                                                         |
|  4. PRIORITY QUEUES                                                     |
|     * Fan-out workers process high-engagement followers first           |
|     * Users who frequently engage get updates sooner                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6: FEED RANKING ALGORITHM

### CHRONOLOGICAL VS RANKED FEED

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHRONOLOGICAL FEED:                                                    |
|  * Simply sort by post creation time (newest first)                     |
|  * Simple, transparent, predictable                                     |
|  * Problem: users miss important posts from close friends               |
|  * Problem: low-quality posts from high-frequency posters dominate      |
|                                                                         |
|  RANKED FEED:                                                           |
|  * Use ML model to predict engagement probability                       |
|  * Show posts most likely to be interesting to this specific user       |
|  * Much higher engagement metrics                                       |
|  * Problem: filter bubble, less serendipity                             |
|  * Problem: perceived as less "fair"                                    |
|                                                                         |
|  MODERN APPROACH: Let users choose (toggle), default to ranked.         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### RANKING SIGNAL DETAILS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FEED RANKING SIGNALS:                                                  |
|                                                                         |
|  AFFINITY SCORE (How close is the author to this user?):                |
|  +---------------------------------------------+                        |
|  | Signal                | Weight               |                       |
|  |---------------------------------------------+                        |
|  | Direct messages       | Very High            |                       |
|  | Profile views         | High                 |                       |
|  | Comment interactions  | High                 |                       |
|  | Like interactions     | Medium               |                       |
|  | Mutual friends        | Medium               |                       |
|  | Follow recency        | Low                  |                       |
|  +---------------------------------------------+                        |
|                                                                         |
|  POST QUALITY SCORE:                                                    |
|  +---------------------------------------------+                        |
|  | Signal                | Weight               |                       |
|  |---------------------------------------------+                        |
|  | Engagement rate       | Very High            |                       |
|  | Comments count        | High                 |                       |
|  | Shares/Retweets       | High                 |                       |
|  | Likes count           | Medium               |                       |
|  | Has media             | Medium               |                       |
|  | Post length           | Low                  |                       |
|  +---------------------------------------------+                        |
|                                                                         |
|  TIME DECAY:                                                            |
|  * Recent posts weighted higher                                         |
|  * Exponential decay: score *= e^(-lambda * age_hours)                  |
|  * lambda tuned so posts >48 hours old score near 0                     |
|                                                                         |
|  FINAL SCORE = Affinity * PostQuality * TimeDecay * DiversityBoost      |
|                                                                         |
|  DiversityBoost: penalize showing too many posts from same author       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### RANKING PIPELINE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FEED RANKING PIPELINE:                                                 |
|                                                                         |
|  Stage 1: CANDIDATE GENERATION                                          |
|  +---------------------------+                                          |
|  | Fetch ~1000 candidate     |                                          |
|  | posts from followed users |                                          |
|  | (from cache + celebrity)  |                                          |
|  +---------------------------+                                          |
|           |                                                             |
|           v                                                             |
|  Stage 2: FIRST PASS RANKING                                            |
|  +---------------------------+                                          |
|  | Lightweight model scores  |                                          |
|  | all 1000 candidates       |                                          |
|  | Prune to top 200          |                                          |
|  +---------------------------+                                          |
|           |                                                             |
|           v                                                             |
|  Stage 3: DEEP RANKING                                                  |
|  +---------------------------+                                          |
|  | Full ML model with all    |                                          |
|  | features (user history,   |                                          |
|  | context, social signals)  |                                          |
|  | Rank 200 -> top 50        |                                          |
|  +---------------------------+                                          |
|           |                                                             |
|           v                                                             |
|  Stage 4: DIVERSITY & POLICY                                            |
|  +---------------------------+                                          |
|  | Apply diversity rules     |                                          |
|  | Remove duplicates         |                                          |
|  | Apply content policy      |                                          |
|  | Return top 20 for page 1  |                                          |
|  +---------------------------+                                          |
|                                                                         |
|  LATENCY BUDGET:                                                        |
|  Candidate generation: 50ms | First pass: 30ms                          |
|  Deep ranking: 100ms | Diversity: 20ms | Total: ~200ms                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7: DETAILED COMPONENT DESIGN

### POST SERVICE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  POST SERVICE RESPONSIBILITIES:                                         |
|                                                                         |
|  1. Create posts (validate, store, trigger fan-out)                     |
|  2. Read posts (by ID, by user timeline)                                |
|  3. Update posts (edit within time window)                              |
|  4. Delete posts (soft delete, cascade to feeds)                        |
|                                                                         |
|  POST CREATION FLOW:                                                    |
|  1. Validate content (length, format, spam check)                       |
|  2. If has media: upload to blob store, get media URLs                  |
|  3. Generate unique post ID (Snowflake ID for time-ordering)            |
|  4. Write to Posts DB (primary storage)                                 |
|  5. Write to User Timeline Cache (author's own posts)                   |
|  6. Publish PostCreated event to Kafka                                  |
|  7. Return post ID to client                                            |
|                                                                         |
|  POST ID GENERATION (Snowflake):                                        |
|  +------+------------------+---------+------------+                     |
|  | Sign | Timestamp (41b)  | Node ID | Sequence   |                     |
|  | 1 bit|    ~69 years     | (10b)   | (12b)      |                     |
|  +------+------------------+---------+------------+                     |
|                                                                         |
|  Benefits: Time-ordered, globally unique, no coordination needed        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### FAN-OUT SERVICE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FAN-OUT SERVICE:                                                       |
|                                                                         |
|  Consumes PostCreated events from Kafka and distributes                 |
|  posts to followers' feed caches.                                       |
|                                                                         |
|  FLOW:                                                                  |
|  1. Receive PostCreated event                                           |
|  2. Check author's follower count                                       |
|     * If < 10K: proceed with fan-out on write                           |
|     * If >= 10K: skip (handled on read)                                 |
|  3. Fetch follower list from Social Graph Service                       |
|  4. For each follower:                                                  |
|     a. Check if follower has muted/blocked author                       |
|     b. Prepend post_id to follower's feed cache (Redis sorted set)      |
|     c. Trim cache to max 800 entries                                    |
|  5. Update fan-out metrics (latency, count)                             |
|                                                                         |
|  SCALING:                                                               |
|  * Multiple Kafka partitions (partition by author_id)                   |
|  * Many consumer instances processing in parallel                       |
|  * Batch Redis writes (pipeline) for efficiency                         |
|  * Async processing: post is immediately visible to author              |
|                                                                         |
|  FAILURE HANDLING:                                                      |
|  * Kafka ensures at-least-once delivery                                 |
|  * Idempotent writes (sorted set with score = timestamp)                |
|  * Dead letter queue for persistent failures                            |
|  * Retry with exponential backoff                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SOCIAL GRAPH SERVICE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SOCIAL GRAPH SERVICE:                                                  |
|                                                                         |
|  Manages follow/unfollow relationships.                                 |
|                                                                         |
|  STORAGE OPTIONS:                                                       |
|                                                                         |
|  Option 1: ADJACENCY LIST IN REDIS                                      |
|  * followers:{user_id} -> Set of follower IDs                           |
|  * following:{user_id} -> Set of following IDs                          |
|  * O(1) follow/unfollow, O(N) list all followers                        |
|  * Memory: 200B edges x 8B = 1.6 TB (needs cluster)                     |
|                                                                         |
|  Option 2: GRAPH DATABASE (Neo4j)                                       |
|  * (User)-[:FOLLOWS]->(User)                                            |
|  * Great for complex queries (mutual friends, 2nd degree)               |
|  * Harder to scale horizontally                                         |
|                                                                         |
|  Option 3: RELATIONAL TABLE (Recommended for simplicity)                |
|  * followers(follower_id, followee_id, created_at)                      |
|  * Sharded by followee_id (efficient follower list retrieval)           |
|  * Index on follower_id for "who am I following?" queries               |
|                                                                         |
|  RECOMMENDED: MySQL/Postgres sharded table + Redis cache for hot data   |
|                                                                         |
|  FOLLOW OPERATION:                                                      |
|  1. Insert into followers table                                         |
|  2. Increment follower/following counters (async)                       |
|  3. Update Redis cache                                                  |
|  4. Trigger notification to followee                                    |
|  5. Re-compute feed for follower (async, backfill recent posts)         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### FEED CACHE DESIGN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FEED CACHE ARCHITECTURE (Redis):                                       |
|                                                                         |
|  DATA STRUCTURE: Sorted Set per user                                    |
|  Key: feed:{user_id}                                                    |
|  Members: post_id                                                       |
|  Score: timestamp (for chronological ordering)                          |
|                                                                         |
|  EXAMPLE:                                                               |
|  feed:user123 = {                                                       |
|    post_789: 1708000001,  (newest)                                      |
|    post_456: 1707999500,                                                |
|    post_234: 1707998000,                                                |
|    ...                                                                  |
|    post_012: 1707900000   (oldest, 800th entry)                         |
|  }                                                                      |
|                                                                         |
|  OPERATIONS:                                                            |
|  * Add post to feed:  ZADD feed:user123 <timestamp> <post_id>           |
|  * Get feed page:     ZREVRANGEBYSCORE feed:user123 +inf -inf           |
|                       LIMIT <offset> <count>                            |
|  * Trim old entries:  ZREMRANGEBYRANK feed:user123 0 -801               |
|                                                                         |
|  CACHE SIZING:                                                          |
|  * 500M active users x 800 entries x 8B = 3.2 TB                        |
|  * Redis cluster: 50 nodes x 64 GB each = 3.2 TB                        |
|  * With replication (3x): 150 Redis nodes                               |
|                                                                         |
|  EVICTION POLICY:                                                       |
|  * LRU eviction for users who haven't been active in 7+ days            |
|  * On-demand rebuild when evicted user returns                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8: DATABASE SCHEMA

### CORE TABLES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TABLE: users                                                           |
|  +----------------+-------------+-----------------------------------+   |
|  | Column         | Type        | Notes                             |   |
|  +----------------+-------------+-----------------------------------+   |
|  | user_id        | BIGINT (PK) | Snowflake ID                      |   |
|  | username       | VARCHAR(50) | Unique, indexed                   |   |
|  | display_name   | VARCHAR(100)|                                   |   |
|  | email          | VARCHAR(255)| Unique, indexed                   |   |
|  | bio            | TEXT        |                                   |   |
|  | profile_pic    | VARCHAR(500)| CDN URL                           |   |
|  | follower_count | INT         | Denormalized counter              |   |
|  | following_count| INT         | Denormalized counter              |   |
|  | is_celebrity   | BOOLEAN     | True if followers > 10K           |   |
|  | created_at     | TIMESTAMP   |                                   |   |
|  | updated_at     | TIMESTAMP   |                                   |   |
|  +----------------+-------------+-----------------------------------+   |
|  Sharding key: user_id                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TABLE: posts                                                           |
|  +----------------+-------------+-----------------------------------+   |
|  | Column         | Type        | Notes                             |   |
|  +----------------+-------------+-----------------------------------+   |
|  | post_id        | BIGINT (PK) | Snowflake ID (time-ordered)       |   |
|  | author_id      | BIGINT (FK) | References users.user_id          |   |
|  | content        | TEXT        | Post text content                 |   |
|  | media_urls     | JSON        | Array of media CDN URLs           |   |
|  | media_type     | ENUM        | NONE, IMAGE, VIDEO, LINK          |   |
|  | like_count     | INT         | Denormalized counter              |   |
|  | comment_count  | INT         | Denormalized counter              |   |
|  | share_count    | INT         | Denormalized counter              |   |
|  | is_deleted     | BOOLEAN     | Soft delete flag                  |   |
|  | created_at     | TIMESTAMP   | Indexed for timeline queries      |   |
|  +----------------+-------------+-----------------------------------+   |
|  Sharding key: author_id (co-locate user's posts)                       |
|  Index: (author_id, created_at DESC) for user timeline                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TABLE: followers                                                       |
|  +----------------+-------------+-----------------------------------+   |
|  | Column         | Type        | Notes                             |   |
|  +----------------+-------------+-----------------------------------+   |
|  | follower_id    | BIGINT      | The user who follows              |   |
|  | followee_id    | BIGINT      | The user being followed           |   |
|  | created_at     | TIMESTAMP   |                                   |   |
|  +----------------+-------------+-----------------------------------+   |
|  Primary key: (follower_id, followee_id)                                |
|  Index: (followee_id, follower_id) for "who follows me?" query          |
|  Sharding key: followee_id (efficient fan-out: get all followers)       |
|                                                                         |
|  TABLE: likes                                                           |
|  +----------------+-------------+-----------------------------------+   |
|  | Column         | Type        | Notes                             |   |
|  +----------------+-------------+-----------------------------------+   |
|  | user_id        | BIGINT      |                                   |   |
|  | post_id        | BIGINT      |                                   |   |
|  | created_at     | TIMESTAMP   |                                   |   |
|  +----------------+-------------+-----------------------------------+   |
|  Primary key: (user_id, post_id) -- prevents duplicate likes            |
|  Index: (post_id) for "who liked this post?"                            |
|                                                                         |
|  TABLE: comments                                                        |
|  +----------------+-------------+-----------------------------------+   |
|  | Column         | Type        | Notes                             |   |
|  +----------------+-------------+-----------------------------------+   |
|  | comment_id     | BIGINT (PK) | Snowflake ID                      |   |
|  | post_id        | BIGINT (FK) | Indexed                           |   |
|  | author_id      | BIGINT (FK) |                                   |   |
|  | parent_id      | BIGINT      | NULL for top-level, FK for reply  |   |
|  | content        | TEXT        |                                   |   |
|  | created_at     | TIMESTAMP   |                                   |   |
|  +----------------+-------------+-----------------------------------+   |
|  Index: (post_id, created_at) for threaded comment retrieval            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: API DESIGN

### REST API ENDPOINTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  POST APIS:                                                             |
|                                                                         |
|  POST /api/v1/posts                                                     |
|  Body: { content, media_ids[], hashtags[], mentions[] }                 |
|  Response: { post_id, created_at }                                      |
|                                                                         |
|  GET /api/v1/posts/{post_id}                                            |
|  Response: { post_id, author, content, media, likes, comments, ... }    |
|                                                                         |
|  DELETE /api/v1/posts/{post_id}                                         |
|  Response: { success: true }                                            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  FEED APIS:                                                             |
|                                                                         |
|  GET /api/v1/feed?cursor={last_post_id}&limit=20&type=ranked            |
|  Response: {                                                            |
|    posts: [ { post_id, author, content, ... }, ... ],                   |
|    next_cursor: "post_id_of_last_item",                                 |
|    has_more: true                                                       |
|  }                                                                      |
|                                                                         |
|  GET /api/v1/users/{user_id}/timeline?cursor=...&limit=20               |
|  Response: { posts: [...], next_cursor, has_more }                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  SOCIAL APIS:                                                           |
|                                                                         |
|  POST /api/v1/users/{user_id}/follow                                    |
|  DELETE /api/v1/users/{user_id}/follow                                  |
|  GET /api/v1/users/{user_id}/followers?cursor=...&limit=50              |
|  GET /api/v1/users/{user_id}/following?cursor=...&limit=50              |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  INTERACTION APIS:                                                      |
|                                                                         |
|  POST /api/v1/posts/{post_id}/like                                      |
|  DELETE /api/v1/posts/{post_id}/like                                    |
|  POST /api/v1/posts/{post_id}/comments                                  |
|  Body: { content, parent_comment_id? }                                  |
|  GET /api/v1/posts/{post_id}/comments?cursor=...&limit=20               |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  PAGINATION: Cursor-based (not offset-based)                            |
|  * Offset-based breaks with real-time inserts                           |
|  * Cursor = last seen post_id (Snowflake, time-ordered)                 |
|  * WHERE post_id < cursor ORDER BY post_id DESC LIMIT 20                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10: CACHING STRATEGY

### MULTI-LAYER CACHING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CACHING LAYERS:                                                        |
|                                                                         |
|  Layer 1: CDN (Edge Cache)                                              |
|  * Static assets: profile pictures, media thumbnails                    |
|  * Trending posts (same for all users)                                  |
|  * TTL: minutes to hours                                                |
|                                                                         |
|  Layer 2: APPLICATION CACHE (Redis Cluster)                             |
|  +--------------------------------------------------+                   |
|  | Cache Type       | Key Pattern   | Data           |                  |
|  |--------------------------------------------------+                   |
|  | Feed Cache       | feed:{uid}    | Sorted set of  |                  |
|  |                  |               | post_ids       |                  |
|  |                  |               |                |                  |
|  | User Timeline    | timeline:{uid}| User's own     |                  |
|  |                  |               | recent posts   |                  |
|  |                  |               |                |                  |
|  | Post Cache       | post:{pid}    | Full post      |                  |
|  |                  |               | object (JSON)  |                  |
|  |                  |               |                |                  |
|  | User Profile     | user:{uid}    | User metadata  |                  |
|  |                  |               |                |                  |
|  | Social Count     | count:{uid}   | follower/      |                  |
|  |                  |               | following count|                  |
|  |                  |               |                |                  |
|  | Celebrity Posts  | celeb:{uid}   | Recent posts   |                  |
|  |                  |               | from celebrity |                  |
|  +--------------------------------------------------+                   |
|                                                                         |
|  Layer 3: DATABASE QUERY CACHE                                          |
|  * MySQL query cache / PgBouncer connection pooling                     |
|  * Prepared statement cache                                             |
|                                                                         |
|  CACHE INVALIDATION:                                                    |
|  * Post deleted -> Remove from all feed caches (async via Kafka)        |
|  * User unfollows -> Remove author's posts from feed cache              |
|  * Post edited -> Update post cache, feed remains same (just IDs)       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11: MEDIA HANDLING

### IMAGE AND VIDEO PIPELINE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MEDIA UPLOAD FLOW:                                                     |
|                                                                         |
|  1. Client requests pre-signed upload URL from API                      |
|  2. Client uploads directly to Object Store (S3)                        |
|     * Bypasses application server (saves bandwidth)                     |
|  3. Object Store triggers processing pipeline                           |
|                                                                         |
|  IMAGE PROCESSING:                                                      |
|  +--------------------+                                                 |
|  | Original Upload    |                                                 |
|  +--------------------+                                                 |
|           |                                                             |
|     +-----+-----+-----+                                                 |
|     |     |     |     |                                                 |
|     v     v     v     v                                                 |
|  +-----+-----+-----+-------+                                            |
|  |thumb|small|med  |original|                                           |
|  |150px|400px|800px|as-is   |                                           |
|  +-----+-----+-----+-------+                                            |
|           |                                                             |
|           v                                                             |
|  Store all variants in S3, serve via CDN                                |
|  Client requests appropriate size based on device                       |
|                                                                         |
|  VIDEO PROCESSING:                                                      |
|  +--------------------+                                                 |
|  | Original Upload    |                                                 |
|  +--------------------+                                                 |
|           |                                                             |
|           v                                                             |
|  +--------------------+                                                 |
|  | Transcoding Service|                                                 |
|  +--------------------+                                                 |
|     |     |     |                                                       |
|     v     v     v                                                       |
|  +-----+-----+-----+                                                    |
|  |480p |720p |1080p|  (adaptive bitrate)                                |
|  +-----+-----+-----+                                                    |
|           |                                                             |
|           v                                                             |
|  Generate thumbnail, store in S3, serve via CDN                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12: NOTIFICATION INTEGRATION

### NOTIFICATION FLOW

```
+--------------------------------------------------------------------------+
|                                                                          |
|  NOTIFICATION TRIGGERS:                                                  |
|                                                                          |
|  +------------------------------------+----------------+                 |
|  | Event                              | Notify         |                 |
|  +------------------------------------+----------------+                 |
|  | Someone likes your post            | Post author    |                 |
|  | Someone comments on your post      | Post author    |                 |
|  | Someone follows you                | Followee       |                 |
|  | Someone mentions you               | Mentioned user |                 |
|  | Someone shares your post           | Post author    |                 |
|  +------------------------------------+----------------+                 |
|                                                                          |
|  ARCHITECTURE:                                                           |
|  * Events published to Kafka topic: "notifications"                      |
|  * Notification Service consumes events                                  |
|  * For each event:                                                       |
|    1. Check user's notification preferences                              |
|    2. If user is ONLINE: send via WebSocket (real-time)                  |
|    3. If user is OFFLINE: send push notification (APNs/FCM)              |
|    4. Store notification in DB for notification inbox                    |
|                                                                          |
|  BATCHING:                                                               |
|  * "John and 49 others liked your post" instead of 50 notifications      |
|  * Aggregate within a time window (e.g., 5 minutes)                      |
|  * Celebrity posts: only notify for the first N likes                    |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 13: SCALING AND RELIABILITY

### SHARDING STRATEGY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATABASE SHARDING:                                                     |
|                                                                         |
|  POSTS TABLE: Shard by author_id                                        |
|  * All posts by same user on same shard                                 |
|  * User timeline query hits single shard                                |
|  * Fan-out reads are cross-shard (acceptable, cached)                   |
|                                                                         |
|  FOLLOWERS TABLE: Shard by followee_id                                  |
|  * "Get all followers of user X" hits single shard                      |
|  * Critical for fan-out service performance                             |
|                                                                         |
|  LIKES/COMMENTS: Shard by post_id                                       |
|  * All interactions for a post on same shard                            |
|  * "Get all likes for post Y" hits single shard                         |
|                                                                         |
|  SHARD COUNT: Start with 256 shards (allows growth)                     |
|  SHARD MAP: Consistent hashing for minimal resharding                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### RELIABILITY PATTERNS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RELIABILITY AND FAULT TOLERANCE:                                       |
|                                                                         |
|  1. CIRCUIT BREAKER                                                     |
|     * If Feed Service is slow, return stale cached feed                 |
|     * If Ranking Service is down, fall back to chronological            |
|     * If Notification Service is down, queue and retry                  |
|                                                                         |
|  2. GRACEFUL DEGRADATION                                                |
|     * Level 1: Full experience (ranked feed + real-time)                |
|     * Level 2: Chronological feed (ranking down)                        |
|     * Level 3: Cached feed only (feed generation down)                  |
|     * Level 4: Show user's own timeline (feed service down)             |
|                                                                         |
|  3. RATE LIMITING                                                       |
|     * Post creation: 50 posts/hour per user                             |
|     * Feed reads: 100 requests/minute per user                          |
|     * Follow actions: 200/day per user                                  |
|     * API: token bucket algorithm                                       |
|                                                                         |
|  4. MONITORING                                                          |
|     * Feed generation latency (p50, p95, p99)                           |
|     * Fan-out lag (time from post to last follower cache update)        |
|     * Cache hit rate (target > 95%)                                     |
|     * Error rates per service                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MULTI-REGION DEPLOYMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MULTI-REGION ARCHITECTURE:                                             |
|                                                                         |
|  +------------------+          +------------------+                     |
|  |   US-EAST        |          |   EU-WEST        |                     |
|  |                  |          |                  |                     |
|  | +------+ +-----+|  Async   | +------+ +-----+|                       |
|  | |App   | |Redis||<-------->| |App   | |Redis||                       |
|  | |Server| |Cache||  Repli-  | |Server| |Cache||                       |
|  | +------+ +-----+|  cation  | +------+ +-----+|                       |
|  |                  |          |                  |                     |
|  | +------+ +-----+|          | +------+ +-----+|                       |
|  | |MySQL | |Kafka||          | |MySQL | |Kafka||                       |
|  | |Primary| |    ||          | |Replica| |    ||                       |
|  | +------+ +-----+|          | +------+ +-----+|                       |
|  +------------------+          +------------------+                     |
|                                                                         |
|  * Users routed to nearest region via GeoDNS                            |
|  * Writes go to primary region, async replicated                        |
|  * Reads served from local region (eventual consistency OK)             |
|  * Cross-region follow relationships handled via async sync             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DETAILED WRITE/READ PATHS AND STATE MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                        |
|  1. ENTITY STATE MACHINE (Feed Item Lifecycle)                         |
|                                                                        |
|    [CREATED] --> [FANNING_OUT] --> [RANKED] --> [DELIVERED] --> [SEEN] |
|        |              |               |                                |
|        |              |               +---> [FILTERED]  (spam/blocked) |
|        |              |                                                |
|        |              +---> (partial: some followers done, others not) |
|        |                                                               |
|        +---> [DELETED]  (author deletes post)                          |
|                                                                        |
|    CREATED:     Post written to posts table, media URLs attached       |
|    FANNING_OUT: Fan-out workers pushing post_id to follower caches     |
|    RANKED:      Post scored by ranking algo for a specific user        |
|    DELIVERED:   Post included in a user's feed API response            |
|    SEEN:        User scrolled past the post (impression logged)        |
|    FILTERED:    Post removed by spam filter or user block list         |
|    DELETED:     is_deleted=true, async removal from all feed caches    |
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  2. CRITICAL WRITE PATH (Post Creation + Hybrid Fan-Out)               |
|                                                                        |
|    Author: POST /api/v1/posts { content, media_ids[], mentions[] }     |
|      |                                                                 |
|      v                                                                 |
|    Step 1: Write post to PostgreSQL                                    |
|      |                                                                 |
|      |     INSERT INTO posts                                           |
|      |       (post_id, author_id, content, media_urls,                 |
|      |        media_type, like_count, comment_count,                   |
|      |        share_count, is_deleted, created_at)                     |
|      |     VALUES                                                      |
|      |       (snowflake_id(), 12345, 'Hello world',                    |
|      |        '["https://cdn/img1.jpg"]', 'IMAGE',                     |
|      |        0, 0, 0, false, NOW());                                  |
|      v                                                                 |
|    Step 2: Write to author timeline cache                              |
|      |     Redis: ZADD timeline:{author_id} <timestamp> <post_id>      |
|      |     Redis: ZREMRANGEBYRANK timeline:{author_id} 0 -801          |
|      |       (keep only latest 800 posts)                              |
|      v                                                                 |
|    Step 3: Cache post object                                           |
|      |     Redis: SET post:{post_id} <post_json> EX 86400              |
|      v                                                                 |
|    Step 4: Publish to Kafka for fan-out                                |
|      |     Topic: post_created                                         |
|      |     Payload: { post_id, author_id, is_celebrity }               |
|      v                                                                 |
|    Step 5: Fan-out workers consume from Kafka                          |
|      |                                                                 |
|      |  IF author.is_celebrity = false (followers < 10K):              |
|      |    SELECT follower_id FROM followers                            |
|      |      WHERE followee_id = author_id;                             |
|      |    For each follower:                                           |
|      |      Redis: ZADD feed:{follower_id} <timestamp> <post_id>       |
|      |      Redis: ZREMRANGEBYRANK feed:{follower_id} 0 -501           |
|      |        (keep feed cache at 500 entries max)                     |
|      |                                                                 |
|      |  IF author.is_celebrity = true (followers >= 10K):              |
|      |    Redis: ZADD celeb:{author_id} <timestamp> <post_id>          |
|      |    (no fan-out; merged at read time)                            |
|      v                                                                 |
|    Return { post_id, created_at } to author                            |
|                                                                        |
|    WRITE ORDER: PostgreSQL -> Redis timeline -> Redis post cache       |
|                 -> Kafka -> fan-out to Redis feed caches               |
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  3. READ PATH (Feed Generation - Cache + Merge + Rank)                 |
|                                                                        |
|    User: GET /api/v1/feed?cursor={last_post_id}&limit=20               |
|      |                                                                 |
|      v                                                                 |
|    Step 1: Fetch pre-computed feed from Redis                          |
|      |     ZREVRANGEBYSCORE feed:{user_id} +inf <cursor> LIMIT 20      |
|      |     Returns list of post_ids (pushed by fan-out workers)        |
|      v                                                                 |
|    Step 2: Fetch celebrity posts (fan-out-on-read portion)             |
|      |     Get user's followed celebrities from social graph           |
|      |     For each celebrity:                                         |
|      |       ZREVRANGEBYSCORE celeb:{celeb_id} +inf <cursor> LIMIT 5   |
|      |     Merge celebrity post_ids with Step 1 results                |
|      v                                                                 |
|    Step 3: Hydrate post objects                                        |
|      |     For each post_id:                                           |
|      |       Redis: GET post:{post_id}  (batch MGET for speed)         |
|      |       Cache miss -> SELECT * FROM posts WHERE post_id = ?       |
|      |       Then SET post:{post_id} <json> EX 86400                   |
|      v                                                                 |
|    Step 4: Rank posts (ML scoring)                                     |
|      |     Score = f(affinity, recency, engagement, post_type)         |
|      |     Filter out: blocked users, muted keywords, seen posts       |
|      |     Sort by score DESC, take top 20                             |
|      v                                                                 |
|    Step 5: Return paginated response                                   |
|            { posts: [...], next_cursor, has_more }                     |
|                                                                        |
|    CACHE MISS (cold user, no feed in Redis):                           |
|      Fall back to full fan-out-on-read:                                |
|      Get all followed user_ids -> fetch their recent posts ->          |
|      merge, rank, return. Then populate feed:{user_id} in Redis.       |
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  4. FAILURE SCENARIOS                                                  |
|                                                                        |
|  What Fails               | Impact & Recovery                          |
|  -------------------------+--------------------------------------------+
|  Redis cluster down       | Feed reads fall back to DB fan-out-on-read |
|                           | (slow but functional). Post writes still   |
|                           | go to PostgreSQL. Fan-out queues in Kafka  |
|                           | until Redis recovers and caches rebuild.   |
|  -------------------------+--------------------------------------------+
|  Kafka down               | New posts saved to DB but fan-out stalls.  |
|                           | Existing feed caches serve stale feeds.    |
|                           | On recovery, replay un-consumed events.    |
|                           | Users may see delayed posts for minutes.   |
|  -------------------------+--------------------------------------------+
|  Fan-out worker crash     | Partial fan-out: some followers got the    |
|                           | post, others didn't. Kafka consumer offset |
|                           | not committed, so message is reprocessed.  |
|                           | ZADD is idempotent (safe to re-execute).   |
|  -------------------------+--------------------------------------------+
|  Celebrity post storm     | 100M-follower user posts -> read-path      |
|                           | merging adds latency. Mitigate: cache      |
|                           | celeb:{id} aggressively, pre-compute       |
|                           | celeb merge for active users.              |
|  -------------------------+--------------------------------------------+
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  5. CLEANUP / EXPIRY                                                   |
|                                                                        |
|    Feed Cache Trimming (on every ZADD):                                |
|      ZREMRANGEBYRANK feed:{user_id} 0 -501                             |
|      Keeps feed cache at 500 post_ids max per user                     |
|                                                                        |
|    Post Deletion Propagation (async via Kafka):                        |
|      Author deletes post -> UPDATE posts SET is_deleted=true           |
|      Kafka event: post_deleted { post_id, author_id }                  |
|      Workers: ZREM feed:{follower_id} <post_id> for all followers      |
|      Redis: DEL post:{post_id}                                         |
|                                                                        |
|    Stale Cache Expiry:                                                 |
|      post:{pid} keys: EX 86400 (24h TTL)                               |
|      feed:{uid} keys: no TTL (maintained by trim + fan-out)            |
|      Inactive user feed caches: evicted by Redis LRU policy            |
|      celeb:{uid} keys: EX 3600 (1h, rebuilt from DB on miss)           |
|                                                                        |
|    Soft-Deleted Posts Cleanup (weekly batch job):                      |
|      DELETE FROM posts WHERE is_deleted = true                         |
|        AND created_at < NOW() - INTERVAL 30 DAY;                       |
|                                                                        |
+-------------------------------------------------------------------------+
```

## SECTION 14: INTERVIEW Q&A

### QUESTION 1: WHY HYBRID FAN-OUT?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: Why use a hybrid fan-out approach instead of pure push or pull?     |
|                                                                         |
|  A: Pure push (fan-out on write) is ideal for most users because it     |
|  pre-computes feeds, making reads extremely fast. However, for          |
|  celebrities with millions of followers, pushing to all followers       |
|  is prohibitively expensive (100M writes per post).                     |
|                                                                         |
|  Pure pull (fan-out on read) avoids the celebrity problem but makes     |
|  every feed read slow because you must query hundreds of timelines      |
|  and merge them in real-time.                                           |
|                                                                         |
|  The hybrid approach uses push for normal users (99% of users) and      |
|  pull for celebrities (top 1%). This gives us fast reads for the        |
|  common case while avoiding the write amplification problem.            |
|                                                                         |
|  The threshold (e.g., 10K followers) is tunable based on system         |
|  capacity and latency requirements.                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 2: HOW TO HANDLE FEED CONSISTENCY?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: What consistency guarantees does the feed provide?                  |
|                                                                         |
|  A: We use eventual consistency for feeds. When a user posts:           |
|  * The post appears on the author's own timeline immediately            |
|    (strong consistency for own content)                                 |
|  * The post appears in followers' feeds within seconds                  |
|    (eventual consistency via async fan-out)                             |
|                                                                         |
|  This is acceptable because:                                            |
|  1. Users rarely coordinate to check if they see the same feed          |
|  2. A few seconds delay is imperceptible                                |
|  3. Strong consistency would require synchronous writes to all          |
|     follower feeds, which is too slow                                   |
|                                                                         |
|  For likes/comments counts, we use approximate counters that            |
|  periodically sync with the source of truth in the database.            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 3: HOW DOES CURSOR-BASED PAGINATION WORK?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: Why cursor-based pagination over offset-based?                      |
|                                                                         |
|  A: Offset-based pagination (LIMIT 20 OFFSET 40) breaks in              |
|  real-time feeds because new posts shift the offset.                    |
|                                                                         |
|  PROBLEM WITH OFFSET:                                                   |
|  * User loads page 1 (posts 1-20)                                       |
|  * 5 new posts arrive                                                   |
|  * User loads page 2 (OFFSET 20) -- sees 5 duplicates!                  |
|                                                                         |
|  CURSOR-BASED SOLUTION:                                                 |
|  * Page 1: GET /feed?limit=20                                           |
|  * Response includes cursor = last_post_id (e.g., post_789)             |
|  * Page 2: GET /feed?cursor=post_789&limit=20                           |
|  * Query: WHERE post_id < 789 ORDER BY post_id DESC LIMIT 20            |
|  * New posts don't affect pagination since we're using the post_id      |
|    as a stable anchor point.                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 4: HOW TO HANDLE POST DELETION?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: What happens when a user deletes a post?                            |
|                                                                         |
|  A: We use soft delete + async cleanup:                                 |
|                                                                         |
|  1. Mark post as is_deleted = true in Post DB (immediate)               |
|  2. Remove from author's timeline cache (immediate)                     |
|  3. Publish PostDeleted event to Kafka                                  |
|  4. Fan-out service removes post_id from all follower feed caches       |
|     (async, may take seconds to minutes)                                |
|  5. If someone reads their feed before cleanup, the feed service        |
|     checks is_deleted when hydrating post details and filters it out    |
|                                                                         |
|  The double-check (step 5) ensures deleted posts never show even        |
|  if async cleanup hasn't completed yet.                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 5: HOW TO HANDLE THUNDERING HERD?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How do you handle thundering herd when a celebrity posts?           |
|                                                                         |
|  A: When a celebrity with 100M followers posts, millions of followers   |
|  may try to read the post simultaneously, causing cache stampede.       |
|                                                                         |
|  SOLUTIONS:                                                             |
|  1. REQUEST COALESCING                                                  |
|     * If multiple users request the same celebrity's timeline           |
|       simultaneously, only one DB query is made                         |
|     * Others wait for the result and share it                           |
|                                                                         |
|  2. PRE-WARMING CACHE                                                   |
|     * When celebrity posts, immediately cache their post                |
|     * Don't wait for first read to trigger cache population             |
|                                                                         |
|  3. LEASE-BASED LOCKING                                                 |
|     * Only one process can rebuild a cache entry at a time              |
|     * Others serve stale data or wait briefly                           |
|                                                                         |
|  4. STALE-WHILE-REVALIDATE                                              |
|     * Serve slightly stale feed while refreshing in background          |
|     * Users get fast response, data refreshes async                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 6: HOW TO IMPLEMENT TRENDING TOPICS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How would you implement trending topics/hashtags?                   |
|                                                                         |
|  A: Use a streaming count-min sketch approach:                          |
|                                                                         |
|  1. REAL-TIME COUNTING                                                  |
|     * Every post with a hashtag publishes to Kafka                      |
|     * Stream processor (Flink/Spark) maintains sliding window counts    |
|     * Count hashtag occurrences in last 1h, 4h, 24h windows             |
|                                                                         |
|  2. TRENDING SCORE                                                      |
|     * Not just absolute count (would always be generic topics)          |
|     * Score = current_velocity / baseline_velocity                      |
|     * A hashtag trending is one with unusually high current activity    |
|                                                                         |
|  3. STORAGE                                                             |
|     * Top 100 trending topics stored in Redis (updated every minute)    |
|     * Personalized trending: filter by user's interests/location        |
|                                                                         |
|  4. DISPLAY                                                             |
|     * Trending topics cached at CDN level (same for region)             |
|     * Updated every 5 minutes (not real-time, reduces load)             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 7: HOW TO PREVENT SPAM?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How do you prevent spam and abuse in the news feed?                 |
|                                                                         |
|  A: Multi-layered approach:                                             |
|                                                                         |
|  1. RATE LIMITING                                                       |
|     * Max posts per hour/day per user                                   |
|     * Max follows per day                                               |
|     * Max likes per minute                                              |
|                                                                         |
|  2. CONTENT FILTERING (at post creation)                                |
|     * ML model classifies content as spam/not-spam                      |
|     * Blocked word lists                                                |
|     * URL scanning against known malicious domains                      |
|                                                                         |
|  3. BEHAVIORAL SIGNALS                                                  |
|     * New accounts with high posting frequency flagged                  |
|     * Accounts with low follower:following ratio flagged                |
|     * Duplicate content detection (near-duplicate hashing)              |
|                                                                         |
|  4. USER REPORTS                                                        |
|     * Users can report spam posts                                       |
|     * High-report posts auto-hidden pending review                      |
|                                                                         |
|  5. SHADOW BANNING                                                      |
|     * Spam accounts' posts only visible to themselves                   |
|     * Not pushed to any follower feeds                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 8: DATABASE CHOICE JUSTIFICATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: Why these specific database choices?                                |
|                                                                         |
|  A: Each database is chosen for its specific access pattern:            |
|                                                                         |
|  MySQL/PostgreSQL (Posts, Users):                                       |
|  * Strong consistency for user data                                     |
|  * Rich query support (joins for hydrating feed)                        |
|  * Mature sharding solutions (Vitess, Citus)                            |
|  * Well-understood operationally                                        |
|                                                                         |
|  Redis (Feed Cache, Counters):                                          |
|  * Sub-millisecond reads for feed retrieval                             |
|  * Sorted sets perfect for ordered feed storage                         |
|  * Atomic operations for counters (INCR/DECR)                           |
|  * Pub/Sub for real-time feed updates                                   |
|                                                                         |
|  Elasticsearch (Search):                                                |
|  * Full-text search on post content                                     |
|  * Hashtag and user search                                              |
|  * Trending topic aggregation                                           |
|                                                                         |
|  Kafka (Event Streaming):                                               |
|  * Decouples post creation from fan-out                                 |
|  * Handles burst traffic (buffer during spikes)                         |
|  * Exactly-once semantics for fan-out                                   |
|  * Multiple consumers (fan-out, notifications, analytics)               |
|                                                                         |
|  S3 / Object Store (Media):                                             |
|  * Cheap, durable storage for images/videos                             |
|  * Direct upload from client (pre-signed URLs)                          |
|  * CDN integration for global distribution                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 9: HOW TO HANDLE FEED FOR NEW USERS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How does the feed work for new users with no follows?               |
|                                                                         |
|  A: Cold start problem - solved with multiple strategies:               |
|                                                                         |
|  1. ONBOARDING FLOW                                                     |
|     * Ask user to select interests (sports, tech, music, etc.)          |
|     * Suggest popular accounts to follow in those categories            |
|     * Pre-populate feed with trending content in interests              |
|                                                                         |
|  2. EXPLORE/DISCOVER FEED                                               |
|     * Show globally popular and trending content                        |
|     * Personalize based on what user engages with                       |
|     * Gradually transition from explore to personalized feed            |
|                                                                         |
|  3. SOCIAL GRAPH BOOTSTRAP                                              |
|     * Import contacts (with permission) to find existing users          |
|     * Suggest friends-of-friends                                        |
|     * "People you may know" based on demographics                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 10: WHAT METRICS WOULD YOU MONITOR?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Q: What key metrics would you monitor for this system?                  |
|                                                                          |
|  A: Organized by category:                                               |
|                                                                          |
|  PERFORMANCE:                                                            |
|  * Feed generation latency: p50, p95, p99 (target: <500ms p99)           |
|  * Post creation latency (target: <1s)                                   |
|  * Fan-out completion time (target: <5s for 99% of posts)                |
|  * Cache hit rate (target: >95%)                                         |
|                                                                          |
|  AVAILABILITY:                                                           |
|  * Service uptime (target: 99.99%)                                       |
|  * Error rate per endpoint (target: <0.1%)                               |
|  * Database replication lag                                              |
|  * Redis cluster health                                                  |
|                                                                          |
|  BUSINESS:                                                               |
|  * DAU / MAU ratio (engagement health)                                   |
|  * Posts per user per day                                                |
|  * Feed scroll depth (how many posts users view)                         |
|  * Time to first interaction after feed load                             |
|                                                                          |
|  CAPACITY:                                                               |
|  * Queue depth (Kafka consumer lag)                                      |
|  * Storage growth rate                                                   |
|  * CPU/memory utilization across services                                |
|  * Network bandwidth utilization                                         |
|                                                                          |
+--------------------------------------------------------------------------+
```

### QUESTION 11: HOW TO HANDLE READ-AFTER-WRITE CONSISTENCY?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How do you ensure a user sees their own post immediately?           |
|                                                                         |
|  A: Read-after-write consistency for the author:                        |
|                                                                         |
|  1. After creating a post, the Post Service writes to:                  |
|     a. Posts DB (source of truth)                                       |
|     b. Author's timeline cache (synchronous)                            |
|     c. Author's own feed cache (synchronous prepend)                    |
|                                                                         |
|  2. The client also optimistically adds the post to the local           |
|     feed state immediately (client-side optimistic update).             |
|                                                                         |
|  3. If the user refreshes, the API checks both:                         |
|     * The feed cache (may not have the post yet)                        |
|     * The user's own timeline (will have the post)                      |
|     And merges them, ensuring own posts are always visible.             |
|                                                                         |
|  This way, the author always sees their post while followers            |
|  see it eventually (within seconds) via async fan-out.                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 12: HOW WOULD YOU EVOLVE THIS DESIGN?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: What would you add or change as the system grows?                   |
|                                                                         |
|  A: Evolution roadmap:                                                  |
|                                                                         |
|  PHASE 1 (0-10M users): Monolith                                        |
|  * Single service, single DB                                            |
|  * Simple chronological feed                                            |
|  * In-memory cache                                                      |
|                                                                         |
|  PHASE 2 (10M-100M users): Service Split                                |
|  * Separate Post, Feed, Social Graph services                           |
|  * Add Redis for feed caching                                           |
|  * Add Kafka for async processing                                       |
|  * Simple fan-out on write for all users                                |
|                                                                         |
|  PHASE 3 (100M-500M users): Scale Out                                   |
|  * Database sharding                                                    |
|  * Hybrid fan-out (celebrity optimization)                              |
|  * ML-based feed ranking                                                |
|  * Multi-region deployment                                              |
|                                                                         |
|  PHASE 4 (500M+ users): Optimization                                    |
|  * Advanced ranking models (deep learning)                              |
|  * Real-time feature store for ranking                                  |
|  * Edge computing for feed delivery                                     |
|  * Video/live streaming integration                                     |
|  * Content recommendation engine                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 15: WRAP-UP

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SUMMARY OF KEY DESIGN DECISIONS:                                       |
|                                                                         |
|  1. HYBRID FAN-OUT STRATEGY                                             |
|     Fan-out on write for normal users (pre-compute feed at post         |
|     time). Fan-out on read for celebrities (fetch at read time).        |
|     Threshold: users with >10K followers use fan-out on read.           |
|     This avoids the thundering herd problem for celebrity posts.        |
|                                                                         |
|  2. MULTI-STAGE RANKING PIPELINE                                        |
|     Candidate generation (retrieve from pre-computed feed cache)        |
|     -> first-pass scoring (lightweight ML model, ~50ms) -> deep         |
|     ranking (full model, ~100ms) -> diversity injection (~20ms).        |
|     Total budget: ~200ms to rank a feed page.                           |
|                                                                         |
|  3. FEED CACHE AS PRIMARY READ PATH                                     |
|     Pre-computed feed stored in Redis sorted sets. Feed reads           |
|     hit cache directly (sub-10ms). Cache miss falls through to          |
|     fan-out-on-read path. Cache invalidation on new posts/unfollows.    |
|                                                                         |
|  4. ASYNC POST PROCESSING PIPELINE                                      |
|     Post creation is synchronous (write to DB, return ID). Fan-out,     |
|     media processing, notification, and search indexing happen          |
|     asynchronously via Kafka. Decouples post latency from fan-out       |
|     cost.                                                               |
|                                                                         |
|  5. GRAPH-BASED SOCIAL LAYER                                            |
|     Follow/friend relationships stored in graph DB or adjacency         |
|     list. Powers fan-out target resolution and "mutual friends"         |
|     features. Cached in Redis for hot-path lookups.                     |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  KEY TRADE-OFFS:                                                        |
|                                                                         |
|  * FAN-OUT ON WRITE vs READ: Write gives instant feed reads but         |
|    wastes work for inactive users and is expensive for celebrities.     |
|    Read saves write cost but adds read latency. Hybrid balances         |
|    both at the cost of two code paths and merge logic.                  |
|                                                                         |
|  * RANKED vs CHRONOLOGICAL: Ranking boosts engagement but adds          |
|    latency (~200ms) and complexity (ML models, feature stores).         |
|    Chronological is simple but lower engagement. We chose ranked        |
|    with chronological as a fallback if ranking is slow.                 |
|                                                                         |
|  * FEED FRESHNESS vs CACHE HIT RATE: Longer cache TTL = higher          |
|    hit rate but staler feed. Shorter TTL = fresher but more cache       |
|    misses and fan-out-on-read fallbacks. We use 60s TTL with            |
|    event-driven invalidation on new posts from close friends.           |
|                                                                         |
|  * CONSISTENCY vs AVAILABILITY: Feed reads are eventually consistent    |
|    (a new post may take seconds to appear in all followers' feeds).     |
|    Acceptable trade-off: users tolerate slight delay in feed but        |
|    not feed downtime.                                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 16: QUICK REFERENCE SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NEWS FEED SYSTEM - QUICK REFERENCE                                     |
|                                                                         |
|  SCALE: 500M DAU, 1B posts/day, 10B reads/day                           |
|                                                                         |
|  KEY DECISIONS:                                                         |
|  1. Hybrid fan-out (push for normal, pull for celebrities)              |
|  2. Redis sorted sets for feed cache                                    |
|  3. Snowflake IDs for time-ordered post IDs                             |
|  4. Cursor-based pagination                                             |
|  5. Kafka for async event processing                                    |
|  6. ML-based feed ranking with diversity rules                          |
|  7. Shard posts by author_id, followers by followee_id                  |
|                                                                         |
|  LATENCY BUDGET:                                                        |
|  Feed read (cache hit): <50ms                                           |
|  Feed read (cache miss): <500ms                                         |
|  Post creation: <1s (including async fan-out trigger)                   |
|  Fan-out completion: <5s for 99% of posts                               |
|                                                                         |
|  MAIN TRADEOFFS:                                                        |
|  * Consistency vs latency (chose eventual consistency)                  |
|  * Storage vs compute (chose pre-computation with caching)              |
|  * Simplicity vs performance (chose hybrid complexity for scale)        |
|                                                                         |
+-------------------------------------------------------------------------+
```
