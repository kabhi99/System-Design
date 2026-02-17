# Time-Series Database System Design

## Table of Contents

1. [Introduction](#introduction)
2. [What is a Time-Series Database](#what-is-a-time-series-database)
3. [Requirements](#requirements)
4. [Scale Estimation](#scale-estimation)
5. [High-Level Architecture](#high-level-architecture)
6. [Data Model](#data-model)
7. [Storage Engine Design](#storage-engine-design)
8. [Write Path](#write-path)
9. [Read Path](#read-path)
10. [Compression Techniques](#compression-techniques)
11. [Retention Policies and Downsampling](#retention-policies-and-downsampling)
12. [Sharding and Partitioning](#sharding-and-partitioning)
13. [Query Language Comparison](#query-language-comparison)
14. [Real-World System Comparison](#real-world-system-comparison)
15. [Use Cases](#use-cases)
16. [Trade-offs and Design Decisions](#trade-offs-and-design-decisions)
17. [Failure Handling and Reliability](#failure-handling-and-reliability)
18. [Monitoring the Monitor](#monitoring-the-monitor)
19. [Interview Q&A](#interview-qa)

---

## Introduction

Time-series data is one of the fastest-growing categories of data. From server
monitoring to IoT sensors to financial tick data, the need to store, query, and
analyze timestamped data points at massive scale has driven the creation of
specialized database systems. This document covers the end-to-end design of a
time-series database (TSDB) system suitable for a system design interview.

---

## What is a Time-Series Database

### Definition

A time-series database is a database optimized for storing and querying data
points that are indexed by time. Each data point typically consists of:

- A **metric name** (what is being measured)
- A set of **tags/labels** (dimensions that describe the source)
- A **timestamp** (when the measurement was taken)
- One or more **values** (the actual measurement)

### Why Not Just Use a Relational Database?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Why Traditional Databases Struggle with Time-Series Data:              |
|                                                                         |
|  1. Write Volume: Millions of inserts per second overwhelm              |
|     row-based storage engines (B-tree write amplification)              |
|                                                                         |
|  2. Query Pattern: Queries are almost always by time range,             |
|     not by primary key lookup                                           |
|                                                                         |
|  3. Data Lifecycle: Old data loses granularity value; needs             |
|     automatic downsampling and expiration                               |
|                                                                         |
|  4. Compression: Timestamps and values are highly compressible          |
|     with specialized codecs (10-20x vs generic compression)             |
|                                                                         |
|  5. Schema: Metrics appear and disappear dynamically;                   |
|     rigid schemas are a poor fit                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Key Properties of Time-Series Data

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Property             | Implication                                      |
|  ---------------------+--------------------------------------------------|
|  Write-heavy          | Optimize write path above all else               |
|  Append-only          | No random updates; data is immutable once        |
|                       | written                                          |
|  Recent data is hot   | Cache recent data; tiered storage for old        |
|  Time-ordered         | Sequential I/O; exploit temporal locality        |
|  Bulk deletes         | Drop entire time partitions, not individual      |
|                       | rows                                             |
|  High cardinality     | Tag combinations can explode; must manage        |
|                       | carefully                                        |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## Requirements

### Functional Requirements

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FR-1: Ingest data points (metric + tags + timestamp + value)           |
|  FR-2: Query data by time range for a given metric + tag set            |
|  FR-3: Perform aggregations (avg, sum, min, max, count, percentiles)    |
|  FR-4: Support downsampling / rollup queries                            |
|  FR-5: Support retention policies (auto-delete old data)                |
|  FR-6: Tag-based filtering and grouping (GROUP BY tag)                  |
|  FR-7: Support for multiple value types (float64, int64, bool, string)  |
|  FR-8: Alerting integration (threshold-based triggers)                  |
|  FR-9: Metadata queries (list metrics, list tag values)                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Non-Functional Requirements

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NFR-1: High write throughput (>= 1M data points/sec)                   |
|  NFR-2: Low-latency reads for recent data (< 10ms for last hour)        |
|  NFR-3: Efficient range scans (sequential I/O optimized)                |
|  NFR-4: High compression ratio (>= 10:1 for typical metrics)            |
|  NFR-5: Horizontal scalability (add nodes to increase capacity)         |
|  NFR-6: Durability (no data loss on single node failure)                |
|  NFR-7: Availability (99.9%+ uptime)                                    |
|  NFR-8: Multi-year retention (years of raw data, decades of rollups)    |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## Scale Estimation

### Given Numbers

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Metrics:           10 million unique time series                       |
|  Write throughput:  1 million data points per second                    |
|  Data points/day:   1 billion                                           |
|  Retention:         Raw data: 30 days                                   |
|                     1-min rollups: 1 year                               |
|                     1-hour rollups: 5 years                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Storage Estimation

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Single data point (uncompressed):                                      |
|    - Timestamp:  8 bytes (int64, nanoseconds)                           |
|    - Value:      8 bytes (float64)                                      |
|    - Overhead:   ~4 bytes (series reference, alignment)                 |
|    - Total:      ~20 bytes per point                                    |
|                                                                         |
|  With compression (Gorilla-style, ~12:1 ratio):                         |
|    - Compressed: ~1.6 bytes per point                                   |
|                                                                         |
|  Daily raw storage:                                                     |
|    - Uncompressed: 1B points x 20 bytes = 20 GB/day                     |
|    - Compressed:   1B points x 1.6 bytes = 1.6 GB/day                   |
|                                                                         |
|  30-day raw retention:                                                  |
|    - Compressed: 1.6 GB x 30 = ~48 GB                                   |
|                                                                         |
|  1-min rollups (1 year):                                                |
|    - Points/day: 1B / 60 = ~16.7M                                       |
|    - Per rollup: ~40 bytes (min, max, sum, count, avg)                  |
|    - Daily: 16.7M x 40 bytes = ~670 MB (compressed ~60 MB)              |
|    - Yearly: 60 MB x 365 = ~22 GB                                       |
|                                                                         |
|  Total estimated storage: ~100-200 GB (well within single-cluster)      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Throughput Estimation

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Write throughput:                                                      |
|    - 1M points/sec x 20 bytes = 20 MB/sec sustained write               |
|    - With batching: ~50K batch inserts/sec (20 points/batch avg)        |
|                                                                         |
|  Read throughput:                                                       |
|    - Dashboard queries: ~10K queries/sec (mostly recent data)           |
|    - Alerting evaluations: ~100K rule evaluations/min                   |
|    - Typical query: scan 1 hour of 1 metric = ~3600 points              |
|                                                                         |
|  Network:                                                               |
|    - Ingestion: 20 MB/sec + protocol overhead = ~40 MB/sec              |
|    - Query responses: ~100 MB/sec peak                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## High-Level Architecture

```
+--------------------------------------------------------------------------+
|                         TSDB SYSTEM OVERVIEW                             |
+--------------------------------------------------------------------------+
|                                                                          |
|  +-------------+    +-------------+    +-------------+                   |
|  |  Collector  |    |  Collector  |    |  Collector  |                   |
|  |  (Agent)    |    |  (Agent)    |    |  (Agent)    |                   |
|  +------+------+    +------+------+    +------+------+                   |
|         |                  |                  |                          |
|         +------------------+------------------+                          |
|                            |                                             |
|                     +------v------+                                      |
|                     |   Load      |                                      |
|                     |  Balancer   |                                      |
|                     +------+------+                                      |
|                            |                                             |
|              +-------------+-------------+                               |
|              |                           |                               |
|       +------v------+            +------v------+                         |
|       |   Write     |            |   Query     |                         |
|       |   Gateway   |            |   Gateway   |                         |
|       +------+------+            +------+------+                         |
|              |                           |                               |
|       +------v------+            +------v------+                         |
|       |  Ingestion  |            |   Query     |                         |
|       |  Pipeline   |            |   Engine    |                         |
|       +------+------+            +------+------+                         |
|              |                           |                               |
|              +-------------+-------------+                               |
|                            |                                             |
|                     +------v------+                                      |
|                     |  Storage    |                                      |
|                     |  Engine     |                                      |
|                     +------+------+                                      |
|                            |                                             |
|              +-------------+-------------+                               |
|              |             |             |                               |
|       +------v---+  +-----v----+  +-----v----+                           |
|       | Recent   |  | Warm     |  | Cold     |                           |
|       | (Memory  |  | (SSD)    |  | (HDD/S3) |                           |
|       |  + SSD)  |  |          |  |          |                           |
|       +----------+  +----------+  +----------+                           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Component Overview

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Component          | Responsibility                                    |
|  -------------------+---------------------------------------------------|
|  Collectors/Agents  | Scrape or receive metrics from applications       |
|  Write Gateway      | Accept writes, validate, route to correct shard   |
|  Ingestion Pipeline | Batch, compress, write to WAL and memtable        |
|  Query Gateway      | Parse queries, plan execution, aggregate results  |
|  Query Engine       | Execute scans, apply filters, compute aggregates  |
|  Storage Engine     | Manage on-disk storage, compaction, retention     |
|  Metadata Store     | Track active series, tags, label indexes          |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## Data Model

### Core Concepts

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A time series is uniquely identified by:                               |
|                                                                         |
|    metric_name{tag1="val1", tag2="val2", ...}                           |
|                                                                         |
|  Example:                                                               |
|    cpu_usage{host="web-01", region="us-east", core="0"}                 |
|                                                                         |
|  Each time series contains ordered pairs:                               |
|    [(t1, v1), (t2, v2), (t3, v3), ...]                                  |
|                                                                         |
|  Where:                                                                 |
|    t = timestamp (int64 nanoseconds since epoch)                        |
|    v = value (float64 for most metrics)                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Internal Representation

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Series ID (TSID):                                                      |
|    - Hash of (metric_name + sorted tags)                                |
|    - uint64, used as internal identifier                                |
|    - Avoids repeating full label set for every point                    |
|                                                                         |
|  Series Index (Inverted Index):                                         |
|    - tag_key=tag_value -> Set of TSIDs                                  |
|    - Enables fast lookup: "give me all series where region=us-east"     |
|                                                                         |
|  Data Storage:                                                          |
|    - Organized by TSID + time block                                     |
|    - Each block covers a fixed time range (e.g., 2 hours)               |
|    - Within a block: compressed arrays of timestamps and values         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Schema Example

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Logical View:                                                          |
|                                                                         |
|  +----------------+-------------------------------------------+         |
|  | Series ID      | Metric + Tags                             |         |
|  +----------------+-------------------------------------------+         |
|  | 0x7A3F01       | cpu_usage{host="web-01", core="0"}        |         |
|  | 0x7A3F02       | cpu_usage{host="web-01", core="1"}        |         |
|  | 0x7A3F03       | mem_free{host="web-01"}                   |         |
|  +----------------+-------------------------------------------+         |
|                                                                         |
|  Data Blocks:                                                           |
|                                                                         |
|  +----------+---------------------------+---------------------------+   |
|  | TSID     | Timestamps (compressed)   | Values (compressed)       |   |
|  +----------+---------------------------+---------------------------+   |
|  | 0x7A3F01 | [delta-of-delta encoded]  | [XOR float compressed]    |   |
|  | 0x7A3F02 | [delta-of-delta encoded]  | [XOR float compressed]    |   |
|  +----------+---------------------------+---------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## Storage Engine Design

### LSM-Tree Optimized for Time-Series

Traditional LSM-trees work well for write-heavy workloads, but we adapt them
specifically for time-series patterns.

```
+--------------------------------------------------------------------------+
|                                                                          |
|                    TIME-SERIES LSM STORAGE ENGINE                        |
|                                                                          |
|  Write Request                                                           |
|       |                                                                  |
|       v                                                                  |
|  +----------+     +------------------------------------------+           |
|  |   WAL    |---->|  Write-Ahead Log (sequential append)     |           |
|  +----------+     +------------------------------------------+           |
|       |                                                                  |
|       v                                                                  |
|  +----------+     +------------------------------------------+           |
|  | MemTable |---->|  In-memory sorted structure (per series)  |          |
|  +----------+     +------------------------------------------+           |
|       |                                                                  |
|       | (flush when full or time block closes)                           |
|       v                                                                  |
|  +----------+     +------------------------------------------+           |
|  |  Block   |---->|  Immutable compressed block on disk       |          |
|  |  File    |     |  Contains: index + data + metadata        |          |
|  +----------+     +------------------------------------------+           |
|       |                                                                  |
|       | (compaction merges overlapping blocks)                           |
|       v                                                                  |
|  +----------+     +------------------------------------------+           |
|  | Compacted|---->|  Larger, optimized blocks                 |          |
|  |  Blocks  |     |  Non-overlapping time ranges              |          |
|  +----------+     +------------------------------------------+           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Time-Based Block Organization

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Timeline:                                                               |
|  |----2h----|----2h----|----2h----|----2h----|                           |
|  | Block 1  | Block 2  | Block 3  | Block 4  |                           |
|  |  (disk)  |  (disk)  |  (disk)  | (memory) |                           |
|                                                                          |
|  Each block contains:                                                    |
|  +---------------------------------------------------+                   |
|  |  Block Header                                     |                   |
|  |    - Min/Max timestamp                            |                   |
|  |    - Number of series                             |                   |
|  |    - Number of data points                        |                   |
|  +---------------------------------------------------+                   |
|  |  Series Index                                     |                   |
|  |    - TSID -> offset in data section               |                   |
|  +---------------------------------------------------+                   |
|  |  Data Section                                     |                   |
|  |    - Per series: compressed timestamps + values   |                   |
|  +---------------------------------------------------+                   |
|  |  Label Index                                      |                   |
|  |    - Inverted index for tag-based lookups         |                   |
|  +---------------------------------------------------+                   |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Columnar vs Row-Based Storage

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Row-Based (traditional):                                               |
|    [ts1, val1] [ts2, val2] [ts3, val3] ...                              |
|    - Good for point lookups                                             |
|    - Poor compression (mixed types interleaved)                         |
|                                                                         |
|  Columnar (TSDB preferred):                                             |
|    Timestamps: [ts1, ts2, ts3, ...]  <- delta encoding works great      |
|    Values:     [val1, val2, val3, ...] <- XOR compression works great   |
|    - Excellent compression (same-type arrays)                           |
|    - Ideal for range scans and aggregations                             |
|    - Can skip value column if only checking timestamps                  |
|                                                                         |
|  Recommendation: Columnar storage within each block, organized by       |
|  time series. Each series chunk stores timestamps and values as         |
|  separate compressed arrays.                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## Write Path

### End-to-End Write Flow

```
+-------------------------------------------------------------------------+
|                                                                         |
|               WRITE PATH (DETAILED)                                     |
|                                                                         |
|  1. Client sends batch of data points                                   |
|     |                                                                   |
|     v                                                                   |
|  2. Write Gateway receives request                                      |
|     - Validates format and timestamps                                   |
|     - Resolves or creates Series IDs (TSID)                             |
|     - Routes to correct shard based on TSID                             |
|     |                                                                   |
|     v                                                                   |
|  3. Ingestion Node processes the batch                                  |
|     - Appends to Write-Ahead Log (WAL) for durability                   |
|     - Inserts into in-memory MemTable                                   |
|     |                                                                   |
|     v                                                                   |
|  4. MemTable accumulates data points                                    |
|     - Organized per-series for efficient compression                    |
|     - When block time window closes (e.g., every 2 hours):              |
|       a. Freeze current MemTable                                        |
|       b. Compress and flush to disk as immutable Block                  |
|       c. Truncate WAL up to flushed point                               |
|     |                                                                   |
|     v                                                                   |
|  5. Background compaction                                               |
|     - Merges small blocks into larger ones                              |
|     - Removes deleted series                                            |
|     - Optimizes for sequential reads                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Write-Ahead Log (WAL)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WAL Design:                                                            |
|                                                                         |
|  +--------+--------+--------+--------+--------+                         |
|  | Entry1 | Entry2 | Entry3 | Entry4 | Entry5 | ...                     |
|  +--------+--------+--------+--------+--------+                         |
|                                                                         |
|  Each WAL Entry:                                                        |
|  +------------------------------------------+                           |
|  | CRC32 checksum | Length | Series ID |    |                           |
|  | Timestamp      | Value  |                |                           |
|  +------------------------------------------+                           |
|                                                                         |
|  Properties:                                                            |
|  - Sequential append only (fast on any storage)                         |
|  - Segmented into fixed-size files (e.g., 128 MB)                       |
|  - Old segments deleted after successful block flush                    |
|  - On crash recovery: replay WAL from last checkpoint                   |
|                                                                         |
|  Optimization: Batch WAL writes (group commit)                          |
|  - Accumulate entries for ~10ms, then fsync once                        |
|  - Trades tiny latency increase for massive throughput gain             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MemTable Design

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MemTable Structure (per ingestion node):                               |
|                                                                         |
|  +-------------------+                                                  |
|  | Active MemTable   |  <- Accepts new writes                           |
|  +-------------------+                                                  |
|  |                   |                                                  |
|  |  Series Map:      |                                                  |
|  |  TSID -> Buffer   |                                                  |
|  |                   |                                                  |
|  |  0x7A3F01 -> [(t1,v1), (t2,v2), ...]                                 |
|  |  0x7A3F02 -> [(t1,v1), (t2,v2), ...]                                 |
|  |  0x7A3F03 -> [(t1,v1), (t2,v2), ...]                                 |
|  |                   |                                                  |
|  +-------------------+                                                  |
|                                                                         |
|  When flushing:                                                         |
|  1. Current MemTable becomes "frozen" (read-only)                       |
|  2. New MemTable created for incoming writes                            |
|  3. Frozen MemTable compressed and written to block file                |
|  4. Frozen MemTable freed from memory                                   |
|                                                                         |
|  Memory budget: ~2-4 GB per node for active + frozen tables             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Compaction Strategy

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Time-Based Compaction:                                                 |
|                                                                         |
|  Before compaction:                                                     |
|  |--2h--|--2h--|--2h--|--2h--|--2h--|--2h--|                            |
|  | B1   | B2   | B3   | B4   | B5   | B6   |                            |
|                                                                         |
|  After compaction (level 1):                                            |
|  |------6h------|------6h------|                                        |
|  |   B1+B2+B3   |   B4+B5+B6   |                                        |
|                                                                         |
|  After compaction (level 2):                                            |
|  |-------------12h-------------|                                        |
|  |        B1+B2+B3+B4+B5+B6    |                                        |
|                                                                         |
|  Benefits:                                                              |
|  - Fewer files to open for range queries                                |
|  - Better compression ratios (more data to compress together)           |
|  - Opportunity to drop deleted series                                   |
|  - Aligned time boundaries simplify query planning                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## Read Path

### Query Execution Flow

```
+-------------------------------------------------------------------------+
|                                                                         |
|               READ PATH (DETAILED)                                      |
|                                                                         |
|  1. Client sends query                                                  |
|     Example: avg(cpu_usage{region="us-east"}) over last 1 hour          |
|     |                                                                   |
|     v                                                                   |
|  2. Query Gateway parses and plans                                      |
|     - Parse query into AST                                              |
|     - Identify time range: [now-1h, now]                                |
|     - Identify label matchers: region="us-east"                         |
|     - Determine which shards to query                                   |
|     |                                                                   |
|     v                                                                   |
|  3. Series Resolution                                                   |
|     - Query inverted index: region="us-east" -> {TSID1, TSID2, ...}     |
|     - Intersect with metric_name="cpu_usage" -> final TSID set          |
|     |                                                                   |
|     v                                                                   |
|  4. Block Selection                                                     |
|     - Find blocks overlapping [now-1h, now]                             |
|     - For each matching block, read series index                        |
|     - Locate data chunks for matching TSIDs                             |
|     |                                                                   |
|     v                                                                   |
|  5. Data Retrieval                                                      |
|     - Decompress timestamp + value arrays                               |
|     - Apply time range filter (trim to exact range)                     |
|     - For MemTable data: read directly from memory                      |
|     |                                                                   |
|     v                                                                   |
|  6. Aggregation                                                         |
|     - Compute avg() across all matching series                          |
|     - Apply step interval (e.g., 1 point per minute)                    |
|     - Return result as time series of aggregated values                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Aggregation Types

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Supported Aggregations:                                                |
|                                                                         |
|  Basic:                                                                 |
|    - avg(series)    : Mean of values in each time step                  |
|    - sum(series)    : Sum of values in each time step                   |
|    - min(series)    : Minimum value in each time step                   |
|    - max(series)    : Maximum value in each time step                   |
|    - count(series)  : Number of data points per step                    |
|                                                                         |
|  Statistical:                                                           |
|    - percentile(series, 99)  : P99 latency calculation                  |
|    - stddev(series)          : Standard deviation                       |
|    - rate(series)            : Per-second rate of change                |
|    - irate(series)           : Instantaneous rate (last 2 points)       |
|    - increase(series)        : Total increase over range                |
|                                                                         |
|  Grouping:                                                              |
|    - ... by (tag)            : Split into groups by tag value           |
|    - ... without (tag)       : Group by all tags except specified       |
|                                                                         |
|  Percentile computation:                                                |
|    - Exact: sort all values, pick index (expensive for large sets)      |
|    - Approximate: t-digest or HDR histogram (streaming-friendly)        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Query Optimization

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Optimization Techniques:                                               |
|                                                                         |
|  1. Block-level min/max filtering                                       |
|     - Each block stores min/max timestamps and value ranges             |
|     - Skip entire blocks that cannot contain matching data              |
|                                                                         |
|  2. Predicate pushdown                                                  |
|     - Push label filters into the index lookup phase                    |
|     - Avoid scanning data for non-matching series                       |
|                                                                         |
|  3. Chunk-level caching                                                 |
|     - LRU cache for recently accessed compressed chunks                 |
|     - Hot data stays in memory after first access                       |
|                                                                         |
|  4. Parallel scan                                                       |
|     - Different blocks/series scanned concurrently                      |
|     - Aggregate partial results with merge step                         |
|                                                                         |
|  5. Pre-aggregation (materialized rollups)                              |
|     - For common queries, store pre-computed aggregates                 |
|     - Trade storage for query speed                                     |
|                                                                         |
|  6. Query result caching                                                |
|     - Cache immutable time range results                                |
|     - Only recompute the "open" (current) time block                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## Compression Techniques

### Why Compression Matters

```
+-------------------------------------------------------------------------+
|                                                                         |
|  At 1B points/day, compression directly determines:                     |
|    - Storage cost (10x compression = 10x cost reduction)                |
|    - I/O throughput (less data to read = faster queries)                |
|    - Cache efficiency (more data fits in memory)                        |
|                                                                         |
|  Typical compression ratios for time-series data:                       |
|    - Generic (gzip, lz4):         3-5x                                  |
|    - Specialized (Gorilla):       10-15x                                |
|    - Specialized + generic:       15-20x                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Timestamp Compression: Delta-of-Delta

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Observation: Metrics are usually collected at regular intervals         |
|  (e.g., every 15 seconds).                                               |
|                                                                          |
|  Raw timestamps:     [1000, 1015, 1030, 1045, 1060, 1075]                |
|                                                                          |
|  Step 1 - Delta encoding:                                                |
|    Deltas:           [1000, 15, 15, 15, 15, 15]                          |
|    (First value stored as-is, rest as differences)                       |
|                                                                          |
|  Step 2 - Delta of delta:                                                |
|    Delta-of-delta:   [1000, 15, 0, 0, 0, 0]                              |
|    (Most values are 0 when collection interval is regular!)              |
|                                                                          |
|  Step 3 - Variable-length encoding:                                      |
|    0  -> 1 bit  (single '0' bit)                                         |
|    Small delta-of-delta -> few bits                                      |
|    Large delta-of-delta -> more bits                                     |
|                                                                          |
|  Result: Regular 15-second metrics compress to ~1 bit/timestamp          |
|                                                                          |
|  Encoding scheme (from Facebook Gorilla paper):                          |
|  +------+-------+---------------------------------------------+          |
|  | Bits | Range | Encoding                                    |          |
|  +------+-------+---------------------------------------------+          |
|  | 1    | 0     | '0'                                         |          |
|  | 10   | <=63  | '10' + 7 bits                               |          |
|  | 14   | <=255 | '110' + 9 bits                              |          |
|  | 17   | <=2047| '1110' + 12 bits                            |          |
|  | 36   | else  | '1111' + 32 bits                            |          |
|  +------+-------+---------------------------------------------+          |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Value Compression: XOR Float Encoding

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Observation: Consecutive metric values are often similar               |
|  (e.g., CPU usage: 45.2, 45.3, 45.1, 45.4)                              |
|                                                                         |
|  XOR Encoding (Gorilla paper):                                          |
|                                                                         |
|  1. Store first value as raw 64-bit float                               |
|  2. For each subsequent value, XOR with previous                        |
|     - If XOR == 0: values are identical, store single '0' bit           |
|     - If XOR != 0: find leading and trailing zeros                      |
|       - If same window as previous: '10' + significant bits             |
|       - If different window: '11' + 5 bits leading + 6 bits length      |
|         + significant bits                                              |
|                                                                         |
|  Example:                                                               |
|    v1 = 45.2 (stored as 64-bit float: 0x4049999999999A)                 |
|    v2 = 45.3                                                            |
|    XOR = v1 XOR v2 = 0x0000000000000200                                 |
|    Leading zeros: 53, Trailing zeros: 9, Significant bits: 2            |
|    -> Store just 2 significant bits + metadata                          |
|                                                                         |
|  For slowly-changing metrics: ~1-2 bits per value!                      |
|  For volatile metrics: ~15-30 bits per value                            |
|  Average across typical workloads: ~5-8 bits per value                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Combined Compression Pipeline

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Full Compression Pipeline:                                             |
|                                                                         |
|  Raw Data  ->  Columnar Split  ->  Specialized  ->  Block Compression   |
|                                    Encoding                             |
|                                                                         |
|  [ts, val]    Timestamps[]        Delta-of-delta    Optional LZ4/       |
|  [ts, val]    Values[]            XOR float         Snappy on top       |
|  [ts, val]                                                              |
|                                                                         |
|  Compression ratios at each stage:                                      |
|  +----------------------------------+--------+                          |
|  | Stage                            | Ratio  |                          |
|  +----------------------------------+--------+                          |
|  | Raw (16 bytes/point)             | 1x     |                          |
|  | + Delta-of-delta timestamps      | 2-3x   |                          |
|  | + XOR float values               | 6-10x  |                          |
|  | + Block compression (LZ4)        | 10-15x |                          |
|  +----------------------------------+--------+                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## Retention Policies and Downsampling

### Retention Tiers

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Retention Strategy:                                                    |
|                                                                         |
|  Time Since Write     Resolution     Storage Tier     Action            |
|  -------------------+-------------+-----------------+------------------+|
|  0 - 2 hours        | Raw (15s)   | Memory + WAL    | Active ingest   | |
|  2 hours - 30 days  | Raw (15s)   | SSD              | Query-optimized ||
|  30 days - 1 year   | 1-minute    | SSD/HDD          | Downsampled     ||
|  1 year - 5 years   | 1-hour      | HDD/Object Store | Archival        ||
|  > 5 years          | Deleted     | N/A              | Purged          ||
|  -------------------+-------------+-----------------+------------------+|
|                                                                         |
+-------------------------------------------------------------------------+
```

### Downsampling (Rollup) Process

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Downsampling Pipeline:                                                 |
|                                                                         |
|  Raw data (15-second intervals):                                        |
|  [t1:45.2] [t2:45.3] [t3:45.1] [t4:45.4] ... (4 points per minute)      |
|                                                                         |
|       | Rollup to 1-minute                                              |
|       v                                                                 |
|  1-minute aggregate (for each minute window):                           |
|  +-----------------------------------------------------+                |
|  | min: 45.1 | max: 45.4 | sum: 181.0 | count: 4      |                 |
|  | avg: 45.25 (computed from sum/count)                 |               |
|  +-----------------------------------------------------+                |
|                                                                         |
|       | Rollup to 1-hour (from 1-minute rollups)                        |
|       v                                                                 |
|  1-hour aggregate (for each hour window):                               |
|  +-----------------------------------------------------+                |
|  | min: min(all 1-min mins)                             |               |
|  | max: max(all 1-min maxes)                            |               |
|  | sum: sum(all 1-min sums)                             |               |
|  | count: sum(all 1-min counts)                         |               |
|  +-----------------------------------------------------+                |
|                                                                         |
|       | Rollup to 1-day (from 1-hour rollups)                           |
|       v                                                                 |
|  1-day aggregate: same pattern                                          |
|                                                                         |
|  Key: Store min, max, sum, count (not just avg) to enable               |
|  correct re-aggregation at coarser granularities.                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Automatic Retention Enforcement

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Retention Enforcement:                                                 |
|                                                                         |
|  1. Time-based block organization makes deletion trivial:               |
|     - Each block covers a fixed time range                              |
|     - To delete data older than 30 days: delete block files             |
|     - No expensive row-by-row deletion                                  |
|                                                                         |
|  2. Downsampling runs as a background job:                              |
|     - Triggered when blocks age past a threshold                        |
|     - Reads raw blocks, computes rollups, writes rollup blocks          |
|     - Raw blocks deleted only after rollups are confirmed durable       |
|                                                                         |
|  3. Tiered storage migration:                                           |
|     - Hot blocks (recent) on fast SSD                                   |
|     - Warm blocks moved to cheaper SSD/HDD                              |
|     - Cold blocks moved to object storage (S3)                          |
|     - Metadata always on SSD for fast lookups                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## Sharding and Partitioning

### Sharding Strategies

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Strategy 1: Shard by Time (Time-Based Partitioning)                    |
|                                                                         |
|  +--------+  +--------+  +--------+  +--------+                         |
|  | Day 1  |  | Day 2  |  | Day 3  |  | Day 4  |                         |
|  | All    |  | All    |  | All    |  | All    |                         |
|  | series |  | series |  | series |  | series |                         |
|  +--------+  +--------+  +--------+  +--------+                         |
|                                                                         |
|  Pros: Simple deletion, natural for time-range queries                  |
|  Cons: All writes go to one partition (today), hotspot problem          |
|                                                                         |
|  ---------------------------------------------------------------        |
|                                                                         |
|  Strategy 2: Shard by Metric (Hash-Based)                               |
|                                                                         |
|  +--------+  +--------+  +--------+  +--------+                         |
|  | Shard0 |  | Shard1 |  | Shard2 |  | Shard3 |                         |
|  | A-F    |  | G-L    |  | M-R    |  | S-Z    |                         |
|  | series |  | series |  | series |  | series |                         |
|  +--------+  +--------+  +--------+  +--------+                         |
|                                                                         |
|  Pros: Write load distributed, parallel queries                         |
|  Cons: Cross-shard queries needed, deletion requires all shards         |
|                                                                         |
|  ---------------------------------------------------------------        |
|                                                                         |
|  Strategy 3: Shard by Time AND Metric (Recommended)                     |
|                                                                         |
|  +------------------+------------------+                                |
|  |   Day 1          |   Day 2          |                                |
|  | +------+------+  | +------+------+  |                                |
|  | |Shard0|Shard1|  | |Shard0|Shard1|  |                                |
|  | | A-M  | N-Z  |  | | A-M  | N-Z  |  |                                |
|  | +------+------+  | +------+------+  |                                |
|  +------------------+------------------+                                |
|                                                                         |
|  Pros: Distributes writes, efficient time deletion, parallel reads      |
|  Cons: More complex routing, more shards to manage                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Consistent Hashing for Series Assignment

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Series -> Shard Assignment:                                            |
|                                                                         |
|  1. Compute TSID = hash(metric_name + sorted_tags)                      |
|  2. Map TSID to shard using consistent hash ring                        |
|  3. Each shard owns a range of the hash space                           |
|                                                                         |
|         +-----+                                                         |
|        /       \                                                        |
|       / Shard 0 \                                                       |
|      |   0-63    |                                                      |
|      |           |                                                      |
|  +---+           +---+                                                  |
|  |Shard 3        Shard 1|                                               |
|  |192-255        64-127 |                                               |
|  +---+           +---+                                                  |
|      |           |                                                      |
|      | Shard 2   |                                                      |
|       \ 128-191 /                                                       |
|        \       /                                                        |
|         +-----+                                                         |
|                                                                         |
|  Rebalancing: When adding/removing shards, only ~1/N series move        |
|  Virtual nodes: Each physical node owns multiple ranges for balance     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Replication

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Replication Strategy:                                                  |
|                                                                         |
|  - Replication factor: 3 (configurable)                                 |
|  - Write quorum: 2 of 3 (W=2)                                           |
|  - Read quorum: 1 of 3 (R=1) for recent data                            |
|                                                                         |
|  Write Flow:                                                            |
|  Client -> Write Gateway -> Primary Shard -> Replica 1                  |
|                                           -> Replica 2                  |
|                                                                         |
|  Ack to client after W replicas confirm.                                |
|  Async replication for remaining replicas.                              |
|                                                                         |
|  For time-series, eventual consistency is usually acceptable:           |
|  - Monitoring dashboards tolerate slight delays                         |
|  - Alerts can use the primary replica                                   |
|  - Historical queries are immutable once block is closed                |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## Query Language Comparison

```
+--------------------------------------------------------------------------+
|                                                                          |
|  PromQL (Prometheus):                                                    |
|    avg(rate(http_requests_total{job="api"}[5m])) by (method)             |
|    - Functional style                                                    |
|    - Built-in rate, histogram functions                                  |
|    - No JOIN or subqueries (limited)                                     |
|                                                                          |
|  InfluxQL (InfluxDB):                                                    |
|    SELECT mean("value") FROM "cpu_usage"                                 |
|    WHERE "region" = 'us-east' AND time > now() - 1h                      |
|    GROUP BY time(1m), "host"                                             |
|    - SQL-like syntax                                                     |
|    - Familiar to SQL users                                               |
|    - Limited expressiveness for complex transformations                  |
|                                                                          |
|  Flux (InfluxDB 2.0):                                                    |
|    from(bucket: "metrics")                                               |
|      |> range(start: -1h)                                                |
|      |> filter(fn: (r) => r._measurement == "cpu")                       |
|      |> aggregateWindow(every: 1m, fn: mean)                             |
|    - Pipe-based functional language                                      |
|    - Very expressive                                                     |
|    - Steeper learning curve                                              |
|                                                                          |
|  SQL Extensions (TimescaleDB):                                           |
|    SELECT time_bucket('1 minute', time) AS bucket,                       |
|           avg(value)                                                     |
|    FROM metrics                                                          |
|    WHERE metric_name = 'cpu_usage'                                       |
|      AND time > NOW() - INTERVAL '1 hour'                                |
|    GROUP BY bucket                                                       |
|    ORDER BY bucket;                                                      |
|    - Full SQL + time-series extensions                                   |
|    - JOINs, subqueries, CTEs all work                                    |
|    - Leverages existing SQL ecosystem                                    |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## Real-World System Comparison

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Feature         | InfluxDB  | TimescaleDB| Prometheus | VictoriaM      |
|  ----------------+-----------+------------+------------+--------------  |
|  Storage Engine  | Custom    | PostgreSQL | Custom     | Custom         |
|  Query Language  | InfluxQL/ | SQL        | PromQL     | PromQL+        |
|                  | Flux      |            |            | MetricsQL      |
|  Clustering      | Enterprise| PostgreSQL | Thanos/    | Built-in       |
|                  | only      | native     | Cortex     |                |
|  Compression     | Custom    | PostgreSQL | Gorilla    | Custom         |
|                  |           | + custom   |            | (excellent)    |
|  Cardinality     | Moderate  | High       | Limited    | Very High      |
|  Write Perf      | High      | Moderate   | High       | Very High      |
|  Long-term       | Built-in  | Built-in   | Needs      | Built-in       |
|  Storage         |           |            | Thanos/S3  |                |
|  Best For        | General   | SQL users  | Kubernetes | High-scale     |
|                  | TSDB use  | hybrid     | monitoring | monitoring     |
|  License         | MIT/      | Apache 2.0 | Apache 2.0 | Apache 2.0     |
|                  | Commercial|            |            |                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Key Architectural Differences

```
+-------------------------------------------------------------------------+
|                                                                         |
|  InfluxDB:                                                              |
|  - Custom storage engine (TSM - Time Structured Merge Tree)             |
|  - Inverted index for tag lookups                                       |
|  - Write-optimized with WAL + TSM files                                 |
|  - Cardinality limits can be a problem at scale                         |
|                                                                         |
|  TimescaleDB:                                                           |
|  - Extension on top of PostgreSQL                                       |
|  - Hypertables = auto-partitioned tables by time                        |
|  - Full SQL support including JOINs with relational data                |
|  - Leverages PostgreSQL ecosystem (backup, replication, etc.)           |
|                                                                         |
|  Prometheus:                                                            |
|  - Pull-based model (scrapes targets on schedule)                       |
|  - Local storage only (not designed for long-term)                      |
|  - Thanos/Cortex adds long-term storage and global view                 |
|  - Excellent Kubernetes integration                                     |
|                                                                         |
|  VictoriaMetrics:                                                       |
|  - Prometheus-compatible but much more efficient                        |
|  - Handles very high cardinality better                                 |
|  - Built-in clustering and long-term storage                            |
|  - Lower resource usage than alternatives                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## Use Cases

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. Infrastructure Monitoring                                           |
|     - CPU, memory, disk, network metrics from servers                   |
|     - Container/pod metrics from Kubernetes                             |
|     - Typical: 100K-10M series, 15-60 second intervals                  |
|     - Query pattern: dashboards + alerting rules                        |
|                                                                         |
|  2. Application Performance Monitoring (APM)                            |
|     - Request latency histograms, error rates, throughput               |
|     - Distributed tracing metrics (span durations)                      |
|     - Typical: 1M-100M series, high cardinality tags                    |
|     - Query pattern: P99 latency over time, error rate spikes           |
|                                                                         |
|  3. IoT / Sensor Data                                                   |
|     - Temperature, humidity, pressure from millions of devices          |
|     - Typical: 10M-1B series, irregular intervals                       |
|     - Query pattern: aggregations over device groups, anomaly detect    |
|                                                                         |
|  4. Financial Market Data                                               |
|     - Stock prices, trading volumes, order book snapshots               |
|     - Typical: 100K series, sub-second intervals                        |
|     - Query pattern: OHLCV candles, VWAP, technical indicators          |
|     - Requirement: exact values, no lossy compression                   |
|                                                                         |
|  5. Network / Telecom Monitoring                                        |
|     - Bandwidth, packet loss, latency per link/device                   |
|     - Typical: millions of interfaces, 5-minute SNMP polls              |
|     - Query pattern: top-N talkers, capacity planning                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## Trade-offs and Design Decisions

### Key Trade-offs

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Trade-off 1: Write Latency vs Durability                               |
|                                                                         |
|  Option A: Sync WAL on every write                                      |
|    + Zero data loss on crash                                            |
|    - 10x slower writes (fsync bottleneck)                               |
|                                                                         |
|  Option B: Batch WAL writes (group commit every 10ms)                   |
|    + 10x higher write throughput                                        |
|    - Up to 10ms of data loss on crash                                   |
|                                                                         |
|  Decision: Option B for monitoring (10ms loss acceptable)               |
|            Option A for financial data (no loss tolerated)              |
|                                                                         |
|  ---------------------------------------------------------------        |
|                                                                         |
|  Trade-off 2: Query Flexibility vs Performance                          |
|                                                                         |
|  Option A: Full SQL support (TimescaleDB approach)                      |
|    + JOINs, subqueries, familiar syntax                                 |
|    - SQL optimizer not tuned for time-series patterns                   |
|    - Higher per-query overhead                                          |
|                                                                         |
|  Option B: Custom query language (PromQL approach)                      |
|    + Highly optimized for time-series operations                        |
|    - Limited expressiveness                                             |
|    - Another language to learn                                          |
|                                                                         |
|  Decision: Depends on user base. PromQL for DevOps, SQL for analysts    |
|                                                                         |
|  ---------------------------------------------------------------        |
|                                                                         |
|  Trade-off 3: Compression vs Random Access                              |
|                                                                         |
|  Option A: Compress entire series as one chunk                          |
|    + Maximum compression ratio                                          |
|    - Must decompress entire chunk for any access                        |
|                                                                         |
|  Option B: Compress in small chunks (e.g., 120 points)                  |
|    + Can skip chunks outside query range                                |
|    - Slightly worse compression ratio                                   |
|                                                                         |
|  Decision: Option B with chunk boundaries aligned to time intervals     |
|                                                                         |
|  ---------------------------------------------------------------        |
|                                                                         |
|  Trade-off 4: Push vs Pull Ingestion                                    |
|                                                                         |
|  Push (InfluxDB, VictoriaMetrics):                                      |
|    + Lower latency, applications control when to send                   |
|    + Works across firewalls/NATs                                        |
|    - Risk of overwhelming the TSDB (need backpressure)                  |
|                                                                         |
|  Pull (Prometheus):                                                     |
|    + TSDB controls ingestion rate                                       |
|    + Can detect target failures (scrape failed)                         |
|    - Requires network access to all targets                             |
|    - Harder to scale across networks                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## Failure Handling and Reliability

### Node Failure Scenarios

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Scenario 1: Ingestion Node Failure                                     |
|    Detection: Heartbeat timeout (e.g., 10 seconds)                      |
|    Recovery:                                                            |
|    1. Consistent hash ring marks node as down                           |
|    2. Series reassigned to next node on the ring                        |
|    3. Clients retry writes to new node                                  |
|    4. WAL on failed node replayed when it recovers                      |
|    Data loss window: Last group commit interval (up to 10ms)            |
|                                                                         |
|  Scenario 2: Storage Node Disk Failure                                  |
|    Detection: I/O errors, SMART warnings                                |
|    Recovery:                                                            |
|    1. Mark affected blocks as degraded                                  |
|    2. Serve reads from replicas                                         |
|    3. Re-replicate blocks to healthy nodes                              |
|    4. Replace failed disk, rebuild from replicas                        |
|    Data loss: None (if replication factor >= 2)                         |
|                                                                         |
|  Scenario 3: Network Partition                                          |
|    Detection: Split-brain detection via quorum                          |
|    Recovery:                                                            |
|    1. Majority partition continues serving                              |
|    2. Minority partition rejects writes (or queues locally)             |
|    3. On healing: reconcile using timestamps (last-write-wins)          |
|    Consistency: Eventual, with possible duplicates                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Data Integrity

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Integrity Measures:                                                     |
|                                                                          |
|  1. WAL entries: CRC32 checksum per entry                                |
|     - Detects corruption during replay                                   |
|                                                                          |
|  2. Block files: CRC32 per chunk + SHA256 per block                      |
|     - Verified on reads (optional, configurable)                         |
|     - Verified during compaction                                         |
|                                                                          |
|  3. Replication: Compare block checksums across replicas                 |
|     - Background consistency check (anti-entropy)                        |
|     - Repair from healthy replica if mismatch                            |
|                                                                          |
|  4. Idempotent writes:                                                   |
|     - Same (series, timestamp, value) written twice = no effect          |
|     - Enables safe retries on failure                                    |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## Monitoring the Monitor

```
+--------------------------------------------------------------------------+
|                                                                          |
|  A TSDB used for monitoring must itself be monitored.                    |
|                                                                          |
|  Key Internal Metrics:                                                   |
|                                                                          |
|  Ingestion:                                                              |
|    - tsdb_ingested_samples_total (rate of ingestion)                     |
|    - tsdb_wal_write_duration_seconds (WAL write latency)                 |
|    - tsdb_head_active_series (current active series count)               |
|    - tsdb_head_series_created_total (series churn rate)                  |
|                                                                          |
|  Storage:                                                                |
|    - tsdb_blocks_total (number of on-disk blocks)                        |
|    - tsdb_compactions_total (compaction rate)                            |
|    - tsdb_storage_size_bytes (total storage used)                        |
|    - tsdb_compression_ratio (actual compression achieved)                |
|                                                                          |
|  Queries:                                                                |
|    - tsdb_query_duration_seconds (query latency histogram)               |
|    - tsdb_query_samples_scanned (per-query efficiency)                   |
|    - tsdb_query_cache_hit_ratio (cache effectiveness)                    |
|                                                                          |
|  Approach: Export these metrics in the same format the TSDB ingests      |
|  (e.g., Prometheus exposition format). Use a separate, small             |
|  monitoring instance to watch the main cluster.                          |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## Interview Q&A

### Q1: Why not use a regular relational database for time-series data?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  A: Relational databases are designed for random reads/writes with       |
|  B-tree indexes. Time-series data has fundamentally different access     |
|  patterns:                                                               |
|                                                                          |
|  1. Writes are append-only (no updates). B-tree write amplification      |
|     wastes I/O on maintaining sorted structures.                         |
|                                                                          |
|  2. Reads are sequential time-range scans. Row-based storage forces      |
|     reading unnecessary columns.                                         |
|                                                                          |
|  3. Timestamps and values compress 10-15x with specialized codecs.       |
|     Generic databases achieve only 3-5x.                                 |
|                                                                          |
|  4. Retention policies need bulk deletion by time range. Deleting        |
|     millions of rows from a B-tree is expensive; dropping a time         |
|     partition is O(1).                                                   |
|                                                                          |
|  5. Schema is dynamic -- new metrics appear constantly. Rigid schemas    |
|     require ALTER TABLE for each new metric.                             |
|                                                                          |
|  Exception: TimescaleDB bridges this gap by adding time-series           |
|  optimizations (hypertables, compression) on top of PostgreSQL.          |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q2: Explain Gorilla compression and why it works for time-series.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A: Facebook's Gorilla paper (2015) introduced two key techniques:      |
|                                                                         |
|  1. Delta-of-delta for timestamps: Since metrics are collected at       |
|     regular intervals, the difference between consecutive deltas is     |
|     usually 0. This compresses to 1 bit per timestamp.                  |
|                                                                         |
|  2. XOR for float values: Consecutive metric values are often similar.  |
|     XOR of similar float64 values has many leading/trailing zeros,      |
|     which can be encoded in just a few bits.                            |
|                                                                         |
|  Combined result: ~1.37 bytes per data point (vs 16 bytes raw),         |
|  which is ~12x compression. This allows keeping 26 hours of data        |
|  for 2 billion series in 1.5 TB of RAM.                                 |
|                                                                         |
|  Why it works specifically for time-series:                             |
|  - Regular collection intervals -> delta-of-delta ~= 0                  |
|  - Slowly changing values -> XOR has few significant bits               |
|  - Append-only -> can compress in streaming fashion                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q3: How do you handle high cardinality?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A: High cardinality (millions of unique tag combinations) is the #1    |
|  operational problem for TSDBs.                                         |
|                                                                         |
|  Problems:                                                              |
|  - Inverted index grows large (memory pressure)                         |
|  - Series churn (new series created/destroyed frequently)               |
|  - Query planning becomes expensive (many series to resolve)            |
|                                                                         |
|  Solutions:                                                             |
|  1. Limit cardinality per metric (configurable cap)                     |
|  2. Use efficient inverted index (roaring bitmaps instead of sets)      |
|  3. Series ID caching with LRU eviction                                 |
|  4. Bloom filters for existence checks before index lookup              |
|  5. Pre-aggregation to reduce series count for common queries           |
|  6. Shard the index across nodes (distribute memory burden)             |
|  7. Label value interning (store each unique string once)               |
|                                                                         |
|  Real-world limits:                                                     |
|  - Prometheus: ~10M active series per instance (practical)              |
|  - VictoriaMetrics: handles 100M+ series with efficient indexing        |
|  - InfluxDB: historically struggled, improved in newer versions         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q4: How does downsampling work, and why store min/max/sum/count?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A: Downsampling reduces data volume by replacing N raw points with     |
|  a single aggregate over a time window.                                 |
|                                                                         |
|  Why not just store avg?                                                |
|  - avg(avg(x)) != avg(x) for unequal group sizes                        |
|  - If 1-minute window has 4 points and another has 2 points,            |
|    averaging the averages gives wrong result                            |
|                                                                         |
|  By storing min, max, sum, count we can:                                |
|  - Recompute correct avg at any coarser granularity: avg = sum/count    |
|  - Get correct min/max (min of mins, max of maxes)                      |
|  - Get correct count (sum of counts)                                    |
|  - This is the basis of the "summary statistics" approach               |
|                                                                         |
|  Limitation: percentiles cannot be re-aggregated from summaries.        |
|  For percentiles, use t-digest or histogram sketches that can be        |
|  merged across windows.                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q5: How would you shard a time-series database?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A: Two-dimensional sharding: by time AND by series.                    |
|                                                                         |
|  Time dimension:                                                        |
|  - Partition data into time blocks (e.g., 2 hours, 1 day)               |
|  - Enables efficient retention (drop old partitions)                    |
|  - Queries usually span limited time ranges                             |
|                                                                         |
|  Series dimension:                                                      |
|  - Hash series ID to assign to a shard (consistent hashing)             |
|  - Distributes write load across nodes                                  |
|  - Each shard handles a subset of all series                            |
|                                                                         |
|  Query routing:                                                         |
|  - Single-series query: route to specific shard                         |
|  - Multi-series query (e.g., sum by region): fan out to all shards,     |
|    aggregate results at the query gateway                               |
|                                                                         |
|  Rebalancing: Use consistent hashing with virtual nodes to minimize     |
|  data movement when adding/removing shards.                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q6: What happens when a write node fails?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A: The system handles this through multiple mechanisms:                |
|                                                                         |
|  1. Detection: Health check / heartbeat failure within seconds          |
|  2. Rerouting: Consistent hash ring updated, affected series routed     |
|     to next healthy node                                                |
|  3. WAL Recovery: When failed node restarts, replays WAL to recover     |
|     data that was in the memtable but not yet flushed to disk           |
|  4. Replication: If using replication factor > 1, reads served from     |
|     replica while primary recovers                                      |
|                                                                         |
|  Data loss potential:                                                   |
|  - With synchronous replication: zero data loss                         |
|  - With async replication: up to replication lag (usually < 1 second)   |
|  - Without replication: up to last group commit (usually < 10ms)        |
|                                                                         |
|  In practice: Most monitoring TSDBs accept tiny data loss windows       |
|  (a few seconds of metrics) in exchange for higher write throughput.    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q7: How do you handle out-of-order data?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A: Out-of-order (OOO) data is common in distributed systems due to     |
|  network delays, clock skew, or late-arriving batches.                  |
|                                                                         |
|  Approaches:                                                            |
|                                                                         |
|  1. Reject out-of-order (Prometheus < 2.39):                            |
|     - Simplest approach, enforces monotonic timestamps                  |
|     - Data loss for late arrivals                                       |
|                                                                         |
|  2. OOO buffer (Prometheus >= 2.39, VictoriaMetrics):                   |
|     - Maintain a separate buffer for out-of-order points                |
|     - Merge during compaction                                           |
|     - Configurable OOO window (e.g., accept data up to 1 hour late)     |
|                                                                         |
|  3. Write to correct time block (InfluxDB):                             |
|     - Keep recent blocks open for writes                                |
|     - Higher complexity but seamless for users                          |
|                                                                         |
|  Recommendation: Allow configurable OOO window. Data outside the        |
|  window is rejected with an error. This balances flexibility with       |
|  storage engine simplicity.                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q8: Compare pull vs push ingestion models.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A:                                                                     |
|  Pull (Prometheus model):                                               |
|  - TSDB scrapes HTTP endpoints on a schedule                            |
|  - Pros: TSDB controls load, detects target failures                    |
|  - Cons: Requires network access to targets, harder across firewalls    |
|                                                                         |
|  Push (InfluxDB/VictoriaMetrics model):                                 |
|  - Applications send data to TSDB endpoint                              |
|  - Pros: Works across firewalls, lower latency, simpler for clients     |
|  - Cons: Risk of overwhelming TSDB, need backpressure mechanism         |
|                                                                         |
|  Hybrid (modern best practice):                                         |
|  - Support both models                                                  |
|  - Use pull for infrastructure (Prometheus-style)                       |
|  - Use push for applications and IoT (direct send)                      |
|  - Agent/collector handles the translation                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q9: How would you implement alerting on top of this TSDB?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  A: Alerting evaluates rules periodically against recent data:           |
|                                                                          |
|  1. Rule definition:                                                     |
|     alert: HighCPU                                                       |
|     expr: avg(cpu_usage{env="prod"}) > 90                                |
|     for: 5m                                                              |
|     severity: critical                                                   |
|                                                                          |
|  2. Evaluation loop (every 15-60 seconds):                               |
|     - Execute the query expression against recent data                   |
|     - Check if threshold is breached                                     |
|     - Track "pending" state (must be true for `for` duration)            |
|     - Fire alert when confirmed                                          |
|                                                                          |
|  3. Optimization:                                                        |
|     - Cache recent data in memory (hot path)                             |
|     - Pre-compute common sub-expressions                                 |
|     - Batch rule evaluations (100K rules/minute feasible)                |
|                                                                          |
|  4. Alert routing:                                                       |
|     - Deduplication (don't re-fire same alert)                           |
|     - Grouping (batch related alerts)                                    |
|     - Silencing/inhibition rules                                         |
|     - Notification channels (PagerDuty, Slack, email)                    |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q10: What are the main scaling bottlenecks?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A: The main bottlenecks shift as the system scales:                    |
|                                                                         |
|  At small scale (< 1M series):                                          |
|  - Usually not bottlenecked; single node handles it                     |
|                                                                         |
|  At medium scale (1M - 50M series):                                     |
|  - Inverted index memory: O(unique_tag_values * series_count)           |
|  - Solution: Shard the index, use roaring bitmaps                       |
|                                                                         |
|  At large scale (50M - 1B series):                                      |
|  - Series churn: Creating/deleting series is expensive                  |
|  - Solution: Pre-allocate series IDs, batch index updates               |
|                                                                         |
|  - Query fan-out: Cross-shard queries slow as shards increase           |
|  - Solution: Pre-aggregation, materialized views                        |
|                                                                         |
|  - Compaction I/O: Background compaction competes with queries          |
|  - Solution: Dedicated compaction nodes, rate limiting                  |
|                                                                         |
|  At extreme scale (> 1B series):                                        |
|  - Metadata management: Tracking chunk locations for billions of        |
|    series is itself a distributed systems problem                       |
|  - Solution: Hierarchical sharding, metadata caching                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q11: How does a TSDB handle schema changes (new tags, new metrics)?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A: Unlike relational databases, TSDBs are typically schema-on-write:   |
|                                                                         |
|  - New metric names: Automatically created on first write. The TSDB     |
|    creates a new series ID and adds it to the inverted index.           |
|                                                                         |
|  - New tags: Also automatically handled. Each unique combination of     |
|    metric + tags creates a new series. No ALTER TABLE needed.           |
|                                                                         |
|  - Changing tags: This creates a new series (different TSID). The old   |
|    series continues to exist with historical data. Queries must union   |
|    both series for full history.                                        |
|                                                                         |
|  - Value type changes: Most TSDBs enforce type per series. Changing     |
|    from float to int would require a new metric name.                   |
|                                                                         |
|  Trade-off: Schema-on-write is flexible but can lead to "cardinality    |
|  explosion" if applications emit tags with unbounded values (e.g.,      |
|  user_id as a tag). Best practice: Only use low-cardinality values      |
|  as tags; high-cardinality identifiers go in the metric value or a      |
|  separate log/trace system.                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q12: How would you design the system for multi-tenancy?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A: Multi-tenancy requires isolation between tenants:                   |
|                                                                         |
|  Data isolation:                                                        |
|  - Prefix series with tenant ID: tenant_123/cpu_usage{host="a"}         |
|  - Or: separate storage per tenant (stronger isolation)                 |
|  - Queries always filtered by tenant ID                                 |
|                                                                         |
|  Resource isolation:                                                    |
|  - Per-tenant rate limits (writes/sec, active series, query rate)       |
|  - Per-tenant storage quotas                                            |
|  - Priority queues for query execution (paid tier gets priority)        |
|                                                                         |
|  Architecture options:                                                  |
|  1. Shared everything: All tenants on same cluster, isolated by ID      |
|     + Efficient resource utilization                                    |
|     - Noisy neighbor risk                                               |
|                                                                         |
|  2. Shared storage, dedicated compute: Separate query/ingest per        |
|     tenant, shared storage layer                                        |
|     + Better isolation                                                  |
|     - More complex routing                                              |
|                                                                         |
|  3. Dedicated clusters: Each tenant gets own cluster                    |
|     + Complete isolation                                                |
|     - Expensive, hard to manage at scale                                |
|                                                                         |
|  Real-world: Grafana Cloud (Cortex/Mimir) uses shared-everything        |
|  with per-tenant limits. Datadog uses dedicated shards for large        |
|  customers.                                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## Summary

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY DESIGN DECISIONS FOR A TIME-SERIES DATABASE:                       |
|                                                                         |
|  1. Storage: Columnar, time-partitioned blocks with LSM-style writes    |
|  2. Compression: Gorilla (delta-of-delta + XOR float) for 10-15x        |
|  3. Write path: WAL + MemTable + periodic flush to immutable blocks     |
|  4. Read path: Index lookup + block scan + aggregation pipeline         |
|  5. Sharding: Two-dimensional (time + series hash)                      |
|  6. Retention: Time-based partition drops + downsampling rollups        |
|  7. Consistency: Eventual consistency acceptable for most use cases     |
|  8. Compression is the single biggest lever for cost and performance    |
|                                                                         |
|  Remember: The fundamental insight is that time-series data is          |
|  append-only, time-ordered, and compressible. Every design decision     |
|  should exploit these properties.                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```
