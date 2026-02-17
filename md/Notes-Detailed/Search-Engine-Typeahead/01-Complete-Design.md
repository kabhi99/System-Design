# Design a Search Engine and Typeahead/Autocomplete System

## Table of Contents

1. Requirements
2. Scale Estimation
3. High-Level Architecture
4. Detailed Design - Search Engine
5. Detailed Design - Typeahead/Autocomplete
6. Inverted Index Deep Dive
7. Ranking Algorithms (TF-IDF, BM25)
8. Query Processing Pipeline
9. Sharding Strategy
10. Real-Time vs Batch Indexing
11. Spell Correction
12. Relevance Tuning and Personalization
13. Database Schema
14. API Design
15. Key Algorithms
16. Monitoring and Observability
17. Failure Scenarios and Mitigations
18. Interview Q&A

---

## 1. Requirements

### 1.1 Functional Requirements

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Search Engine:                                                         |
|  - Full-text search across billions of documents                        |
|  - Ranked results by relevance                                          |
|  - Support Boolean queries (AND, OR, NOT)                               |
|  - Phrase search ("exact match")                                        |
|  - Faceted search / filters (date, type, domain)                        |
|  - Pagination of results                                                |
|  - Spell correction ("Did you mean...?")                                |
|  - Snippet generation (highlighted matches)                             |
|                                                                         |
|  Typeahead / Autocomplete:                                              |
|  - Suggest completions as user types                                    |
|  - Frequency-based ranking of suggestions                               |
|  - Personalized suggestions                                             |
|  - Trending queries surfaced                                            |
|  - Support multi-language queries                                       |
|  - Maximum 10 suggestions per prefix                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 1.2 Non-Functional Requirements

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Performance:                                                            |
|  - Typeahead latency: < 50ms (p99)                                       |
|  - Search latency: < 200ms (p99)                                         |
|  - Indexing lag: < 5 minutes for new content                             |
|                                                                          |
|  Availability:                                                           |
|  - 99.99% uptime for search                                              |
|  - 99.999% uptime for typeahead                                          |
|                                                                          |
|  Scalability:                                                            |
|  - Handle 5 billion searches per day                                     |
|  - Index 50+ billion documents                                           |
|  - Support 100 million unique queries per day                            |
|                                                                          |
|  Consistency:                                                            |
|  - Eventual consistency acceptable for index updates                     |
|  - Strong consistency NOT required                                       |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 2. Scale Estimation

### 2.1 Traffic Estimates

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Searches per day:        5,000,000,000 (5B)                            |
|  Searches per second:     5B / 86400 ~ 58,000 QPS                       |
|  Peak QPS (3x):           ~175,000 QPS                                  |
|                                                                         |
|  Typeahead requests:      ~10x search (each keystroke)                  |
|  Typeahead QPS:           ~580,000 QPS average                          |
|  Peak typeahead QPS:      ~1,750,000 QPS                                |
|                                                                         |
|  Unique queries/day:      100,000,000 (100M)                            |
|  Documents indexed:       50,000,000,000 (50B)                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.2 Storage Estimates

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Average document size:          10 KB (text content)                   |
|  Total document storage:         50B x 10 KB = 500 TB                   |
|  Inverted index size:            ~15-20% of raw data = 75-100 TB        |
|  Typeahead trie storage:         ~5-10 GB (compressed)                  |
|  Query logs (30 days):           5B/day x 200 bytes x 30 = 30 TB        |
|  Metadata + auxiliary indices:   ~50 TB                                 |
|                                                                         |
|  Total storage estimate:         ~700 TB+                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.3 Bandwidth Estimates

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Search request size:            ~200 bytes                             |
|  Search response size:           ~5 KB (10 results + snippets)          |
|  Incoming bandwidth:             58K x 200B = ~12 MB/s                  |
|  Outgoing bandwidth:             58K x 5KB  = ~290 MB/s                 |
|                                                                         |
|  Typeahead request size:         ~100 bytes                             |
|  Typeahead response size:        ~500 bytes (10 suggestions)            |
|  Typeahead outgoing bandwidth:   580K x 500B = ~290 MB/s                |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 3. High-Level Architecture

### 3.1 Search Engine Architecture

```
+--------------------------------------------------------------------------+
|                        SEARCH ENGINE ARCHITECTURE                        |
+--------------------------------------------------------------------------+
|                                                                          |
|   +----------+     +-----------+     +------------+                      |
|   |  Client  |---->|   Load    |---->|   Query    |                      |
|   | (Browser)|     |  Balancer |     |  Service   |                      |
|   +----------+     +-----------+     +------+-----+                      |
|                                             |                            |
|                          +------------------+------------------+         |
|                          |                  |                  |         |
|                    +-----v-----+    +-------v------+   +------v-------+  |
|                    |  Query    |    |  Ranking     |   |  Spell       |  |
|                    |  Parser   |    |  Service     |   |  Checker     |  |
|                    +-----------+    +--------------+   +--------------+  |
|                          |                  |                            |
|                    +-----v------------------v-----+                      |
|                    |       Index Service           |                     |
|                    |  (Coordinator / Scatter-      |                     |
|                    |   Gather across shards)       |                     |
|                    +-----+-----+-----+-----+------+                      |
|                          |     |     |     |                             |
|               +----------+  +--+  +--+  +--+----------+                  |
|               |          |  |  |  |  |  |          |   |                 |
|          +----v----+ +---v--v+ +v--v--+ +v-------+ |   |                 |
|          | Shard 0 | |Shard 1| |Shard 2| |Shard N | |   |                |
|          | (Index) | |(Index)| |(Index)| |(Index) | |   |                |
|          +---------+ +-------+ +-------+ +--------+ |   |                |
|                                                         |                |
+--------------------------------------------------------------------------+
```

### 3.2 Typeahead Architecture

```
+-------------------------------------------------------------------------+
|                       TYPEAHEAD ARCHITECTURE                            |
+-------------------------------------------------------------------------+
|                                                                         |
|   +----------+     +-----------+     +--------------+                   |
|   |  Client  |---->|   Load    |---->|  Typeahead   |                   |
|   | (Browser)|     |  Balancer |     |   Service    |                   |
|   +----------+     +-----------+     +------+-------+                   |
|                                             |                           |
|                     +-----------------------+----------+                |
|                     |                                  |                |
|               +-----v--------+              +----------v---------+      |
|               |  Trie Server |              |  Aggregation       |      |
|               |  (In-Memory) |              |  Service           |      |
|               |              |              |  (Trending +       |      |
|               |  Prefix -->  |              |   Personalized)    |      |
|               |  Top-K       |              +--------------------+      |
|               |  Suggestions |                        |                 |
|               +---------+----+              +---------v----------+      |
|                         |                   |  Query Log         |      |
|               +---------v----------+        |  Aggregator        |      |
|               |  Trie Builder      |        |  (Kafka + Flink)   |      |
|               |  (Offline/Batch)   |        +--------------------+      |
|               +--------------------+                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.3 Combined System Overview

```
+-------------------------------------------------------------------------+
|                        COMBINED SYSTEM OVERVIEW                         |
+-------------------------------------------------------------------------+
|                                                                         |
|   User Types "wea"                                                      |
|       |                                                                 |
|       v                                                                 |
|   +-----------+    +------------------+    +------------------+         |
|   | Typeahead |--->| Suggestions:     |--->| "weather today"  |         |
|   | Service   |    | (prefix match)   |    | "weather app"    |         |
|   +-----------+    +------------------+    | "wearing glasses"|         |
|                                            +------------------+         |
|   User selects "weather today" and presses Enter                        |
|       |                                                                 |
|       v                                                                 |
|   +-----------+    +------------------+    +------------------+         |
|   | Search    |--->| Full-text search |--->| Ranked results   |         |
|   | Engine    |    | on index         |    | with snippets    |         |
|   +-----------+    +------------------+    +------------------+         |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 4. Detailed Design - Search Engine

