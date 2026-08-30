# URL SHORTENER
*Chapter 5: Interview Q&A*

Interview-focused cheat sheet: 60-second pitch, tradeoff table,
common follow-ups, failure grid, memorable numbers.

## SECTION 5.1: 60-SECOND ELEVATOR PITCH

```
+-------------------------------------------------------------------------+
|                                                                         |
|  "We built a URL shortener that handles 10 billion redirects a day     |
|  with p99 latency under 100 ms globally, and 100 million shortens.    |
|                                                                         |
|  It's a heavily read-optimized system:                                 |
|                                                                         |
|    1. CDN edge caches redirects (~80% hit rate) for global latency.   |
|                                                                         |
|    2. Redis Cluster serves origin traffic in <5 ms, backed by a       |
|       Cassandra ring partitioned by short_code for durability +       |
|       multi-region.                                                    |
|                                                                         |
|    3. A range-based ID generator (Zookeeper coordinated) hands out    |
|       IDs 10K at a time to shorten workers, so no collisions ever.   |
|                                                                         |
|    4. Bloom filter absorbs bot enumeration attacks -- 99.9% of        |
|       404s never touch the DB.                                         |
|                                                                         |
|    5. Hot URLs (viral links) are handled with multi-key replication  |
|       and extended CDN cache to prevent hot-key problems.             |
|                                                                         |
|    6. Analytics pipeline via Kafka -> Flink -> ClickHouse for rich    |
|       queries + Redis counters for real-time click count."           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.2: THE TRADEOFF TABLE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +----------------------+---------------+-------------+---------------+ |
|  | Decision             | Chose         | Alternative | Why           | |
|  +----------------------+---------------+-------------+---------------+ |
|  | ID generation        | Range counter | Random hash | No collisions | |
|  | Short code length    | 7 chars       | 6 or 8      | 96y headroom  | |
|  | Redirect type        | 302 Found     | 301 Moved   | Analytics +   | |
|  |                      |               |             | mutability    | |
|  | Primary store        | Cassandra     | Postgres    | Multi-region  | |
|  |                      |               |             | + TTL native  | |
|  | Cache                | Redis Cluster | Memcached   | Bloom + rich  | |
|  |                      |               |             | data types    | |
|  | Non-existent code    | Bloom filter  | Neg cache   | Attack proof  | |
|  | Custom alias         | LWT on write  | App lock    | Atomic + safe | |
|  | Safety scan          | Async post-   | Sync in     | Fast shorten  | |
|  |                      | create        | shorten     | + fallback    | |
|  | Click counting       | Async batched | Sync INCR   | Latency +     | |
|  |                      |               |             | hot key       | |
|  | CDN caching          | 60s (default) | Longer      | Analytics     | |
|  |                      | 24h (hot)     |             | accuracy      | |
|  +----------------------+---------------+-------------+---------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.3: COMMON FOLLOW-UP QUESTIONS

### Q: HOW DO YOU PREVENT MALICIOUS URL REDIRECTS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Multi-layer defense:                                                   |
|                                                                         |
|  1. AT CREATION                                                         |
|     * Sync check against local blacklist (well-known bad domains)       |
|     * Async scan via Google Safe Browsing API + internal ML model       |
|     * If flagged post-scan, add to takedown list                        |
|                                                                         |
|  2. AT REDIRECT                                                         |
|     * Check takedown:{code} in Redis                                    |
|     * If takedown -> serve warning page instead of 302                  |
|                                                                         |
|  3. POST-INCIDENT                                                       |
|     * Takedown API for security team                                    |
|     * Global cache invalidation on takedown flag                        |
|     * Rescan URLs periodically (destinations can go bad)                |
|                                                                         |
|  4. RATE LIMITING                                                       |
|     * Limit shortens per user (prevent bulk-spam)                       |
|     * Alert on user with high takedown rate                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: HOW DO YOU SUPPORT CUSTOM DOMAINS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Enterprise users want mybrand.co/xyz instead of bit.ly/xyz.            |
|                                                                         |
|  Setup:                                                                 |
|    1. Customer adds CNAME record: mybrand.co -> our-cdn.provider.com    |
|    2. We issue TLS cert via ACME (Let's Encrypt)                        |
|    3. Our CDN routes mybrand.co/xyz -> our backend                      |
|    4. Backend maps (mybrand.co, xyz) -> long URL                        |
|                                                                         |
|  DB SCHEMA CHANGE                                                       |
|                                                                         |
|    Primary key: (domain, short_code)                                    |
|    Default domain: bit.ly                                               |
|                                                                         |
|  Same short_code can exist under different domains without conflict.    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: HOW DO YOU HANDLE EXPIRED URLS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Cassandra native TTL:                                                  |
|    INSERT INTO urls ... USING TTL <seconds>;                            |
|                                                                         |
|  After TTL, Cassandra tombstones the row (deleted lazily).              |
|                                                                         |
|  On redirect:                                                           |
|    * Cache stores the URL with the same TTL as DB                       |
|    * If cached: value is not stale unless expired                       |
|    * If DB miss on expected code (bloom said "yes"): return 410 Gone    |
|                                                                         |
|  BLOOM FILTER STALENESS                                                 |
|    Bloom retains the code -> 0.01% extra DB lookups for expired codes  |
|    Acceptable overhead. Periodic rebuild reclaims accuracy.            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: HOW DO YOU DO LINK PREVIEW / OPEN GRAPH?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  When Twitter, Slack, etc. crawl a short URL:                           |
|                                                                         |
|  Approach A: Return a preview page (200 OK with OG meta tags)          |
|    Requires: fetch the destination, parse OG tags, cache them           |
|    User-agent detection: if crawler UA -> preview; else -> redirect     |
|                                                                         |
|  Approach B: Return 302 -> destination handles OG                       |
|    Destination might not support OG. User sees no preview.              |
|                                                                         |
|  We do Approach A for paid tier.                                        |
|    * Async job crawls destination on shorten                            |
|    * Extracts OG tags, stores in link_metadata table                    |
|    * Redirect service detects crawler UA and serves preview            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: WHAT IF A LONG URL IS ALSO A SHORT URL (LOOP)?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  User shortens bit.ly/aaa (a valid bit.ly URL) -> gets bit.ly/bbb.      |
|  bit.ly/bbb -> bit.ly/aaa -> long URL. Two-hop redirect.                |
|                                                                         |
|  Or: bit.ly/aaa <-> bit.ly/bbb infinite loop.                           |
|                                                                         |
|  MITIGATION                                                             |
|                                                                         |
|  On shorten, if long_url matches OUR domain pattern:                    |
|    * Resolve to final destination internally                            |
|    * Store the RESOLVED long URL, not the intermediate                  |
|                                                                         |
|  This flattens hop chains and prevents loops.                           |
|                                                                         |
|  For URLs pointing to competitor shorteners (t.co, tinyurl):            |
|    * Optionally resolve (adds latency to shorten API)                   |
|    * Or leave as-is and let browser follow chain (default)              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: HOW WOULD YOU MIGRATE FROM AUTO-INCREMENT TO RANGE-BASED IDS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Suppose we start with Postgres AUTO_INCREMENT and outgrow it.          |
|                                                                         |
|  MIGRATION PLAN                                                         |
|                                                                         |
|  1. Cap the Postgres counter at ID = X (freeze new writes to Postgres)  |
|  2. Configure Zookeeper /idgen/next_start = X + safety_gap (X + 1M)     |
|  3. Deploy new range-based ID generator alongside                       |
|  4. Shorten service switches to range-based                             |
|  5. Postgres data migrated to Cassandra in the background               |
|                                                                         |
|  During migration:                                                      |
|    Reads: try Cassandra first, fall back to Postgres                    |
|    Writes: only to Cassandra                                            |
|                                                                         |
|  Backward compatibility:                                                |
|    Old codes (< X) continue to work indefinitely                        |
|    Cache warms Cassandra reads for old codes                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: HOW DO YOU MONITOR COST?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MONTHLY COST ESTIMATE (rough)                                          |
|                                                                         |
|  +------------------+-----------+---------------------------+           |
|  | Component        | Cost      | Note                      |           |
|  +------------------+-----------+---------------------------+           |
|  | CDN (Cloudflare) | ~$50K     | 10B redirects, 80% hit    |           |
|  | Cassandra ring   | ~$30K     | 20 nodes, 100 TB          |           |
|  | Redis cluster    | ~$15K     | 30 nodes                  |           |
|  | Kafka + Flink    | ~$10K     | Analytics pipeline        |           |
|  | ClickHouse       | ~$8K      | Analytics store           |           |
|  | Compute (fleet)  | ~$20K     | Shorten + Redirect + IdGen|           |
|  | Zookeeper        | ~$1K      | 3-node quorum             |           |
|  | Safety scan API  | ~$5K      | Google Safe Browsing      |           |
|  +------------------+-----------+---------------------------+           |
|  | TOTAL            | ~$140K/mo | ~$1.7M/year               |           |
|  +------------------+-----------+---------------------------+           |
|                                                                         |
|  KEY OBSERVATION                                                        |
|                                                                         |
|  CDN dominates cost. Every 10% improvement in CDN hit rate saves       |
|  $5K/month. This is where engineering investment matters.               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.4: FAILURE MODE GRID

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +------------------------+--------------------+----------------------+ |
|  | Failure                | Detection          | Mitigation           | |
|  +------------------------+--------------------+----------------------+ |
|  | Redis primary crash    | Client errors      | Sentinel fail-over   | |
|  | Cassandra node down    | Ring alert         | Ring self-heals      | |
|  | ZK unreachable         | ID range refresh   | Redis fallback range | |
|  |                        | fails              |                      | |
|  | CDN outage             | 5xx from CDN       | Origin-direct DNS    | |
|  |                        |                    | (traffic surge)      | |
|  | Bot enumeration attack | 404 rate spike     | Bloom + WAF          | |
|  | Viral URL hot key      | key_qps > 10K      | Multi-key replicate  | |
|  | Malicious URL detected | Safety scan flag   | Takedown flag +      | |
|  |                        |                    | cache invalidation   | |
|  | ID exhausted           | Range depletion    | Reserve new range    | |
|  | Bloom FP rate up       | metric alert       | Rebuild larger BF    | |
|  | Analytics pipeline lag | Kafka consumer lag | Scale Flink workers  | |
|  | Custom alias collision | LWT reject         | 409 to caller        | |
|  | Region failure         | Health check fail  | DNS shift + Cassandra| |
|  |                        |                    | multi-DC replication | |
|  +------------------------+--------------------+----------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.5: NUMBERS TO MEMORIZE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALE                                                                  |
|    100M shortens / day  (~1,200 QPS)                                    |
|    10B redirects / day  (~115K QPS avg, 350K peak)                      |
|    100:1 read:write ratio                                               |
|                                                                         |
|  LATENCY                                                                |
|    Redirect p99: 100 ms                                                 |
|    Redirect p50 (cache hit): 20 ms                                      |
|    Shorten p99: 500 ms                                                  |
|                                                                         |
|  DATA                                                                   |
|    URL record: ~600 bytes                                               |
|    Per-day storage: 60 GB                                               |
|    5-year storage: 110 TB (3x replicated = 330 TB)                      |
|                                                                         |
|  SHORT CODE                                                             |
|    7 Base62 chars                                                       |
|    62^7 = 3.5 trillion possible codes                                   |
|    96 years of runway                                                   |
|                                                                         |
|  BLOOM FILTER                                                           |
|    100B codes, 0.1% FP -> ~180 GB                                       |
|    Sharded across 50 Redis nodes                                        |
|                                                                         |
|  RANGE COUNTER                                                          |
|    10,000 IDs per range                                                 |
|    10K ZK ops/day at 100M/day scale                                     |
|                                                                         |
|  COST                                                                   |
|    ~$140K/month at target scale                                         |
|    CDN dominates (35% of total)                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.6: HIGH-VALUE TALKING POINTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  * "100:1 read:write asymmetry drives every architectural decision --   |
|    aggressive CDN caching, Redis in front of Cassandra, denormalized    |
|    user_urls table for fast list queries."                              |
|                                                                         |
|  * "302 (not 301) redirects so we can track every click and update     |
|    destinations without stale browser caches. CDN edge cache with       |
|    max-age=60 gets us the latency benefit while keeping analytics       |
|    accurate."                                                           |
|                                                                         |
|  * "Range-based ID generation avoids collisions by construction. 10K   |
|    IDs per range means ZK is only touched every 100 seconds per         |
|    instance -- no coordination bottleneck."                             |
|                                                                         |
|  * "Bloom filter is the key defense against bot enumeration. Without   |
|    it, one bot could DDoS our DB with fake code lookups."               |
|                                                                         |
|  * "Hot URL detection triggers multi-key replication AND CDN 'always   |
|    cache' rules. A viral link's traffic is absorbed at the edge."       |
|                                                                         |
|  * "Cassandra multi-DC replication gives us active-active reads with   |
|    no application code changes. Custom alias uniqueness uses LWT with   |
|    quorum-each-DC for global consistency at a small latency cost."      |
|                                                                         |
|  * "URL safety scanning is async because sync would double our shorten |
|    latency. The takedown flag path handles URLs that go bad post-       |
|    scan -- redirect service checks takedown:{code} before serving."     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.7: CROSS-REFERENCES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  * Consistent hashing (for cache sharding):                             |
|      System Design/Fundamentals/06-Sharding-And-Replication.md          |
|                                                                         |
|  * CAP tradeoffs (for Cassandra tuning):                                |
|      System Design/Fundamentals/02-CAP-And-Consistency.md               |
|                                                                         |
|  * Bloom filter theory (for sizing):                                    |
|      System Design/Fundamentals/20-Database-Internals-Deep-Dive.md      |
|                                                                         |
|  * Rate limiting algorithms (for per-user shorten limits):              |
|      System Design/Rate-Limiter/01-Requirements-And-Algorithms.md       |
|                                                                         |
|  * Cache patterns (deep dive):                                          |
|      System Design/Fundamentals/04-Caching.md                           |
|                                                                         |
|  * Kafka partitioning (for click event topic):                          |
|      System Design/Kafka/02-Architecture-Deep-Dive.md                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.8: THE ONE-DIAGRAM SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|         Client                                                          |
|            |                                                            |
|            v                                                            |
|      +---------+                                                        |
|      |   CDN   |  80% edge-cached  ->  0 origin hit                     |
|      +----+----+                                                        |
|           |                                                             |
|           | 20%                                                         |
|           v                                                             |
|      +---------+     +----------+                                       |
|      | Redir   |---->|  Bloom   |  404 fast path                        |
|      | Service |     +----------+                                       |
|      +----+----+                                                        |
|           |                                                             |
|           v                                                             |
|      +---------+     +-----------+                                      |
|      |  Redis  |---->| Cassandra |  (cache miss ~1%)                    |
|      | Cluster |     |   Ring    |                                      |
|      +---+-----+     +-----+-----+                                      |
|          |                 |                                            |
|          v                 v                                            |
|       (Click event Kafka)                                               |
|                 |                                                       |
|                 v                                                       |
|             Flink -> ClickHouse (analytics)                             |
|             Flink -> Redis counter (real-time)                          |
|                                                                         |
|      SHORTEN PATH                                                       |
|                                                                         |
|      Client -> API -> Shorten Svc -> ID Gen (ZK) -> Cassandra           |
|                                                    |                    |
|                                                    +-> Bloom.ADD        |
|                                                    +-> Safety Scan Kafka|
|                                                                         |
+-------------------------------------------------------------------------+
```

