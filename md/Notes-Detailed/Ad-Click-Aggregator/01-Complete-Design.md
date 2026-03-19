# AD CLICK AGGREGATOR / REAL-TIME EVENT COUNTING SYSTEM
*Complete Design: Requirements, Architecture, and Interview Guide*

An ad click aggregation system counts ad clicks and impressions in real-time
for billing, reporting, analytics dashboards, and fraud detection. At scale,
it must process billions of events daily with exactly-once counting semantics
to ensure accurate advertiser billing and campaign performance measurement.

## SECTION 1: UNDERSTANDING THE PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS AN AD CLICK AGGREGATOR?                                        |
|                                                                         |
|  When a user clicks on an ad or views an impression:                    |
|                                                                         |
|  1. The click/impression event is captured with metadata                |
|  2. Events are aggregated by ad, campaign, advertiser, time window      |
|  3. Aggregated counts power billing, dashboards, and fraud detection    |
|  4. Advertisers see real-time campaign performance (<1 min delay)       |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  WHY IS THIS HARD?                                                      |
|                                                                         |
|  1. MASSIVE SCALE                                                       |
|     * 10K+ clicks/sec, 100K+ impressions/sec                            |
|     * Billions of events per day to count accurately                    |
|                                                                         |
|  2. EXACTLY-ONCE COUNTING                                               |
|     * Over-counting = overcharging advertisers (lawsuits)               |
|     * Under-counting = revenue loss for the platform                    |
|     * Must be accurate for billing, not just analytics                  |
|                                                                         |
|  3. REAL-TIME REQUIREMENT                                               |
|     * Dashboard must update within 1 minute                             |
|     * Fraud must be detected in seconds to prevent drain                |
|                                                                         |
|  4. FAULT TOLERANCE                                                     |
|     * A single node failure cannot lose events                          |
|     * System must keep counting even during deployments                 |
|                                                                         |
|  5. LATE-ARRIVING EVENTS                                                |
|     * Mobile devices may batch events and send late                     |
|     * Network delays can cause out-of-order arrival                     |
|     * Must correctly assign late events to past time windows            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS:                                               |
|                                                                         |
|  1. CLICK/IMPRESSION TRACKING                                           |
|     * Track ad clicks with full event metadata                          |
|     * Track ad impressions (ad was rendered/viewable)                   |
|     * Capture: ad_id, user_id, timestamp, IP, user_agent, referrer      |
|                                                                         |
|  2. REAL-TIME AGGREGATION                                               |
|     * Aggregate by ad_id, campaign_id, advertiser_id                    |
|     * Aggregate by dimensions: geo, device type, OS, browser            |
|     * Time-windowed aggregation: per minute, hour, day                  |
|     * Dashboard reflects counts within 1 minute of event                |
|                                                                         |
|  3. HISTORICAL QUERIES                                                  |
|     * Query click/impression counts for any past time range             |
|     * Drill-down by any dimension combination                           |
|     * Support ad-hoc analytical queries                                 |
|                                                                         |
|  4. FRAUD FILTERING                                                     |
|     * Detect and flag fraudulent clicks in real-time                    |
|     * Filter bot traffic, click farms, competitor abuse                 |
|     * Flag but do not discard - store for audit                         |
|                                                                         |
|  5. BILLING FEED                                                        |
|     * Provide verified click counts for CPC billing                     |
|     * Provide verified impression counts for CPM billing                |
|     * Reconciliation pipeline for billing accuracy                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  NON-FUNCTIONAL REQUIREMENTS:                                           |
|                                                                         |
|  * Throughput: 10K+ clicks/sec, 100K+ impressions/sec peak              |
|  * Exactly-once counting for billing pipeline                           |
|  * At-least-once for analytics (slight over-count acceptable)           |
|  * Fault-tolerant: no single point of failure                           |
|  * Idempotent: reprocessing same event produces same result             |
|  * Latency: dashboard updates within 1 minute                           |
|  * Durability: zero event loss after acknowledgment                     |
|  * Scalable: handle 10x traffic spikes (viral ads, Black Friday)        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3: BACK-OF-ENVELOPE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TRAFFIC ESTIMATES:                                                     |
|                                                                         |
|  Clicks:                                                                |
|    * Average: 10,000 clicks/sec                                         |
|    * Peak (2-3x): ~30,000 clicks/sec                                    |
|    * Daily: 10K * 86,400 = ~860M clicks/day                             |
|                                                                         |
|  Impressions:                                                           |
|    * Average: 100,000 impressions/sec                                   |
|    * Peak: ~300,000 impressions/sec                                     |
|    * Daily: 100K * 86,400 = ~8.6B impressions/day                       |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  STORAGE ESTIMATES:                                                     |
|                                                                         |
|  Raw click event size: ~500 bytes                                       |
|    (ad_id, user_id, timestamp, ip, user_agent, referrer, geo, etc.)     |
|                                                                         |
|  Raw event storage per day:                                             |
|    Clicks:      860M * 500B = ~430 GB/day                               |
|    Impressions: 8.6B * 300B = ~2.6 TB/day                               |
|    Total raw:   ~3 TB/day > ~1.1 PB/year                                |
|                                                                         |
|  Aggregated storage (much smaller):                                     |
|    1M unique ads * 1440 minutes * 100B = ~144 GB/day                    |
|    With dimensions: ~500 GB/day aggregated                              |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  AGGREGATION WINDOWS:                                                   |
|                                                                         |
|    1-minute granularity > 1,440 buckets/day per ad                      |
|    1-hour granularity   > 24 buckets/day per ad                         |
|    1-day granularity    > 1 bucket/day per ad                           |
|                                                                         |
|    Keep minute-level for 7 days, hour-level for 90 days,                |
|    day-level indefinitely. Roll up older data.                          |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  KAFKA SIZING:                                                          |
|                                                                         |
|    110K events/sec * 500B avg = ~55 MB/sec ingestion                    |
|    With 3x replication: ~165 MB/sec disk write                          |
|    Partitions: at least 100 (for parallelism)                           |
|    Retention: 7 days > ~21 TB per topic                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