### 4.1 Document Ingestion Pipeline

```
+-------------------------------------------------------------------------+
|                     DOCUMENT INGESTION PIPELINE                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  +--------+    +----------+    +-----------+    +-------------+         |
|  | Web    |--->| Content  |--->| Document  |--->| Index       |         |
|  | Crawler|    | Parser   |    | Processor |    | Writer      |         |
|  +--------+    +----------+    +-----------+    +------+------+         |
|                     |               |                  |                |
|                     v               v                  v                |
|               +-----------+  +------------+    +---------------+        |
|               | Extract:  |  | Tokenize   |    | Write to      |        |
|               | - Title   |  | Stem       |    | inverted      |        |
|               | - Body    |  | Remove     |    | index +       |        |
|               | - Links   |  |  stopwords |    | forward index |        |
|               | - Meta    |  | Normalize  |    +---------------+        |
|               +-----------+  +------------+                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 4.2 Query Execution Flow

```
+-------------------------------------------------------------------------+
|                        QUERY EXECUTION FLOW                             |
+-------------------------------------------------------------------------+
|                                                                         |
|  Step 1: Query Reception                                                |
|  +-------------------------------------------------------------------+  |
|  | User query: "best weather apps 2024"                              |  |
|  +-------------------------------------------------------------------+  |
|                               |                                         |
|  Step 2: Query Parsing        v                                         |
|  +-------------------------------------------------------------------+  |
|  | Tokens: ["best", "weather", "apps", "2024"]                       |  |
|  | After stemming: ["best", "weather", "app", "2024"]                |  |
|  | Stop words removed: ["best", "weather", "app", "2024"]            |  |
|  +-------------------------------------------------------------------+  |
|                               |                                         |
|  Step 3: Scatter to Shards    v                                         |
|  +-------------------------------------------------------------------+  |
|  | Coordinator sends query to ALL index shards                       |  |
|  | Each shard returns top-K results locally                          |  |
|  +-------------------------------------------------------------------+  |
|                               |                                         |
|  Step 4: Gather + Merge       v                                         |
|  +-------------------------------------------------------------------+  |
|  | Coordinator merges results from all shards                        |  |
|  | Re-ranks globally using combined scores                           |  |
|  +-------------------------------------------------------------------+  |
|                               |                                         |
|  Step 5: Response             v                                         |
|  +-------------------------------------------------------------------+  |
|  | Generate snippets, apply personalization, return top 10           |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 4.3 Elasticsearch/Solr Architecture Overview

```
+--------------------------------------------------------------------------+
|               ELASTICSEARCH CLUSTER ARCHITECTURE                         |
+--------------------------------------------------------------------------+
|                                                                          |
|   +-------------------+                                                  |
|   |   Client Node     |  (Load balancer / Coordinating node)             |
|   +--------+----------+                                                  |
|            |                                                             |
|   +--------v----------+   +-------------------+  +-------------------+   |
|   |   Master Node     |   |   Master Node     |  |   Master Node     |   |
|   |   (Eligible)      |   |   (Eligible)      |  |   (Elected)       |   |
|   +-------------------+   +-------------------+  +-------------------+   |
|                                                                          |
|   Cluster State: Index metadata, shard allocation, node membership       |
|                                                                          |
|   +-------------------+   +-------------------+  +-------------------+   |
|   |   Data Node 1     |   |   Data Node 2     |  |   Data Node 3     |   |
|   |                   |   |                   |  |                   |   |
|   |  [Shard 0-P]      |   |  [Shard 1-P]      |  |  [Shard 2-P]      |   |
|   |  [Shard 2-R]      |   |  [Shard 0-R]      |  |  [Shard 1-R]      |   |
|   +-------------------+   +-------------------+  +-------------------+   |
|                                                                          |
|   P = Primary Shard,  R = Replica Shard                                  |
|                                                                          |
|   Each Shard = Complete Lucene Index:                                    |
|   - Inverted Index (term -> posting list)                                |
|   - Stored Fields (original document)                                    |
|   - Doc Values (columnar data for sorting/aggregation)                   |
|   - Term Vectors (per-document term info)                                |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 5. Detailed Design - Typeahead/Autocomplete

### 5.1 Trie Data Structure

```
+--------------------------------------------------------------------------+
|                       TRIE DATA STRUCTURE                                |
+--------------------------------------------------------------------------+
|                                                                          |
|   Each node stores:                                                      |
|   - Character                                                            |
|   - Is end of word (boolean)                                             |
|   - Top-K suggestions (pre-computed)                                     |
|   - Frequency/score for ranking                                          |
|                                                                          |
|   Example Trie for: "tree", "try", "true", "trunk"                       |
|                                                                          |
|                    (root)                                                |
|                      |                                                   |
|                      t                                                   |
|                      |                                                   |
|                      r                                                   |
|                    / | \                                                 |
|                   e  u  y                                                |
|                   |  |  |                                                |
|                   e  n  [end: "try"]                                     |
|                   |  |                                                   |
|              [end: k  e                                                  |
|              "tree"]|  |                                                 |
|                  [end: [end:                                             |
|                  "trunk"]"true"]                                         |
|                                                                          |
|   Optimization: Store top-K at each node                                 |
|   Node "tr" stores: ["tree"(1000), "trump"(800), "true"(600)]            |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 5.2 Typeahead Service Flow

