# DISTRIBUTED TRACING SYSTEM DESIGN (JAEGER-LIKE)

CHAPTER 3: STORAGE AND DATA MODEL
## TABLE OF CONTENTS
*-----------------*
*1. Data Model Design*
*2. Storage Schema (Cassandra)*
*3. Indexing Strategy (Elasticsearch)*
*4. Storage Patterns*
*5. Data Retention and Archival*

SECTION 3.1: DATA MODEL DESIGN
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SPAN DATA MODEL                                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  message Span {                                                |  |*
*|  |    // Identity                                                 |  |*
*|  |    bytes   trace_id          = 1;  // 128-bit unique ID      |  |*
*|  |    bytes   span_id           = 2;  // 64-bit unique ID       |  |*
*|  |    bytes   parent_span_id    = 3;  // 64-bit (null for root) |  |*
*|  |                                                                 |  |*
*|  |    // Names                                                    |  |*
*|  |    string  operation_name    = 4;  // e.g., "HTTP GET /orders"|  |*
*|  |                                                                 |  |*
*|  |    // Timing                                                   |  |*
*|  |    int64   start_time        = 5;  // microseconds since epoch|  |*
*|  |    int64   duration          = 6;  // microseconds            |  |*
*|  |                                                                 |  |*
*|  |    // References (parent relationships)                       |  |*
*|  |    repeated SpanRef references = 7;                           |  |*
*|  |                                                                 |  |*
*|  |    // Additional data                                         |  |*
*|  |    repeated Tag    tags      = 8;  // key-value attributes   |  |*
*|  |    repeated Log    logs      = 9;  // timestamped events     |  |*
*|  |    Process         process   = 10; // service info           |  |*
*|  |                                                                 |  |*
*|  |    // Flags                                                    |  |*
*|  |    uint32  flags             = 11; // sampling flags         |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SUPPORTING TYPES                                                      |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  message Tag {                                                 |  |*
*|  |    string key = 1;                                            |  |*
*|  |    oneof value {                                              |  |*
*|  |      string str_value    = 2;                                |  |*
*|  |      bool   bool_value   = 3;                                |  |*
*|  |      int64  int_value    = 4;                                |  |*
*|  |      double double_value = 5;                                |  |*
*|  |      bytes  binary_value = 6;                                |  |*
*|  |    }                                                           |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  message Log {                                                 |  |*
*|  |    int64          timestamp = 1;  // microseconds            |  |*
*|  |    repeated Tag   fields    = 2;  // log fields              |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  message Process {                                             |  |*
*|  |    string        service_name = 1;                            |  |*
*|  |    repeated Tag  tags         = 2;  // hostname, ip, version |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  message SpanRef {                                             |  |*
*|  |    enum RefType {                                             |  |*
*|  |      CHILD_OF     = 0;  // synchronous call                  |  |*
*|  |      FOLLOWS_FROM = 1;  // async/fire-and-forget            |  |*
*|  |    }                                                           |  |*
*|  |    RefType ref_type   = 1;                                    |  |*
*|  |    bytes   trace_id   = 2;                                    |  |*
*|  |    bytes   span_id    = 3;                                    |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  COMMON TAGS (Semantic Conventions)                                   |*
*|                                                                         |*
*|  HTTP Tags:                                                            |*
*|  +------------------------+------------------------------------------+|*
*|  | Tag                    | Example                                  ||*
*|  +------------------------+------------------------------------------+|*
*|  | http.method            | "GET", "POST"                           ||*
*|  | http.url               | "/api/orders/123"                       ||*
*|  | http.status_code       | 200, 404, 500                           ||*
*|  | http.request_content_length | 1024                               ||*
*|  +------------------------+------------------------------------------+|*
*|                                                                         |*
*|  Database Tags:                                                        |*
*|  +------------------------+------------------------------------------+|*
*|  | db.system              | "postgresql", "mysql", "redis"          ||*
*|  | db.statement           | "SELECT * FROM users WHERE id=?"       ||*
*|  | db.name                | "orders_db"                             ||*
*|  | db.operation           | "SELECT", "INSERT"                      ||*
*|  +------------------------+------------------------------------------+|*
*|                                                                         |*
*|  Error Tags:                                                           |*
*|  +------------------------+------------------------------------------+|*
*|  | error                  | true                                     ||*
*|  | error.message          | "Connection timeout"                    ||*
*|  | error.stack            | "at Service.call (service.js:45)..."   ||*
*|  +------------------------+------------------------------------------+|*
*|                                                                         |*
*|  Custom Business Tags:                                                 |*
*|  +------------------------+------------------------------------------+|*
*|  | user.id                | "user_12345"                            ||*
*|  | order.id               | "order_67890"                           ||*
*|  | tenant.id              | "acme_corp"                             ||*
*|  | feature.flag           | "new_checkout_enabled"                  ||*
*|  +------------------------+------------------------------------------+|*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3.2: STORAGE SCHEMA (CASSANDRA)
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHY CASSANDRA FOR TRACE STORAGE?                                     |*
*|                                                                         |*
*|  * High write throughput (LSM-tree based)                            |*
*|  * Linear scalability                                                  |*
*|  * Time-series friendly (TTL for retention)                          |*
*|  * Primary key lookups are very fast                                 |*
*|  * Proven at scale (Uber, Netflix)                                   |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  TABLE 1: TRACES (Main span storage)                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CREATE TABLE traces (                                         |  |*
*|  |    trace_id        blob,      -- Partition key                |  |*
*|  |    span_id         blob,      -- Clustering key               |  |*
*|  |    span_hash       bigint,    -- For deduplication            |  |*
*|  |    parent_id       blob,                                       |  |*
*|  |    operation_name  text,                                       |  |*
*|  |    flags           int,                                        |  |*
*|  |    start_time      bigint,    -- microseconds                 |  |*
*|  |    duration        bigint,    -- microseconds                 |  |*
*|  |    tags            list<frozen<tag>>,                         |  |*
*|  |    logs            list<frozen<log>>,                         |  |*
*|  |    refs            list<frozen<span_ref>>,                    |  |*
*|  |    process         frozen<process>,                           |  |*
*|  |    PRIMARY KEY (trace_id, span_id)                            |  |*
*|  |  ) WITH CLUSTERING ORDER BY (span_id ASC)                     |  |*
*|  |    AND default_time_to_live = 604800;  -- 7 days TTL         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ACCESS PATTERNS:                                                      |*
*|  * Get all spans for trace: SELECT * FROM traces WHERE trace_id = ? |*
*|  * Very fast: Single partition read                                  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  TABLE 2: SERVICE_NAMES (Service index)                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CREATE TABLE service_names (                                  |  |*
*|  |    service_name text,                                          |  |*
*|  |    PRIMARY KEY (service_name)                                  |  |*
*|  |  );                                                              |  |*
*|  |                                                                 |  |*
*|  |  -- Used for: "List all services" dropdown in UI              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  TABLE 3: OPERATION_NAMES (Operation index per service)               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CREATE TABLE operation_names (                                |  |*
*|  |    service_name    text,                                       |  |*
*|  |    operation_name  text,                                       |  |*
*|  |    PRIMARY KEY (service_name, operation_name)                 |  |*
*|  |  );                                                              |  |*
*|  |                                                                 |  |*
*|  |  -- Used for: "List operations for service" dropdown          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  TABLE 4: SERVICE_NAME_INDEX (Find traces by service)                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CREATE TABLE service_name_index (                             |  |*
*|  |    service_name  text,                                         |  |*
*|  |    bucket        int,        -- Time bucket (e.g., hour)      |  |*
*|  |    start_time    bigint,                                       |  |*
*|  |    trace_id      blob,                                         |  |*
*|  |    PRIMARY KEY ((service_name, bucket), start_time, trace_id) |  |*
*|  |  ) WITH CLUSTERING ORDER BY (start_time DESC);                |  |*
*|  |                                                                 |  |*
*|  |  -- Time bucketing prevents hot partitions                    |  |*
*|  |  -- bucket = timestamp / 3600  (hourly buckets)               |  |*
*|  |                                                                 |  |*
*|  |  QUERY: Find recent traces for "order-service"               |  |*
*|  |  SELECT trace_id FROM service_name_index                      |  |*
*|  |  WHERE service_name = 'order-service'                         |  |*
*|  |    AND bucket IN (current_hour, current_hour - 1, ...)       |  |*
*|  |  LIMIT 20;                                                     |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  TABLE 5: TAG_INDEX (Find traces by tag)                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CREATE TABLE tag_index (                                      |  |*
*|  |    service_name  text,                                         |  |*
*|  |    tag_key       text,                                         |  |*
*|  |    tag_value     text,                                         |  |*
*|  |    bucket        int,                                          |  |*
*|  |    start_time    bigint,                                       |  |*
*|  |    trace_id      blob,                                         |  |*
*|  |    span_id       blob,                                         |  |*
*|  |    PRIMARY KEY ((service_name, tag_key, tag_value, bucket),   |  |*
*|  |                 start_time, trace_id, span_id)                |  |*
*|  |  ) WITH CLUSTERING ORDER BY (start_time DESC);                |  |*
*|  |                                                                 |  |*
*|  |  QUERY: Find traces with error=true for order-service        |  |*
*|  |  SELECT trace_id FROM tag_index                                |  |*
*|  |  WHERE service_name = 'order-service'                         |  |*
*|  |    AND tag_key = 'error'                                      |  |*
*|  |    AND tag_value = 'true'                                     |  |*
*|  |    AND bucket IN (...)                                        |  |*
*|  |  LIMIT 20;                                                     |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  TABLE 6: DURATION_INDEX (Find slow traces)                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CREATE TABLE duration_index (                                 |  |*
*|  |    service_name    text,                                       |  |*
*|  |    operation_name  text,                                       |  |*
*|  |    bucket          int,                                        |  |*
*|  |    duration        bigint,                                     |  |*
*|  |    start_time      bigint,                                     |  |*
*|  |    trace_id        blob,                                       |  |*
*|  |    PRIMARY KEY ((service_name, operation_name, bucket),       |  |*
*|  |                 duration, start_time, trace_id)               |  |*
*|  |  ) WITH CLUSTERING ORDER BY (duration DESC);                  |  |*
*|  |                                                                 |  |*
*|  |  QUERY: Find slowest traces for "GET /orders"                 |  |*
*|  |  SELECT trace_id, duration FROM duration_index               |  |*
*|  |  WHERE service_name = 'order-service'                         |  |*
*|  |    AND operation_name = 'HTTP GET /orders'                   |  |*
*|  |    AND bucket IN (...)                                        |  |*
*|  |  LIMIT 20;                                                     |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  TABLE 7: DEPENDENCIES (Service graph)                                |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CREATE TABLE dependencies (                                   |  |*
*|  |    ts_bucket   bigint,       -- Daily bucket                  |  |*
*|  |    parent      text,         -- Caller service                |  |*
*|  |    child       text,         -- Called service                |  |*
*|  |    call_count  counter,      -- Number of calls               |  |*
*|  |    PRIMARY KEY (ts_bucket, parent, child)                     |  |*
*|  |  );                                                              |  |*
*|  |                                                                 |  |*
*|  |  -- Aggregated from spans: parent_service -> child_service    |  |*
*|  |  -- Updated by Spark/Flink job processing spans              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3.3: INDEXING STRATEGY (ELASTICSEARCH)
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHY ELASTICSEARCH FOR INDEXING?                                      |*
*|                                                                         |*
*|  Cassandra limitations:                                                |*
*|  * Must know partition key for queries                               |*
*|  * No ad-hoc queries                                                  |*
*|  * No full-text search                                               |*
*|                                                                         |*
*|  Elasticsearch provides:                                               |*
*|  * Flexible queries on any field                                     |*
*|  * Full-text search on logs                                          |*
*|  * Aggregations (service stats)                                      |*
*|  * Fast range queries                                                 |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DUAL-STORAGE ARCHITECTURE                                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |                       Collector                                |  |*
*|  |                          |                                      |  |*
*|  |            +-------------+-------------+                       |  |*
*|  |            |                           |                       |  |*
*|  |            v                           v                       |  |*
*|  |  +-----------------+         +-----------------+              |  |*
*|  |  |   Cassandra     |         |  Elasticsearch  |              |  |*
*|  |  |                 |         |                 |              |  |*
*|  |  |  Full span data |         |  Index only:    |              |  |*
*|  |  |  (complete JSON)|         |  - trace_id     |              |  |*
*|  |  |                 |         |  - service_name |              |  |*
*|  |  |                 |         |  - operation    |              |  |*
*|  |  |                 |         |  - tags         |              |  |*
*|  |  |                 |         |  - timestamp    |              |  |*
*|  |  |                 |         |  - duration     |              |  |*
*|  |  +-----------------+         +-----------------+              |  |*
*|  |          ^                           |                         |  |*
*|  |          |                           | 1. Search query        |  |*
*|  |          |                           v                         |  |*
*|  |          |                    Returns: trace_ids              |  |*
*|  |          |                           |                         |  |*
*|  |          +---------------------------+                         |  |*
*|  |                2. Fetch full spans by trace_id                |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  ELASTICSEARCH INDEX MAPPING                                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  {                                                              |  |*
*|  |    "mappings": {                                               |  |*
*|  |      "properties": {                                          |  |*
*|  |        "traceID": {                                           |  |*
*|  |          "type": "keyword"                                    |  |*
*|  |        },                                                      |  |*
*|  |        "spanID": {                                            |  |*
*|  |          "type": "keyword"                                    |  |*
*|  |        },                                                      |  |*
*|  |        "operationName": {                                     |  |*
*|  |          "type": "keyword"                                    |  |*
*|  |        },                                                      |  |*
*|  |        "serviceName": {                                       |  |*
*|  |          "type": "keyword"                                    |  |*
*|  |        },                                                      |  |*
*|  |        "startTime": {                                         |  |*
*|  |          "type": "date",                                      |  |*
*|  |          "format": "epoch_micros"                             |  |*
*|  |        },                                                      |  |*
*|  |        "startTimeMillis": {                                   |  |*
*|  |          "type": "date"                                       |  |*
*|  |        },                                                      |  |*
*|  |        "duration": {                                          |  |*
*|  |          "type": "long"                                       |  |*
*|  |        },                                                      |  |*
*|  |        "tags": {                                               |  |*
*|  |          "type": "nested",                                    |  |*
*|  |          "properties": {                                      |  |*
*|  |            "key": {"type": "keyword"},                       |  |*
*|  |            "value": {"type": "keyword"}                      |  |*
*|  |          }                                                     |  |*
*|  |        },                                                      |  |*
*|  |        "tag": {                                                |  |*
*|  |          "type": "object",                                    |  |*
*|  |          "dynamic": "true"   // Allow any tag.* field        |  |*
*|  |        }                                                       |  |*
*|  |      }                                                         |  |*
*|  |    }                                                           |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  INDEX LIFECYCLE MANAGEMENT                                           |*
*|                                                                         |*
*|  TIME-BASED INDICES:                                                   |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  jaeger-span-2024-01-01                                       |  |*
*|  |  jaeger-span-2024-01-02                                       |  |*
*|  |  jaeger-span-2024-01-03  <- current (hot)                     |  |*
*|  |                                                                 |  |*
*|  |  Benefits:                                                     |  |*
*|  |  * Easy time-based queries                                    |  |*
*|  |  * Simple retention (drop old indices)                       |  |*
*|  |  * Optimize old indices (force merge)                        |  |*
*|  |                                                                 |  |*
*|  |  ILM Policy:                                                   |  |*
*|  |  {                                                             |  |*
*|  |    "policy": {                                                |  |*
*|  |      "phases": {                                              |  |*
*|  |        "hot": {                                               |  |*
*|  |          "actions": {                                        |  |*
*|  |            "rollover": {                                     |  |*
*|  |              "max_size": "50GB",                             |  |*
*|  |              "max_age": "1d"                                 |  |*
*|  |            }                                                  |  |*
*|  |          }                                                    |  |*
*|  |        },                                                     |  |*
*|  |        "warm": {                                              |  |*
*|  |          "min_age": "2d",                                    |  |*
*|  |          "actions": {                                        |  |*
*|  |            "forcemerge": {"max_num_segments": 1}            |  |*
*|  |          }                                                    |  |*
*|  |        },                                                     |  |*
*|  |        "delete": {                                            |  |*
*|  |          "min_age": "7d",                                    |  |*
*|  |          "actions": {"delete": {}}                          |  |*
*|  |        }                                                      |  |*
*|  |      }                                                        |  |*
*|  |    }                                                           |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SAMPLE QUERIES                                                        |*
*|                                                                         |*
*|  Find traces with error for specific service:                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  {                                                              |  |*
*|  |    "query": {                                                  |  |*
*|  |      "bool": {                                                 |  |*
*|  |        "must": [                                              |  |*
*|  |          {"term": {"serviceName": "order-service"}},         |  |*
*|  |          {"term": {"tag.error": "true"}},                    |  |*
*|  |          {"range": {                                          |  |*
*|  |            "startTimeMillis": {                               |  |*
*|  |              "gte": "now-24h"                                 |  |*
*|  |            }                                                   |  |*
*|  |          }}                                                    |  |*
*|  |        ]                                                       |  |*
*|  |      }                                                         |  |*
*|  |    },                                                          |  |*
*|  |    "aggs": {                                                   |  |*
*|  |      "traces": {                                              |  |*
*|  |        "terms": {"field": "traceID", "size": 20}            |  |*
*|  |      }                                                         |  |*
*|  |    }                                                           |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  Find slowest traces (P99):                                           |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  {                                                              |  |*
*|  |    "query": {                                                  |  |*
*|  |      "bool": {                                                 |  |*
*|  |        "must": [                                              |  |*
*|  |          {"term": {"serviceName": "order-service"}},         |  |*
*|  |          {"term": {"operationName": "HTTP GET /orders"}}    |  |*
*|  |        ]                                                       |  |*
*|  |      }                                                         |  |*
*|  |    },                                                          |  |*
*|  |    "sort": [{"duration": "desc"}],                           |  |*
*|  |    "size": 20                                                  |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3.4: STORAGE PATTERNS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  HOT/WARM/COLD STORAGE TIERS                                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |  HOT TIER (0-2 days)                                      ||  |*
*|  |  |  Storage: NVMe SSD                                        ||  |*
*|  |  |  * Recent traces, fast access                            ||  |*
*|  |  |  * Most queries hit this tier                            ||  |*
*|  |  |  * Full indexing                                          ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                          |                                      |  |*
*|  |                          v                                      |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |  WARM TIER (2-7 days)                                     ||  |*
*|  |  |  Storage: SSD                                              ||  |*
*|  |  |  * Less frequent access                                   ||  |*
*|  |  |  * Compressed, force-merged indices                      ||  |*
*|  |  |  * Acceptable query latency                              ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                          |                                      |  |*
*|  |                          v                                      |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |  COLD TIER (7-30+ days)                                   ||  |*
*|  |  |  Storage: Object Storage (S3)                             ||  |*
*|  |  |  * Archival, compliance                                   ||  |*
*|  |  |  * Trace ID lookup only                                   ||  |*
*|  |  |  * Higher query latency OK                               ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  GRAFANA TEMPO APPROACH (Object Storage Native)                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Spans -> Tempo -> Object Storage (S3/GCS)                      |  |*
*|  |                                                                 |  |*
*|  |  HOW IT WORKS:                                                 |  |*
*|  |  1. Buffer spans in memory                                    |  |*
*|  |  2. Batch into blocks (Parquet-like format)                  |  |*
*|  |  3. Write block to object storage                            |  |*
*|  |  4. Update bloom filter index                                 |  |*
*|  |                                                                 |  |*
*|  |  BLOCK STRUCTURE:                                              |  |*
*|  |  s3://tempo-traces/                                           |  |*
*|  |    +-- block-uuid/                                            |  |*
*|  |        +-- data.parquet     (spans data)                     |  |*
*|  |        +-- bloom.gz         (trace ID bloom filter)          |  |*
*|  |        +-- meta.json        (block metadata)                 |  |*
*|  |                                                                 |  |*
*|  |  FINDING A TRACE:                                              |  |*
*|  |  1. Check bloom filter of each block                         |  |*
*|  |  2. Only read blocks where bloom says "maybe yes"           |  |*
*|  |  3. Scan data file for trace ID                              |  |*
*|  |                                                                 |  |*
*|  |  PROS:                                                         |  |*
*|  |  * 10-100x cheaper than Elasticsearch                        |  |*
*|  |  * Scales infinitely                                          |  |*
*|  |  * No database to manage                                      |  |*
*|  |                                                                 |  |*
*|  |  CONS:                                                         |  |*
*|  |  * Can only search by trace ID (use exemplars for discovery)|  |*
*|  |  * Higher query latency                                       |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  WRITE OPTIMIZATION                                                    |*
*|                                                                         |*
*|  BATCHING:                                                             |*
*|  * Don't write each span individually                                |*
*|  * Batch 100-1000 spans per write                                    |*
*|  * Reduces round-trips, improves throughput                          |*
*|                                                                         |*
*|  ASYNC WRITES:                                                         |*
*|  * Use async I/O (don't block on storage)                           |*
*|  * Buffer in memory, write in background                            |*
*|  * Handle backpressure gracefully                                    |*
*|                                                                         |*
*|  COMPRESSION:                                                          |*
*|  * Compress span data before storage                                 |*
*|  * LZ4 (fast) or Zstd (better ratio)                               |*
*|  * 5-10x compression typical                                         |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3.5: DATA RETENTION AND ARCHIVAL
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  RETENTION STRATEGIES                                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  STRATEGY 1: Time-based TTL                                    |  |*
*|  |  -----------------------------                                  |  |*
*|  |  * All data expires after X days                              |  |*
*|  |  * Simplest approach                                           |  |*
*|  |  * Cassandra: default_time_to_live                            |  |*
*|  |  * ES: ILM delete phase                                       |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  STRATEGY 2: Tiered retention                                  |  |*
*|  |  -------------------------------                                |  |*
*|  |  * Hot: 7 days full detail                                    |  |*
*|  |  * Warm: 30 days sampled (1%)                                |  |*
*|  |  * Cold: 90 days errors only                                 |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  STRATEGY 3: Smart retention                                   |  |*
*|  |  ------------------------------                                 |  |*
*|  |  Keep traces that match criteria:                             |  |*
*|  |  * Has error                                                   |  |*
*|  |  * Duration > P99                                             |  |*
*|  |  * Tagged as "important"                                      |  |*
*|  |  * Random sample (1%)                                         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  COST CALCULATION EXAMPLE                                             |*
*|                                                                         |*
*|  Scenario: 17B spans/day, 500 bytes/span                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  OPTION A: Elasticsearch Only (7 days)                        |  |*
*|  |  --------------------------------------                        |  |*
*|  |  Raw: 8.5 TB/day × 7 = 59.5 TB                                |  |*
*|  |  With replicas (2x): 119 TB                                   |  |*
*|  |  ES cluster: ~40 nodes × m5.4xlarge                          |  |*
*|  |  Cost: ~$50,000/month                                         |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  OPTION B: Cassandra + Elasticsearch                          |  |*
*|  |  --------------------------------------                        |  |*
*|  |  Cassandra (spans): 30 TB (RF=3, compressed)                 |  |*
*|  |  Elasticsearch (index only): 3 TB                            |  |*
*|  |  Cost: ~$25,000/month                                         |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  OPTION C: Tempo + Object Storage                             |  |*
*|  |  --------------------------------------                        |  |*
*|  |  S3: 12 TB compressed                                         |  |*
*|  |  S3 storage: ~$300/month                                      |  |*
*|  |  Tempo instances: 5 nodes                                     |  |*
*|  |  Cost: ~$5,000/month                                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF CHAPTER 3