```
+---------------------------------------------------------------------------+
|                                                                           |
|  AD CLICK AGGREGATION ARCHITECTURE                                        |
|                                                                           |
|  +--------+    +---------------+    +------------------+                  |
|  | User   | -> | Click Tracker | -> | Message Queue    |                  |
|  | clicks |    | (API endpoint)|    | (Kafka)          |                  |
|  | ad     |    | - validate    |    | - raw events     |                  |
|  +--------+    | - dedup       |    | - partitioned    |                  |
|                | - enrich geo  |    |   by ad_id       |                  |
|                +---------------+    +--------+---------+                  |
|                                              |                            |
|                          +-------------------+-------------------+        |
|                          |                                       |        |
|                          v                                       v        |
|                  +----------------+                    +--------------+   |
|                  | Stream         |                    | Fraud        |   |
|                  | Processor      |                    | Detection    |   |
|                  | (Flink)        |                    | Engine       |   |
|                  | - window agg   |                    | - real-time  |   |
|                  | - multi-dim    |                    |   scoring    |   |
|                  +-------+--------+                    +------+-------+   |
|                          |                                    |           |
|                          v                                    v           |
|                  +----------------+                    +--------------+   |
|                  | Aggregation DB |                    | Fraud        |   |
|                  | (ClickHouse /  |                    | Flagging DB  |   |
|                  |  Apache Druid) |                    +--------------+   |
|                  +-------+--------+                                       |
|                          |                                                |
|                          v                                                |
|                  +----------------+    +------------------+               |
|                  | Query Service  | -> | Real-Time        |               |
|                  | (API)          |    | Dashboard        |               |
|                  | - rollups      |    | (advertiser UI)  |               |
|                  | - drill-down   |    +------------------+               |
|                  +----------------+                                       |
|                          |                                                |
|                          v                                                |
|                  +----------------+                                       |
|                  | Billing        |                                       |
|                  | Service        |                                       |
|                  | (verified      |                                       |
|                  |  counts)       |                                       |
|                  +----------------+                                       |
|                                                                           |
+---------------------------------------------------------------------------+
```

## SECTION 5: DATA COLLECTION - CLICK EVENT SCHEMA & TRACKING