```
+--------------------------------------------------------------------------+
|                      TYPEAHEAD SERVICE FLOW                              |
+--------------------------------------------------------------------------+
|                                                                          |
|   1. User types "wea"                                                    |
|   2. Client debounces (100-200ms wait after last keystroke)              |
|   3. Request: GET /typeahead?q=wea&limit=10                              |
|                                                                          |
|   Server-side:                                                           |
|   +---------------------------------------------------------------+      |
|   |  a) Look up prefix "wea" in Trie                              |      |
|   |  b) Retrieve pre-computed top-K suggestions at node            |     |
|   |  c) Apply personalization boost                                |     |
|   |  d) Filter inappropriate content                               |     |
|   |  e) Return ranked suggestions                                  |     |
|   +---------------------------------------------------------------+      |
|                                                                          |
|   Response (< 50ms):                                                     |
|   +---------------------------------------------------------------+      |
|   |  ["weather forecast", "weather today", "weather map",          |     |
|   |   "weather channel", "weather radar", "weather app",           |     |
|   |   "weapons", "wealth management", "wearing", "weaving"]        |     |
|   +---------------------------------------------------------------+      |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 5.3 Trie Update Strategy

```
+-------------------------------------------------------------------------+
|                       TRIE UPDATE STRATEGY                              |
+-------------------------------------------------------------------------+
|                                                                         |
|  Option A: Offline Rebuild (Recommended for large scale)                |
|  +-------------------------------------------------------------------+  |
|  |  1. Collect query logs every N hours (e.g., every 1-2 hours)      |  |
|  |  2. Aggregate query frequencies                                   |  |
|  |  3. Build new Trie in background                                  |  |
|  |  4. Swap old Trie with new Trie atomically                        |  |
|  |  5. Each Trie server loads the new snapshot                       |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Option B: Real-Time Updates (For trending queries)                     |
|  +-------------------------------------------------------------------+  |
|  |  1. Stream query logs via Kafka                                   |  |
|  |  2. Use Flink/Spark Streaming to detect trending queries          |  |
|  |  3. Push trending queries to Trie servers                         |  |
|  |  4. Insert/update nodes incrementally                             |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Hybrid Approach (Best practice):                                       |
|  +-------------------------------------------------------------------+  |
|  |  - Base Trie: Rebuilt every 2 hours from aggregated logs          |  |
|  |  - Trending overlay: Real-time updates for trending queries       |  |
|  |  - Merge at query time: base + trending suggestions               |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 6. Inverted Index Deep Dive

### 6.1 Structure

```
+-------------------------------------------------------------------------+
|                        INVERTED INDEX STRUCTURE                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  Term Dictionary          Posting Lists                                 |
|  +-------------+          +------------------------------------+        |
|  | "weather"   | -------> | DocID:1, TF:3, Pos:[5,12,45]      |         |
|  +-------------+          | DocID:7, TF:1, Pos:[22]            |        |
|  | "forecast"  | ---+     | DocID:15, TF:5, Pos:[1,8,20,33,50]|         |
|  +-------------+    |     +------------------------------------+        |
|  | "today"     | -+ |                                                   |
|  +-------------+  | |     +------------------------------------+        |
|  | "map"       |  | +---> | DocID:1, TF:1, Pos:[6]            |         |
|  +-------------+  |       | DocID:22, TF:2, Pos:[1,15]        |         |
|                   |       +------------------------------------+        |
|                   |                                                     |
|                   |       +------------------------------------+        |
|                   +-----> | DocID:1, TF:2, Pos:[1,30]         |         |
|                           | DocID:5, TF:1, Pos:[10]           |         |
|                           | DocID:7, TF:1, Pos:[1]            |         |
|                           +------------------------------------+        |
|                                                                         |
|  Each posting entry contains:                                           |
|  - Document ID                                                          |
|  - Term Frequency (TF): how many times term appears in doc              |
|  - Position List: where in document the term appears                    |
|  - (Optional) Field info: title vs body occurrence                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.2 Forward Index (Document Store)

```
+-------------------------------------------------------------------------+
|                          FORWARD INDEX                                  |
+-------------------------------------------------------------------------+
|                                                                         |
|  DocID -> Document Metadata                                             |
|  +------+-------------------------------------------+                   |
|  | ID   | URL              | Title        | Length  |                   |
|  +------+-------------------------------------------+                   |
|  |  1   | weather.com/...  | Weather Now  | 5000    |                   |
|  |  5   | news.com/today   | Today News   | 3200    |                   |
|  |  7   | blog.com/wx      | WX Forecast  | 1200    |                   |
|  | 15   | accu.com/daily   | Daily Wthr   | 8000    |                   |
|  | 22   | nws.gov/fcst     | NWS Forecast | 4500    |                   |
|  +------+-------------------------------------------+                   |
|                                                                         |
|  Used for:                                                              |
|  - Snippet generation (retrieve original text)                          |
|  - Document length normalization in BM25                                |
|  - Returning document metadata in search results                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.3 Index Compression

```
+--------------------------------------------------------------------------+
|                       INDEX COMPRESSION                                  |
+--------------------------------------------------------------------------+
|                                                                          |
|  Posting List Compression:                                               |
|                                                                          |
|  Original DocIDs:  [1, 7, 15, 22, 105, 108, 300]                         |
|                                                                          |
|  Delta Encoding:   [1, 6, 8, 7, 83, 3, 192]                              |
|  (Store gaps between consecutive IDs)                                    |
|                                                                          |
|  Variable-Byte Encoding (VByte):                                         |
|  - Small gaps = 1 byte, large gaps = 2+ bytes                            |
|  - Significant space savings for clustered DocIDs                        |
|                                                                          |
|  Frame of Reference (FOR):                                               |
|  - Divide into blocks of 128 DocIDs                                      |
|  - Store min value + bit-packed offsets                                  |
|                                                                          |
|  Typical compression ratios:                                             |
|  - Posting lists: 4-10x compression                                      |
|  - Overall index: 15-20% of raw document size                            |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 7. Ranking Algorithms (TF-IDF, BM25)

### 7.1 TF-IDF

```
+--------------------------------------------------------------------------+
|                           TF-IDF SCORING                                 |
+--------------------------------------------------------------------------+
|                                                                          |
|  TF (Term Frequency):                                                    |
|  - How often a term appears in a document                                |
|  - TF(t,d) = count(t in d) / total_terms(d)                              |
|  - Or logarithmic: TF = 1 + log(count)                                   |
|                                                                          |
|  IDF (Inverse Document Frequency):                                       |
|  - How rare a term is across all documents                               |
|  - IDF(t) = log(N / DF(t))                                               |
|    where N = total docs, DF(t) = docs containing term t                  |
|                                                                          |
|  TF-IDF Score:                                                           |
|  - score(t, d) = TF(t, d) x IDF(t)                                       |
|                                                                          |
|  Example:                                                                |
|  - Query: "weather forecast"                                             |
|  - N = 50,000,000,000 documents                                          |
|  - "weather" appears in 500M docs -> IDF = log(50B/500M) = 2.0           |
|  - "forecast" appears in 50M docs -> IDF = log(50B/50M) = 3.0            |
|  - Doc with TF("weather")=0.05 and TF("forecast")=0.03                   |
|  - Score = (0.05 x 2.0) + (0.03 x 3.0) = 0.19                            |
|                                                                          |
|  Limitation: Does not account for document length normalization          |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 7.2 BM25 (Best Match 25)

