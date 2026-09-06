# CHAPTER 25: BACK-OF-THE-ENVELOPE — NUMBERS TO MEMORIZE
*The "quote-these-in-any-interview" reference chapter*

Interviewers don't want exact numbers — they want to see that you can
**estimate within 10x** in under 60 seconds and justify the number.
This chapter gives you the ~40 numbers that cover 90% of every system
design sizing question you'll be asked.

**Memorize the bold ones. Everything else is derivable from them.**

---

## SECTION 25.1: THE BIG 3 — TIME, POWERS OF 2, LATENCY

These three tables are the foundation. Learn them cold.

### 25.1.1 Time constants (seconds in a day / month / year)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TIME → SECONDS                                                         |
|                                                                         |
|  1 minute  =         60 s                                               |
|  1 hour    =      3,600 s                                               |
|  1 day     =     86,400 s   ≈ 10^5    ← memorize                        |
|  1 month   =    2,600,000 s ≈ 2.6 × 10^6                                |
|  1 year    =   31,500,000 s ≈ 3.15 × 10^7                               |
|                                                                         |
|  RULE OF THUMB: 1 day ≈ 100,000 seconds (~10^5)                         |
|  So "1 event / user / day" from 1M DAU = 1M / 10^5 = 10 QPS             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 25.1.2 Powers of 2 → decimal (the storage table)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  POWERS OF 2                                                            |
|                                                                         |
|  2^10   =           1,024   ≈ 1 thousand  = 1 KB                        |
|  2^20   =       1,048,576   ≈ 1 million   = 1 MB                        |
|  2^30   =   1,073,741,824   ≈ 1 billion   = 1 GB                        |
|  2^32   =   4,294,967,296   ≈ 4 billion   ← IPv4 space, INT max         |
|  2^40   ≈       1 trillion  = 1 TB                                      |
|  2^50   ≈    1 quadrillion  = 1 PB                                      |
|  2^63   ≈  9.2 × 10^18      ← BIGINT (signed) max                       |
|                                                                         |
|  MENTAL MODEL: each 10-bit jump = 3 zeros in decimal                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 25.1.3 Latency numbers every developer should know (Jeff Dean, updated)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LATENCY LADDER (order of magnitude — memorize these ratios)            |
|                                                                         |
|  L1 cache reference               0.5   ns                              |
|  Branch mispredict                  5   ns                              |
|  L2 cache reference                 7   ns                              |
|  Mutex lock/unlock                 25   ns                              |
|  Main memory reference            100   ns    ← 200x slower than L1     |
|  Compress 1KB with Zippy        3,000   ns   =    3 µs                  |
|  Send 1KB over 1 Gbps LAN      10,000   ns   =   10 µs                  |
|  Read 4KB random from SSD     150,000   ns   =  150 µs                  |
|  Read 1MB sequential from RAM 250,000   ns   =  250 µs                  |
|  Round trip within datacenter 500,000   ns   =  500 µs   = 0.5 ms       |
|  Read 1MB sequential from SSD 1,000,000 ns   = 1     ms                 |
|  Disk seek (spinning HDD)     10,000,000 ns  = 10    ms                 |
|  Read 1MB sequential from HDD 30,000,000 ns  = 30    ms                 |
|  Round trip CA → Netherlands  150,000,000 ns = 150 ms  ← speed of light |
|                                                                         |
|  KEY RATIOS TO REMEMBER:                                                |
|  * RAM is  ~200x faster than SSD random read                            |
|  * SSD is  ~100x faster than HDD                                        |
|  * Same-DC roundtrip = 0.5 ms, cross-continent = 150 ms (300x)          |
|  * 1 ms of budget lets you do ~10 same-DC roundtrips or 1 SSD read      |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## SECTION 25.2: BANDWIDTH & THROUGHPUT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NETWORK BANDWIDTH (typical modern hardware)                            |
|                                                                         |
|  Home broadband (down)      50-500  Mbps                                |
|  4G mobile                   5-50   Mbps                                |
|  5G mobile                  50-1000 Mbps                                |
|  Datacenter NIC             10-100  Gbps    ← per server                |
|  Cross-DC link              1-100   Gbps                                |
|  Cross-continent link       10-400  Gbps    (backbone)                  |
|                                                                         |
|  DISK / MEMORY BANDWIDTH                                                |
|                                                                         |
|  HDD sequential             ~100    MB/s                                |
|  SSD sequential             ~500    MB/s                                |
|  NVMe sequential            ~3      GB/s                                |
|  DDR4 memory                ~25     GB/s                                |
|                                                                         |
|  UNIT CONVERSION TRAP:                                                  |
|  * 1 Gbps = 125 MB/s   (divide by 8 for bits→bytes)                     |
|  * 10 Gbps NIC saturated = 1.25 GB/s = big files fast                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## SECTION 25.3: TYPICAL OBJECT SIZES (bytes per thing)