```
+--------------------------------------------------------------------------+
|                                                                          |
|  CLICK EVENT SCHEMA:                                                     |
|                                                                          |
|  {                                                                       |
|    "click_id":     "uuid-v4"        // unique, for dedup                 |
|    "event_type":   "click|impression"                                    |
|    "ad_id":        "ad_12345"       // which ad                          |
|    "campaign_id":  "camp_678"       // parent campaign                   |
|    "advertiser_id":"adv_99"         // who pays                          |
|    "user_id":      "user_abc"       // hashed/anonymized                 |
|    "timestamp":    1700000000000    // event time (ms)                   |
|    "ip":           "203.0.113.42"   // for geo + fraud                   |
|    "user_agent":   "Mozilla/5.0..." // device/browser info               |
|    "referrer":     "https://..."    // page where ad shown               |
|    "placement_id": "slot_top_banner"// where on the page                 |
|    "geo":          {"country":"US","region":"CA","city":"SF"}            |
|    "device_type":  "mobile|desktop|tablet"                               |
|  }                                                                       |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  CLICK TRACKING METHODS:                                                 |
|                                                                          |
|  METHOD 1: REDIRECT (most common for clicks)                             |
|  +-----------+   +----------------+   +----------------+                 |
|  | User      | > | Ad Platform    | > | Advertiser's   |                 |
|  | clicks ad |   | click tracker  |   | landing page   |                 |
|  +-----------+   | /track?ad=123  |   +----------------+                 |
|                  | logs event,    |                                      |
|                  | 302 redirect   |                                      |
|                  +----------------+                                      |
|                                                                          |
|  Pros: reliable, captures all clicks                                     |
|  Cons: adds ~50ms latency to redirect                                    |
|                                                                          |
|  METHOD 2: TRACKING PIXEL (for impressions)                              |
|  +-----------+   +----------------+                                      |
|  | Page      | > | <img src=      |                                      |
|  | renders   |   |  "/pixel?      |                                      |
|  | ad        |   |   ad=123" />   |                                      |
|  +-----------+   +----------------+                                      |
|                                                                          |
|  1x1 transparent GIF/PNG loaded when ad is displayed.                    |
|  Server logs the impression event on image request.                      |
|  Pros: no user interaction needed, fire-and-forget                       |
|  Cons: ad blockers can block, no JS context                              |
|                                                                          |
|  METHOD 3: JAVASCRIPT BEACON (most flexible)                             |
|  +-----------+   +-------------------+                                   |
|  | Ad JS     | > | navigator.sendBeacon(                                 |
|  | code      |   |   "/track",       |                                   |
|  | executes  |   |   eventPayload    |                                   |
|  +-----------+   | )                 |                                   |
|                  +-------------------+                                   |
|                                                                          |
|  Pros: rich data (viewability, scroll, hover time)                       |
|  Cons: requires JS execution, can be blocked                             |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  DEDUPLICATION AT INGESTION:                                             |
|                                                                          |
|  Problem: user double-clicks, retries, network duplicates                |
|                                                                          |
|  Solution: click_id + TTL-based dedup set                                |
|                                                                          |
|  +-------------+    +------------------+    +-----------------+          |
|  | Click event | -> | Check click_id   | -> | Already seen?   |          |
|  | arrives     |    | in Redis/Bloom   |    | YES: discard    |          |
|  +-------------+    | filter           |    | NO: accept,     |          |
|                     +------------------+    |     add to set  |          |
|                                             +-----------------+          |
|                                                                          |
|  Redis SET with TTL (e.g., 5 minutes):                                   |
|    SETNX click_id:uuid-v4 1 EX 300                                       |
|    * If key exists > duplicate, drop                                     |
|    * If key new > first time, process                                    |
|                                                                          |
|  Alternative: Bloom filter for memory efficiency                         |
|    * 1 billion events, 0.1% FP rate ~ 1.2 GB                             |
|    * Rotate bloom filter every few minutes                               |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 6: STREAM PROCESSING - KAFKA + FLINK

```
+--------------------------------------------------------------------------+
|                                                                          |
|  KAFKA AS THE EVENT BUS:                                                 |
|                                                                          |
|  +----------+   +----------+   +----------+                              |
|  | Tracker  |   | Tracker  |   | Tracker  |                              |
|  | Server 1 |   | Server 2 |   | Server N |                              |
|  +----+-----+   +----+-----+   +----+-----+                              |
|       |              |              |                                    |
|       v              v              v                                    |
|  +--------------------------------------------------+                    |
|  |              KAFKA CLUSTER                        |                   |
|  |                                                   |                   |
|  |  Topic: ad-clicks                                 |                   |
|  |  +------+ +------+ +------+ +------+ +------+    |                    |
|  |  | P0   | | P1   | | P2   | | P3   | | P4   |   |                     |
|  |  |ad 0-9| |10-19 | |20-29 | |30-39 | |40-49 |   |                     |
|  |  +------+ +------+ +------+ +------+ +------+    |                    |
|  |                                                   |                   |
|  |  Partitioned by: hash(ad_id) % num_partitions     |                   |
|  |  Ensures all events for an ad go to same partition |                  |
|  |  > ordered processing per ad                      |                   |
|  |                                                   |                   |
|  +--------------------------------------------------+                    |
|       |              |              |                                    |
|       v              v              v                                    |
|  +----------+   +----------+   +----------+                              |
|  | Flink    |   | Flink    |   | Flink    |                              |
|  | Task 0   |   | Task 1   |   | Task N   |                              |
|  +----------+   +----------+   +----------+                              |
|                                                                          |
|  WHY KAFKA?                                                              |
|  * Durable: events persisted to disk, replicated                         |
|  * Replayable: reprocess from any offset on failure                      |
|  * High throughput: 100K+ messages/sec per broker                        |
|  * Decouples ingestion from processing                                   |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  FLINK/SPARK STREAMING FOR AGGREGATION:                                  |
|                                                                          |
|  Events --> [Window] --> [Aggregate] --> [Sink to DB]                    |
|                                                                          |
|  WINDOWING STRATEGIES:                                                   |
|                                                                          |
|  1. TUMBLING WINDOW (fixed, non-overlapping)                             |
|     +--------+--------+--------+--------+                                |
|     | 0-1min | 1-2min | 2-3min | 3-4min |                                |
|     +--------+--------+--------+--------+                                |
|     Each event belongs to exactly ONE window.                            |
|     Best for: per-minute counts, billing aggregation                     |
|                                                                          |
|  2. SLIDING WINDOW (overlapping)                                         |
|     +-----------+                                                        |
|     |  0 - 5min |                                                        |
|     +-----------+                                                        |
|        +-----------+                                                     |
|        |  1 - 6min |                                                     |
|        +-----------+                                                     |
|           +-----------+                                                  |
|           |  2 - 7min |                                                  |
|           +-----------+                                                  |
|     Window size=5min, slide=1min.                                        |
|     Events may belong to multiple windows.                               |
|     Best for: "clicks in last 5 minutes" real-time dashboard             |
|                                                                          |
|  3. SESSION WINDOW (gap-based)                                           |
|     +---+     +------+  +--+        +----+                               |
|     | e | gap | e  e |  |e | gap    | e  |                               |
|     +---+     +------+  +--+        +----+                               |
|     Session closes after inactivity gap (e.g., 30 sec).                  |
|     Best for: user session click analysis                                |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  WATERMARKS FOR LATE DATA:                                               |
|                                                                          |
|  Problem: events arrive out of order due to network delays               |
|                                                                          |
|     Event time:    10:00:01  10:00:03  10:00:02  10:00:05                |
|     Arrival time:  10:00:02  10:00:04  10:00:06  10:00:06                |
|                                              ^                           |
|                                          late event!                     |
|                                                                          |
|  Watermark = "I believe all events up to time T have arrived"            |
|                                                                          |
|  Watermark = max_event_time - allowed_lateness                           |
|  Example: allowed_lateness = 2 minutes                                   |
|    * If current max event time = 10:05                                   |
|    * Watermark = 10:03                                                   |
|    * Window [10:00-10:01] can fire (all events assumed arrived)          |
|    * Events with time < watermark are "late"                             |
|      > route to a side output for late processing                        |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  EXACTLY-ONCE SEMANTICS:                                                 |
|                                                                          |
|  The billing pipeline REQUIRES exactly-once counting.                    |
|                                                                          |
|  THREE COMPONENTS:                                                       |
|                                                                          |
|  1. Kafka Transactions (idempotent producer + transactional consume)     |
|     * Producer writes with idempotency key > no dupes on retry           |
|     * Consumer commits offset + output atomically                        |
|                                                                          |
|  2. Flink Checkpointing (Chandy-Lamport algorithm)                       |
|     * Periodic snapshots of operator state + Kafka offsets               |
|     * On failure: restore from last checkpoint, replay from offset       |
|     * State and offset are consistent > no double-count                  |
|                                                                          |
|  3. Idempotent Sink                                                      |
|     * Write aggregation results with a unique (window, key) ID           |
|     * UPSERT into DB: if same key exists, overwrite (not add)            |
|     * Re-execution produces identical result                             |
|                                                                          |
|  End-to-end exactly-once:                                                |
|  Kafka idempotent producer > Flink checkpointing > idempotent sink       |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 7: AGGREGATION - MULTI-DIMENSIONAL COUNTING