```
+--------------------------------------------------------------------------+
|                          BM25 SCORING                                    |
+--------------------------------------------------------------------------+
|                                                                          |
|  BM25 is the industry standard for search ranking.                       |
|  It improves on TF-IDF with saturation and length normalization.         |
|                                                                          |
|  Formula:                                                                |
|  score(D,Q) = SUM over qi in Q:                                          |
|                                                                          |
|            IDF(qi) x f(qi,D) x (k1 + 1)                                  |
|    ---------------------------------------------------                   |
|     f(qi,D) + k1 x (1 - b + b x |D| / avgdl)                             |
|                                                                          |
|  Where:                                                                  |
|  - f(qi, D) = term frequency of qi in document D                         |
|  - |D|      = document length (in terms)                                 |
|  - avgdl    = average document length across corpus                      |
|  - k1       = term frequency saturation parameter (default: 1.2)         |
|  - b        = length normalization parameter (default: 0.75)             |
|                                                                          |
|  Key Properties:                                                         |
|  +--------------------------------------------------------------------+  |
|  | 1. TF Saturation: Diminishing returns for repeated terms           |  |
|  |    - TF=1 -> big boost, TF=10 -> smaller additional boost          |  |
|  | 2. Length Normalization: Penalizes longer documents slightly       |  |
|  |    - b=0 means no length normalization                             |  |
|  |    - b=1 means full length normalization                           |  |
|  | 3. IDF component: Same as classic IDF                              |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 7.3 Beyond BM25 - Learning to Rank

```
+-------------------------------------------------------------------------+
|                       LEARNING TO RANK                                  |
+-------------------------------------------------------------------------+
|                                                                         |
|  Modern search engines use ML models on top of BM25:                    |
|                                                                         |
|  Feature Vector per (query, document) pair:                             |
|  +-------------------------------------------------------------------+  |
|  |  - BM25 score                                                     |  |
|  |  - PageRank of document                                           |  |
|  |  - Click-through rate for this query-doc pair                     |  |
|  |  - Document freshness (age)                                       |  |
|  |  - Domain authority                                               |  |
|  |  - Title match score                                              |  |
|  |  - URL match score                                                |  |
|  |  - User engagement metrics (dwell time, bounce rate)              |  |
|  |  - Query-document semantic similarity (BERT, embeddings)          |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Approaches:                                                            |
|  1. Pointwise: Predict relevance score per document                     |
|  2. Pairwise: Predict which of two documents is more relevant           |
|  3. Listwise: Optimize entire ranked list (LambdaMART, etc.)            |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 8. Query Processing Pipeline

### 8.1 Pipeline Stages

```
+-------------------------------------------------------------------------+
|                    QUERY PROCESSING PIPELINE                            |
+-------------------------------------------------------------------------+
|                                                                         |
|  Raw Query: "Best Weather apps for iOS 2024"                            |
|       |                                                                 |
|       v                                                                 |
|  +------------------+                                                   |
|  | 1. Tokenization  |  -> ["Best", "Weather", "apps", "for",            |
|  +------------------+       "iOS", "2024"]                              |
|       |                                                                 |
|       v                                                                 |
|  +------------------+                                                   |
|  | 2. Lowercasing   |  -> ["best", "weather", "apps", "for",            |
|  +------------------+       "ios", "2024"]                              |
|       |                                                                 |
|       v                                                                 |
|  +------------------+                                                   |
|  | 3. Stop Word     |  -> ["best", "weather", "apps", "ios", "2024"]    |
|  |    Removal        |      (removed "for")                             |
|  +------------------+                                                   |
|       |                                                                 |
|       v                                                                 |
|  +------------------+                                                   |
|  | 4. Stemming /    |  -> ["best", "weather", "app", "ios", "2024"]     |
|  |    Lemmatization |      ("apps" -> "app")                            |
|  +------------------+                                                   |
|       |                                                                 |
|       v                                                                 |
|  +------------------+                                                   |
|  | 5. Synonym       |  -> also search: "iOS" -> "iPhone", "Apple"       |
|  |    Expansion     |                                                   |
|  +------------------+                                                   |
|       |                                                                 |
|       v                                                                 |
|  +------------------+                                                   |
|  | 6. Query Plan    |  -> Determine: intersect posting lists            |
|  |    Generation    |     for "weather" AND "app"                       |
|  +------------------+                                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 8.2 Stemming Algorithms

```
+-------------------------------------------------------------------------+
|                       STEMMING ALGORITHMS                               |
+-------------------------------------------------------------------------+
|                                                                         |
|  Porter Stemmer (most common):                                          |
|  - "running"    -> "run"                                                |
|  - "connection" -> "connect"                                            |
|  - "organization" -> "organ" (over-stemming issue!)                     |
|                                                                         |
|  Snowball Stemmer (improved Porter):                                    |
|  - Better handling of edge cases                                        |
|  - Multi-language support                                               |
|                                                                         |
|  Lemmatization (dictionary-based):                                      |
|  - "better"  -> "good" (understands morphology)                         |
|  - "running" -> "run"                                                   |
|  - More accurate but slower                                             |
|                                                                         |
|  Trade-off: Stemming = faster, less accurate                            |
|             Lemmatization = slower, more accurate                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 9. Sharding Strategy

### 9.1 Document-Based Sharding (Preferred)

```
+-------------------------------------------------------------------------+
|                   DOCUMENT-BASED SHARDING                               |
+-------------------------------------------------------------------------+
|                                                                         |
|  Each shard holds a subset of ALL documents.                            |
|  Every shard has a COMPLETE inverted index for its documents.           |
|                                                                         |
|  +-------------------+  +-------------------+  +-------------------+    |
|  |    Shard 0        |  |    Shard 1        |  |    Shard 2        |    |
|  |  Docs 0 - 999K    |  |  Docs 1M - 1.99M |  |  Docs 2M - 2.99M   |    |
|  |                   |  |                   |  |                   |    |
|  |  Inverted index   |  |  Inverted index   |  |  Inverted index   |    |
|  |  for terms in     |  |  for terms in     |  |  for terms in     |    |
|  |  these docs only  |  |  these docs only  |  |  these docs only  |    |
|  +-------------------+  +-------------------+  +-------------------+    |
|                                                                         |
|  Query execution: SCATTER-GATHER                                        |
|  - Send query to ALL shards                                             |
|  - Each shard returns local top-K                                       |
|  - Coordinator merges and re-ranks globally                             |
|                                                                         |
|  Pros:                                                                  |
|  + Each shard is independent                                            |
|  + Easy to add/remove shards                                            |
|  + Reindexing affects only one shard                                    |
|                                                                         |
|  Cons:                                                                  |
|  - Every query hits ALL shards (fan-out)                                |
|  - High query amplification                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 9.2 Term-Based Sharding

```
+-------------------------------------------------------------------------+
|                     TERM-BASED SHARDING                                 |
+-------------------------------------------------------------------------+
|                                                                         |
|  Each shard holds posting lists for a subset of TERMS.                  |
|                                                                         |
|  +-------------------+  +-------------------+  +-------------------+    |
|  |    Shard 0        |  |    Shard 1        |  |    Shard 2        |    |
|  |  Terms: A - H     |  |  Terms: I - P     |  |  Terms: Q - Z     |    |
|  |                   |  |                   |  |                   |    |
|  |  Full posting     |  |  Full posting     |  |  Full posting     |    |
|  |  lists for these  |  |  lists for these  |  |  lists for these  |    |
|  |  terms            |  |  terms            |  |  terms            |    |
|  +-------------------+  +-------------------+  +-------------------+    |
|                                                                         |
|  Query "weather forecast":                                              |
|  - "weather" -> Shard 2 (Q-Z)                                           |
|  - "forecast" -> Shard 0 (A-H)                                          |
|  - Must intersect posting lists from different shards                   |
|                                                                         |
|  Pros:                                                                  |
|  + Only relevant shards queried                                         |
|  + Less fan-out for single-term queries                                 |
|                                                                         |
|  Cons:                                                                  |
|  - Multi-term queries need cross-shard coordination                     |
|  - Hot terms (e.g., "the") create hotspot shards                        |
|  - Document scoring harder (need global doc info)                       |
|  - Industry prefers document-based sharding                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 10. Real-Time vs Batch Indexing