Learn to draw this in 2 minutes. Everything hangs off this skeleton.

## INTERVIEW CRUX — SAY THIS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  URL SHORTENER — WHAT TO SAY IN THE INTERVIEW                           |
|                                                                         |
|  DEFAULT ANSWER (when asked "how would you design X?"):                 |
|  * CDN + Redirect service in front of Redis Cluster + Cassandra         |
|  * Range-based counter (Zookeeper-coordinated) -> Base62 encode -> 7    |
|      char code; no collisions by construction                           |
|  * Cassandra partitioned by short_code (multi-region, native TTL)       |
|  * 302 redirect + Cache-Control max-age=60 -> click analytics stay      |
|      accurate; Kafka -> Flink -> ClickHouse for rich stats              |
|  * Bloom filter (RedisBloom) absorbs bot enumeration on 404s            |
|                                                                         |
|  IF ASKED "how do you handle X?" (~3-5 common follow-ups):              |
|  * a URL goes viral (hot key)? Extended CDN edge cache + multi-key      |
|      replicate the hot code across shards; DB never sees the storm      |
|  * custom aliases? Cassandra LWT / unique constraint on INSERT --       |
|      first writer wins, second gets 409 Conflict                        |
|  * malicious URLs? Async safety scan on create + takedown:{code}        |
|      Redis flag checked on every redirect; global cache invalidate      |
|  * expired URLs? Cassandra native TTL -> 410 Gone; bloom retains        |
|      the code briefly, tiny FP overhead until periodic rebuild          |
|  * collisions? None -- counter-based IDs are unique by construction;    |
|      hash-based would need retry loops (birthday paradox at 2M URLs)    |
|                                                                         |
|  NUMBERS TO DROP:                                                       |
|  * 10B redirects/day (~115K QPS avg, ~350K peak)                        |
|  * 100M shortens/day (100:1 read:write asymmetry drives design)         |
|  * Redirect p99 < 100 ms globally; p50 < 20 ms (cache hit)              |
|  * 7-char Base62 = 62^7 = 3.5 trillion codes = ~96 years runway         |
|  * URL record ~600 B; 60 GB/day; 110 TB over 5 years (3x replica)       |
|  * ~80% CDN edge hit rate -> origin sees only ~23K QPS                  |
|  * ~$140K/month at target scale (CDN dominates 35%)                     |
|                                                                         |
|  REAL-WORLD PATTERNS TO NAME-DROP:                                      |
|  * Bitly: market leader; branded links + rich analytics                 |
|  * Twitter t.co: mandatory shortening for all shared links              |
|  * TinyURL: original; simple hash-based (fine at low scale)             |
|  * Firebase Dynamic Links: shortening + deep-linking for mobile         |
|                                                                         |
|  ONE-LINE CRUX:                                                         |
|  "Range-counter Base62 IDs, CDN + Redis in front of Cassandra, bloom    |
|   filter for 404s, 302 for accurate analytics."                         |
|                                                                         |
+-------------------------------------------------------------------------+
```