```
+--------------------------------------------------------------------------+
|                                                                          |
|  PRE-AGGREGATION STRATEGY:                                               |
|                                                                          |
|  Raw events are pre-aggregated into summary tables:                      |
|                                                                          |
|  MINUTE-LEVEL (kept 7 days):                                             |
|  +--------+----------+-----------+------+--------+-------+--------+      |
|  | ad_id  | campaign | advertiser| geo  | device | minute| clicks   |    |
|  +--------+----------+-----------+------+--------+-------+--------+      |
|  | ad_123 | camp_1   | adv_5     | US   | mobile | 10:01 | 47       |    |
|  | ad_123 | camp_1   | adv_5     | US   | desktop| 10:01 | 23       |    |
|  | ad_456 | camp_2   | adv_5     | UK   | mobile | 10:01 | 12       |    |
|  +--------+----------+-----------+------+--------+-------+--------+      |
|                                                                          |
|  HOUR-LEVEL (rolled up, kept 90 days):                                   |
|  +--------+----------+-----------+------+--------+------+--------+       |
|  | ad_id  | campaign | advertiser| geo  | device | hour | clicks |       |
|  +--------+----------+-----------+------+--------+------+--------+       |
|  | ad_123 | camp_1   | adv_5     | US   | mobile | 10:00| 2,841  |       |
|  +--------+----------+-----------+------+--------+------+--------+       |
|                                                                          |
|  DAY-LEVEL (rolled up, kept indefinitely):                               |
|  +--------+----------+-----------+------+--------+------+--------+       |
|  | ad_id  | campaign | advertiser| geo  | device | date | clicks |       |
|  +--------+----------+-----------+------+--------+------+--------+       |
|  | ad_123 | camp_1   | adv_5     | US   | mobile | Dec1 | 68,184 |       |
|  +--------+----------+-----------+------+--------+------+--------+       |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  MULTI-DIMENSIONAL AGGREGATION:                                          |
|                                                                          |
|  Dimensions:   ad_id, campaign_id, advertiser_id, geo, device_type       |
|  Measures:     click_count, impression_count, spend                      |
|                                                                          |
|  Query examples:                                                         |
|    "Total clicks for campaign X in last 24 hours"                        |
|    "Clicks by country for advertiser Y today"                            |
|    "CTR (click/impression) by device type for ad Z"                      |
|                                                                          |
|  MapReduce Pattern in Stream Processing:                                 |
|                                                                          |
|  MAP PHASE:                                                              |
|    Input event > emit (key, 1)                                           |
|    key = (ad_id, minute_bucket)                                          |
|                                                                          |
|  REDUCE PHASE:                                                           |
|    Sum all values for same key                                           |
|    (ad_123, 10:01) > 47 clicks                                           |
|                                                                          |
|  Incremental aggregation: maintain running count in state                |
|    event arrives > state[key] += 1                                       |
|    window fires > emit state[key], reset                                 |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  LAMBDA vs KAPPA ARCHITECTURE:                                           |
|                                                                          |
|  LAMBDA ARCHITECTURE:                                                    |
|                                                                          |
|              +---> [Batch Layer] ---> Batch Views ---+                   |
|              |     (MapReduce on                     |                   |
|  Raw Events -+      full dataset)                    +--> Serving Layer  |
|              |                                       |                   |
|              +---> [Speed Layer] ---> Real-time  ----+                   |
|                    (Flink on live                                        |
|                     stream)                                              |
|                                                                          |
|  * Batch layer: ground truth, recomputes everything periodically         |
|  * Speed layer: approximate real-time counts                             |
|  * Serving layer merges both views                                       |
|  * Pro: batch corrects any stream errors                                 |
|  * Con: maintaining two codepaths is complex                             |
|                                                                          |
|  KAPPA ARCHITECTURE (preferred for this system):                         |
|                                                                          |
|  Raw Events ---> [Stream Layer] ---> Real-time Views                     |
|                  (Flink only)                                            |
|                                                                          |
|  * Single codebase for all processing                                    |
|  * Reprocess by replaying Kafka from beginning                           |
|  * Simpler to maintain and reason about                                  |
|  * Requires Kafka to retain long enough for replay                       |
|                                                                          |
|  BATCH RECONCILIATION (regardless of architecture):                      |
|  * Nightly job compares stream counts vs raw event count                 |
|  * Discrepancies flagged and corrected for billing                       |
|  * Provides confidence in billing accuracy                               |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 8: FRAUD DETECTION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CLICK FRAUD TYPES:                                                     |
|                                                                         |
|  1. BOT CLICKS                                                          |
|     * Automated scripts clicking ads repeatedly                         |
|     * Headless browsers with fake user agents                           |
|     * Sophisticated bots that mimic human behavior                      |
|                                                                         |
|  2. CLICK FARMS                                                         |
|     * Warehouses of low-paid workers clicking ads                       |
|     * Same IP range, similar patterns                                   |
|     * Real devices but non-genuine intent                               |
|                                                                         |
|  3. COMPETITOR CLICKS                                                   |
|     * Competitors clicking rival ads to drain budget                    |
|     * Hard to distinguish from real clicks                              |
|     * Often use VPNs/proxies to hide identity                           |
|                                                                         |
|  4. PUBLISHER FRAUD                                                     |
|     * Publishers clicking their own ads for revenue                     |
|     * Incentivized clicks ("click this ad to continue")                 |
|     * Ad stacking (multiple ads behind one visible ad)                  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  DETECTION SIGNALS:                                                     |
|                                                                         |
|  +-----------------------+------------------------------------------+   |
|  | Signal                | Detection Method                         |   |
|  +-----------------------+------------------------------------------+   |
|  | Click Velocity        | >N clicks per IP per ad in T seconds     |   |
|  | IP Patterns           | Known datacenter IPs, Tor exit nodes     |   |
|  | User Agent Anomalies  | Missing/malformed UA, headless browser   |   |
|  | Click-to-Conversion   | High clicks, zero conversions = fraud    |   |
|  | Session Behavior      | No mouse movement, instant click         |   |
|  | Geographic Anomaly    | IP in US, timezone in Asia               |   |
|  | Device Fingerprint    | Same canvas hash across "different" users|   |
|  | Click Timing          | Perfectly periodic clicks = bot          |   |
|  +-----------------------+------------------------------------------+   |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  FRAUD DETECTION PIPELINE:                                              |
|                                                                         |
|  +----------+    +-----------+    +------------+    +------------+      |
|  | Raw      | -> | Real-Time | -> | Score      | -> | Flag or    |      |
|  | Click    |    | Rules     |    | Aggregator |    | Allow      |      |
|  | Event    |    | Engine    |    | (ML model) |    |            |      |
|  +----------+    +-----------+    +------------+    +------+-----+      |
|                                                            |            |
|                                          +-----------------+-------+    |
|                                          |                         |    |
|                                          v                         v    |
|                                   +-----------+            +----------+ |
|                                   | Valid     |            | Flagged  | |
|                                   | Events    |            | Events   | |
|                                   | (billing) |            | (review) | |
|                                   +-----------+            +----------+ |
|                                                                         |
|  REAL-TIME LAYER:                                                       |
|  * Rule-based: IP velocity, known bot lists, UA filtering               |
|  * Fast (< 10ms per event), catches obvious fraud                       |
|                                                                         |
|  BATCH ANALYSIS LAYER:                                                  |
|  * ML models: gradient boosted trees, neural networks                   |
|  * Analyzes patterns across hours/days                                  |
|  * Catches sophisticated fraud (click farms, coordinated bots)          |
|  * Retroactively flags clicks for billing adjustment                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: STORAGE DESIGN

```
+--------------------------------------------------------------------------+
|                                                                          |
|  THREE-TIER STORAGE ARCHITECTURE:                                        |
|                                                                          |
|  +--------------------+                                                  |
|  |   HOT STORAGE      |  Recent data (last 24-48 hours)                  |
|  |   ClickHouse /     |  - In-memory + SSD                               |
|  |   Apache Druid     |  - Sub-second query latency                      |
|  |                    |  - Powers real-time dashboard                    |
|  +--------+-----------+                                                  |
|           |                                                              |
|           | (age out after 48 hours)                                     |
|           v                                                              |
|  +--------------------+                                                  |
|  |   WARM STORAGE     |  Recent historical (7 days - 90 days)            |
|  |   ClickHouse /     |  - SSD / HDD                                     |
|  |   Druid historical |  - Query in seconds                              |
|  |                    |  - Hour-level aggregations                       |
|  +--------+-----------+                                                  |
|           |                                                              |
|           | (age out after 90 days)                                      |
|           v                                                              |
|  +--------------------+                                                  |
|  |   COLD STORAGE     |  Long-term archive (years)                       |
|  |   S3 / HDFS        |  - Day-level aggregations                        |
|  |   (Parquet files)  |  - Query in minutes (Spark/Presto)               |
|  |                    |  - Cheapest storage tier                         |
|  +--------------------+                                                  |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  RAW EVENT STORAGE:                                                      |
|                                                                          |
|  Raw events stored as append-only log for:                               |
|  * Audit trail (billing disputes)                                        |
|  * Reprocessing (fix bugs, recompute aggregations)                       |
|  * Compliance (data retention requirements)                              |
|                                                                          |
|  Format: Parquet on S3/HDFS                                              |
|  Partitioned by: date / hour / ad_id_prefix                              |
|                                                                          |
|  s3://raw-events/                                                        |
|    year=2024/                                                            |
|      month=12/                                                           |
|        day=01/                                                           |
|          hour=10/                                                        |
|            part-00001.parquet                                            |
|            part-00002.parquet                                            |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  OLAP DATABASE (ClickHouse) FOR AGGREGATED DATA:                         |
|                                                                          |
|  WHY CLICKHOUSE:                                                         |
|  * Column-oriented: fast aggregation queries (SUM, COUNT, GROUP BY)      |
|  * Vectorized execution: processes columns in batches                    |
|  * Compression: 10-40x on columnar data                                  |
|  * MergeTree engine: excellent for time-series insert + query            |
|                                                                          |
|  Table: ad_click_aggregations                                            |
|  ENGINE = MergeTree()                                                    |
|  PARTITION BY toYYYYMM(event_date)                                       |
|  ORDER BY (ad_id, campaign_id, event_date, event_hour)                   |
|                                                                          |
|  TIME-BASED PARTITIONING:                                                |
|  * Monthly partitions: easy to drop old data                             |
|  * Each partition is a separate directory on disk                        |
|  * Queries with date filters skip irrelevant partitions                  |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 10: QUERY & REPORTING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUERY SERVICE ARCHITECTURE:                                            |
|                                                                         |
|  +------------------+                                                   |
|  | Advertiser       |                                                   |
|  | Dashboard UI     |                                                   |
|  +--------+---------+                                                   |
|           |                                                             |
|           v                                                             |
|  +------------------+    +-----------------+                            |
|  | Query Service    | -> | Cache Layer     |                            |
|  | (REST API)       |    | (Redis)         |                            |
|  |                  |    | - Popular       |                            |
|  | /api/v1/stats    |    |   queries       |                            |
|  | ?ad_id=123       |    | - Dashboard     |                            |
|  | &from=2024-12-01 |    |   rollups       |                            |
|  | &to=2024-12-07   |    | - TTL: 60 sec   |                            |
|  | &group_by=day    |    +-----------------+                            |
|  +--------+---------+         |                                         |
|           |               cache miss                                    |
|           v                   |                                         |
|  +------------------+         |                                         |
|  | Query Router     | <------+                                          |
|  | - last 48h > hot |                                                   |
|  | - 7-90d > warm   |                                                   |
|  | - >90d > cold    |                                                   |
|  +--------+---------+                                                   |
|           |                                                             |
|    +------+------+------+                                               |
|    v             v      v                                               |
|  +-------+  +-------+  +-------+                                        |
|  | Hot   |  | Warm  |  | Cold  |                                        |
|  | (CH)  |  | (CH)  |  | (S3)  |                                        |
|  +-------+  +-------+  +-------+                                        |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  PRE-COMPUTED ROLLUPS:                                                  |
|                                                                         |
|  Materialized views in ClickHouse compute rollups automatically:        |
|                                                                         |
|  Base table (minute-level) > MV: hourly rollup                          |
|                             > MV: daily rollup                          |
|                             > MV: campaign-level daily summary          |
|                             > MV: advertiser-level daily summary        |
|                                                                         |
|  Dashboard loads campaign summary > hits pre-computed MV                |
|  User drills into ad-level > queries minute-level base table            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  REPORTING TIERS:                                                       |
|                                                                         |
|  +------------------+------------------+-------------------+            |
|  | REAL-TIME        | NEAR-REAL-TIME   | BATCH             |            |
|  | (<1 min delay)   | (1-15 min delay) | (hours delay)     |            |
|  +------------------+------------------+-------------------+            |
|  | Live dashboard   | Email reports    | Monthly invoices   |           |
|  | Fraud alerts     | Hourly summaries | Billing reconcile  |           |
|  | Budget pacing    | Trend analysis   | Audit reports      |           |
|  +------------------+------------------+-------------------+            |
|  | Stream           | Stream + cache   | Batch on S3        |           |
|  | processing       | refresh          | (Spark/Presto)     |           |
|  +------------------+------------------+-------------------+            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11: SCALING