These are the sizes you'll multiply against QPS to get storage/bandwidth.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TEXT / METADATA                                                        |
|                                                                         |
|  1 character (ASCII)               1  B                                 |
|  1 character (UTF-8, worst)        4  B                                 |
|  Log line (structured)         ~ 500  B      – 1 KB                     |
|  DB row (typical, indexed)     ~ 100  B      – 1 KB                     |
|  Tweet / short message         ~ 300  B      (with metadata)            |
|  Chat message                  ~ 100  B      – 1 KB                     |
|  User profile record           ~   1  KB     – 5 KB                     |
|  Small JSON API response       ~   1  KB     – 10 KB                    |
|  Click / event record          ~ 100  B      – 500 B                    |
|  UUID (raw / string)              16  B / 36 B                          |
|  URL (typical)                 ~ 100  B                                 |
|                                                                         |
|  MEDIA                                                                  |
|                                                                         |
|  Small thumbnail (JPEG)          10  KB                                 |
|  Regular photo (mobile)       200  KB    – 2 MB                         |
|  RAW photo (DSLR)             25   MB                                   |
|  1 min of MP3 audio (128k)     1   MB                                   |
|  1 min of 480p video           5   MB                                   |
|  1 min of 1080p video         50   MB    ← memorize                     |
|  1 min of 4K video           350   MB                                   |
|                                                                         |
|  HANDY MULTIPLICATIONS                                                  |
|                                                                         |
|  1M tweets/day  × 300 B    = 300 MB/day  → 100 GB/year                  |
|  1M photos/day  × 500 KB   = 500 GB/day  → 180 TB/year                  |
|  1M videos/day  × 50 MB    = 50 TB/day   → 18 PB/year                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## SECTION 25.4: THE MAIN FORMULA — DAU → QPS → STORAGE

This is the single formula you'll use in **90% of interviews**. Memorize it.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QPS = (DAU × actions_per_user_per_day) / 100,000                       |
|                                                                         |
|  (because 1 day ≈ 10^5 seconds — see 25.1.1)                            |
|                                                                         |
|  EXAMPLES:                                                              |
|                                                                         |
|  1M DAU × 10 actions/day   → 10M / 10^5   =    100 QPS  (average)       |
|  100M DAU × 10 actions/day → 1B / 10^5    = 10,000 QPS  (average)       |
|  1B DAU × 10 actions/day   → 10B / 10^5   = 100,000 QPS (average)       |
|                                                                         |
|  STORAGE PER DAY = writes/day × bytes_per_write                         |
|  STORAGE PER YEAR = storage/day × 365                                   |
|                                                                         |
|  EGRESS BANDWIDTH = read QPS × bytes_per_response                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 25.4.1 Worked mini-examples

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: "Twitter has 500M DAU. Estimate write QPS."                         |
|                                                                         |
|  Assume: 2 tweets per user per day (very conservative)                  |
|  Writes/day  = 500M × 2 = 1B                                            |
|  Write QPS   = 1B / 10^5 = 10,000 QPS (average)                         |
|  Peak (3x)   = 30,000 QPS                                               |
|                                                                         |
|  Storage: 1B tweets/day × 300 B = 300 GB/day = ~100 TB/year             |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## SECTION 25.5: READ / WRITE RATIOS BY SERVICE TYPE