```
+--------------------------------------------------------------------------+
|                REAL-TIME vs BATCH INDEXING                               |
+--------------------------------------------------------------------------+
|                                                                          |
|  BATCH INDEXING:                                                         |
|  +--------------------------------------------------------------------+  |
|  |  - Crawl/collect documents periodically                            |  |
|  |  - Build complete index offline                                    |  |
|  |  - Swap old index with new index                                   |  |
|  |  - Latency: hours to days                                          |  |
|  |  - Use case: Web search (non-time-sensitive)                       |  |
|  |  - Simpler architecture                                            |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  NEAR REAL-TIME (NRT) INDEXING:                                          |
|  +--------------------------------------------------------------------+  |
|  |  - Documents indexed within seconds/minutes                        |  |
|  |  - Use write-ahead log + periodic refresh                          |  |
|  |  - Elasticsearch default: refresh every 1 second                   |  |
|  |  - Use case: News search, social media, e-commerce                 |  |
|  |  - More complex, needs careful resource management                 |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  NRT INDEXING FLOW (Elasticsearch-style):                                |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  1. Document arrives -> write to in-memory buffer                  |  |
|  |  2. Also write to transaction log (translog) for durability        |  |
|  |  3. Every 1s: "refresh" - flush buffer to new segment              |  |
|  |     (segment is immutable, now searchable)                         |  |
|  |  4. Periodically: "merge" - combine small segments                 |  |
|  |     into larger ones (background process)                          |  |
|  |  5. Periodically: "flush" - fsync translog, clear it               |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 11. Spell Correction

### 11.1 Edit Distance (Levenshtein)

```
+-------------------------------------------------------------------------+
|                       SPELL CORRECTION                                  |
+-------------------------------------------------------------------------+
|                                                                         |
|  Edit Distance (Levenshtein Distance):                                  |
|  Minimum number of single-character edits to transform one word         |
|  into another. Edits: insertion, deletion, substitution.                |
|                                                                         |
|  Example: "wether" -> "weather"                                         |
|  Edit distance = 1 (insert 'a')                                         |
|                                                                         |
|  DP Matrix for "wether" vs "weather":                                   |
|                                                                         |
|       ""  w  e  a  t  h  e  r                                           |
|  ""    0  1  2  3  4  5  6  7                                           |
|  w     1  0  1  2  3  4  5  6                                           |
|  e     2  1  0  1  2  3  4  5                                           |
|  t     3  2  1  1  1  2  3  4                                           |
|  h     4  3  2  2  2  1  2  3                                           |
|  e     5  4  3  3  3  2  1  2                                           |
|  r     6  5  4  4  4  3  2  1                                           |
|                                                                         |
|  Distance = 1 (bottom-right cell)                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 11.2 Spell Correction Pipeline

```
+-------------------------------------------------------------------------+
|                   SPELL CORRECTION PIPELINE                             |
+-------------------------------------------------------------------------+
|                                                                         |
|  1. Candidate Generation:                                               |
|     - Edit distance 1 from query term                                   |
|     - Edit distance 2 for short words                                   |
|     - Phonetic matching (Soundex, Metaphone)                            |
|       e.g., "fone" -> "phone" (same phonetic code)                      |
|                                                                         |
|  2. Candidate Filtering:                                                |
|     - Keep only candidates that exist in dictionary                     |
|     - Dictionary = all terms in the inverted index                      |
|                                                                         |
|  3. Candidate Ranking:                                                  |
|     - Frequency of candidate term in corpus                             |
|     - Edit distance (prefer distance 1 over 2)                          |
|     - N-gram overlap with original term                                 |
|     - Context: what makes sense given other query terms                 |
|                                                                         |
|  4. Noisy Channel Model:                                                |
|     P(correction | misspelling) ~ P(misspelling | correction)           |
|                                     x P(correction)                     |
|     - P(correction) = language model probability                        |
|     - P(misspelling | correction) = error model probability             |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 12. Relevance Tuning and Personalization

```
+-------------------------------------------------------------------------+
|                  RELEVANCE TUNING & PERSONALIZATION                     |
+-------------------------------------------------------------------------+
|                                                                         |
|  Static Signals (Document Quality):                                     |
|  +-------------------------------------------------------------------+  |
|  |  - PageRank / Domain authority                                    |  |
|  |  - Content freshness                                              |  |
|  |  - Document quality score (spam detection)                        |  |
|  |  - Content length / completeness                                  |  |
|  |  - Structured data / schema markup                                |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Query-Dependent Signals:                                               |
|  +-------------------------------------------------------------------+  |
|  |  - BM25 text relevance score                                      |  |
|  |  - Title match boost                                              |  |
|  |  - Exact phrase match boost                                       |  |
|  |  - Term proximity (how close query terms appear)                  |  |
|  |  - Field boosting (title > h1 > body)                             |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  User Signals (Personalization):                                        |
|  +-------------------------------------------------------------------+  |
|  |  - Search history                                                 |  |
|  |  - Click history and dwell time                                   |  |
|  |  - Location (geo-local results)                                   |  |
|  |  - Language preference                                            |  |
|  |  - Device type (mobile vs desktop)                                |  |
|  |  - Time of day / seasonality                                      |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Final Score = weighted_combination(static, query_dependent, user)      |
|  Typically using a trained ML model (Learning to Rank)                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 13. Database Schema

### 13.1 Document Metadata Store