```
+--------------------------------------------------------------------------+
|                                                                          |
|  SCALING EACH COMPONENT:                                                 |
|                                                                          |
|  1. CLICK TRACKING LAYER                                                 |
|  -------------------------------------------------------------------     |
|  * Stateless HTTP endpoints behind a load balancer                       |
|  * Auto-scale horizontally (add more tracker pods)                       |
|  * Multi-region: deploy trackers in every major region                   |
|    US-EAST, US-WEST, EU, APAC                                            |
|  * CDN edge for redirect latency optimization                            |
|  * Each region writes to local Kafka cluster                             |
|                                                                          |
|  2. KAFKA PARTITIONING                                                   |
|  -------------------------------------------------------------------     |
|                                                                          |
|  Partition by: hash(ad_id) % num_partitions                              |
|                                                                          |
|  WHY ad_id?                                                              |
|  * All events for same ad land in same partition                         |
|  * Enables per-ad ordered processing                                     |
|  * Flink can aggregate per-ad without cross-partition shuffle            |
|                                                                          |
|  Partition count: start with 100+                                        |
|  * More partitions = more parallelism for Flink                          |
|  * Kafka handles millions of partitions across cluster                   |
|                                                                          |
|  Hot-ad problem: one viral ad gets disproportionate traffic              |
|  * Solution: sub-partition hot ads by (ad_id, shard_key)                 |
|  * Or: route hot ads to dedicated Flink task managers                    |
|                                                                          |
|  3. FLINK PARALLELISM                                                    |
|  -------------------------------------------------------------------     |
|  * Flink parallelism matches Kafka partition count                       |
|  * Each Flink task consumes 1+ Kafka partitions                          |
|  * State is checkpointed to S3/HDFS every 30 seconds                     |
|  * On failure: Flink restarts from last checkpoint + Kafka offset        |
|  * Scaling up: increase partitions + Flink task slots                    |
|                                                                          |
|  4. CLICKHOUSE SHARDING                                                  |
|  -------------------------------------------------------------------     |
|                                                                          |
|  +------------+    +------------+    +------------+                      |
|  | Shard 1    |    | Shard 2    |    | Shard 3    |                      |
|  | ad_id 0-99 |    | ad_id      |    | ad_id      |                      |
|  | Replica A  |    | 100-199    |    | 200-299    |                      |
|  | Replica B  |    | Replica A  |    | Replica A  |                      |
|  +------------+    | Replica B  |    | Replica B  |                      |
|                    +------------+    +------------+                      |
|                                                                          |
|  * Shard by ad_id range or hash                                          |
|  * 2 replicas per shard for HA                                           |
|  * Distributed table for cross-shard queries                             |
|  * ZooKeeper coordinates replication                                     |
|                                                                          |
|  5. MULTI-REGION EVENT COLLECTION                                        |
|  -------------------------------------------------------------------     |
|                                                                          |
|  +----------+       +----------+       +----------+                      |
|  | US-East  |       | EU-West  |       | APAC     |                      |
|  | Trackers | ----> | Trackers | ----> | Trackers |                      |
|  | + Kafka  |       | + Kafka  |       | + Kafka  |                      |
|  +----+-----+       +----+-----+       +----+-----+                      |
|       |                  |                  |                            |
|       v                  v                  v                            |
|  +--------------------------------------------------+                    |
|  |  MirrorMaker 2 / Confluent Replicator             |                   |
|  |  (cross-region Kafka replication)                 |                   |
|  +--------------------------------------------------+                    |
|       |                                                                  |
|       v                                                                  |
|  +--------------------------------------------------+                    |
|  |  Central Processing Cluster                       |                   |
|  |  - Flink aggregation                              |                   |
|  |  - ClickHouse storage                             |                   |
|  |  - Global dashboard serving                       |                   |
|  +--------------------------------------------------+                    |
|                                                                          |
|  Collect locally, process centrally.                                     |
|  Low latency for click capture, global view for analytics.               |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 12: INTERVIEW Q&A

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q1: Why not just use a database counter (UPDATE clicks = clicks + 1)?  |
|  -------------------------------------------------------------------    |
|  A: At 10K clicks/sec, a single DB row becomes a contention hotspot.    |
|  Lock contention kills throughput. Instead, we buffer events in Kafka   |
|  and aggregate in-memory using Flink windowed counts. The DB only sees  |
|  pre-aggregated writes (1 write/minute per ad vs 10K writes/sec).       |
|  This reduces DB write load by ~600,000x.                               |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q2: How do you ensure exactly-once counting for billing?               |
|  -------------------------------------------------------------------    |
|  A: Three-part guarantee:                                               |
|  1. Kafka idempotent producer (dedup on producer retries)               |
|  2. Flink checkpointing (snapshot state + Kafka offset atomically)      |
|  3. Idempotent sink (UPSERT with window+key as primary key)             |
|  On failure, Flink restores checkpoint and replays from Kafka offset.   |
|  Re-execution produces identical aggregation result. Plus, a nightly    |
|  batch reconciliation job compares stream counts vs raw event count.    |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q3: What happens when a Flink node crashes mid-window?                 |
|  -------------------------------------------------------------------    |
|  A: Flink's checkpoint mechanism saves operator state and Kafka         |
|  consumer offsets to durable storage (S3) every 30 seconds.             |
|  On crash: a new task manager picks up the failed task, restores        |
|  from the last checkpoint, and re-consumes Kafka from the saved         |
|  offset. The tumbling window state is restored, and counting            |
|  continues without loss or duplication.                                 |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q4: How do you handle late-arriving events (e.g., mobile batch)?       |
|  -------------------------------------------------------------------    |
|  A: Flink watermarks define when a window can close. We set allowed     |
|  lateness to 2 minutes - events arriving within 2 minutes after the     |
|  window closes trigger an updated aggregation (fired again). Events     |
|  arriving later than 2 minutes go to a side output, processed by a      |
|  separate "late event reconciler" that adjusts past aggregations.       |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q5: Why ClickHouse over a traditional RDBMS like PostgreSQL?           |
|  -------------------------------------------------------------------    |
|  A: ClickHouse is columnar - aggregation queries (SUM, COUNT,           |
|  GROUP BY) scan only relevant columns, not entire rows. At our          |
|  scale (billions of rows), this is 10-100x faster than row-based DB.    |
|  ClickHouse also compresses columnar data 10-40x, and its MergeTree     |
|  engine is designed for high-throughput append + analytical read.       |
|  PostgreSQL would work at small scale but not at billions of events.    |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q6: How does fraud detection affect the billing pipeline?              |
|  -------------------------------------------------------------------    |
|  A: We run two fraud pipelines:                                         |
|  1. Real-time rules engine: flags obvious fraud (IP velocity, bots)     |
|     and removes them BEFORE counting for billing.                       |
|  2. Batch ML pipeline: detects sophisticated fraud retroactively.       |
|     Flagged clicks are deducted from billing in the next cycle.         |
|  Flagged events are never deleted - stored for audit and dispute.       |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q7: Lambda vs Kappa - which would you choose and why?                  |
|  -------------------------------------------------------------------    |
|  A: Kappa (stream-only) for this system. Reasons:                       |
|  1. Single codebase - less operational burden                           |
|  2. Kafka can retain events for days/weeks for replay                   |
|  3. Flink exactly-once semantics are mature enough                      |
|  4. Add a nightly batch reconciliation job for billing accuracy -       |
|     this gives the correctness benefit of Lambda without the full       |
|     complexity of maintaining two parallel codepaths.                   |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q8: How do you handle a "hot ad" that gets 10x traffic?                |
|  -------------------------------------------------------------------    |
|  A: A viral ad creates a hot Kafka partition (all events for that       |
|  ad_id land on one partition). Solutions:                               |
|  1. Sub-partition: use (ad_id, random_salt) as key - spreads load       |
|     across partitions. Flink performs a second aggregation pass to      |
|     combine sub-partitions.                                             |
|  2. Dedicated resources: route known hot ads to separate Flink task     |
|     managers with more CPU/memory.                                      |
|  3. Pre-aggregation in tracker: batch 100 events into 1 Kafka           |
|     message with a local counter.                                       |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q9: How would you migrate from Lambda to Kappa architecture?           |
|  -------------------------------------------------------------------    |
|  A: Phased approach:                                                    |
|  1. Run Kappa pipeline in parallel with existing Lambda                 |
|  2. Compare outputs (shadow mode) for correctness                       |
|  3. Gradually shift dashboard reads from batch views to stream views    |
|  4. Keep batch reconciliation job as a safety net                       |
|  5. Decommission batch layer once confidence is high                    |
|  Key: never big-bang migrate - always shadow + compare first.           |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q10: What metrics would you monitor for this system?                   |
|  -------------------------------------------------------------------    |
|  A: Critical metrics:                                                   |
|  * Event ingestion rate vs expected baseline (detect drops)             |
|  * Kafka consumer lag (if Flink falls behind, dashboard is stale)       |
|  * Flink checkpoint duration and failure rate                           |
|  * End-to-end latency: event time > dashboard visible                   |
|  * ClickHouse query p99 latency                                         |
|  * Fraud flagging rate (sudden spike = new attack or false positives)   |
|  * Reconciliation delta (stream count vs batch count)                   |
|  Alert on: consumer lag > 2 min, checkpoint failures, ingestion drop.   |
|                                                                         |
+-------------------------------------------------------------------------+
```