Reads dominate almost every consumer service. Ratio drives your cache
sizing and read-replica count.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICE TYPE                    READ : WRITE RATIO                     |
|                                                                         |
|  Social feed (Twitter, IG)         100:1  to 1000:1  (celebs = 10^6:1)  |
|  News site                         1000:1                               |
|  E-commerce (Amazon)               10:1   to 100:1                      |
|  Search engine                     ~pure read                           |
|  Chat / messaging                  1:1    (read = deliver)              |
|  Analytics / logs / metrics        1:100  (WRITE-heavy)                 |
|  Ad-click ingestion                1:1000 (WRITE-heavy)                 |
|  Payment / order system            5:1    to 20:1                       |
|  File storage (S3-like)            2:1    to 10:1                       |
|                                                                         |
|  IMPLICATIONS:                                                          |
|  * Read-heavy → invest in cache, CDN, read replicas                     |
|  * Write-heavy → invest in Kafka, LSM stores, partitioning              |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## SECTION 25.6: PEAK vs AVERAGE — THE MULTIPLIER

Never quote average QPS alone. Always say "average X, peak ~3-10x".

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PEAK-TO-AVERAGE MULTIPLIER (rule of thumb)                             |
|                                                                         |
|  Steady enterprise SaaS            2x                                   |
|  Consumer web (diurnal)            3-4x                                 |
|  Social / news (event-driven)      5-10x                                |
|  Live events (Super Bowl, IPL)     50-100x                              |
|  Flash sale / drop                 100-1000x                            |
|                                                                         |
|  DEFAULT ANSWER: "Assume peak = 3x average unless the service is        |
|  event-driven, in which case 10x."                                      |
|                                                                         |
|  Provision for PEAK, not average, or you'll fall over at 8 pm.          |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## SECTION 25.7: PER-NODE THROUGHPUT CEILINGS

This tells you how many boxes / shards / brokers you need.
Numbers are approximate but safe to quote in interviews.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMPONENT                    THROUGHPUT PER NODE                       |
|                                                                         |
|  Web / app server (stateless)     5,000 – 20,000  QPS                   |
|  Nginx / HAProxy                  50,000 – 100,000 conn/s               |
|  SQL (Postgres, MySQL) writes     5,000 – 15,000  QPS                   |
|  SQL reads (with indexes)         20,000 – 50,000 QPS                   |
|  Redis / Memcached                100,000 – 1M    ops/s                 |
|  Cassandra / DynamoDB writes      10,000 – 50,000 writes/s              |
|  Kafka broker                     ~ 1 million     msgs/s (with batching)|
|  Elasticsearch queries            ~ 1,000         QPS                   |
|  Object storage (S3) prefix       3,500 PUT / 5,500 GET per prefix      |
|  ML model serving (CPU)           100 – 1,000     QPS                   |
|  ML model serving (GPU)           10,000+         QPS (batched)         |
|                                                                         |
|  RULE OF THUMB FOR "HOW MANY SHARDS?"                                   |
|                                                                         |
|  shards = ceil(peak_QPS / per_shard_ceiling) × 2   (2x headroom)        |
|                                                                         |
|  e.g. 100k write QPS on Postgres → ceil(100k / 10k) × 2 = 20 shards     |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## SECTION 25.8: STORAGE & COMPUTE COSTS (per GB per month)