```
+--------------------------------------------------------------------------+
|                      DATABASE SCHEMA                                     |
+--------------------------------------------------------------------------+
|                                                                          |
|  Table: documents                                                        |
|  +---------------------------------------------------------------+       |
|  | doc_id       BIGINT PRIMARY KEY                                |      |
|  | url          VARCHAR(2048) UNIQUE NOT NULL                     |      |
|  | title        VARCHAR(512)                                      |      |
|  | domain       VARCHAR(256)                                      |      |
|  | content_hash VARCHAR(64)     -- SHA-256 for dedup              |      |
|  | page_rank    FLOAT                                             |      |
|  | language     VARCHAR(5)                                        |      |
|  | last_crawled TIMESTAMP                                         |      |
|  | last_indexed TIMESTAMP                                         |      |
|  | content_type VARCHAR(50)                                       |      |
|  | word_count   INT                                               |      |
|  | created_at   TIMESTAMP                                         |      |
|  +---------------------------------------------------------------+       |
|                                                                          |
|  Table: query_logs                                                       |
|  +---------------------------------------------------------------+       |
|  | log_id       BIGINT PRIMARY KEY                                |      |
|  | query        VARCHAR(512)                                      |      |
|  | user_id      BIGINT                                            |      |
|  | timestamp    TIMESTAMP                                         |      |
|  | results_count INT                                              |      |
|  | latency_ms   INT                                               |      |
|  | clicked_doc  BIGINT (FK -> documents.doc_id)                   |      |
|  | click_position INT                                             |      |
|  | session_id   VARCHAR(64)                                       |      |
|  +---------------------------------------------------------------+       |
|                                                                          |
|  Table: typeahead_suggestions                                            |
|  +---------------------------------------------------------------+       |
|  | suggestion_id BIGINT PRIMARY KEY                               |      |
|  | prefix        VARCHAR(128)                                     |      |
|  | suggestion    VARCHAR(512)                                     |      |
|  | frequency     BIGINT                                           |      |
|  | last_updated  TIMESTAMP                                        |      |
|  | is_trending   BOOLEAN                                          |      |
|  | language      VARCHAR(5)                                       |      |
|  +---------------------------------------------------------------+       |
|                                                                          |
|  Table: index_shards                                                     |
|  +---------------------------------------------------------------+       |
|  | shard_id      INT PRIMARY KEY                                  |      |
|  | node_address  VARCHAR(256)                                     |      |
|  | doc_range_start BIGINT                                         |      |
|  | doc_range_end   BIGINT                                         |      |
|  | status        ENUM('active','rebuilding','standby')            |      |
|  | replica_of    INT (FK -> index_shards.shard_id)                |      |
|  | last_refresh  TIMESTAMP                                        |      |
|  +---------------------------------------------------------------+       |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 14. API Design

### 14.1 Search API

```
+-------------------------------------------------------------------------+
|                          SEARCH API                                     |
+-------------------------------------------------------------------------+
|                                                                         |
|  POST /api/v1/search                                                    |
|  Request:                                                               |
|  {                                                                      |
|    "query": "best weather apps",                                        |
|    "page": 1,                                                           |
|    "page_size": 10,                                                     |
|    "filters": {                                                         |
|      "date_range": { "from": "2024-01-01", "to": "2024-12-31" },        |
|      "language": "en",                                                  |
|      "domain": ["*.com", "*.org"]                                       |
|    },                                                                   |
|    "sort": "relevance",                                                 |
|    "spell_check": true,                                                 |
|    "personalize": true                                                  |
|  }                                                                      |
|                                                                         |
|  Response:                                                              |
|  {                                                                      |
|    "total_results": 15234000,                                           |
|    "latency_ms": 120,                                                   |
|    "spell_suggestion": null,                                            |
|    "results": [                                                         |
|      {                                                                  |
|        "doc_id": "abc123",                                              |
|        "url": "https://example.com/best-weather-apps",                  |
|        "title": "10 Best Weather Apps for 2024",                        |
|        "snippet": "...the <b>best weather apps</b> available...",       |
|        "score": 0.95,                                                   |
|        "domain": "example.com",                                         |
|        "date": "2024-03-15"                                             |
|      }                                                                  |
|    ],                                                                   |
|    "facets": {                                                          |
|      "domain": [{"name":"example.com","count":500}, ...],               |
|      "year":   [{"name":"2024","count":12000}, ...]                     |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 14.2 Typeahead API

```
+-------------------------------------------------------------------------+
|                        TYPEAHEAD API                                    |
+-------------------------------------------------------------------------+
|                                                                         |
|  GET /api/v1/typeahead?q=wea&limit=10&lang=en                           |
|                                                                         |
|  Response:                                                              |
|  {                                                                      |
|    "prefix": "wea",                                                     |
|    "latency_ms": 12,                                                    |
|    "suggestions": [                                                     |
|      { "text": "weather forecast",   "score": 9500, "trending": false },|
|      { "text": "weather today",      "score": 8200, "trending": true }, |
|      { "text": "weather map",        "score": 7100, "trending": false },|
|      { "text": "weather channel",    "score": 6800, "trending": false },|
|      { "text": "weather radar",      "score": 5500, "trending": false },|
|      { "text": "weather app",        "score": 4200, "trending": false },|
|      { "text": "wealth management",  "score": 3100, "trending": false },|
|      { "text": "weapons",            "score": 2800, "trending": false },|
|      { "text": "wearing",            "score": 1500, "trending": false },|
|      { "text": "weaving",            "score": 900,  "trending": false } |
|    ]                                                                    |
|  }                                                                      |
|                                                                         |
|  Client-side optimizations:                                             |
|  - Debounce: wait 100-200ms after last keystroke before requesting      |
|  - Cache: store recent prefix -> results mapping                        |
|  - Prefetch: if user typed "we", cache "wea","web","wes" results        |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 15. Key Algorithms

### 15.1 Posting List Intersection

```
+-------------------------------------------------------------------------+
|                   POSTING LIST INTERSECTION                             |
+-------------------------------------------------------------------------+
|                                                                         |
|  For AND queries, we need to find documents containing ALL terms.       |
|                                                                         |
|  Method 1: Two-Pointer Merge (sorted lists)                             |
|  +-------------------------------------------------------------------+  |
|  |  List A (weather): [1, 3, 7, 15, 22, 45, 100]                     |  |
|  |  List B (forecast): [3, 7, 10, 22, 50, 100, 200]                  |  |
|  |                                                                   |  |
|  |  i=0, j=0: A[0]=1 < B[0]=3  -> advance i                          |  |
|  |  i=1, j=0: A[1]=3 = B[0]=3  -> MATCH! output 3, advance both      |  |
|  |  i=2, j=1: A[2]=7 = B[1]=7  -> MATCH! output 7, advance both      |  |
|  |  i=3, j=2: A[3]=15 > B[2]=10 -> advance j                         |  |
|  |  ...                                                              |  |
|  |  Result: [3, 7, 22, 100]                                          |  |
|  |  Time: O(n + m) where n, m are list sizes                         |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Method 2: Skip Pointers (for long lists)                               |
|  +-------------------------------------------------------------------+  |
|  |  Add skip pointers every sqrt(n) elements                         |  |
|  |  [1, 3, 7, 15, 22, 45, 100, 200, 500, 800]                        |  |
|  |       ^skip         ^skip          ^skip                          |  |
|  |  Can skip over blocks that definitely don't contain matches       |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Optimization: Start intersection with shortest list first              |
|  (reduces total comparisons)                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 15.2 Top-K in Trie

```
+-------------------------------------------------------------------------+
|                     TOP-K IN TRIE ALGORITHM                             |
+-------------------------------------------------------------------------+
|                                                                         |
|  Approach 1: Pre-compute top-K at each node (Recommended)               |
|  +-------------------------------------------------------------------+  |
|  |  During Trie construction:                                        |  |
|  |  - At each node, store the top-K most frequent completions        |  |
|  |  - Query time: O(prefix_length) to reach node + O(1) to return    |  |
|  |  - Space: O(nodes x K) additional storage                         |  |
|  |  - Update: Need to rebuild or propagate changes upward            |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Approach 2: DFS from prefix node (for small datasets)                  |
|  +-------------------------------------------------------------------+  |
|  |  - Traverse to prefix node: O(prefix_length)                      |  |
|  |  - DFS to find all completions: O(subtree_size)                   |  |
|  |  - Use max-heap to maintain top-K                                 |  |
|  |  - Too slow for production at scale                               |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Approach 3: Ternary Search Tree (space optimization)                   |
|  +-------------------------------------------------------------------+  |
|  |  - Less memory than standard Trie                                 |  |
|  |  - Each node: left child, equal child, right child                |  |
|  |  - Useful when character set is large (Unicode)                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 16. Monitoring and Observability

```
+-------------------------------------------------------------------------+
|                   MONITORING & OBSERVABILITY                            |
+-------------------------------------------------------------------------+
|                                                                         |
|  Search Metrics:                                                        |
|  +-------------------------------------------------------------------+  |
|  |  - Query latency (p50, p95, p99)                                  |  |
|  |  - Queries per second (QPS)                                       |  |
|  |  - Error rate (5xx responses)                                     |  |
|  |  - Zero-result rate (queries with no results)                     |  |
|  |  - Cache hit ratio                                                |  |
|  |  - Index freshness (lag between crawl and searchable)             |  |
|  |  - Shard health and replication status                            |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Relevance Metrics:                                                     |
|  +-------------------------------------------------------------------+  |
|  |  - Click-through rate (CTR) at position 1, 2, 3...                |  |
|  |  - Mean Reciprocal Rank (MRR)                                     |  |
|  |  - Normalized Discounted Cumulative Gain (NDCG)                   |  |
|  |  - Dwell time after click                                         |  |
|  |  - Bounce rate (quick back to results)                            |  |
|  |  - Query reformulation rate                                       |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Typeahead Metrics:                                                     |
|  +-------------------------------------------------------------------+  |
|  |  - Suggestion acceptance rate                                     |  |
|  |  - Latency (must be < 50ms)                                       |  |
|  |  - Trie size and memory usage                                     |  |
|  |  - Suggestion coverage (% of queries with suggestions)            |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 17. Failure Scenarios and Mitigations

```
+-------------------------------------------------------------------------+
|                 FAILURE SCENARIOS & MITIGATIONS                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  Scenario 1: Index Shard Failure                                        |
|  +-------------------------------------------------------------------+  |
|  |  Impact: Partial results (missing documents from that shard)      |  |
|  |  Mitigation:                                                      |  |
|  |  - Replica shards on different nodes/racks                        |  |
|  |  - Promote replica to primary automatically                       |  |
|  |  - Degrade gracefully: return partial results with warning        |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Scenario 2: Typeahead Service Overload                                 |
|  +-------------------------------------------------------------------+  |
|  |  Impact: Slow or no suggestions                                   |  |
|  |  Mitigation:                                                      |  |
|  |  - CDN caching of popular prefixes                                |  |
|  |  - Client-side caching of recent results                          |  |
|  |  - Rate limiting per user                                         |  |
|  |  - Circuit breaker pattern                                        |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Scenario 3: Indexing Pipeline Failure                                  |
|  +-------------------------------------------------------------------+  |
|  |  Impact: Stale search results                                     |  |
|  |  Mitigation:                                                      |  |
|  |  - Write-ahead log for durability                                 |  |
|  |  - Retry with exponential backoff                                 |  |
|  |  - Alert if index freshness exceeds SLA                           |  |
|  |  - Fallback to last known good index                              |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Scenario 4: Query of Death (expensive query crashes nodes)             |
|  +-------------------------------------------------------------------+  |
|  |  Impact: Cascading failures across search cluster                 |  |
|  |  Mitigation:                                                      |  |
|  |  - Query timeout (kill after 5s)                                  |  |
|  |  - Query complexity analysis before execution                     |  |
|  |  - Bulkhead pattern: isolate heavy queries                        |  |
|  |  - Block known bad query patterns                                 |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Scenario 5: Datacenter Failure                                         |
|  +-------------------------------------------------------------------+  |
|  |  Impact: Complete service outage in that region                   |  |
|  |  Mitigation:                                                      |  |
|  |  - Multi-datacenter replication                                   |  |
|  |  - DNS-based failover to backup datacenter                        |  |
|  |  - Each DC has full copy of index                                 |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 18. Interview Q&A

### Q1: How would you design a typeahead system that handles 1M QPS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  1. Use distributed Trie servers with pre-computed top-K at each node   |
|  2. Shard tries by prefix range (a-f, g-m, n-s, t-z)                    |
|  3. Add CDN/edge caching for the most popular prefixes                  |
|  4. Client-side caching + debouncing to reduce requests                 |
|  5. Keep tries entirely in memory (~5-10 GB)                            |
|  6. Use read replicas to scale horizontally                             |
|  7. Rebuild tries offline every 1-2 hours, atomic swap                  |
|  8. Use a real-time overlay for trending queries                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q2: Why is BM25 preferred over TF-IDF?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  1. TF saturation: BM25 has diminishing returns for high TF             |
|     (10 occurrences isn't 10x better than 1 occurrence)                 |
|  2. Document length normalization: BM25 penalizes long docs that        |
|     naturally have more term occurrences                                |
|  3. Tunable parameters (k1, b) allow domain-specific optimization       |
|  4. Probabilistic foundation gives it stronger theoretical backing      |
|  5. Empirically, BM25 consistently outperforms TF-IDF in benchmarks     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q3: How do you handle the "scatter-gather" problem with many shards?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  Problem: With document-based sharding, every query hits ALL shards.    |
|  As shard count grows, tail latency increases.                          |
|                                                                         |
|  Solutions:                                                             |
|  1. Limit shard count (use larger shards, fewer of them)                |
|  2. Two-phase retrieval: Phase 1 returns IDs + scores, Phase 2          |
|     fetches full docs only for top results                              |
|  3. Tiered index: hot documents in tier-1 (fast SSDs),                  |
|     cold documents in tier-2 (only searched if needed)                  |
|  4. Speculative execution: send to replicas in parallel,                |
|     use whichever responds first                                        |
|  5. Adaptive timeout: skip slow shards, return partial results          |
|  6. Caching: frequent queries served from cache (Redis)                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q4: How would you implement real-time trending in typeahead?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  1. Stream all search queries to Kafka                                  |
|  2. Use Flink/Spark Streaming with a sliding window (e.g., 1 hour)      |
|  3. Count query frequency in current window vs previous window          |
|  4. If current_count / previous_count > threshold -> trending           |
|  5. Push trending queries to typeahead servers as an overlay            |
|  6. Boost trending queries' scores in suggestion ranking                |
|  7. Apply safety filters (remove offensive/spam trending queries)       |
|  8. Decay trending score over time (exponential decay)                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q5: Explain inverted index vs forward index.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Forward Index: Document -> Terms                                       |
|  DocID:1 -> ["weather", "forecast", "today", "sunny"]                   |
|  DocID:2 -> ["weather", "app", "mobile", "ios"]                         |
|                                                                         |
|  Inverted Index: Term -> Documents                                      |
|  "weather"  -> [DocID:1, DocID:2]                                       |
|  "forecast" -> [DocID:1]                                                |
|  "app"      -> [DocID:2]                                                |
|                                                                         |
|  Search uses inverted index (fast term lookup).                         |
|  Forward index used for snippet generation and doc retrieval.           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q6: How do you handle multi-language search?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Answer:                                                                 |
|  1. Language detection at indexing time (CLD2, fastText)                 |
|  2. Language-specific analyzers:                                         |
|     - Different stemmers per language                                    |
|     - Language-specific stop word lists                                  |
|     - CJK languages need different tokenizers (character n-grams)        |
|  3. Separate indices per language (or language field in single index)    |
|  4. Cross-language retrieval: translate query or use multilingual        |
|     embeddings (mBERT, XLM-R)                                            |
|  5. Script detection for proper tokenization                             |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q7: How would you implement "Did you mean...?" spell correction?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Answer:                                                                 |
|  1. Generate candidates: edit distance 1-2 from each query term          |
|  2. Filter: only keep candidates that exist in term dictionary           |
|  3. Score candidates using:                                              |
|     - Frequency in corpus (prefer common words)                          |
|     - Edit distance (prefer closer matches)                              |
|     - Noisy channel model: P(correction) x P(typo|correction)            |
|  4. Context-aware: use bigram/trigram language model                     |
|     "best wether apps" -> "weather" not "whether"                        |
|  5. Show suggestion only if corrected query would return                 |
|     significantly more results                                           |
|  6. Use a pre-computed spelling dictionary indexed by n-grams            |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q8: How do you ensure search result freshness?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Answer:                                                                 |
|  1. Near real-time indexing pipeline (Kafka -> indexer -> ES)            |
|  2. Prioritize re-crawling of frequently changing pages                  |
|  3. Use change detection (If-Modified-Since, ETags, sitemaps)            |
|  4. Time-decay boosting: newer documents scored higher for               |
|     time-sensitive queries                                               |
|  5. Separate "fresh" index for recent content, merged at query time      |
|  6. Push-based indexing for partner content (API submissions)            |
|  7. Monitor index freshness SLA (alert if lag > threshold)               |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q9: Document-based vs Term-based sharding -- which and why?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  Document-based sharding is strongly preferred in practice.             |
|                                                                         |
|  Reasons:                                                               |
|  1. Each shard is a self-contained mini-search-engine                   |
|  2. Local scoring is accurate (all terms for a doc are on same shard)   |
|  3. Adding/rebalancing shards is easier (just move documents)           |
|  4. No cross-shard coordination for multi-term queries                  |
|  5. Term-based creates hotspots (common terms like "the")               |
|                                                                         |
|  Trade-off accepted:                                                    |
|  - Every query must fan out to all shards (scatter-gather)              |
|  - Mitigated by: caching, tiered indices, speculative execution         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q10: How would you design the caching layer for search?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  Multi-level caching:                                                   |
|                                                                         |
|  Level 1: CDN/Edge Cache                                                |
|  - Cache popular query results at edge                                  |
|  - TTL: 5-15 minutes                                                    |
|  - High hit rate for trending/head queries                              |
|                                                                         |
|  Level 2: Application Cache (Redis/Memcached)                           |
|  - Query string -> serialized results                                   |
|  - TTL: 1-5 minutes                                                     |
|  - Handles ~30-40% of queries (head/torso)                              |
|                                                                         |
|  Level 3: Shard-Level Cache                                             |
|  - Cache posting list intersections for common term pairs               |
|  - Cache top-K results for frequent queries per shard                   |
|  - OS page cache for index files                                        |
|                                                                         |
|  Invalidation: Time-based (TTL) rather than event-based                 |
|  (eventual consistency is acceptable for search)                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q11: How would you add semantic search capabilities?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Answer:                                                                |
|  1. Generate dense embeddings for documents using models like           |
|     BERT, Sentence-BERT, or domain-specific models                      |
|  2. Store embeddings in a vector database (Pinecone, Milvus, FAISS)     |
|  3. At query time:                                                      |
|     a) Generate query embedding                                         |
|     b) Find nearest neighbors using ANN (Approximate Nearest Neighbor)  |
|     c) Combine with BM25 results (hybrid search)                        |
|  4. Hybrid scoring: alpha * BM25_score + (1-alpha) * vector_score       |
|  5. ANN algorithms: HNSW (Hierarchical Navigable Small World) or        |
|     IVF (Inverted File Index) for scalable nearest neighbor search      |
|  6. Benefits: handles synonyms, paraphrases, and semantic intent        |
|     without explicit synonym dictionaries                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q12: What happens when a user types a query? Walk through end-to-end.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  End-to-end flow for typing "best weather app":                         |
|                                                                         |
|  1. User types "b" -> typeahead request (after debounce)                |
|  2. Trie lookup "b" -> returns ["best buy", "bank of america", ...]     |
|  3. User types "be" -> new request, "best buy", "best weather"...       |
|  4. User types "best " -> "best buy", "best weather app"...             |
|  5. User selects "best weather app" or presses Enter                    |
|                                                                         |
|  Search execution:                                                      |
|  6.  Query received by load balancer -> query service                   |
|  7.  Query parser: tokenize, stem, remove stop words                    |
|  8.  Spell check: no corrections needed                                 |
|  9.  Coordinator scatters query to all N index shards                   |
|  10. Each shard: look up posting lists for each term                    |
|  11. Each shard: intersect posting lists (AND logic)                    |
|  12. Each shard: score matching docs using BM25                         |
|  13. Each shard: return local top-100 (doc_id, score)                   |
|  14. Coordinator: gather, merge, global re-rank (+ ML model)            |
|  15. Fetch document metadata for top 10 from forward index              |
|  16. Generate snippets with highlighted terms                           |
|  17. Apply personalization adjustments                                  |
|  18. Return response to client (< 200ms)                                |
|  19. Log query + results for analytics                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## Summary: Key Design Decisions

```
+--------------------------------------------------------------------------+
|                     KEY DESIGN DECISIONS                                 |
+--------------------------------------------------------------------------+
|                                                                          |
|  Decision              | Choice           | Rationale                    |
|  ----------------------+------------------+----------------------------  |
|  Sharding strategy     | Document-based   | Independent shards,          |
|                        |                  | simpler scoring              |
|  Ranking algorithm     | BM25 + ML model  | Industry standard +          |
|                        |                  | personalization              |
|  Typeahead structure   | Trie + top-K     | O(prefix_len) lookup,        |
|                        | pre-computed     | constant response time       |
|  Index refresh         | NRT (1s refresh) | Balance freshness vs cost    |
|  Spell correction      | Noisy channel +  | Context-aware, high          |
|                        | language model   | accuracy                     |
|  Caching               | Multi-level      | CDN + Redis + shard-level    |
|  Consistency model     | Eventual         | Acceptable for search        |
|  Replication           | 1 primary +      | Availability + read          |
|                        | 2 replicas       | throughput                   |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

*End of Search Engine and Typeahead System Design*
