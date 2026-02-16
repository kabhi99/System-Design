# SOCIAL MEDIA PLATFORM SYSTEM DESIGN (TWITTER/FACEBOOK-LIKE)

A COMPLETE CONCEPTUAL GUIDE
SECTION 1: UNDERSTANDING THE PROBLEM
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHAT IS A SOCIAL MEDIA PLATFORM?                                      |*
*|                                                                         |*
*|  A service that allows users to:                                       |*
*|  * Create and share content (posts, photos, videos)                   |*
*|  * Follow/friend other users                                          |*
*|  * View a personalized feed of content                                |*
*|  * Interact with content (like, comment, share)                       |*
*|  * Receive notifications about activities                             |*
*|                                                                         |*
*|  Examples: Twitter/X, Facebook, Instagram, LinkedIn                    |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  KEY CHALLENGES                                                        |*
*|                                                                         |*
*|  1. NEWS FEED GENERATION (The hardest problem!)                       |*
*|     * How to show relevant content from thousands of followees?       |*
*|     * Real-time vs batch processing                                   |*
*|     * Handling celebrities with millions of followers                 |*
*|                                                                         |*
*|  2. SCALE                                                              |*
*|     * Billions of users                                               |*
*|     * Millions of posts per second                                    |*
*|     * Petabytes of media                                              |*
*|                                                                         |*
*|  3. REAL-TIME                                                          |*
*|     * Users expect instant updates                                    |*
*|     * Push notifications                                               |*
*|     * Live engagement                                                  |*
*|                                                                         |*
*|  4. AVAILABILITY                                                       |*
*|     * Always-on service                                               |*
*|     * Graceful degradation                                            |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2: REQUIREMENTS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  FUNCTIONAL REQUIREMENTS                                               |*
*|                                                                         |*
*|  1. USER MANAGEMENT                                                    |*
*|     * Sign up / login                                                  |*
*|     * Profile (bio, profile picture, settings)                        |*
*|     * Follow/unfollow other users                                     |*
*|     * Block/mute users                                                 |*
*|                                                                         |*
*|  2. POST CREATION                                                      |*
*|     * Create text posts (tweets) - 280 chars                          |*
*|     * Attach images/videos                                            |*
*|     * Mentions (@username)                                             |*
*|     * Hashtags (#topic)                                                |*
*|     * Delete own posts                                                 |*
*|                                                                         |*
*|  3. NEWS FEED                                                          |*
*|     * View personalized feed of posts                                 |*
*|     * See posts from people you follow                                |*
*|     * Reverse chronological or ranked                                 |*
*|     * Infinite scroll (pagination)                                    |*
*|                                                                         |*
*|  4. INTERACTIONS                                                       |*
*|     * Like/unlike posts                                               |*
*|     * Comment on posts                                                 |*
*|     * Repost/retweet                                                   |*
*|     * Share posts                                                      |*
*|                                                                         |*
*|  5. SEARCH                                                             |*
*|     * Search users                                                     |*
*|     * Search posts (by content, hashtag)                              |*
*|     * Trending topics                                                  |*
*|                                                                         |*
*|  6. NOTIFICATIONS                                                      |*
*|     * New follower                                                     |*
*|     * Post liked/commented/shared                                     |*
*|     * Mentions                                                         |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  NON-FUNCTIONAL REQUIREMENTS                                           |*
*|                                                                         |*
*|  1. SCALE                                                              |*
*|     * 500 million daily active users                                  |*
*|     * 1 billion posts per day                                         |*
*|                                                                         |*
*|  2. PERFORMANCE                                                        |*
*|     * Feed load: < 200ms                                              |*
*|     * Post creation: < 500ms                                          |*
*|                                                                         |*
*|  3. AVAILABILITY                                                       |*
*|     * 99.99% uptime                                                   |*
*|     * Eventual consistency acceptable                                 |*
*|                                                                         |*
*|  4. RELIABILITY                                                        |*
*|     * Posts should never be lost                                      |*
*|     * Media durably stored                                            |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3: SCALE ESTIMATION
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  USER STATISTICS                                                       |*
*|                                                                         |*
*|  * 1 billion total users                                              |*
*|  * 500 million DAU (daily active users)                               |*
*|  * Average user follows 200 people                                    |*
*|  * Average user posts 2 times per week                                |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  POSTS/TWEETS                                                          |*
*|                                                                         |*
*|  Posts per day:                                                        |*
*|  * 500M DAU × 2 posts/week ÷ 7 = ~140 million posts/day              |*
*|  * Let's assume 500 million posts/day (including reposts)            |*
*|                                                                         |*
*|  Posts per second:                                                     |*
*|  * 500M / 86400 ≈ 6,000 posts/second                                 |*
*|  * Peak (2x): 12,000 posts/second                                    |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  FEED READS                                                            |*
*|                                                                         |*
*|  Feed requests per day:                                                |*
*|  * 500M DAU × 10 feed views/day = 5 billion feed requests/day        |*
*|                                                                         |*
*|  Feed requests per second:                                             |*
*|  * 5B / 86400 ≈ 58,000 feed requests/second                          |*
*|  * Peak: 100,000+ requests/second                                    |*
*|                                                                         |*
*|  READ:WRITE RATIO = 58,000 : 6,000 ≈ 10:1                            |*
*|  (Read heavy system!)                                                  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  STORAGE                                                               |*
*|                                                                         |*
*|  Post storage:                                                         |*
*|  * Post ID: 8 bytes                                                   |*
*|  * User ID: 8 bytes                                                   |*
*|  * Content: 280 bytes (text)                                          |*
*|  * Timestamp: 8 bytes                                                 |*
*|  * Metadata: 100 bytes                                                |*
*|  * Total: ~400 bytes per post                                        |*
*|                                                                         |*
*|  Posts per year:                                                       |*
*|  * 500M posts/day × 365 = 182.5 billion posts/year                   |*
*|  * Storage: 182.5B × 400 bytes = 73 TB/year (just text)             |*
*|                                                                         |*
*|  Media storage:                                                        |*
*|  * 20% of posts have images (avg 200 KB)                             |*
*|  * 5% have videos (avg 5 MB)                                         |*
*|  * Much larger than text storage!                                    |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  FOLLOWERS GRAPH                                                       |*
*|                                                                         |*
*|  Follow relationships:                                                 |*
*|  * 1B users × 200 avg follows = 200 billion edges                    |*
*|  * Each edge: 16 bytes (follower_id + followee_id)                  |*
*|  * Total: 200B × 16 = 3.2 TB                                        |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4: HIGH-LEVEL ARCHITECTURE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SYSTEM OVERVIEW                                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |                     CLIENTS                                    |  |*
*|  |              (Web, iOS, Android)                               |  |*
*|  |                        |                                        |  |*
*|  |                        v                                        |  |*
*|  |            +-----------------------+                          |  |*
*|  |            |     CDN (Media)       |                          |  |*
*|  |            +-----------+-----------+                          |  |*
*|  |                        |                                        |  |*
*|  |                        v                                        |  |*
*|  |            +-----------------------+                          |  |*
*|  |            |    LOAD BALANCER      |                          |  |*
*|  |            +-----------+-----------+                          |  |*
*|  |                        |                                        |  |*
*|  |    +-------------------+-------------------+                  |  |*
*|  |    |                   |                   |                  |  |*
*|  |    v                   v                   v                  |  |*
*|  |  +---------+       +---------+       +---------+            |  |*
*|  |  |  API    |       |  API    |       |  API    |            |  |*
*|  |  | Server  |       | Server  |       | Server  |            |  |*
*|  |  +----+----+       +----+----+       +----+----+            |  |*
*|  |       |                 |                 |                  |  |*
*|  |       +-----------------+-----------------+                  |  |*
*|  |                         |                                     |  |*
*|  |    +--------------------+--------------------+               |  |*
*|  |    |                    |                    |               |  |*
*|  |    v                    v                    v               |  |*
*|  |  +----------+    +----------+    +--------------+           |  |*
*|  |  |   Post   |    |   Feed   |    |    User      |           |  |*
*|  |  | Service  |    | Service  |    |   Service    |           |  |*
*|  |  +----+-----+    +----+-----+    +------+-------+           |  |*
*|  |       |               |                 |                    |  |*
*|  |       v               v                 v                    |  |*
*|  |  +----------+   +-----------+    +--------------+           |  |*
*|  |  |  Posts   |   |   Feed    |    |    Users     |           |  |*
*|  |  |   DB     |   |   Cache   |    |     DB       |           |  |*
*|  |  +----------+   |  (Redis)  |    +--------------+           |  |*
*|  |                 +-----------+                                |  |*
*|  |                                                                 |  |*
*|  |    +--------------------------------------------+              |  |*
*|  |    |              MESSAGE QUEUE                 |              |  |*
*|  |    |               (Kafka)                      |              |  |*
*|  |    +------------------+-------------------------+              |  |*
*|  |                       |                                        |  |*
*|  |         +-------------+-------------+                         |  |*
*|  |         v             v             v                         |  |*
*|  |   +----------+  +----------+  +----------+                   |  |*
*|  |   | Fanout   |  | Notific. |  | Search   |                   |  |*
*|  |   | Service  |  | Service  |  | Indexer  |                   |  |*
*|  |   +----------+  +----------+  +----------+                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*CORE SERVICES*
*-------------*
*1. USER SERVICE*
** Authentication, profiles, settings*
** Follow/unfollow relationships*
** User search*
*2. POST SERVICE*
** Create, read, delete posts*
** Store post metadata*
** Handle mentions and hashtags*
*3. FEED SERVICE (Most complex!)*
** Generate personalized news feed*
** Cache user timelines*
** Handle pagination*
*4. FANOUT SERVICE*
** Distribute posts to followers*
** Handle different fanout strategies*
*5. NOTIFICATION SERVICE*
** Push notifications*
** In-app notifications*
** Email digests*
*6. MEDIA SERVICE*
** Upload images/videos*
** Transcode and resize*
** Serve via CDN*
*7. SEARCH SERVICE*
** Index posts and users*
** Full-text search*
** Trending topics*

SECTION 5: DATA MODEL
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  DATABASE SCHEMA                                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: users                                                  |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | Column          | Type          | Description            | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | user_id         | BIGINT (PK)   | Unique identifier      | |  |*
*|  |  | username        | VARCHAR(50)   | Unique handle          | |  |*
*|  |  | email           | VARCHAR(255)  | Login email            | |  |*
*|  |  | password_hash   | VARCHAR(255)  | Bcrypt hash            | |  |*
*|  |  | display_name    | VARCHAR(100)  | Shown name             | |  |*
*|  |  | bio             | VARCHAR(500)  | Profile description    | |  |*
*|  |  | profile_pic_url | VARCHAR(500)  | Avatar URL             | |  |*
*|  |  | follower_count  | INT           | Denormalized count     | |  |*
*|  |  | following_count | INT           | Denormalized count     | |  |*
*|  |  | created_at      | TIMESTAMP     | Registration time      | |  |*
*|  |  | is_verified     | BOOLEAN       | Blue checkmark         | |  |*
*|  |  | is_celebrity    | BOOLEAN       | Has 1M+ followers      | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  INDEXES:                                                      |  |*
*|  |  * username (unique)                                          |  |*
*|  |  * email (unique)                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: follows                                                |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | Column          | Type          | Description            | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | follower_id     | BIGINT (PK)   | Who is following       | |  |*
*|  |  | followee_id     | BIGINT (PK)   | Who is being followed  | |  |*
*|  |  | created_at      | TIMESTAMP     | When followed          | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  PRIMARY KEY: (follower_id, followee_id)                      |  |*
*|  |                                                                 |  |*
*|  |  INDEXES:                                                      |  |*
*|  |  * (followee_id, created_at) - Get followers of user         |  |*
*|  |  * (follower_id, created_at) - Get who user follows          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: posts                                                  |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | Column          | Type          | Description            | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | post_id         | BIGINT (PK)   | Snowflake ID          | |  |*
*|  |  | user_id         | BIGINT        | Author                | |  |*
*|  |  | content         | VARCHAR(280)  | Post text             | |  |*
*|  |  | created_at      | TIMESTAMP     | Post time             | |  |*
*|  |  | reply_to_id     | BIGINT        | NULL if not reply     | |  |*
*|  |  | repost_of_id    | BIGINT        | NULL if original      | |  |*
*|  |  | like_count      | INT           | Denormalized          | |  |*
*|  |  | reply_count     | INT           | Denormalized          | |  |*
*|  |  | repost_count    | INT           | Denormalized          | |  |*
*|  |  | has_media       | BOOLEAN       | Has image/video       | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  INDEXES:                                                      |  |*
*|  |  * (user_id, created_at DESC) - User's timeline              |  |*
*|  |  * (reply_to_id) - Get replies to a post                     |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: likes                                                  |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | user_id         | BIGINT (PK)   | Who liked              | |  |*
*|  |  | post_id         | BIGINT (PK)   | What was liked         | |  |*
*|  |  | created_at      | TIMESTAMP     | When liked             | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  PRIMARY KEY: (user_id, post_id)                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: media                                                  |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | media_id        | BIGINT (PK)   | Unique ID              | |  |*
*|  |  | post_id         | BIGINT        | Associated post        | |  |*
*|  |  | media_type      | ENUM          | IMAGE, VIDEO, GIF      | |  |*
*|  |  | url             | VARCHAR(500)  | CDN URL                | |  |*
*|  |  | thumbnail_url   | VARCHAR(500)  | Preview URL            | |  |*
*|  |  | width           | INT           | Dimensions             | |  |*
*|  |  | height          | INT           | Dimensions             | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SNOWFLAKE ID (Distributed ID Generation)                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  64-bit ID structure:                                          |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  | 1 bit |   41 bits    | 10 bits  |    12 bits           |  |  |*
*|  |  |unused |  timestamp   | machine  |    sequence          |  |  |*
*|  |  |       | (ms since    |    ID    |    number            |  |  |*
*|  |  |       |  epoch)      |          |                      |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  |  Benefits:                                                     |  |*
*|  |  * Sortable by time (timestamp prefix)                        |  |*
*|  |  * Generated locally (no coordination)                        |  |*
*|  |  * 4096 IDs per millisecond per machine                      |  |*
*|  |  * Used by Twitter, Discord                                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 6: NEWS FEED - THE CORE CHALLENGE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  THE NEWS FEED PROBLEM                                                 |*
*|                                                                         |*
*|  When user opens app, show posts from people they follow              |*
*|  Sorted by time (or relevance)                                         |*
*|                                                                         |*
*|  Seems simple? Let's see...                                           |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  APPROACH 1: PULL MODEL (Fan-in on Read)                              |*
*|  --------------------------------------                                |*
*|                                                                         |*
*|  When user requests feed:                                              |*
*|  1. Get list of people user follows                                   |*
*|  2. Query posts from each followed user                               |*
*|  3. Merge and sort by time                                            |*
*|  4. Return top N posts                                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  User A follows: [B, C, D, E, ... 200 users]                  |  |*
*|  |                                                                 |  |*
*|  |  Feed Request:                                                 |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  +-------------+     SELECT * FROM posts                      |  |*
*|  |  | Get follows |     WHERE user_id IN (B, C, D, E, ...)      |  |*
*|  |  | (200 users) |     ORDER BY created_at DESC                |  |*
*|  |  +-------------+     LIMIT 20;                                |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  Merge & Sort                                                  |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  Return Feed                                                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  PROBLEM: Too slow at scale!                                          |*
*|                                                                         |*
*|  * User follows 200 people                                            |*
*|  * Query 200 user timelines                                           |*
*|  * Merge millions of posts                                            |*
*|  * Every. Single. Feed. Request.                                     |*
*|  * 58,000 requests/second = disaster!                                |*
*|                                                                         |*
*|  WHEN TO USE PULL:                                                     |*
*|  * User has very few followers                                       |*
*|  * Celebrities viewing their feed (they follow few people)           |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  APPROACH 2: PUSH MODEL (Fan-out on Write)  ⭐ PREFERRED             |*
*|  ------------------------------------------------------               |*
*|                                                                         |*
*|  When user posts:                                                      |*
*|  1. Store post in posts table                                        |*
*|  2. Get list of followers                                            |*
*|  3. Push post to each follower's feed cache                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  User B creates post                                           |  |*
*|  |  User B has 1000 followers: [A, C, D, ...]                    |  |*
*|  |                                                                 |  |*
*|  |  Post Created:                                                 |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  +-------------+                                               |  |*
*|  |  | Store Post  |                                               |  |*
*|  |  | in Posts DB |                                               |  |*
*|  |  +-------------+                                               |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |              FANOUT SERVICE                             |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  For each follower:                                    |  |  |*
*|  |  |    Add post_id to their feed cache                     |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  feed:user_A > [post_123, post_456, ...]              |  |  |*
*|  |  |  feed:user_C > [post_123, post_789, ...]              |  |  |*
*|  |  |  feed:user_D > [post_123, post_101, ...]              |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  |  When User A requests feed:                                   |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  Simply read from feed:user_A (already prepared!)            |  |*
*|  |  O(1) lookup from Redis!                                      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  PROS:                                                                 |*
*|  Y Feed reads are instant (pre-computed)                             |*
*|  Y Simple feed query                                                  |*
*|                                                                         |*
*|  CONS:                                                                 |*
*|  X Write amplification (1 post > 1000 writes)                        |*
*|  X Celebrities with 50M followers = DISASTER                        |*
*|  X Wasted work for inactive users                                    |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  THE CELEBRITY PROBLEM                                                |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Taylor Swift posts a tweet                                    |  |*
*|  |  She has 90 million followers                                  |  |*
*|  |                                                                 |  |*
*|  |  With pure push:                                               |  |*
*|  |  * 90 million cache writes!                                   |  |*
*|  |  * Takes minutes to fanout                                    |  |*
*|  |  * Massive spike in Redis traffic                             |  |*
*|  |  * Some users see post instantly, others wait minutes         |  |*
*|  |                                                                 |  |*
*|  |  This is called the "Hot Key" or "Thundering Herd" problem    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  APPROACH 3: HYBRID MODEL ⭐⭐ BEST (Twitter's Approach)             |*
*|  ------------------------------------------------------               |*
*|                                                                         |*
*|  Combine push and pull based on who is posting:                       |*
*|                                                                         |*
*|  NORMAL USERS (< 10K followers): Use PUSH                            |*
*|  * Fanout to all followers' caches                                   |*
*|  * Fast and simple                                                    |*
*|                                                                         |*
*|  CELEBRITIES (> 10K followers): Use PULL                             |*
*|  * Don't fanout their posts                                          |*
*|  * Merge at read time                                                |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  User A's Feed Request:                                        |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  Step 1: Get pre-computed feed from cache                ||  |*
*|  |  |          (posts from normal users A follows)             ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Step 2: Get list of celebrities A follows               ||  |*
*|  |  |          [Taylor Swift, Elon Musk, ...]                  ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Step 3: Fetch recent posts from each celebrity          ||  |*
*|  |  |          (Pull model for celebrities only)               ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Step 4: Merge both lists, sort by time                  ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Step 5: Return combined feed                            ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  Result:                                                       |  |*
*|  |  * Normal user posts: instant (pre-cached)                    |  |*
*|  |  * Celebrity posts: quick pull (user follows ~10 celebrities)|  |*
*|  |  * Best of both worlds!                                       |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 7: FEED CACHE DESIGN
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  FEED CACHE STRUCTURE (Redis)                                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Key: feed:{user_id}                                          |  |*
*|  |  Value: Sorted Set of post_ids (sorted by timestamp)          |  |*
*|  |                                                                 |  |*
*|  |  Example:                                                      |  |*
*|  |  feed:user_123 = {                                            |  |*
*|  |    post_999: 1705312800,   (Jan 15, 3:00 PM)                  |  |*
*|  |    post_998: 1705312200,   (Jan 15, 2:50 PM)                  |  |*
*|  |    post_997: 1705311600,   (Jan 15, 2:40 PM)                  |  |*
*|  |    ...                                                         |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  Operations:                                                   |  |*
*|  |  * ZADD feed:user_123 {timestamp} {post_id}  (add post)      |  |*
*|  |  * ZREVRANGE feed:user_123 0 19             (get top 20)     |  |*
*|  |  * ZREMRANGEBYRANK feed:user_123 0 -801    (trim to 800)    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  CACHE SIZING:                                                         |*
*|                                                                         |*
*|  * Store only 800 post IDs per user feed (not full posts)           |*
*|  * Post ID: 8 bytes                                                   |*
*|  * Score (timestamp): 8 bytes                                        |*
*|  * Per entry: ~20 bytes (with Redis overhead)                       |*
*|  * Per user: 800 × 20 = 16 KB                                       |*
*|  * 500M users: 500M × 16 KB = 8 TB                                  |*
*|                                                                         |*
*|  Note: Only cache active users (logged in last 7 days)              |*
*|  100M active users × 16 KB = 1.6 TB (manageable!)                  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  POST CONTENT CACHE                                                   |*
*|                                                                         |*
*|  Feed cache stores only post IDs                                      |*
*|  Actual post content cached separately:                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Key: post:{post_id}                                          |  |*
*|  |  Value: JSON blob of post data                                |  |*
*|  |                                                                 |  |*
*|  |  post:999 = {                                                  |  |*
*|  |    "post_id": 999,                                            |  |*
*|  |    "user_id": 456,                                            |  |*
*|  |    "username": "john_doe",                                    |  |*
*|  |    "display_name": "John Doe",                                |  |*
*|  |    "avatar_url": "https://cdn.../avatar.jpg",                |  |*
*|  |    "content": "Hello world!",                                 |  |*
*|  |    "created_at": "2024-01-15T15:00:00Z",                     |  |*
*|  |    "like_count": 42,                                          |  |*
*|  |    "reply_count": 5,                                          |  |*
*|  |    "has_media": true,                                         |  |*
*|  |    "media": [{"url": "...", "type": "image"}]                |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  FEED REQUEST FLOW:                                                   |*
*|                                                                         |*
*|  1. Get post IDs from feed cache: ZREVRANGE feed:user_123 0 19      |*
*|  2. Multi-get post content: MGET post:999 post:998 post:997 ...     |*
*|  3. Return hydrated posts                                            |*
*|                                                                         |*
*|  If post not in cache > fetch from DB, cache it (read-through)      |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 8: POST CREATION FLOW
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  DETAILED POST CREATION FLOW                                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  User creates post: "Hello #world @friend"                    |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  STEP 1: API RECEIVES REQUEST                                 |  |*
*|  |  -----------------------------                                 |  |*
*|  |  POST /api/posts                                              |  |*
*|  |  {                                                             |  |*
*|  |    "content": "Hello #world @friend",                        |  |*
*|  |    "media_ids": ["m123"]                                      |  |*
*|  |  }                                                             |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  STEP 2: VALIDATION                                           |  |*
*|  |  ------------------                                            |  |*
*|  |  * Authenticate user                                          |  |*
*|  |  * Validate content length (≤280 chars)                      |  |*
*|  |  * Check rate limits                                          |  |*
*|  |  * Scan for spam/abuse                                        |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  STEP 3: GENERATE POST ID (Snowflake)                        |  |*
*|  |  -------------------------------------                         |  |*
*|  |  post_id = snowflake_generator.next()                        |  |*
*|  |  // 1234567890123456789                                       |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  STEP 4: STORE POST IN DATABASE                               |  |*
*|  |  -------------------------------                               |  |*
*|  |  INSERT INTO posts (post_id, user_id, content, ...)          |  |*
*|  |  VALUES (1234567890123456789, 42, 'Hello #world @friend', ...)|  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  STEP 5: PUBLISH TO MESSAGE QUEUE                             |  |*
*|  |  ---------------------------------                             |  |*
*|  |  kafka.publish('post-created', {                              |  |*
*|  |    post_id: 1234567890123456789,                              |  |*
*|  |    user_id: 42,                                                |  |*
*|  |    is_celebrity: false,                                       |  |*
*|  |    follower_count: 500,                                       |  |*
*|  |    mentions: ["friend"],                                      |  |*
*|  |    hashtags: ["world"]                                        |  |*
*|  |  })                                                            |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  STEP 6: RETURN RESPONSE (Don't wait for fanout!)            |  |*
*|  |  -------------------------------------------------             |  |*
*|  |  HTTP 201 Created                                              |  |*
*|  |  {                                                             |  |*
*|  |    "post_id": "1234567890123456789",                         |  |*
*|  |    "created_at": "2024-01-15T15:00:00Z"                      |  |*
*|  |  }                                                             |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  ASYNC PROCESSING (After response)                                    |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  FANOUT SERVICE (Consumes from Kafka)                         |  |*
*|  |  ------------------------------------                          |  |*
*|  |                                                                 |  |*
*|  |  1. Check if user is celebrity                                |  |*
*|  |     If yes > skip fanout (use pull model)                    |  |*
*|  |                                                                 |  |*
*|  |  2. Get follower list                                         |  |*
*|  |     SELECT follower_id FROM follows WHERE followee_id = 42   |  |*
*|  |                                                                 |  |*
*|  |  3. For each follower:                                        |  |*
*|  |     ZADD feed:{follower_id} {timestamp} {post_id}            |  |*
*|  |                                                                 |  |*
*|  |  4. Trim feed if > 800 posts:                                 |  |*
*|  |     ZREMRANGEBYRANK feed:{follower_id} 0 -801                |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  NOTIFICATION SERVICE (Consumes from Kafka)                   |  |*
*|  |  ------------------------------------------                    |  |*
*|  |                                                                 |  |*
*|  |  For @friend mention:                                         |  |*
*|  |  1. Lookup user "friend"                                      |  |*
*|  |  2. Create notification record                                |  |*
*|  |  3. Push notification to user (WebSocket/FCM/APNs)           |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  SEARCH INDEXER (Consumes from Kafka)                        |  |*
*|  |  ---------------------------------------                       |  |*
*|  |                                                                 |  |*
*|  |  1. Index post content in Elasticsearch                       |  |*
*|  |  2. Index hashtags                                            |  |*
*|  |  3. Update trending topics                                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 9: FOLLOW/UNFOLLOW
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  FOLLOW USER FLOW                                                      |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  User A follows User B                                         |  |*
*|  |                                                                 |  |*
*|  |  1. INSERT INTO follows (follower_id, followee_id)            |  |*
*|  |     VALUES (A, B)                                              |  |*
*|  |                                                                 |  |*
*|  |  2. INCREMENT users.follower_count WHERE user_id = B          |  |*
*|  |                                                                 |  |*
*|  |  3. INCREMENT users.following_count WHERE user_id = A         |  |*
*|  |                                                                 |  |*
*|  |  4. Async: Backfill A's feed with B's recent posts           |  |*
*|  |     (Get last 20 posts from B, add to A's feed cache)        |  |*
*|  |                                                                 |  |*
*|  |  5. Async: Send notification to B ("A followed you")         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  UNFOLLOW USER FLOW                                                    |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  User A unfollows User B                                       |  |*
*|  |                                                                 |  |*
*|  |  1. DELETE FROM follows                                        |  |*
*|  |     WHERE follower_id = A AND followee_id = B                 |  |*
*|  |                                                                 |  |*
*|  |  2. DECREMENT users.follower_count WHERE user_id = B          |  |*
*|  |                                                                 |  |*
*|  |  3. DECREMENT users.following_count WHERE user_id = A         |  |*
*|  |                                                                 |  |*
*|  |  4. Optionally: Remove B's posts from A's feed cache         |  |*
*|  |     (Usually lazy - let them expire naturally)               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  STORING FOLLOW GRAPH                                                  |*
*|                                                                         |*
*|  For small scale: Relational DB (follows table)                       |*
*|                                                                         |*
*|  For large scale: Graph database                                       |*
*|  * Neo4j, Amazon Neptune, TigerGraph                                  |*
*|  * Optimized for traversing relationships                             |*
*|  * "Get followers of followers" type queries                          |*
*|                                                                         |*
*|  Alternative: Redis for hot data                                       |*
*|  * followers:{user_id} > Set of follower IDs                         |*
*|  * following:{user_id} > Set of followee IDs                         |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 10: NOTIFICATIONS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  NOTIFICATION TYPES                                                    |*
*|                                                                         |*
*|  * New follower                                                        |*
*|  * Post liked                                                          |*
*|  * Post commented on                                                   |*
*|  * Post reposted/shared                                               |*
*|  * Mentioned in post (@username)                                      |*
*|  * Reply to your post                                                  |*
*|  * Direct message                                                      |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  NOTIFICATION ARCHITECTURE                                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |                Event Sources                                   |  |*
*|  |  +--------+ +--------+ +--------+ +--------+                 |  |*
*|  |  |  Like  | |Comment | | Follow | |Mention |                 |  |*
*|  |  | Service| |Service | |Service | | Parser |                 |  |*
*|  |  +---+----+ +---+----+ +---+----+ +---+----+                 |  |*
*|  |      |          |          |          |                       |  |*
*|  |      +----------+----+-----+----------+                       |  |*
*|  |                      |                                         |  |*
*|  |                      v                                         |  |*
*|  |           +----------------------+                            |  |*
*|  |           |    MESSAGE QUEUE     |                            |  |*
*|  |           |      (Kafka)         |                            |  |*
*|  |           +----------+-----------+                            |  |*
*|  |                      |                                         |  |*
*|  |                      v                                         |  |*
*|  |           +----------------------+                            |  |*
*|  |           | NOTIFICATION SERVICE |                            |  |*
*|  |           |                      |                            |  |*
*|  |           |  * Dedup events      |                            |  |*
*|  |           |  * Check preferences |                            |  |*
*|  |           |  * Rate limit        |                            |  |*
*|  |           |  * Aggregate (batch) |                            |  |*
*|  |           +----------+-----------+                            |  |*
*|  |                      |                                         |  |*
*|  |      +---------------+---------------+                        |  |*
*|  |      |               |               |                        |  |*
*|  |      v               v               v                        |  |*
*|  |  +--------+     +--------+     +--------+                    |  |*
*|  |  |  Push  |     |In-App  |     | Email  |                    |  |*
*|  |  | (FCM/  |     |(WebSoc |     | Digest |                    |  |*
*|  |  | APNs)  |     |  ket)  |     |        |                    |  |*
*|  |  +--------+     +--------+     +--------+                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  NOTIFICATION AGGREGATION                                             |*
*|                                                                         |*
*|  Instead of: "A liked your post"                                      |*
*|              "B liked your post"                                      |*
*|              "C liked your post"                                      |*
*|                                                                         |*
*|  Send:       "A, B, C and 47 others liked your post"                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  AGGREGATION STRATEGY:                                         |  |*
*|  |                                                                 |  |*
*|  |  1. Collect events in time window (e.g., 5 minutes)           |  |*
*|  |  2. Group by (target_user, notification_type, target_object)  |  |*
*|  |  3. Merge into single notification                            |  |*
*|  |  4. Send batched notification                                 |  |*
*|  |                                                                 |  |*
*|  |  Example grouping:                                             |  |*
*|  |  Key: (user_123, "like", post_456)                           |  |*
*|  |  Value: [user_A, user_B, user_C, ...]                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 11: MEDIA HANDLING
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  MEDIA UPLOAD FLOW                                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. CLIENT UPLOADS MEDIA                                       |  |*
*|  |     POST /api/media/upload                                    |  |*
*|  |     Body: multipart/form-data (image file)                    |  |*
*|  |                                                                 |  |*
*|  |  2. MEDIA SERVICE PROCESSES                                    |  |*
*|  |     * Validate file (type, size, no malware)                  |  |*
*|  |     * Generate unique ID                                       |  |*
*|  |     * Upload to temporary storage                             |  |*
*|  |                                                                 |  |*
*|  |  3. ASYNC PROCESSING (Queue)                                  |  |*
*|  |     * Resize to multiple dimensions (thumbnail, medium, full) |  |*
*|  |     * Compress for web                                        |  |*
*|  |     * Extract metadata (EXIF)                                 |  |*
*|  |     * Strip sensitive metadata                                |  |*
*|  |     * Upload to CDN (S3 + CloudFront)                        |  |*
*|  |                                                                 |  |*
*|  |  4. RETURN MEDIA ID                                           |  |*
*|  |     {                                                          |  |*
*|  |       "media_id": "m123",                                     |  |*
*|  |       "status": "processing"                                  |  |*
*|  |     }                                                          |  |*
*|  |                                                                 |  |*
*|  |  5. CLIENT CREATES POST WITH media_ids                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  IMAGE VARIANTS                                                        |*
*|                                                                         |*
*|  Store multiple sizes for different use cases:                        |*
*|                                                                         |*
*|  +----------------+-----------------+-----------------------------+  |*
*|  | Variant        | Dimensions      | Use Case                    |  |*
*|  +----------------+-----------------+-----------------------------+  |*
*|  | thumbnail      | 150x150         | Timeline preview            |  |*
*|  | small          | 340x340         | Mobile feed                 |  |*
*|  | medium         | 680x680         | Desktop feed                |  |*
*|  | large          | 1024x1024       | Expanded view               |  |*
*|  | original       | As uploaded     | Download                    |  |*
*|  +----------------+-----------------+-----------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  VIDEO HANDLING                                                        |*
*|                                                                         |*
*|  1. Upload original video                                             |*
*|  2. Transcode to multiple resolutions (480p, 720p, 1080p)           |*
*|  3. Generate HLS/DASH segments for adaptive streaming               |*
*|  4. Extract thumbnail frames                                         |*
*|  5. Generate preview GIF                                              |*
*|  6. Serve via CDN with adaptive bitrate                              |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 12: SEARCH AND TRENDING
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SEARCH ARCHITECTURE                                                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |                     POST CREATED                               |  |*
*|  |                          |                                      |  |*
*|  |                          v                                      |  |*
*|  |                    +-----------+                               |  |*
*|  |                    |   Kafka   |                               |  |*
*|  |                    +-----+-----+                               |  |*
*|  |                          |                                      |  |*
*|  |                          v                                      |  |*
*|  |               +----------------------+                        |  |*
*|  |               |   SEARCH INDEXER     |                        |  |*
*|  |               |                      |                        |  |*
*|  |               |  Parse post content  |                        |  |*
*|  |               |  Extract entities    |                        |  |*
*|  |               |  Build search doc    |                        |  |*
*|  |               +----------+-----------+                        |  |*
*|  |                          |                                      |  |*
*|  |                          v                                      |  |*
*|  |               +----------------------+                        |  |*
*|  |               |    ELASTICSEARCH     |                        |  |*
*|  |               |                      |                        |  |*
*|  |               |  posts index:        |                        |  |*
*|  |               |  * content (text)    |                        |  |*
*|  |               |  * hashtags          |                        |  |*
*|  |               |  * mentions          |                        |  |*
*|  |               |  * author            |                        |  |*
*|  |               |  * timestamp         |                        |  |*
*|  |               |                      |                        |  |*
*|  |               |  users index:        |                        |  |*
*|  |               |  * username          |                        |  |*
*|  |               |  * display_name      |                        |  |*
*|  |               |  * bio               |                        |  |*
*|  |               +----------------------+                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  TRENDING TOPICS                                                       |*
*|                                                                         |*
*|  What's trending = Topics with sudden increase in volume              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  ALGORITHM:                                                    |  |*
*|  |                                                                 |  |*
*|  |  1. Count hashtag usage in sliding windows                    |  |*
*|  |     * Last 1 hour, 4 hours, 24 hours                         |  |*
*|  |                                                                 |  |*
*|  |  2. Calculate velocity (rate of change)                       |  |*
*|  |     velocity = current_count / avg_historical_count          |  |*
*|  |                                                                 |  |*
*|  |  3. Score = volume × velocity                                 |  |*
*|  |     High volume + high velocity = trending                   |  |*
*|  |                                                                 |  |*
*|  |  4. Filter spam/abuse                                         |  |*
*|  |     * Remove bot-driven hashtags                              |  |*
*|  |     * Block prohibited content                                |  |*
*|  |                                                                 |  |*
*|  |  5. Personalize by location/interests                        |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  IMPLEMENTATION:                                               |  |*
*|  |                                                                 |  |*
*|  |  Redis Sorted Sets for real-time counting:                    |  |*
*|  |                                                                 |  |*
*|  |  trending:hashtags:hourly > {#topic1: 5000, #topic2: 4500}   |  |*
*|  |                                                                 |  |*
*|  |  ZINCRBY trending:hashtags:hourly 1 "#worldcup"              |  |*
*|  |  ZREVRANGE trending:hashtags:hourly 0 9 (top 10)             |  |*
*|  |                                                                 |  |*
*|  |  Expire old windows, aggregate in background job              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 13: SCALING STRATEGIES
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  DATABASE SHARDING                                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  USERS TABLE: Shard by user_id                                |  |*
*|  |  * User 1-1M > Shard 1                                        |  |*
*|  |  * User 1M-2M > Shard 2                                       |  |*
*|  |  * etc.                                                        |  |*
*|  |                                                                 |  |*
*|  |  POSTS TABLE: Shard by user_id (author)                       |  |*
*|  |  * User's posts stored on same shard as user                 |  |*
*|  |  * Enables efficient user timeline queries                    |  |*
*|  |                                                                 |  |*
*|  |  FOLLOWS TABLE: Shard by follower_id                          |  |*
*|  |  * "Who do I follow?" is fast (single shard)                 |  |*
*|  |  * "Who follows me?" requires scatter-gather                 |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  CACHE LAYERS                                                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  L1: Client Cache (browser/app)                               |  |*
*|  |  +-- Recently viewed content                                  |  |*
*|  |                                                                 |  |*
*|  |  L2: CDN (CloudFront/Cloudflare)                              |  |*
*|  |  +-- Static assets, media, public profiles                   |  |*
*|  |                                                                 |  |*
*|  |  L3: Application Cache (Redis)                                |  |*
*|  |  +-- Feed cache, post cache, session cache                   |  |*
*|  |                                                                 |  |*
*|  |  L4: Database Query Cache                                     |  |*
*|  |  +-- Frequent queries                                         |  |*
*|  |                                                                 |  |*
*|  |  L5: Database                                                  |  |*
*|  |  +-- Source of truth                                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  READ REPLICAS                                                         |*
*|                                                                         |*
*|  * Write to master, read from replicas                               |*
*|  * Separate read traffic from write traffic                          |*
*|  * Eventual consistency acceptable for feed reads                    |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  GEOGRAPHIC DISTRIBUTION                                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  +--------------+    +--------------+    +--------------+     |  |*
*|  |  |  US-WEST     |    |   EU-WEST    |    |  ASIA-PAC    |     |  |*
*|  |  |              |    |              |    |              |     |  |*
*|  |  | +----------+ |    | +----------+ |    | +----------+ |     |  |*
*|  |  | |   CDN    | |    | |   CDN    | |    | |   CDN    | |     |  |*
*|  |  | |  Edge    | |    | |  Edge    | |    | |  Edge    | |     |  |*
*|  |  | +----------+ |    | +----------+ |    | +----------+ |     |  |*
*|  |  | +----------+ |    | +----------+ |    | +----------+ |     |  |*
*|  |  | |   API    | |    | |   API    | |    | |   API    | |     |  |*
*|  |  | | Servers  | |    | | Servers  | |    | | Servers  | |     |  |*
*|  |  | +----------+ |    | +----------+ |    | +----------+ |     |  |*
*|  |  | +----------+ |    | +----------+ |    | +----------+ |     |  |*
*|  |  | |  Redis   | |    | |  Redis   | |    | |  Redis   | |     |  |*
*|  |  | |  Cache   | |    | |  Cache   | |    | |  Cache   | |     |  |*
*|  |  | +----------+ |    | +----------+ |    | +----------+ |     |  |*
*|  |  | +----------+ |    | +----------+ |    | +----------+ |     |  |*
*|  |  | | DB Read  | |    | | DB Read  | |    | | DB Read  | |     |  |*
*|  |  | | Replica  | |    | | Replica  | |    | | Replica  | |     |  |*
*|  |  | +----------+ |    | +----------+ |    | +----------+ |     |  |*
*|  |  +--------------+    +--------------+    +--------------+     |  |*
*|  |         |                   |                   |              |  |*
*|  |         +-------------------+-------------------+              |  |*
*|  |                             |                                   |  |*
*|  |                             v                                   |  |*
*|  |               +----------------------------+                   |  |*
*|  |               |     PRIMARY DATABASE       |                   |  |*
*|  |               |       (US-EAST)            |                   |  |*
*|  |               +----------------------------+                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 14: INTERVIEW QUICK REFERENCE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  KEY TALKING POINTS                                                    |*
*|                                                                         |*
*|  1. NEWS FEED (Most important!)                                       |*
*|     * Push model for normal users                                     |*
*|     * Pull model for celebrities                                      |*
*|     * Hybrid approach is best                                         |*
*|                                                                         |*
*|  2. FANOUT                                                             |*
*|     * Async via message queue (Kafka)                                 |*
*|     * Don't block post creation                                       |*
*|     * Celebrity problem: skip fanout, use pull                       |*
*|                                                                         |*
*|  3. CACHING                                                            |*
*|     * Feed cache: Redis sorted sets (post IDs by time)               |*
*|     * Post cache: Redis (full post data)                             |*
*|     * Only cache active users                                        |*
*|                                                                         |*
*|  4. DATA MODEL                                                         |*
*|     * Snowflake IDs (sortable, distributed)                          |*
*|     * Denormalized counts (like_count, follower_count)              |*
*|     * Separate media storage                                          |*
*|                                                                         |*
*|  5. SCALE                                                              |*
*|     * Shard databases by user_id                                     |*
*|     * Read replicas for heavy read load                              |*
*|     * CDN for media                                                   |*
*|     * Multiple regions                                                |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  COMMON INTERVIEW QUESTIONS                                           |*
*|                                                                         |*
*|  Q: How do you generate the news feed?                               |*
*|  A: Hybrid push/pull. Push for normal users, pull for celebrities.  |*
*|     Feed cache in Redis with sorted sets of post IDs.               |*
*|                                                                         |*
*|  Q: How do you handle celebrities with millions of followers?        |*
*|  A: Don't fanout their posts. Use pull model - fetch their posts   |*
*|     at read time and merge with pre-computed feed.                  |*
*|                                                                         |*
*|  Q: How do you make posting fast?                                    |*
*|  A: Write to DB, publish to Kafka, return immediately.              |*
*|     Fanout happens async. User doesn't wait.                        |*
*|                                                                         |*
*|  Q: How do you handle a post going viral?                           |*
*|  A: Cache the post content aggressively. For feed generation,       |*
*|     the post ID is already fanned out - just need to fetch content.|*
*|                                                                         |*
*|  Q: How do you scale the database?                                   |*
*|  A: Shard by user_id. User's data co-located on same shard.        |*
*|     Read replicas for timeline queries.                              |*
*|                                                                         |*
*|  Q: How do you handle real-time updates?                             |*
*|  A: WebSocket connection for active users.                          |*
*|     Push new posts to connected clients.                             |*
*|     Long-polling fallback.                                           |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  ARCHITECTURE SUMMARY                                                  |*
*|                                                                         |*
*|  Write Path:                                                          |*
*|  Client > API > Posts DB > Kafka > Fanout > Feed Cache              |*
*|                                                                         |*
*|  Read Path:                                                            |*
*|  Client > API > Feed Cache (+ Celebrity Pull) > Post Cache > DB     |*
*|                                                                         |*
*|  Key Numbers:                                                          |*
*|  * 500M DAU, 5B feed requests/day                                    |*
*|  * 500M posts/day, 6K posts/second                                  |*
*|  * Feed cache: 800 post IDs per user                                |*
*|  * Read:Write ratio = 10:1                                           |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

ADVANCED TOPICS & REAL-WORLD PROBLEMS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  VIRAL CONTENT HANDLING (Thundering Herd)                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Problem: Post goes viral > millions of requests for same post |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  Celebrity tweets > 50M impressions in 1 hour            ||  |*
*|  |  |  All hit cache for same post > Hot key problem           ||  |*
*|  |  |  Cache invalidation > Thundering herd to DB              ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  Solutions:                                                    |  |*
*|  |                                                                 |  |*
*|  |  1. HOT KEY DETECTION + REPLICATION                           |  |*
*|  |     * Monitor cache hit rate per key                         |  |*
*|  |     * If > threshold, replicate to multiple cache shards    |  |*
*|  |     * post:123 > post:123:replica_1, :replica_2, ...        |  |*
*|  |     * Random read from any replica                          |  |*
*|  |                                                                 |  |*
*|  |  2. LOCAL CACHING (L1 Cache)                                  |  |*
*|  |     * In-memory cache on each API server                    |  |*
*|  |     * Very short TTL (10 seconds)                           |  |*
*|  |     * Reduces Redis hits significantly                      |  |*
*|  |                                                                 |  |*
*|  |  3. CDN FOR STATIC POST DATA                                  |  |*
*|  |     * Serialize post to JSON, cache at edge                 |  |*
*|  |     * Works for public posts                                 |  |*
*|  |     * Engagement counts updated via client-side fetch       |  |*
*|  |                                                                 |  |*
*|  |  4. REQUEST COALESCING                                        |  |*
*|  |     * If 1000 requests for same post arrive simultaneously  |  |*
*|  |     * Only 1 actually fetches from DB                       |  |*
*|  |     * Others wait and get same result                       |  |*
*|  |     * Singleflight pattern                                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  BOT & SPAM DETECTION                                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Bot Indicators:                                               |  |*
*|  |  * Account age < 7 days + high posting volume                |  |*
*|  |  * Same content posted to multiple accounts                  |  |*
*|  |  * Posting at inhuman speeds (< 2 sec between posts)        |  |*
*|  |  * Following/unfollowing in patterns                        |  |*
*|  |  * No profile picture, generic bio                          |  |*
*|  |  * All posts contain links                                   |  |*
*|  |                                                                 |  |*
*|  |  Detection System:                                             |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  User Action                                              ||  |*
*|  |  |      |                                                    ||  |*
*|  |  |      v                                                    ||  |*
*|  |  |  Feature Extraction                                      ||  |*
*|  |  |  * Account age, post frequency, content similarity      ||  |*
*|  |  |  * Network analysis (who they follow/followed by)       ||  |*
*|  |  |  * Device fingerprint, IP reputation                    ||  |*
*|  |  |      |                                                    ||  |*
*|  |  |      v                                                    ||  |*
*|  |  |  ML Model (Real-time scoring)                           ||  |*
*|  |  |      |                                                    ||  |*
*|  |  |      +--> Score < 0.3: Allow                            ||  |*
*|  |  |      +--> Score 0.3-0.7: CAPTCHA / Verify              ||  |*
*|  |  |      +--> Score > 0.7: Block + Review                  ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  Actions:                                                      |  |*
*|  |  * Soft block: Content hidden from others, user doesn't know |  |*
*|  |  * Hard block: Account suspended                             |  |*
*|  |  * Rate limit: Reduce allowed actions                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  CONTENT MODERATION AT SCALE                                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  500M posts/day > Can't manually review all                   |  |*
*|  |                                                                 |  |*
*|  |  Multi-Layer Approach:                                         |  |*
*|  |                                                                 |  |*
*|  |  LAYER 1: AUTOMATED (Catches 95%)                             |  |*
*|  |  * ML classifiers for hate speech, violence, nudity          |  |*
*|  |  * Keyword/phrase blocklists                                 |  |*
*|  |  * Image recognition (nudity, violence, copyrighted)        |  |*
*|  |  * Hash matching (known bad content database)               |  |*
*|  |                                                                 |  |*
*|  |  LAYER 2: USER REPORTS                                        |  |*
*|  |  * Report button on all content                              |  |*
*|  |  * Prioritize by: report volume, reporter trust score       |  |*
*|  |  * Auto-hide if reports > threshold before human review     |  |*
*|  |                                                                 |  |*
*|  |  LAYER 3: HUMAN REVIEW                                        |  |*
*|  |  * Edge cases, appeals, high-stakes decisions               |  |*
*|  |  * Trust & Safety team                                       |  |*
*|  |  * Queue prioritization by severity                         |  |*
*|  |                                                                 |  |*
*|  |  Shadow Banning:                                              |  |*
*|  |  * User can post, but content not shown to others           |  |*
*|  |  * User doesn't know they're restricted                     |  |*
*|  |  * Reduces ban evasion attempts                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  FEED RANKING ALGORITHM (Beyond Chronological)                        |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Problem: Chronological feed means you miss good content      |  |*
*|  |           if you don't check frequently                        |  |*
*|  |                                                                 |  |*
*|  |  RANKING SIGNALS:                                              |  |*
*|  |                                                                 |  |*
*|  |  Engagement:                                                   |  |*
*|  |  * Likes, comments, reposts, time spent viewing              |  |*
*|  |  * Click-through rate on links                               |  |*
*|  |  * Video watch time / completion rate                        |  |*
*|  |                                                                 |  |*
*|  |  Relationship:                                                 |  |*
*|  |  * How often you interact with this author                   |  |*
*|  |  * Mutual followers                                          |  |*
*|  |  * Direct messages history                                   |  |*
*|  |                                                                 |  |*
*|  |  Content:                                                      |  |*
*|  |  * Topics you engage with (ML clustering)                   |  |*
*|  |  * Media type preference (video vs text)                    |  |*
*|  |  * Language match                                            |  |*
*|  |                                                                 |  |*
*|  |  Freshness:                                                    |  |*
*|  |  * Time decay (older = lower score)                         |  |*
*|  |  * Breaking news boost                                       |  |*
*|  |                                                                 |  |*
*|  |  Quality:                                                      |  |*
*|  |  * Author reputation/verification                           |  |*
*|  |  * Content quality score (not clickbait)                    |  |*
*|  |                                                                 |  |*
*|  |  FORMULA (Simplified):                                        |  |*
*|  |  score = engagement_score                                    |  |*
*|  |        × relationship_weight                                 |  |*
*|  |        × content_relevance                                   |  |*
*|  |        × time_decay(age)                                     |  |*
*|  |        × quality_multiplier                                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  TRENDING TOPIC MANIPULATION PREVENTION                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Attack: Coordinated bot networks artificially trend topics   |  |*
*|  |                                                                 |  |*
*|  |  Detection:                                                    |  |*
*|  |  * Velocity anomaly: Too fast rise for organic content       |  |*
*|  |  * Account clustering: Same IP, similar creation time       |  |*
*|  |  * Content similarity: Copy-paste posts                      |  |*
*|  |  * Geographic anomaly: Topic trends only in bot-farm regions|  |*
*|  |                                                                 |  |*
*|  |  Prevention:                                                   |  |*
*|  |  * Weight by account age/trust                               |  |*
*|  |  * Require diverse set of authors for trending              |  |*
*|  |  * Geographic distribution requirement                       |  |*
*|  |  * Manual review for sensitive topics                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DIRECT MESSAGING ARCHITECTURE                                        |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Different from public posts:                                 |  |*
*|  |  * Real-time delivery requirement                            |  |*
*|  |  * End-to-end encryption option                              |  |*
*|  |  * Read receipts, typing indicators                          |  |*
*|  |  * Group conversations                                        |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  User A                           User B                  ||  |*
*|  |  |    |                                ^                     ||  |*
*|  |  |    | Send message                   | Receive             ||  |*
*|  |  |    v                                |                     ||  |*
*|  |  |  +---------+                   +---------+               ||  |*
*|  |  |  |  Chat   |                   |  Chat   |               ||  |*
*|  |  |  | Gateway |                   | Gateway |               ||  |*
*|  |  |  +----+----+                   +----+----+               ||  |*
*|  |  |       |                             ^                     ||  |*
*|  |  |       v                             |                     ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |  |              MESSAGE QUEUE (Kafka)                  | ||  |*
*|  |  |  |         Partitioned by conversation_id              | ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |       |                             ^                     ||  |*
*|  |  |       v                             |                     ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |  |              CHAT DATABASE                          | ||  |*
*|  |  |  |   Cassandra (write-optimized for message history)   | ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  End-to-End Encryption:                                       |  |*
*|  |  * Key exchange during conversation start                    |  |*
*|  |  * Server stores encrypted blobs, can't read                 |  |*
*|  |  * Client-side decryption                                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  STORIES / EPHEMERAL CONTENT                                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Stories = Posts that disappear after 24 hours                |  |*
*|  |                                                                 |  |*
*|  |  Design Considerations:                                        |  |*
*|  |                                                                 |  |*
*|  |  1. STORAGE                                                    |  |*
*|  |     * Store in separate table with TTL                        |  |*
*|  |     * Or use TTL in Cassandra/Redis                          |  |*
*|  |     * Auto-deleted after 24 hours                            |  |*
*|  |                                                                 |  |*
*|  |  2. FEED GENERATION (Different from main feed)                |  |*
*|  |     * Pull model only (stories from people you follow)       |  |*
*|  |     * No fanout needed (ephemeral, less critical)           |  |*
*|  |     * Query: Get stories from followed users, last 24 hours |  |*
*|  |                                                                 |  |*
*|  |  3. VIEW TRACKING                                             |  |*
*|  |     * Track who viewed your story                            |  |*
*|  |     * Viewer list also ephemeral (deleted with story)       |  |*
*|  |                                                                 |  |*
*|  |  4. ARCHIVE OPTION                                            |  |*
*|  |     * "Highlight" to save permanently                        |  |*
*|  |     * Move from ephemeral to permanent storage               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  ADS & MONETIZATION                                                    |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Ads appear in feed alongside organic posts                   |  |*
*|  |                                                                 |  |*
*|  |  AD SERVING:                                                   |  |*
*|  |  1. User requests feed                                        |  |*
*|  |  2. Feed service calls Ad Service in parallel                |  |*
*|  |  3. Ad Service runs auction:                                 |  |*
*|  |     * Find eligible ads (targeting matches user)            |  |*
*|  |     * Rank by: bid × predicted_engagement                   |  |*
*|  |     * Apply frequency caps (don't show same ad too often)   |  |*
*|  |  4. Insert winning ads at positions 3, 7, 12, etc.          |  |*
*|  |                                                                 |  |*
*|  |  TARGETING SIGNALS:                                            |  |*
*|  |  * Demographics (age, gender, location)                      |  |*
*|  |  * Interests (based on follows, engagement)                  |  |*
*|  |  * Behavior (recent searches, purchases)                     |  |*
*|  |  * Lookalike audiences                                       |  |*
*|  |  * Retargeting (visited advertiser's website)               |  |*
*|  |                                                                 |  |*
*|  |  PRIVACY CONSIDERATIONS:                                       |  |*
*|  |  * GDPR consent for personalized ads                        |  |*
*|  |  * Opt-out option                                            |  |*
*|  |  * Ad transparency ("Why am I seeing this?")                |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  GRAPH DATABASE FOR SOCIAL CONNECTIONS                                |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Why Graph DB for large-scale social networks:               |  |*
*|  |                                                                 |  |*
*|  |  Query: "People you may know" (friends of friends)           |  |*
*|  |                                                                 |  |*
*|  |  Relational (slow):                                           |  |*
*|  |  SELECT * FROM follows f1                                     |  |*
*|  |  JOIN follows f2 ON f1.followee_id = f2.follower_id          |  |*
*|  |  WHERE f1.follower_id = me                                    |  |*
*|  |    AND f2.followee_id NOT IN (my_follows)                    |  |*
*|  |  -- Multiple table scans, very slow at scale                 |  |*
*|  |                                                                 |  |*
*|  |  Graph DB (fast):                                             |  |*
*|  |  MATCH (me)-[:FOLLOWS]->()-[:FOLLOWS]->(suggestion)          |  |*
*|  |  WHERE NOT (me)-[:FOLLOWS]->(suggestion)                     |  |*
*|  |  RETURN suggestion                                            |  |*
*|  |  -- Traverses graph directly, O(edges) not O(nodes²)         |  |*
*|  |                                                                 |  |*
*|  |  Options:                                                      |  |*
*|  |  * Neo4j (mature, ACID)                                       |  |*
*|  |  * Amazon Neptune (managed)                                   |  |*
*|  |  * TigerGraph (analytics)                                     |  |*
*|  |  * Facebook's TAO (custom, not available)                    |  |*
*|  |                                                                 |  |*
*|  |  Hybrid approach:                                              |  |*
*|  |  * Primary data in MySQL/PostgreSQL                          |  |*
*|  |  * Graph queries in dedicated graph store                    |  |*
*|  |  * Async sync between them                                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

ARCHITECTURE DIAGRAM
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|                          +--------------+                              |*
*|                          |   CLIENTS    |                              |*
*|                          +------+-------+                              |*
*|                                 |                                      |*
*|                                 v                                      |*
*|                          +--------------+                              |*
*|                          |     CDN      | <-- Media/Static            |*
*|                          +------+-------+                              |*
*|                                 |                                      |*
*|                                 v                                      |*
*|                          +--------------+                              |*
*|                          | Load Balancer|                              |*
*|                          +------+-------+                              |*
*|                                 |                                      |*
*|            +--------------------+--------------------+                |*
*|            v                    v                    v                |*
*|      +----------+        +----------+        +----------+            |*
*|      |   API    |        |   API    |        |   API    |            |*
*|      | Servers  |        | Servers  |        | Servers  |            |*
*|      +----+-----+        +----+-----+        +----+-----+            |*
*|           |                   |                   |                  |*
*|           +-------------------+-------------------+                  |*
*|                               |                                      |*
*|      +------------------------+------------------------+            |*
*|      |                        |                        |            |*
*|      v                        v                        v            |*
*|  +--------+             +----------+            +----------+        |*
*|  |  Feed  |             |   Post   |            |   User   |        |*
*|  |Service |             | Service  |            | Service  |        |*
*|  +---+----+             +----+-----+            +----+-----+        |*
*|      |                       |                       |              |*
*|      v                       v                       v              |*
*|  +--------+             +----------+            +----------+        |*
*|  |  Feed  |             |  Posts   |            |  Users   |        |*
*|  | Cache  |             |    DB    |            |    DB    |        |*
*|  |(Redis) |             +----------+            +----------+        |*
*|  +--------+                   |                                     |*
*|                               |                                     |*
*|                               v                                     |*
*|                        +--------------+                             |*
*|                        |    KAFKA     |                             |*
*|                        +------+-------+                             |*
*|                               |                                     |*
*|            +------------------+------------------+                  |*
*|            v                  v                  v                  |*
*|     +----------+       +----------+       +----------+             |*
*|     | Fanout   |       | Notific. |       |  Search  |             |*
*|     | Service  |       | Service  |       | Indexer  |             |*
*|     +----+-----+       +----------+       +----+-----+             |*
*|          |                                     |                   |*
*|          v                                     v                   |*
*|     +----------+                         +----------+              |*
*|     |  Feed    |                         |Elasticsea|              |*
*|     |  Cache   |                         |   rch    |              |*
*|     | (Redis)  |                         +----------+              |*
*|     +----------+                                                   |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF SOCIAL MEDIA PLATFORM SYSTEM DESIGN
