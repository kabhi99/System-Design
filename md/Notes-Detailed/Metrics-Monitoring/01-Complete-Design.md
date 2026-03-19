# DESIGN A METRICS MONITORING & ALERTING SYSTEM (PROMETHEUS / DATADOG STYLE)

*Complete Design: Requirements, Architecture, and Interview Guide*

## SECTION 1: UNDERSTANDING THE PROBLEM

Modern distributed systems consist of hundreds or thousands of microservices
running across multiple datacenters. Without monitoring, you're flying blind -
you won't know about failures until users complain.

### WHY MONITORING MATTERS

```
  +-----------------------------------------------------------------+
  |                  Without Monitoring                             |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  User complaint > Engineer investigates > SSH into servers >    |
  |  grep through logs > find the issue > 2 hours later             |
  |                                                                 |
  |                  With Monitoring                                |
  |                                                                 |
  |  Metric spike detected > Alert fires > Engineer checks          |
  |  dashboard > identifies root cause > 5 minutes later            |
  |                                                                 |
  |  Monitoring reduces MTTR (Mean Time To Recovery) from           |
  |  hours to minutes.                                              |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### WHAT ARE METRICS?

Metrics are numeric measurements collected at regular intervals. They describe
the health and behavior of a system over time.

```
  +-----------------------------------------------------------------+
  |                     Metric Types                                |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  COUNTER                                                        |
  |    Monotonically increasing value. Only goes up (or resets).    |
  |    Examples: total HTTP requests, errors, bytes sent            |
  |    Usage: rate(http_requests_total[5m]) > requests/sec          |
  |                                                                 |
  |    Value                                                        |
  |    ^                                                            |
  |    |              .-----------                                  |
  |    |         .----'                                             |
  |    |    .---'                                                   |
  |    |.--'                                                        |
  |    +-----------------------------> Time                         |
  |                                                                 |
  |  GAUGE                                                          |
  |    Value that goes up and down. A snapshot in time.             |
  |    Examples: CPU usage, memory usage, queue depth, temperature  |
  |                                                                 |
  |    Value                                                        |
  |    ^     .                                                      |
  |    |    / \    .-.                                              |
  |    |   /   \  / . \   .                                         |
  |    |  /     \/     '-'                                          |
  |    | /                                                          |
  |    +-----------------------------> Time                         |
  |                                                                 |
  |  HISTOGRAM                                                      |
  |    Samples observations and counts them in configurable         |
  |    buckets. Used for latency distributions, request sizes.      |
  |    Examples: request duration (p50, p95, p99)                   |
  |                                                                 |
  |    Count                                                        |
  |    ^                                                            |
  |    |  |||                                                       |
  |    |  |||||                                                     |
  |    |  |||||||                                                   |
  |    |  |||||||||                                                 |
  |    +--+-+-+-+-+-+-+----> Latency (ms)                           |
  |       10 25 50 100 250                                          |
  |                                                                 |
  |  SUMMARY                                                        |
  |    Like histogram but calculates quantiles client-side.         |
  |    Pre-computes p50, p90, p99 on the application itself.        |
  |    Pros: accurate quantiles. Cons: can't aggregate across       |
  |    instances (you can't average percentiles).                   |
  |                                                                 |
  +-----------------------------------------------------------------+
```

## SECTION 2: REQUIREMENTS

### FUNCTIONAL REQUIREMENTS

```
  +------------------------------------------------------------+
  |                  Functional Requirements                   |
  +------------------------------------------------------------+
  |                                                            |
  |  F1. Collect metrics from thousands of services            |
  |  F2. Store time-series data efficiently                    |
  |  F3. Query metrics with flexible aggregation               |
  |  F4. Visualize metrics on dashboards (graphs, tables)      |
  |  F5. Define alerting rules on metric thresholds            |
  |  F6. Send notifications (email, Slack, PagerDuty)          |
  |  F7. Support labels/tags for dimensional queries           |
  |      (e.g., http_requests{method="GET", status="500"})     |
  |                                                            |
  +------------------------------------------------------------+
```

### NON-FUNCTIONAL REQUIREMENTS

```
  +------------------------------------------------------------+
  |                Non-Functional Requirements                 |
  +------------------------------------------------------------+
  |                                                            |
  |  NF1. Handle millions of active time series                |
  |  NF2. Write throughput: millions of samples/sec            |
  |  NF3. Storage retention: 30 days hot, 1+ year cold         |
  |  NF4. Query latency: < 1s for dashboard queries            |
  |  NF5. Alerting latency: < 1 min from spike to alert        |
  |  NF6. High availability: monitoring must survive failures  |
  |  NF7. Scalable: adding more services shouldn't break it    |
  |                                                            |
  +------------------------------------------------------------+
```

## SECTION 3: BACK-OF-ENVELOPE ESTIMATION

```
  +-----------------------------------------------------------------+
  |              Back-of-Envelope Calculations                      |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  Assumptions:                                                   |
  |    - 1,000 microservices                                        |
  |    - Each emits ~500 distinct metric time series                |
  |    - Collection interval: 15 seconds                            |
  |                                                                 |
  |  Active Time Series:                                            |
  |    1,000 services x 500 metrics = 500,000 time series           |
  |                                                                 |
  |  Samples per second:                                            |
  |    500,000 series / 15s interval ~ 33,000 samples/sec           |
  |                                                                 |
  |  Samples per day:                                               |
  |    33,000 x 86,400 ~ 2.85 billion samples/day                   |
  |                                                                 |
  |  Storage per sample:                                            |
  |    - Naive: 8B timestamp + 8B value + ~50B labels = 66 bytes    |
  |    - Compressed (Gorilla): ~1.37 bytes/sample avg               |
  |                                                                 |
  |  Storage per day:                                               |
  |    - Naive: 2.85B x 66B ~ 188 GB/day                            |
  |    - Compressed: 2.85B x 1.37B ~ 3.9 GB/day                     |
  |                                                                 |
  |  30-day retention:                                              |
  |    - Compressed: ~117 GB (very manageable!)                     |
  |                                                                 |
  |  At larger scale (10K services, 5M series):                     |
  |    - ~330K samples/sec                                          |
  |    - ~39 GB/day compressed                                      |
  |    - ~1.2 TB for 30-day retention                               |
  |                                                                 |
  +-----------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

```
  +====================================================================-+
  |              METRICS MONITORING SYSTEM - HIGH LEVEL                 |
  +====================================================================-+
  |                                                                     |
  |  +-------------+  +-------------+  +-------------+                  |
  |  | Service A   |  | Service B   |  | Service C   |                  |
  |  | /metrics    |  | /metrics    |  | /metrics    |                  |
  |  +------+------+  +------+------+  +------+------+                  |
  |         |                |                |                         |
  |         v                v                v                         |
  |  +------+----------------+----------------+------+                  |
  |  |           Collection Layer                     |                 |
  |  |  (Scrapers / Agents / Exporters)               |                 |
  |  +-------------------------+----------------------+                 |
  |                            |                                        |
  |                            v                                        |
  |  +-------------------------+----------------------+                 |
  |  |           Ingestion Pipeline                   |                 |
  |  |  (Buffering, Batching, Validation)             |                 |
  |  +-------------------------+----------------------+                 |
  |                            |                                        |
  |                            v                                        |
  |  +-------------------------+----------------------+                 |
  |  |        Time-Series Database (TSDB)             |                 |
  |  |  (Write-optimized, compressed storage)         |                 |
  |  +---+-----------------+------------------+-------+                 |
  |      |                 |                  |                         |
  |      v                 v                  v                         |
  |  +---+------+   +-----+------+   +-------+-------+                  |
  |  |  Query   |   |  Alerting  |   |   Dashboard   |                  |
  |  |  Engine  |   |  Engine    |   |   (Grafana)   |                  |
  |  +---+------+   +-----+------+   +---------------+                  |
  |      |                |                                             |
  |      v                v                                             |
  |  +---+------+   +-----+-----------+                                 |
  |  | API /    |   | Notification    |                                 |
  |  | PromQL   |   | (Slack, PD,    |                                  |
  |  +----------+   |  Email, SMS)   |                                  |
  |                  +----------------+                                 |
  |                                                                     |
  +====================================================================-+
```

## SECTION 5: DEEP DIVE: DATA MODEL

### METRIC STRUCTURE

```
  +------------------------------------------------------------------+
  |                    Metric Data Point                             |
  +------------------------------------------------------------------+
  |                                                                  |
  |  metric_name { label1="val1", label2="val2" }  value  @timestamp |
  |                                                                  |
  |  Example:                                                        |
  |    http_requests_total{method="GET", status="200", service="api"}|
  |      > 14523  @ 1678900000                                       |
  |                                                                  |
  |  Components:                                                     |
  |    +------------------+------------------------------------------+
  |    | Metric Name      | http_requests_total                      |
  |    +------------------+------------------------------------------+
  |    | Labels (Tags)    | method="GET", status="200",              |
  |    |                  | service="api"                            |
  |    +------------------+------------------------------------------+
  |    | Value            | 14523 (float64)                          |
  |    +------------------+------------------------------------------+
  |    | Timestamp        | 1678900000 (unix seconds or ms)          |
  |    +------------------+------------------------------------------+
  |                                                                  |
  +------------------------------------------------------------------+
```

### DIMENSIONAL DATA MODEL - WHY LABELS MATTER

```
  +--------------------------------------------------------------------+
  |              Labels Enable Dimensional Queries                     |
  +--------------------------------------------------------------------+
  |                                                                    |
  |  Without labels (flat model):                                      |
  |    api_get_200_requests_total = 1000                               |
  |    api_get_500_requests_total = 5                                  |
  |    api_post_200_requests_total = 800                               |
  |    web_get_200_requests_total = 2000                               |
  |    ... hundreds of metric names!                                   |
  |                                                                    |
  |  With labels (dimensional model):                                  |
  |    http_requests_total{service="api", method="GET",  status="200"} |
  |    http_requests_total{service="api", method="GET",  status="500"} |
  |    http_requests_total{service="api", method="POST", status="200"} |
  |    http_requests_total{service="web", method="GET",  status="200"} |
  |                                                                    |
  |  Now you can query:                                                |
  |    - All 500s: http_requests_total{status="500"}                   |
  |    - All POST: http_requests_total{method="POST"}                  |
  |    - Per-service: sum by (service)(http_requests_total)            |
  |                                                                    |
  |  One metric name + labels = infinite query dimensions.             |
  |                                                                    |
  +--------------------------------------------------------------------+
```

### THE CARDINALITY EXPLOSION PROBLEM

```
  +-----------------------------------------------------------------+
  |                  Cardinality Explosion                          |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  Each unique combination of {metric_name + all label values}    |
  |  creates a separate time series.                                |
  |                                                                 |
  |  Safe label:                                                    |
  |    method = "GET" | "POST" | "PUT" | "DELETE"  > 4 values       |
  |    status = "200" | "400" | "404" | "500"      > 4 values       |
  |    = 4 x 4 = 16 time series (fine)                              |
  |                                                                 |
  |  DANGEROUS label:                                               |
  |    user_id = "u_001" | "u_002" | ... | "u_1000000"              |
  |    = 1,000,000 time series PER METRIC (bad!)                    |
  |                                                                 |
  |  +-------------------+-------------------+                      |
  |  |  Cardinality      |  Impact           |                      |
  |  +-------------------+-------------------+                      |
  |  |  < 10K series     |  Fine             |                      |
  |  |  10K - 100K       |  Monitor closely  |                      |
  |  |  100K - 1M        |  Warning zone     |                      |
  |  |  > 1M series      |  Explosion!       |                      |
  |  +-------------------+-------------------+                      |
  |                                                                 |
  |  Rule: NEVER use unbounded values (user_id, request_id, IP)     |
  |  as metric labels. Use logs or traces for high-cardinality.     |
  |                                                                 |
  +-----------------------------------------------------------------+
```

## SECTION 6: DEEP DIVE: COLLECTION - PULL VS PUSH

### PULL MODEL (PROMETHEUS STYLE)

```
  +-----------------------------------------------------------------+
  |                    Pull-Based Collection                        |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  +-------------+    +-------------+    +-------------+          |
  |  | Service A   |    | Service B   |    | Service C   |          |
  |  | :8080       |    | :8080       |    | :8080       |          |
  |  | /metrics    |    | /metrics    |    | /metrics    |          |
  |  +------+------+    +------+------+    +------+------+          |
  |         ^                  ^                  ^                 |
  |         |    HTTP GET      |                  |                 |
  |         |    every 15s     |                  |                 |
  |  +------+------------------+------------------+------+          |
  |  |                Prometheus Server                  |          |
  |  |                                                   |          |
  |  |  +-------------------+                            |          |
  |  |  | Service Discovery |  (Kubernetes, Consul,      |          |
  |  |  | (SD)              |   DNS, file-based)         |          |
  |  |  +-------------------+                            |          |
  |  |                                                   |          |
  |  |  Scrape config:                                   |          |
  |  |    - targets: discovered via SD                   |          |
  |  |    - interval: 15s                                |          |
  |  |    - path: /metrics                               |          |
  |  |    - timeout: 10s                                 |          |
  |  +---------------------------------------------------+          |
  |                                                                 |
  |  /metrics endpoint returns text:                                |
  |    # HELP http_requests_total Total HTTP requests               |
  |    # TYPE http_requests_total counter                           |
  |    http_requests_total{method="GET",status="200"} 14523         |
  |    http_requests_total{method="POST",status="200"} 8901         |
  |    http_request_duration_seconds_bucket{le="0.1"} 24054         |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### PUSH MODEL (STATSD / DATADOG STYLE)

```
  +-----------------------------------------------------------------+
  |                    Push-Based Collection                        |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  +-------------+    +-------------+    +-------------+          |
  |  | Service A   |    | Service B   |    | Service C   |          |
  |  |             |    |             |    |             |          |
  |  | Agent lib   |    | Agent lib   |    | Agent lib   |          |
  |  | pushes      |    | pushes      |    | pushes      |          |
  |  | metrics     |    | metrics     |    | metrics     |          |
  |  +------+------+    +------+------+    +------+------+          |
  |         |                  |                  |                 |
  |         v                  v                  v                 |
  |  +------+------------------+------------------+------+          |
  |  |           Collector / Aggregator                  |          |
  |  |  (StatsD, Telegraf, OTEL Collector)               |          |
  |  +-------------------------+-------------------------+          |
  |                            |                                    |
  |                            v                                    |
  |  +-------------------------+-------------------------+          |
  |  |           Time-Series Database                    |          |
  |  +---------------------------------------------------+          |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### PULL VS PUSH COMPARISON

```
  +--------------------+----------------------------+----------------------------+
  |  Aspect            |  Pull (Prometheus)         |  Push (StatsD/Datadog)     |
  +--------------------+----------------------------+----------------------------+
  |  Who initiates?    |  Monitor scrapes targets   |  Targets push to monitor   |
  +--------------------+----------------------------+----------------------------+
  |  Service discovery |  Required (Kubernetes SD,  |  Not needed - targets      |
  |                    |  Consul, DNS)              |  know where to push        |
  +--------------------+----------------------------+----------------------------+
  |  Firewall          |  Monitor must reach all    |  Targets must reach        |
  |  direction         |  targets (ingress)         |  collector (egress)        |
  +--------------------+----------------------------+----------------------------+
  |  Liveness          |  "Target down" detected    |  "No data" could mean      |
  |  detection         |  when scrape fails         |  target down OR network    |
  +--------------------+----------------------------+----------------------------+
  |  Short-lived jobs  |  Hard - job may finish     |  Easy - push final         |
  |                    |  before next scrape        |  metrics before exit       |
  +--------------------+----------------------------+----------------------------+
  |  Control           |  Centralized - monitor     |  Distributed - each        |
  |                    |  decides what/when         |  target decides            |
  +--------------------+----------------------------+----------------------------+
  |  Backpressure      |  Built-in - monitor        |  Harder - flood risk       |
  |                    |  controls scrape rate      |  if targets push too much  |
  +--------------------+----------------------------+----------------------------+
  |  Debugging         |  curl http://target/       |  Need packet capture       |
  |                    |  metrics (easy!)           |  or collector logs         |
  +--------------------+----------------------------+----------------------------+
```

## SECTION 7: DEEP DIVE: TIME-SERIES STORAGE

### WHY REGULAR DATABASES FAIL

```
  +-----------------------------------------------------------------+
  |           Why PostgreSQL / MySQL Struggle with Metrics          |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  CREATE TABLE metrics (                                         |
  |    metric_name VARCHAR(255),                                    |
  |    labels      JSONB,                                           |
  |    timestamp   BIGINT,                                          |
  |    value       DOUBLE                                           |
  |  );                                                             |
  |                                                                 |
  |  Problems at scale:                                             |
  |    1. Write amplification - B-tree indexes on every insert      |
  |    2. No compression - 66+ bytes per sample, naive storage      |
  |    3. Inefficient range scans - scattered on disk               |
  |    4. Retention/deletion - DELETE FROM is extremely slow        |
  |    5. No time-series optimized queries (rate, avg over time)    |
  |                                                                 |
  |  A purpose-built TSDB can be 50-100x more efficient.            |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### WRITE-OPTIMIZED STORAGE: LSM-TREE

```
  +-----------------------------------------------------------------+
  |                    LSM-Tree Architecture                        |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  Write Path:                                                    |
  |                                                                 |
  |  +----------+    +------------------+    +------------------+   |
  |  | Incoming |    |    MemTable      |    |  WAL (Write-     |   |
  |  | Samples  |--->|  (in-memory,     |--->|  Ahead Log)      |   |
  |  +----------+    |   sorted)        |    |  (durability)    |   |
  |                  +--------+---------+    +------------------+   |
  |                           |                                     |
  |                           | flush when full                     |
  |                           v                                     |
  |                  +--------+---------+                           |
  |                  |  SSTable (Level 0)|  (sorted, immutable)     |
  |                  +--------+---------+                           |
  |                           |                                     |
  |                           | compaction                          |
  |                           v                                     |
  |                  +--------+---------+                           |
  |                  |  SSTable (Level 1)|  (merged, larger)        |
  |                  +--------+---------+                           |
  |                           |                                     |
  |                           v                                     |
  |                  +--------+---------+                           |
  |                  |  SSTable (Level 2)|  (even larger)           |
  |                  +-------------------+                          |
  |                                                                 |
  |  Why LSM-tree for metrics?                                      |
  |    - Sequential writes (append-only) - much faster than B-tree  |
  |    - Compaction merges and compresses in background             |
  |    - Time-partitioned SSTables align with metric time ranges    |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### COMPRESSION: FACEBOOK GORILLA PAPER (2015)

```
  +-----------------------------------------------------------------+
  |         Gorilla Compression Techniques                          |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  TIMESTAMP COMPRESSION: Delta-of-Delta                          |
  |                                                                 |
  |  Raw timestamps (15s interval):                                 |
  |    1000, 1015, 1030, 1045, 1060, 1075                           |
  |                                                                 |
  |  Deltas:                                                        |
  |    15, 15, 15, 15, 15                                           |
  |                                                                 |
  |  Delta-of-deltas:                                               |
  |    0, 0, 0, 0, 0                                                |
  |                                                                 |
  |  Storage: just store "0" with 1 bit each!                       |
  |  (Most samples arrive at regular intervals, so DoD ~ 0)         |
  |                                                                 |
  |  Encoding:                                                      |
  |    DoD = 0         > store '0'        (1 bit)                   |
  |    DoD in [-63,64] > store '10' + 7b  (9 bits)                  |
  |    DoD in [-255,256]>store '110'+ 9b  (12 bits)                 |
  |    DoD in [-2047,2048]>'1110'+ 12b    (16 bits)                 |
  |    Otherwise       > '1111' + 32 bits (36 bits)                 |
  |                                                                 |
  |  ------------------------------------------------------------   |
  |                                                                 |
  |  VALUE COMPRESSION: XOR Encoding                                |
  |                                                                 |
  |  Observation: consecutive values of a metric are often close.   |
  |                                                                 |
  |  XOR of consecutive float64 values:                             |
  |    value[n] XOR value[n-1] > many leading/trailing zeros        |
  |                                                                 |
  |  If XOR = 0 (same value):  store '0'   (1 bit)                  |
  |  If XOR ! 0: store leading zeros + meaningful bits              |
  |                                                                 |
  |  Result: ~1.37 bytes per sample on average!                     |
  |  (vs. 16 bytes uncompressed = ~12x compression)                 |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### DOWNSAMPLING AND RETENTION

```
  +-----------------------------------------------------------------+
  |            Downsampling & Retention Policies                    |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  Time Range        Resolution       Storage                     |
  |  +-----------------+-----------------+-----------------+        |
  |  | Last 24 hours   | Raw (15s)       | Hot storage     |        |
  |  +-----------------+-----------------+-----------------+        |
  |  | 1-7 days        | Raw (15s)       | Warm storage    |        |
  |  +-----------------+-----------------+-----------------+        |
  |  | 7-30 days       | 1-minute avg    | Warm storage    |        |
  |  +-----------------+-----------------+-----------------+        |
  |  | 30-90 days      | 5-minute avg    | Cold storage    |        |
  |  +-----------------+-----------------+-----------------+        |
  |  | 90+ days        | 1-hour avg      | Object store    |        |
  |  |                 |                 | (S3/GCS)        |        |
  |  +-----------------+-----------------+-----------------+        |
  |                                                                 |
  |  Downsampling reduces storage dramatically:                     |
  |    Raw 15s > 5760 points/day                                    |
  |    5-min   > 288 points/day (20x reduction)                     |
  |    1-hour  > 24 points/day (240x reduction)                     |
  |                                                                 |
  |  Time-based partitioning makes deletion trivial:                |
  |    DROP partition (or delete block file) instead of             |
  |    DELETE WHERE timestamp < X                                   |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### PARTITIONING BY TIME (PROMETHEUS TSDB BLOCKS)

```
  +-----------------------------------------------------------------+
  |             Prometheus TSDB Block Layout                        |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  data/                                                          |
  |  +-- 01BKGV7JBM69T2G1BGBGM6KB12/   (block: 2h window)           |
  |  |   +-- meta.json                   (time range, stats)        |
  |  |   +-- index                       (inverted index)           |
  |  |   +-- chunks/                     (compressed samples)       |
  |  |   |   +-- 000001                                             |
  |  |   +-- tombstones                  (deleted series)           |
  |  +-- 01BKGTZQ1HHWHV8FBJXW1Y3W0K/   (next 2h block)              |
  |  |   +-- ...                                                    |
  |  +-- wal/                            (write-ahead log)          |
  |      +-- 00000001                    (current head)             |
  |      +-- 00000002                                               |
  |                                                                 |
  |  +--------+--------+--------+--------+--------+                 |
  |  | Block1 | Block2 | Block3 | Block4 |  HEAD  |                 |
  |  | 2h     | 2h     | 2h     | 2h     | (WAL)  |                 |
  |  +--------+--------+--------+--------+--------+                 |
  |  |<--- compacted into larger blocks --->|      |                |
  |                                                                 |
  |  - Each block is immutable once written                         |
  |  - HEAD block is in-memory + WAL for active writes              |
  |  - Compaction merges small blocks into larger ones              |
  |  - Deletion = remove entire block directory                     |
  |                                                                 |
  +-----------------------------------------------------------------+
```

## SECTION 8: DEEP DIVE: QUERY ENGINE

### PROMQL-STYLE QUERIES

```
  +-----------------------------------------------------------------+
  |                    Query Language                               |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  Instant Query:                                                 |
  |    http_requests_total{service="api", status="500"}             |
  |    > current value of matching series                           |
  |                                                                 |
  |  Range Query:                                                   |
  |    http_requests_total{service="api"}[5m]                       |
  |    > all samples in last 5 minutes                              |
  |                                                                 |
  |  Rate (counter > per-second rate):                              |
  |    rate(http_requests_total[5m])                                |
  |    > requests/sec averaged over 5 minutes                       |
  |                                                                 |
  |  Aggregation:                                                   |
  |    sum by (service)(rate(http_requests_total[5m]))              |
  |    > total request rate grouped by service                      |
  |                                                                 |
  |  Histogram Percentile:                                          |
  |    histogram_quantile(0.99,                                     |
  |      rate(http_request_duration_seconds_bucket[5m]))            |
  |    > p99 latency                                                |
  |                                                                 |
  |  Math:                                                          |
  |    (errors / total) * 100                                       |
  |    > error percentage                                           |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### QUERY EXECUTION FLOW

```
  +-----------------------------------------------------------------+
  |                 Query Execution Pipeline                        |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  "rate(http_requests_total{service='api'}[5m])"                 |
  |                                                                 |
  |  Step 1: Parse                                                  |
  |  +------------------+                                           |
  |  |  AST:            |                                           |
  |  |  rate(           |                                           |
  |  |    selector[5m]  |                                           |
  |  |  )               |                                           |
  |  +--------+---------+                                           |
  |           |                                                     |
  |  Step 2: Select Series                                          |
  |  +--------v---------+                                           |
  |  |  Index Lookup:   |   Inverted index:                         |
  |  |  service="api"   |   service="api" > series [101, 102, 103]  |
  |  |  __name__=       |   Intersect label matchers                |
  |  |    "http_..."    |                                           |
  |  +--------+---------+                                           |
  |           |                                                     |
  |  Step 3: Fetch Samples                                          |
  |  +--------v---------+                                           |
  |  |  Read chunks for |   For each matched series,                |
  |  |  time range      |   decompress and load samples             |
  |  |  [now-5m, now]   |   within the time window                  |
  |  +--------+---------+                                           |
  |           |                                                     |
  |  Step 4: Apply Function                                         |
  |  +--------v---------+                                           |
  |  |  rate():         |   Calculate per-second rate               |
  |  |  (last-first) /  |   from counter values                     |
  |  |  time_range      |                                           |
  |  +--------+---------+                                           |
  |           |                                                     |
  |  Step 5: Return Result                                          |
  |  +--------v---------+                                           |
  |  |  {service="api"} |                                           |
  |  |    > 245.3 req/s |                                           |
  |  +------------------+                                           |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### RECORDING RULES (PRE-COMPUTATION)

```
  +-----------------------------------------------------------------+
  |                    Recording Rules                              |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  Problem: Complex queries on dashboards run every refresh.      |
  |  If 20 engineers have the same dashboard open, that's 20x       |
  |  the same expensive query every 30 seconds.                     |
  |                                                                 |
  |  Solution: Pre-compute and store the result as a new series.    |
  |                                                                 |
  |  Rule definition:                                               |
  |    record: service:http_requests:rate5m                         |
  |    expr: sum by (service)(rate(http_requests_total[5m]))        |
  |    interval: 30s                                                |
  |                                                                 |
  |  +------------------+    +---------------------+                |
  |  | Original series  |    | Recording rule      |                |
  |  | (raw counters)   |--->| evaluates every 30s |                |
  |  +------------------+    +----------+----------+                |
  |                                     |                           |
  |                                     v                           |
  |                          +----------+----------+                |
  |                          | New series:         |                |
  |                          | service:http_       |                |
  |                          | requests:rate5m     |                |
  |                          +---------------------+                |
  |                                                                 |
  |  Dashboard queries the pre-computed series - instant!           |
  |                                                                 |
  +-----------------------------------------------------------------+
```

## SECTION 9: DEEP DIVE: ALERTING

### ALERT RULE LIFECYCLE

```
  +-----------------------------------------------------------------+
  |                   Alert Rule Example                            |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  alert: HighErrorRate                                           |
  |  expr: rate(http_requests_total{status=~"5.."}[5m])             |
  |        / rate(http_requests_total[5m]) > 0.05                   |
  |  for: 5m                                                        |
  |  labels:                                                        |
  |    severity: critical                                           |
  |  annotations:                                                   |
  |    summary: "Error rate > 5% for {{ $labels.service }}"         |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### ALERT STATE MACHINE

```
  +-----------------------------------------------------------------+
  |                  Alert State Transitions                        |
  +-----------------------------------------------------------------+
  |                                                                 |
  |                   condition                                     |
  |                   becomes true                                  |
  |  +----------+    +----------+    +---------+                    |
  |  | INACTIVE |    |          |    |         |                    |
  |  | (normal) |--->| PENDING  |--->| FIRING  |                    |
  |  |          |    | (waiting |    | (alert  |                    |
  |  +----+-----+    |  for     |    |  sent!) |                    |
  |       ^          |  "for"   |    |         |                    |
  |       |          |  duration)|    +----+----+                   |
  |       |          +----+-----+         |                         |
  |       |               |               |                         |
  |       |   condition   |  condition    |  condition              |
  |       |   becomes     |  becomes     |  becomes                 |
  |       |   false       |  false       |  false                   |
  |       |               |               |                         |
  |       +<--------------+               v                         |
  |       |                        +------+-----+                   |
  |       +<-----------------------| RESOLVED   |                   |
  |                                | (recovery  |                   |
  |                                |  sent)     |                   |
  |                                +------------+                   |
  |                                                                 |
  |  "for: 5m" means the condition must be true for 5 continuous    |
  |  minutes before transitioning from PENDING > FIRING.            |
  |  This prevents flapping alerts from noisy metrics.              |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### ALERTING ARCHITECTURE

```
  +-----------------------------------------------------------------+
  |              Alerting System Architecture                       |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  +------------------+                                           |
  |  | TSDB             |                                           |
  |  | (metric data)    |                                           |
  |  +--------+---------+                                           |
  |           |                                                     |
  |           v                                                     |
  |  +--------+---------+      +---------------------------+        |
  |  | Rule Evaluation  |      |  Alert Rules Config       |        |
  |  | Engine           |<-----| (YAML files or API)       |        |
  |  |                  |      +---------------------------+        |
  |  | Runs every 15-60s|                                           |
  |  | per rule group   |                                           |
  |  +--------+---------+                                           |
  |           |                                                     |
  |           | fires alert                                         |
  |           v                                                     |
  |  +--------+---------+                                           |
  |  | Alert Manager    |                                           |
  |  |                  |                                           |
  |  |  +------------+  |                                           |
  |  |  | Grouping   |  |  Combine related alerts into one          |
  |  |  +-----+------+  |  notification (e.g., 50 pod alerts        |
  |  |        |         |  > 1 "cluster unhealthy" notification)    |
  |  |  +-----v------+  |                                           |
  |  |  | Dedup      |  |  Don't re-send the same alert             |
  |  |  +-----+------+  |  every eval cycle                         |
  |  |        |         |                                           |
  |  |  +-----v------+  |                                           |
  |  |  | Silencing  |  |  Suppress during maintenance windows      |
  |  |  +-----+------+  |                                           |
  |  |        |         |                                           |
  |  |  +-----v------+  |                                           |
  |  |  | Inhibition |  |  If "cluster down" fires, suppress        |
  |  |  +-----+------+  |  individual "pod down" alerts             |
  |  |        |         |                                           |
  |  +--------+---------+                                           |
  |           |                                                     |
  |           v                                                     |
  |  +--------+---------------------------------------------+       |
  |  |              Notification Channels                    |      |
  |  +------+--------+--------+--------+--------+-----------+       |
  |         |        |        |        |        |                   |
  |         v        v        v        v        v                   |
  |  +------+--+ +---+---+ +-+----+ +-+---+ +--+--------+           |
  |  | Slack   | | Email | | PD   | | SMS | | Webhook   |           |
  |  +---------+ +-------+ +------+ +-----+ +-----------+           |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### ON-CALL ROUTING

```
  +-----------------------------------------------------------------+
  |                  On-Call Routing Flow                           |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  Alert fires                                                    |
  |    |                                                            |
  |    v                                                            |
  |  +-------------------+                                          |
  |  | Routing Rules     |  severity=critical > on-call team        |
  |  | (label matching)  |  severity=warning  > Slack channel       |
  |  +--------+----------+  service=payments  > payments-oncall     |
  |           |                                                     |
  |           v                                                     |
  |  +--------+----------+                                          |
  |  | PagerDuty / Opsgenie                                         |
  |  |                   |                                          |
  |  | Schedule:         |                                          |
  |  |  Mon-Fri 9-5:     |                                          |
  |  |    Primary: Alice  |                                         |
  |  |    Secondary: Bob  |                                         |
  |  |  After hours:     |                                          |
  |  |    Primary: Carol  |                                         |
  |  +--------+----------+                                          |
  |           |                                                     |
  |           v                                                     |
  |  +--------+----------+                                          |
  |  | Escalation Policy |  No ack in 5 min > escalate              |
  |  |  L1: Primary      |  No ack in 15 min > escalate             |
  |  |  L2: Secondary    |  No ack in 30 min > manager              |
  |  |  L3: Manager      |                                          |
  |  +-------------------+                                          |
  |                                                                 |
  +-----------------------------------------------------------------+
```

## SECTION 10: SCALING

### SCALING CHALLENGES

```
  +-----------------------------------------------------------------+
  |             Single Prometheus Limits                            |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  A single Prometheus instance can handle:                       |
  |    - ~10 million active time series                             |
  |    - ~1 million samples/sec ingestion                           |
  |    - ~200-500 GB of local storage                               |
  |                                                                 |
  |  Beyond this, you need horizontal scaling strategies.           |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### SHARDING BY METRIC HASH

```
  +-----------------------------------------------------------------+
  |                  Functional Sharding                            |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  Assign different metric groups to different instances:         |
  |                                                                 |
  |  +-----------------------+                                      |
  |  | Prometheus Instance 1 |  Scrapes: API services               |
  |  +-----------------------+  Metrics: http_*, grpc_*             |
  |                                                                 |
  |  +-----------------------+                                      |
  |  | Prometheus Instance 2 |  Scrapes: Infrastructure             |
  |  +-----------------------+  Metrics: node_*, container_*        |
  |                                                                 |
  |  +-----------------------+                                      |
  |  | Prometheus Instance 3 |  Scrapes: Database exporters         |
  |  +-----------------------+  Metrics: mysql_*, pg_*, redis_*     |
  |                                                                 |
  |  Hash-based sharding:                                           |
  |    shard = hash(metric_name + labels) % num_shards              |
  |    Each shard only stores a subset of all series                |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### FEDERATION (HIERARCHICAL PROMETHEUS)

```
  +-----------------------------------------------------------------+
  |              Prometheus Federation                              |
  +-----------------------------------------------------------------+
  |                                                                 |
  |                    +-------------------+                        |
  |                    | Global Prometheus |  (aggregated metrics   |
  |                    | (Federation)      |   from all DCs)        |
  |                    +--------+----------+                        |
  |                             ^                                   |
  |               scrape /federate endpoint                         |
  |              +----------+---+----------+                        |
  |              |          |              |                        |
  |  +-----------+--+  +---+----------+  ++------------+            |
  |  | Prometheus   |  | Prometheus   |  | Prometheus   |           |
  |  | DC: US-East  |  | DC: US-West  |  | DC: EU       |           |
  |  +------+-------+  +------+-------+  +------+-------+           |
  |         |                 |                 |                   |
  |    +----+----+      +----+----+       +----+----+               |
  |    | Targets |      | Targets |       | Targets |               |
  |    +---------+      +---------+       +---------+               |
  |                                                                 |
  |  The global instance scrapes pre-aggregated (recording rule)    |
  |  metrics from each DC-level Prometheus.                         |
  |                                                                 |
  |  Limitation: Global instance only sees aggregated data.         |
  |  High-resolution or per-instance queries stay local.            |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### REMOTE STORAGE: THANOS AND CORTEX

```
  +================================================================-+
  |                  THANOS ARCHITECTURE                            |
  +================================================================-+
  |                                                                 |
  |  +-------------------+    +-------------------+                 |
  |  | Prometheus +      |    | Prometheus +      |                 |
  |  | Thanos Sidecar    |    | Thanos Sidecar    |                 |
  |  +--------+----------+    +--------+----------+                 |
  |           |                        |                            |
  |           | upload blocks          | upload blocks              |
  |           v                        v                            |
  |  +--------+------------------------+----------+                 |
  |  |              Object Storage (S3/GCS)       |                 |
  |  |  (long-term, durable, cheap storage)       |                 |
  |  +---------------------+----------------------+                 |
  |                        |                                        |
  |                        v                                        |
  |  +---------------------+----------------------+                 |
  |  |              Thanos Store Gateway           |                |
  |  |  (serves queries from object storage)       |                |
  |  +---------------------+----------------------+                 |
  |                        |                                        |
  |  +---------------------+----------------------+                 |
  |  |              Thanos Querier                 |                |
  |  |  (PromQL-compatible, fan-out queries        |                |
  |  |   to sidecars + store gateways)            |                 |
  |  +---------------------+----------------------+                 |
  |                        |                                        |
  |                        v                                        |
  |  +---------------------+----------------------+                 |
  |  |              Thanos Compactor               |                |
  |  |  (downsamples old data: 5m, 1h)            |                 |
  |  +---------------------------------------------+                |
  |                                                                 |
  |  Benefits:                                                      |
  |    - Unlimited retention (object storage is cheap)              |
  |    - Global query view across all Prometheus instances          |
  |    - Deduplication of HA Prometheus pairs                       |
  |    - Downsampling for efficient long-range queries              |
  |                                                                 |
  +================================================================-+
```

```
  +================================================================-+
  |                  CORTEX ARCHITECTURE                            |
  +================================================================-+
  |                                                                 |
  |  +-------------------+    +-------------------+                 |
  |  | Prometheus        |    | Prometheus        |                 |
  |  | (remote_write)    |    | (remote_write)    |                 |
  |  +--------+----------+    +--------+----------+                 |
  |           |                        |                            |
  |           v                        v                            |
  |  +--------+------------------------+----------+                 |
  |  |              Cortex Distributor            |                 |
  |  |  (accepts writes, shards by series hash)   |                 |
  |  +---------------------+----------------------+                 |
  |                        |                                        |
  |                        v                                        |
  |  +---------------------+----------------------+                 |
  |  |              Cortex Ingester               |                 |
  |  |  (in-memory + WAL, batches to storage)     |                 |
  |  +---------------------+----------------------+                 |
  |                        |                                        |
  |                        v                                        |
  |  +---------------------+----------------------+                 |
  |  |        Long-Term Storage                    |                |
  |  |  (DynamoDB/Cassandra for index,            |                 |
  |  |   S3/GCS for chunks)                       |                 |
  |  +---------------------------------------------+                |
  |                                                                 |
  |  Key difference from Thanos:                                    |
  |    - Thanos: sidecar model, Prometheus stores locally first     |
  |    - Cortex: push model, Prometheus remote-writes directly      |
  |    - Cortex is fully multi-tenant from the ground up            |
  |                                                                 |
  +================================================================-+
```

### QUERY FAN-OUT

```
  +-----------------------------------------------------------------+
  |                 Query Fan-Out Strategy                          |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  User sends: rate(http_requests_total[5m])                      |
  |                                                                 |
  |           +-------------------+                                 |
  |           | Query Frontend    |  (caching, splitting,           |
  |           | (optional)        |   deduplication)                |
  |           +--------+----------+                                 |
  |                    |                                            |
  |                    v                                            |
  |           +--------+----------+                                 |
  |           |    Querier        |                                 |
  |           +--+------+------+--+                                 |
  |              |      |      |                                    |
  |              v      v      v                                    |
  |         +----++ +---+--+ +-+------+                             |
  |         |Shard| |Shard | |Store   |                             |
  |         |  1  | |  2   | |Gateway |                             |
  |         |(hot)| |(hot) | |(cold)  |                             |
  |         +-----+ +------+ +--------+                             |
  |                                                                 |
  |  Querier merges results from all sources and returns            |
  |  a unified response. Client doesn't know about sharding.        |
  |                                                                 |
  +-----------------------------------------------------------------+
```

## SECTION 11: INTERVIEW Q&A

### Q1: Why do we need a specialized time-series database instead of PostgreSQL?

```
  +----------------------------------------------------------------+
  |  Time-series data has unique access patterns:                  |
  |                                                                |
  |  1. Writes are append-only (always the latest timestamp)       |
  |     > LSM-tree or append-only storage is ideal                 |
  |     > B-tree indexes (PostgreSQL) cause write amplification    |
  |                                                                |
  |  2. Reads are almost always range-based ("last 1 hour")        |
  |     > Time-partitioned blocks make range scans fast            |
  |     > Generic row storage scatters data across pages           |
  |                                                                |
  |  3. Data is highly compressible (regular intervals, similar    |
  |     values) > Gorilla encoding achieves 12x compression        |
  |     > PostgreSQL stores 66+ bytes per sample (no compression)  |
  |                                                                |
  |  4. Deletion is time-based ("drop data older than 30 days")    |
  |     > Drop a partition/block file (instant)                    |
  |     > DELETE WHERE ts < X in PG is extremely slow at scale     |
  |                                                                |
  |  5. Specialized query language (rate, histogram_quantile)      |
  |     is purpose-built for time-series analysis                  |
  |                                                                |
  +----------------------------------------------------------------+
```

### Q2: Explain the difference between Pull and Push collection models.

```
  +----------------------------------------------------------------+
  |  Pull (Prometheus):                                            |
  |    - Central server scrapes /metrics from each target          |
  |    - Requires service discovery to find targets                |
  |    - Easy to debug (curl the endpoint)                         |
  |    - Natural backpressure (server controls scrape rate)        |
  |    - Harder for short-lived jobs (may miss them)               |
  |                                                                |
  |  Push (StatsD/Datadog):                                        |
  |    - Each service pushes metrics to a collector                |
  |    - No service discovery needed                               |
  |    - Works great for short-lived batch jobs                    |
  |    - Risk of overwhelming collector (no backpressure)          |
  |    - Harder to tell if "no data" means "down" or "nothing to   |
  |      report"                                                   |
  |                                                                |
  |  Many production systems use both: pull for long-running       |
  |  services, push (via Pushgateway) for batch jobs.              |
  +----------------------------------------------------------------+
```

### Q3: What is the cardinality explosion problem and how do you prevent it?

```
  +-----------------------------------------------------------------+
  |  Cardinality = number of unique time series.                    |
  |  Each unique combo of {metric + label values} = 1 series.       |
  |                                                                 |
  |  If you add a label like user_id with 10M users:                |
  |    http_requests_total x 10M users = 10M series PER METRIC.     |
  |    That can easily hit 100M+ series - TSDB crashes or slows.    |
  |                                                                 |
  |  Prevention:                                                    |
  |    1. Never use unbounded values as labels                      |
  |       (no user_id, request_id, IP addresses, email)             |
  |    2. Keep label value count < 100 per label                    |
  |    3. Use logs/traces for high-cardinality debugging            |
  |    4. Monitor cardinality: Prometheus exposes                   |
  |       prometheus_tsdb_head_series gauge                         |
  |    5. Set per-tenant series limits in multi-tenant systems      |
  |    6. Use relabeling to drop or aggregate noisy labels          |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### Q4: How does Gorilla compression achieve ~1.37 bytes per sample?

```
  +----------------------------------------------------------------+
  |  Two key techniques:                                           |
  |                                                                |
  |  1. Timestamps - Delta-of-Delta:                               |
  |     Metrics arrive at regular intervals (e.g., every 15s).     |
  |     Delta between timestamps ~ constant (15, 15, 15, ...).     |
  |     Delta-of-delta ~ 0, stored in just 1 bit.                  |
  |     Even with jitter, most DoD values fit in 9 bits.           |
  |                                                                |
  |  2. Values - XOR Encoding:                                     |
  |     Consecutive metric values are often similar.               |
  |     XOR of consecutive float64 values > many leading and       |
  |     trailing zeros. Store only the meaningful bits.            |
  |     Same value repeated > just 1 bit ('0').                    |
  |                                                                |
  |  Combined, a 16-byte (timestamp + value) sample compresses     |
  |  to ~1.37 bytes average = ~12x compression.                    |
  |                                                                |
  |  This makes in-memory storage of recent data feasible.         |
  |  Gorilla keeps last 26 hours compressed in RAM.                |
  +----------------------------------------------------------------+
```

### Q5: How does alerting handle flapping metrics?

```
  +-----------------------------------------------------------------+
  |  Flapping: a metric oscillates above and below the threshold    |
  |  rapidly, causing alerts to fire and resolve repeatedly.        |
  |                                                                 |
  |  Solutions:                                                     |
  |                                                                 |
  |  1. "for" duration:                                             |
  |     alert: HighLatency                                          |
  |     expr: latency_p99 > 500                                     |
  |     for: 5m        < must be true for 5 CONTINUOUS minutes      |
  |                                                                 |
  |  2. Hysteresis (different thresholds for fire vs. resolve):     |
  |     Fire when: error_rate > 5%                                  |
  |     Resolve when: error_rate < 2% (not 5%)                      |
  |     Prevents flip-flop at the boundary.                         |
  |                                                                 |
  |  3. Alert grouping:                                             |
  |     Group multiple related alerts into one notification.        |
  |     "50 pods unhealthy" instead of 50 separate alerts.          |
  |                                                                 |
  |  4. Rate-limited notifications:                                 |
  |     Even if alert state changes, only send notifications        |
  |     at most every N minutes (repeat_interval).                  |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### Q6: How would you design this system for multi-tenancy (SaaS monitoring)?

```
  +----------------------------------------------------------------+
  |  Multi-tenancy (like Datadog or Grafana Cloud):                |
  |                                                                |
  |  1. Tenant isolation at ingestion:                             |
  |     Each API key maps to a tenant_id.                          |
  |     Inject tenant_id label on all incoming metrics.            |
  |                                                                |
  |  2. Per-tenant limits:                                         |
  |     - Max active series (cardinality limit)                    |
  |     - Max samples/sec (ingestion rate limit)                   |
  |     - Max query range / complexity                             |
  |                                                                |
  |  3. Storage isolation:                                         |
  |     Option A: Separate TSDB per tenant (simple, wasteful)      |
  |     Option B: Shared TSDB with tenant_id in labels             |
  |               (efficient, harder isolation)                    |
  |     Cortex uses Option B with per-tenant compaction.           |
  |                                                                |
  |  4. Query isolation:                                           |
  |     Querier automatically injects {tenant_id="X"} filter.      |
  |     Tenant A can never see Tenant B's data.                    |
  |                                                                |
  |  5. Fair scheduling:                                           |
  |     Query queue per tenant, weighted fair queuing.             |
  |     Prevent one heavy tenant from starving others.             |
  |                                                                |
  +----------------------------------------------------------------+
```

### Q7: How does Thanos achieve unlimited retention with Prometheus?

```
  +-----------------------------------------------------------------+
  |  Thanos adds a sidecar to each Prometheus instance.             |
  |                                                                 |
  |  Flow:                                                          |
  |    1. Prometheus writes 2-hour TSDB blocks locally              |
  |    2. Thanos Sidecar uploads completed blocks to S3/GCS         |
  |    3. Prometheus can delete local blocks after upload           |
  |    4. Thanos Store Gateway serves queries from object storage   |
  |    5. Thanos Querier merges live (sidecar) + historical         |
  |       (store gateway) data seamlessly                           |
  |    6. Thanos Compactor downsamples old blocks (5m, 1h)          |
  |                                                                 |
  |  Result:                                                        |
  |    - Prometheus keeps only hours/days of local data             |
  |    - Object storage keeps months/years cheaply                  |
  |    - Queries transparently span both                            |
  |    - Downsampled data makes year-long queries fast              |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### Q8: What is the difference between recording rules and alerting rules?

```
  +-----------------------------------------------------------------+
  |  Recording Rules:                                               |
  |    - Pre-compute a query and store result as a new metric       |
  |    - Purpose: speed up dashboard queries, reduce TSDB load      |
  |    - Output: a new time series written back into TSDB           |
  |    - Example: record: job:http_requests:rate5m                  |
  |              expr: sum by (job)(rate(http_requests_total[5m]))  |
  |                                                                 |
  |  Alerting Rules:                                                |
  |    - Evaluate a condition and fire an alert if true             |
  |    - Purpose: notify humans/systems of problems                 |
  |    - Output: an alert sent to Alertmanager                      |
  |    - Example: alert: HighErrorRate                              |
  |              expr: error_rate > 0.05                            |
  |              for: 5m                                            |
  |                                                                 |
  |  Recording rules create data. Alerting rules create actions.    |
  |                                                                 |
  |  Best practice: write recording rules for complex expressions,  |
  |  then use the recorded metric in alerting rules for speed.      |
  +-----------------------------------------------------------------+
```

### Q9: How do you monitor the monitoring system itself?

```
  +----------------------------------------------------------------+
  |  The "meta-monitoring" problem - who watches the watchman?     |
  |                                                                |
  |  Strategies:                                                   |
  |                                                                |
  |  1. Cross-monitoring:                                          |
  |     Prometheus A monitors Prometheus B, and vice versa.        |
  |     Each has alerts for the other's health.                    |
  |                                                                |
  |  2. Deadman's switch (watchdog alert):                         |
  |     A special alert that ALWAYS fires.                         |
  |     If Alertmanager stops receiving it > system is down.       |
  |     External service (e.g., Deadman's Snitch) expects          |
  |     periodic pings; alerts if pings stop.                      |
  |                                                                |
  |  3. Synthetic monitoring:                                      |
  |     External probes (from different infra) that check:         |
  |       - Can I scrape /metrics?                                 |
  |       - Can I query the API?                                   |
  |       - Are alerts flowing?                                    |
  |                                                                |
  |  4. Separate monitoring stack for infra:                       |
  |     Use a completely independent, simple monitoring system     |
  |     (even basic health checks + PagerDuty) for the primary     |
  |     monitoring infrastructure.                                 |
  |                                                                |
  +----------------------------------------------------------------+
```

### Q10: Walk through what happens when a service starts reporting high latency.

```
  +----------------------------------------------------------------+
  |  End-to-End Flow:                                              |
  |                                                                |
  |  1. Service emits: http_request_duration_seconds_bucket{...}   |
  |                                                                |
  |  2. Prometheus scrapes /metrics endpoint (every 15s)           |
  |                                                                |
  |  3. Samples stored in TSDB head block (in-memory + WAL)        |
  |                                                                |
  |  4. Alert rule evaluates every 30s:                            |
  |     histogram_quantile(0.99,                                   |
  |       rate(http_request_duration_seconds_bucket[5m])) > 2.0    |
  |                                                                |
  |  5. Condition becomes true > alert enters PENDING state        |
  |                                                                |
  |  6. After "for: 5m" > alert transitions to FIRING              |
  |                                                                |
  |  7. Prometheus sends alert to Alertmanager                     |
  |                                                                |
  |  8. Alertmanager:                                              |
  |     a. Groups with other service alerts                        |
  |     b. Checks silences (none active)                           |
  |     c. Checks inhibition rules                                 |
  |     d. Routes based on severity=critical > PagerDuty           |
  |                                                                |
  |  9. PagerDuty pages on-call engineer                           |
  |                                                                |
  |  10. Engineer opens Grafana dashboard:                         |
  |      - Sees p99 latency spike at 14:23                         |
  |      - Drills down by endpoint: /api/checkout is slow          |
  |      - Correlates with DB query latency dashboard              |
  |      - Finds slow query, deploys fix                           |
  |                                                                |
  |  11. Latency drops below threshold > RESOLVED                  |
  |      Alertmanager sends recovery notification to Slack.        |
  |                                                                |
  +----------------------------------------------------------------+
```

## SECTION 12: SUMMARY

```
  +================================================================+
  |  KEY TAKEAWAYS                                                 |
  +================================================================+
  |                                                                |
  |  1. Metrics are numeric time-series: counters, gauges,         |
  |     histograms, summaries - each has specific use cases        |
  |                                                                |
  |  2. The dimensional data model (labels/tags) enables powerful  |
  |     ad-hoc queries but beware cardinality explosion            |
  |                                                                |
  |  3. Pull vs Push collection both have trade-offs - Prometheus  |
  |     (pull) is dominant in cloud-native; push works better      |
  |     for short-lived jobs and agent-based architectures         |
  |                                                                |
  |  4. Purpose-built TSDBs with Gorilla compression achieve       |
  |     12x better storage efficiency than general-purpose DBs     |
  |                                                                |
  |  5. Alerting requires careful design: "for" durations,         |
  |     grouping, deduplication, and silencing prevent alert       |
  |     fatigue while ensuring real issues get noticed             |
  |                                                                |
  |  6. Scaling requires sharding (hash-based or functional),      |
  |     federation for multi-DC, and remote storage (Thanos/       |
  |     Cortex) for long-term retention                            |
  |                                                                |
  |  7. Always monitor your monitoring - cross-monitoring,         |
  |     watchdog alerts, and external synthetic checks             |
  |                                                                |
  +================================================================+
```