Useful for cost-vs-latency tradeoffs (e.g. "should we keep this in Redis
or S3?").

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TIER                       COST / GB / MONTH   RELATIVE                |
|                                                                         |
|  RAM (in-app)               ~ $ 2 – $ 5         1x (baseline)           |
|  Redis / ElastiCache        ~ $ 0.20            10x cheaper than RAM    |
|  SSD (EBS gp3)              ~ $ 0.10            50x cheaper than RAM    |
|  HDD                        ~ $ 0.03            150x cheaper            |
|  S3 Standard                ~ $ 0.023           200x cheaper            |
|  S3 Infrequent Access       ~ $ 0.0125          400x cheaper            |
|  S3 Glacier Instant         ~ $ 0.004           1000x cheaper           |
|  S3 Glacier Deep Archive    ~ $ 0.00099         4000x cheaper           |
|                                                                         |
|  QUICK MULTIPLIER: dropping from RAM → S3 is ~200x cost reduction       |
|  but ~1000-10000x latency increase (µs → 10ms)                          |
|                                                                         |
|  COMPUTE                                                                |
|                                                                         |
|  On-demand VM (medium, 2 vCPU / 4 GB)   ~ $ 30 – $ 60 / month           |
|  Spot / preemptible                     ~ 70% off on-demand             |
|  Reserved (1 yr)                        ~ 40% off on-demand             |
|  Egress from AWS to internet            ~ $ 0.09 / GB     ← BIG         |
|  Egress inside same AZ                  free / trivial                  |
|  Egress across AZ                       ~ $ 0.01 / GB                   |
|                                                                         |
|  INTERVIEW POWER-MOVE:                                                  |
|  "The egress cost dominates — 1 PB out / month = $90k. That's why       |
|   Netflix runs Open Connect boxes inside ISPs instead of streaming      |
|   from AWS."                                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## SECTION 25.9: REAL-WORLD SCALE NUMBERS YOU CAN CITE

Drop these to sound informed. All are public / rough as of 2024-2026.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICE                    KEY NUMBERS TO QUOTE                        |
|                                                                         |
|  Google Search              ~ 100k QPS avg (peak higher)                |
|  YouTube                    ~ 2B  DAU, 500 hours uploaded / minute      |
|  Instagram                  ~ 2B  DAU, 100M photos / day                |
|  Facebook                   ~ 2B  DAU, 4 PB new content / day           |
|  WhatsApp                   ~ 2B  users, 100B messages / day            |
|  Twitter / X                ~ 500M DAU, 500M tweets / day               |
|  Netflix                    ~ 260M subs, 15% of global internet at peak |
|  Uber                       ~ 130M MAU, ~ 25M rides / day               |
|  Amazon.com                 ~ 300M active users                         |
|  Stripe                     ~ 10k tx/sec avg, 100k at peak              |
|  Cloudflare                 ~ 55M HTTP req/sec globally                 |
|                                                                         |
|  INDUSTRY-WIDE ANCHORS                                                  |
|                                                                         |
|  * "Popular consumer app" ≈ 100M DAU                                    |
|  * "Big consumer app"     ≈ 1B DAU                                      |
|  * "Big enterprise"       ≈ 10k concurrent users                        |
|  * "Startup PMF"          ≈ 100k DAU                                    |
|  * Kafka at LinkedIn      ≈ 7 trillion msgs/day                         |
|  * Facebook TAO           ≈ 1 billion reads/sec                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## SECTION 25.10: THE 5-QUESTION SIZING TEMPLATE

Any time you're asked "estimate the scale", answer these 5 questions
in order. You'll never be lost.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE 5-QUESTION TEMPLATE                                                |
|                                                                         |
|  1. How many users?                                                     |
|     - DAU / MAU (assume DAU = MAU / 3 if only given MAU)                |
|                                                                         |
|  2. What's the read / write mix per user per day?                       |
|     - "User does X reads, Y writes per day"                             |
|                                                                         |
|  3. What's the payload size per operation?                              |
|     - Read response bytes, write payload bytes                          |
|                                                                         |
|  4. What's the retention?                                               |
|     - "We keep 5 years of history"                                      |
|                                                                         |
|  5. What's the peak multiplier?                                         |
|     - Default 3x for consumer, 10x for viral / event                    |
|                                                                         |
|  THEN DERIVE:                                                           |
|                                                                         |
|  - avg QPS  = DAU × actions_per_user / 10^5                             |
|  - peak QPS = avg × peak_multiplier                                     |
|  - storage/day  = writes/day × bytes                                    |
|  - storage/N-yr = storage/day × 365 × N                                 |
|  - egress bw    = read QPS × bytes_per_response                         |
|  - shards       = ceil(peak QPS / per-node ceiling) × 2                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## SECTION 25.11: WORKED EXAMPLE — DESIGN TWITTER IN 60 SECONDS

Watch how the template + numbers give you a full sizing in one minute.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROBLEM: Design Twitter. Estimate scale.                               |
|                                                                         |
|  STEP 1 — USERS                                                         |
|  DAU = 500M                            (real-world number, quote it)    |
|                                                                         |
|  STEP 2 — ACTIONS PER USER PER DAY                                      |
|  Writes: 2 tweets / user / day         (conservative)                   |
|  Reads:  100 tweets / user / day       (feed views)                     |
|  Read / write ratio ≈ 50:1                                              |
|                                                                         |
|  STEP 3 — PAYLOAD SIZE                                                  |
|  Tweet = 300 B  (text + metadata; images stored separately in S3)       |
|  Feed response ≈ 20 tweets × 300 B = 6 KB per feed load                 |
|                                                                         |
|  STEP 4 — RETENTION                                                     |
|  Forever (tweets are permanent). Estimate 5 years for storage calc.     |
|                                                                         |
|  STEP 5 — PEAK MULTIPLIER                                               |
|  3x (diurnal); 10x for viral moment; use 3x for baseline                |
|                                                                         |
|  DERIVED NUMBERS                                                        |
|                                                                         |
|  Write QPS avg  = 500M × 2   / 10^5 =   10,000 QPS                      |
|  Write QPS peak = 10k × 3           =   30,000 QPS                      |
|  Read QPS avg   = 500M × 100 / 10^5 =  500,000 QPS                      |
|  Read QPS peak  = 500k × 3          = 1,500,000 QPS                     |
|                                                                         |
|  Storage/day   = 1B tweets × 300 B  = 300 GB/day                        |
|  Storage/year  = 300 GB × 365       = 110 TB/year                       |
|  Storage/5-yr  = ~ 550 TB           (tweets only, no media)             |
|                                                                         |
|  Egress bw     = 1.5M QPS × 6 KB    = 9 GB/s = 72 Gbps                  |
|                  → need CDN + read cache to offload                     |
|                                                                         |
|  Shards (writes on Postgres):                                           |
|    ceil(30k / 10k) × 2 = 6 write shards                                 |
|                                                                         |
|  Cache (Redis for hot feeds):                                           |
|    keep last 20 tweets × 500M users × 6 KB = 3 TB hot set               |
|    ÷ 100 GB/node = 30 Redis nodes                                       |
|                                                                         |
|  DONE. You just sized Twitter in 60 seconds using 3 formulas and        |
|  memorized numbers.                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## SECTION 25.12: SECOND WORKED EXAMPLE — YOUTUBE UPLOAD PIPELINE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROBLEM: How much storage does YouTube add every day?                  |
|                                                                         |
|  KNOWN: 500 hours of video uploaded per minute (public number)          |
|                                                                         |
|  1 min of 1080p = 50 MB   (from 25.3)                                   |
|  1 hour = 60 min × 50 MB = 3 GB (per 1080p copy)                        |
|                                                                         |
|  Per-minute upload: 500 hrs × 3 GB = 1,500 GB = 1.5 TB / minute         |
|  Per-day upload:    1.5 TB × 1440  = 2,160 TB   = ~ 2 PB / day (1080p)  |
|                                                                         |
|  BUT: each video is transcoded to ~ 5 resolutions (144, 360, 720,       |
|  1080, 4K) with different codecs (H264, VP9, AV1). Storage multiplier   |
|  ≈ 5-10x. → real storage add ~ 10-20 PB / day.                          |
|                                                                         |
|  KEY TAKEAWAY: transcoding fanout is the hidden multiplier.             |
|  Always ask "how many variants?"                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## SECTION 25.13: QUICK-REFERENCE CHEAT CARD (one-page condensed)

Print this. Tape it to your monitor.

```
+-------------------------------------------------------------------------+
|                                                                         |
|                 BACK-OF-ENVELOPE — CHEAT CARD                           |
|                                                                         |
|  TIME:                                                                  |
|  * 1 day ≈ 10^5 s     * 1 year ≈ 3.15 × 10^7 s                          |
|                                                                         |
|  POWERS OF 2:                                                           |
|  * 2^10 = 1 KB   * 2^20 = 1 MB   * 2^30 = 1 GB   * 2^40 = 1 TB          |
|  * 2^32 = 4B (INT max, IPv4 space)                                      |
|                                                                         |
|  LATENCY:                                                               |
|  * L1 = 0.5 ns   * RAM = 100 ns    * SSD 4KB read = 150 µs              |
|  * Same-DC RTT = 0.5 ms   * SSD 1MB seq = 1 ms   * HDD seek = 10 ms     |
|  * Cross-continent RTT = 150 ms                                         |
|                                                                         |
|  BANDWIDTH:                                                             |
|  * DC NIC = 10-100 Gbps   * SSD = 500 MB/s   * NVMe = 3 GB/s            |
|  * 1 Gbps = 125 MB/s      (÷8 for bit → byte)                           |
|                                                                         |
|  OBJECT SIZES:                                                          |
|  * Tweet = 300 B   * Chat msg = 100 B - 1 KB   * DB row ≈ 1 KB          |
|  * Photo = 500 KB   * 1 min 1080p video = 50 MB                         |
|                                                                         |
|  MAIN FORMULA:                                                          |
|  * QPS = (DAU × actions/user/day) / 10^5                                |
|  * Peak = avg × 3 (steady) or × 10 (viral)                              |
|  * Storage/day = writes/day × bytes                                     |
|                                                                         |
|  READ/WRITE RATIOS:                                                     |
|  * Social feed: 100-1000:1   * E-comm: 10:1                             |
|  * Chat: 1:1   * Analytics: write-heavy 1:100                           |
|                                                                         |
|  PER-NODE CEILINGS:                                                     |
|  * App server: 10k QPS   * SQL write: 10k QPS   * SQL read: 30k         |
|  * Redis: 100k+ ops/s   * Kafka broker: 1M msgs/s                       |
|                                                                         |
|  COSTS ($ / GB / month):                                                |
|  * RAM $2   * Redis $0.20   * SSD $0.10   * S3 $0.023                   |
|  * S3 Glacier $0.004     * Egress $0.09 / GB   ← always the killer      |
|                                                                         |
|  SCALE ANCHORS:                                                         |
|  * Popular app: 100M DAU   * Big consumer: 1B DAU                       |
|  * Google search: ~100k QPS   * WhatsApp: 100B msgs/day                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## SECTION 25.14: COMMON MISTAKES / RED FLAGS TO AVOID

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DON'T DO THIS IN AN INTERVIEW                                          |
|                                                                         |
|  1. Quoting a number without saying peak vs average.                    |
|     WRONG: "Twitter does 30k writes/sec."                               |
|     RIGHT: "10k avg, 30k peak assuming 3x diurnal."                     |
|                                                                         |
|  2. Confusing bits and bytes.                                           |
|     "1 Gbps = 125 MB/s" (divide by 8).                                  |
|                                                                         |
|  3. Ignoring metadata / transcoding fanout.                             |
|     Video stored 5-10x its raw size after transcoding to N resolutions. |
|                                                                         |
|  4. Not sizing the CACHE.                                               |
|     Almost every read-heavy service needs a cache. Size it explicitly:  |
|     hot set × bytes / per-node RAM = number of cache nodes.             |
|                                                                         |
|  5. Forgetting REPLICATION FACTOR in storage.                           |
|     Real storage = logical size × replication factor (usually 3).       |
|                                                                         |
|  6. Skipping EGRESS BANDWIDTH cost.                                     |
|     $0.09/GB × 1 PB = $90k. Often the biggest cost item.                |
|                                                                         |
|  7. Treating peak as average for latency SLOs.                          |
|     Provision compute for peak QPS; provision latency at p99, not p50.  |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## INTERVIEW CRUX — SAY THIS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BACK-OF-THE-ENVELOPE — WHAT TO SAY IN THE INTERVIEW                    |
|                                                                         |
|  DEFAULT APPROACH (walk this out loud, in order):                       |
|  * "Let me start by sizing. I'll use round numbers."                    |
|  * State DAU (or ask). Assume 3x if given MAU only.                     |
|  * State actions/user/day (reads and writes separately).                |
|  * Convert to QPS: DAU × actions / 10^5 (because 1 day ≈ 10^5 s).       |
|  * Multiply by 3x for peak (or 10x if event-driven / viral).            |
|  * State bytes/operation. Multiply for storage/day and egress.          |
|  * State retention (years). Multiply for total storage.                 |
|  * Divide peak QPS by per-node ceiling for shard count (× 2 headroom).  |
|                                                                         |
|  MEMORIZED CONSTANTS TO DROP:                                           |
|  * 1 day = 10^5 s      * 1 year = 3.15 × 10^7 s                         |
|  * 2^30 = 1 GB         * 2^40 = 1 TB                                    |
|  * Same-DC RTT = 0.5 ms    * Cross-continent = 150 ms                   |
|  * RAM = 100 ns   SSD 4KB = 150 µs   HDD seek = 10 ms                   |
|  * SQL: 10k writes/s per node; Redis: 100k+ ops/s; Kafka: 1M msgs/s     |
|  * Photo = 500 KB   Video 1080p = 50 MB/min   Tweet = 300 B             |
|                                                                         |
|  READ/WRITE RATIOS (state these EARLY):                                 |
|  * Social feed 100-1000:1   * E-commerce 10:1   * Chat 1:1              |
|  * Analytics/logging: write-heavy 1:100                                 |
|                                                                         |
|  ALWAYS SIZE THE CACHE:                                                 |
|  * "Hot set" = last-N items × active users × avg bytes                  |
|  * ÷ RAM per Redis node (100 GB typical) = # of cache nodes             |
|                                                                         |
|  ALWAYS CALL OUT COST:                                                  |
|  * "Egress at $0.09/GB dominates — that's why Netflix uses Open         |
|    Connect. For our design we'll rely on CDN caching."                  |
|                                                                         |
|  SENIOR-LEVEL FRAMING:                                                  |
|  * "I care about the ORDER OF MAGNITUDE, not exact numbers."            |
|  * "If any of these assumptions are off, tell me and I'll re-derive."   |
|  * "I'll provision for PEAK, not average."                              |
|  * "Storage number × replication factor of 3 for real storage."         |
|                                                                         |
|  ONE-LINE CRUX:                                                         |
|  "Sizing is 3 formulas: QPS = DAU × actions / 10^5, storage/day =       |
|   writes × bytes, shards = ceil(peak QPS / per-node ceiling) × 2.       |
|   Everything else is memorized constants."                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 25
