# DISTRIBUTED TRACING SYSTEM DESIGN (JAEGER-LIKE)

CHAPTER 1: REQUIREMENTS AND SCALE ESTIMATION
## TABLE OF CONTENTS
*-----------------*
*1. Problem Statement*
*2. Functional Requirements*
*3. Non-Functional Requirements*
*4. Scale Estimation*
*5. Core Concepts*

SECTION 1.1: PROBLEM STATEMENT
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHY DISTRIBUTED TRACING?                                              |*
*|                                                                         |*
*|  In a microservices architecture:                                      |*
*|  * Single request > touches 10-100+ services                          |*
*|  * Each service has its own logs                                       |*
*|  * Debugging is like finding a needle in a haystack                   |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  THE PROBLEM                                                           |*
*|                                                                         |*
*|  User reports: "My order failed"                                       |*
*|                                                                         |*
*|  Without tracing:                                                      |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Request > API Gateway > Order Service > Payment Service       |  |*
*|  |              |               |                |                 |  |*
*|  |              |               |                +-- Error here?   |  |*
*|  |              |               +-- Or here?                       |  |*
*|  |              +-- Maybe here?                                    |  |*
*|  |                                                                 |  |*
*|  |  Each service logs independently:                              |  |*
*|  |  * Different timestamps                                        |  |*
*|  |  * Different request IDs (or none!)                           |  |*
*|  |  * Different log formats                                       |  |*
*|  |  * No causal relationship                                      |  |*
*|  |                                                                 |  |*
*|  |  DEBUGGING: Search each service's logs manually              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  With distributed tracing:                                             |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Trace ID: abc123                                              |  |*
*|  |  +----------------------------------------------------------+  |  |*
*|  |  | API Gateway [span-1]                                     |  |  |*
*|  |  | +-- Order Service [span-2]                              |  |  |*
*|  |  | |   +-- Inventory Check [span-3]    Y 45ms             |  |  |*
*|  |  | |   +-- Payment Service [span-4]   X ERROR - Timeout  |  |  |*
*|  |  | |   |   +-- Stripe API [span-5]    X 30s timeout       |  |  |*
*|  |  | |   +-- (cancelled)                                     |  |  |*
*|  |  | +-- 502 Bad Gateway                                      |  |  |*
*|  |  +----------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  |  DEBUGGING: Single view shows entire request flow           |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 1.2: FUNCTIONAL REQUIREMENTS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  CORE FUNCTIONAL REQUIREMENTS                                          |*
*|                                                                         |*
*|  1. TRACE COLLECTION                                                   |*
*|     * Collect spans from all services                                 |*
*|     * Support multiple languages (Java, Go, Python, Node.js, etc.)   |*
*|     * Context propagation across service boundaries                   |*
*|     * Support various transports (HTTP, gRPC, Kafka, etc.)           |*
*|                                                                         |*
*|  2. TRACE STORAGE                                                      |*
*|     * Store traces durably                                            |*
*|     * Support configurable retention (7 days, 30 days, etc.)        |*
*|     * Handle high write throughput                                    |*
*|                                                                         |*
*|  3. TRACE QUERY & SEARCH                                              |*
*|     * Find traces by trace ID                                        |*
*|     * Search by service name                                          |*
*|     * Search by operation name                                        |*
*|     * Search by tags (user_id, order_id, error=true)                |*
*|     * Search by time range                                            |*
*|     * Search by duration (find slow requests)                        |*
*|                                                                         |*
*|  4. TRACE VISUALIZATION                                               |*
*|     * Display trace timeline (waterfall/Gantt view)                  |*
*|     * Show span hierarchy (parent-child relationships)               |*
*|     * Display span details (tags, logs, errors)                      |*
*|     * Service dependency graph                                        |*
*|                                                                         |*
*|  5. SAMPLING                                                           |*
*|     * Configurable sampling rates                                     |*
*|     * Support different sampling strategies                          |*
*|     * 100% capture of errors/slow requests                           |*
*|                                                                         |*
*|  6. ALERTING (Advanced)                                               |*
*|     * Alert on error rate spikes                                      |*
*|     * Alert on latency anomalies                                      |*
*|     * Integration with alerting systems                               |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 1.3: NON-FUNCTIONAL REQUIREMENTS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  NON-FUNCTIONAL REQUIREMENTS                                           |*
*|                                                                         |*
*|  1. LOW OVERHEAD                                                       |*
*|     * < 1% CPU overhead on instrumented services                     |*
*|     * < 5% latency overhead per request                              |*
*|     * Minimal memory footprint                                        |*
*|                                                                         |*
*|  2. HIGH AVAILABILITY                                                  |*
*|     * Tracing system failure should NOT impact applications          |*
*|     * Fire-and-forget span submission                                |*
*|     * 99.9% availability for query service                          |*
*|                                                                         |*
*|  3. SCALABILITY                                                        |*
*|     * Handle millions of spans per second                            |*
*|     * Scale storage horizontally                                      |*
*|     * Support thousands of services                                  |*
*|                                                                         |*
*|  4. LOW LATENCY                                                        |*
*|     * Spans visible within seconds of generation                     |*
*|     * Query response time < 3 seconds                                |*
*|                                                                         |*
*|  5. DATA INTEGRITY                                                     |*
*|     * No data loss for sampled traces                                |*
*|     * Maintain span relationships correctly                          |*
*|                                                                         |*
*|  6. SECURITY                                                           |*
*|     * Mask/redact sensitive data in spans                           |*
*|     * Access control for trace data                                  |*
*|     * Audit logging                                                   |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 1.4: SCALE ESTIMATION
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  ASSUMPTIONS (Large-scale system)                                      |*
*|                                                                         |*
*|  * 500 microservices                                                  |*
*|  * 100,000 requests per second (peak)                                |*
*|  * Average 20 spans per trace (request touches 20 services)         |*
*|  * 10% sampling rate (production)                                     |*
*|  * 7 days retention                                                   |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SPAN GENERATION RATE                                                  |*
*|                                                                         |*
*|  Total spans generated:                                               |*
*|  100,000 req/s x 20 spans/req = 2,000,000 spans/second              |*
*|                                                                         |*
*|  After 10% sampling:                                                   |*
*|  2,000,000 x 0.1 = 200,000 spans/second                              |*
*|                                                                         |*
*|  Per day:                                                              |*
*|  200,000 x 86,400 = 17.28 billion spans/day                          |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  STORAGE ESTIMATION                                                    |*
*|                                                                         |*
*|  Average span size (uncompressed):                                    |*
*|  +-----------------------------------------------------------------+  |*
*|  |  trace_id:        16 bytes (128-bit)                           |  |*
*|  |  span_id:         8 bytes (64-bit)                             |  |*
*|  |  parent_span_id:  8 bytes                                       |  |*
*|  |  operation_name:  50 bytes (avg)                               |  |*
*|  |  service_name:    30 bytes (avg)                               |  |*
*|  |  start_time:      8 bytes                                       |  |*
*|  |  duration:        8 bytes                                       |  |*
*|  |  tags:            200 bytes (avg, 10 tags)                     |  |*
*|  |  logs:            100 bytes (avg)                              |  |*
*|  |  process_info:    100 bytes                                    |  |*
*|  |  ---------------------------------------                       |  |*
*|  |  Total:           ~500 bytes per span                          |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  Daily storage (uncompressed):                                        |*
*|  17.28B spans x 500 bytes = 8.64 TB/day                              |*
*|                                                                         |*
*|  With compression (5:1 ratio):                                        |*
*|  8.64 TB / 5 = 1.73 TB/day                                           |*
*|                                                                         |*
*|  7-day retention:                                                      |*
*|  1.73 TB x 7 = ~12 TB total storage                                  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  WRITE THROUGHPUT                                                      |*
*|                                                                         |*
*|  200,000 spans/second x 500 bytes = 100 MB/second writes            |*
*|                                                                         |*
*|  This requires:                                                        |*
*|  * Multiple collector instances                                       |*
*|  * Distributed storage (Cassandra/Elasticsearch)                     |*
*|  * Async batched writes                                              |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  NETWORK BANDWIDTH                                                     |*
*|                                                                         |*
*|  Spans from services > Collectors:                                    |*
*|  200,000 spans/s x 500 bytes = 100 MB/s                              |*
*|                                                                         |*
*|  With protocol overhead and retries: ~150 MB/s                       |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  QUERY LOAD                                                            |*
*|                                                                         |*
*|  Assumptions:                                                          |*
*|  * 100 developers/SREs actively debugging                            |*
*|  * 10 queries/minute per person on average                           |*
*|  * 1000 queries/minute = ~17 queries/second                          |*
*|                                                                         |*
*|  Query types:                                                          |*
*|  * Trace by ID: Fast (direct lookup)                                 |*
*|  * Search by tags: More expensive (index scan)                       |*
*|  * Service graphs: Expensive (aggregation)                           |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 1.5: CORE CONCEPTS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  OPENTRACING / OPENTELEMETRY CONCEPTS                                 |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  TRACE                                                                 |*
*|  ------                                                                |*
*|  A trace represents the entire journey of a request through the       |*
*|  distributed system. It's a DAG (Directed Acyclic Graph) of spans.   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |  Trace ID: 1a2b3c4d5e6f7890                                     |  |*
*|  |                                                                 |  |*
*|  |  [Span A: HTTP GET /orders]                                    |  |*
*|  |      |                                                          |  |*
*|  |      +-- [Span B: Query Orders DB]                             |  |*
*|  |      |                                                          |  |*
*|  |      +-- [Span C: Call Payment Service]                        |  |*
*|  |              |                                                  |  |*
*|  |              +-- [Span D: Call Stripe API]                     |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SPAN                                                                  |*
*|  -----                                                                 |*
*|  A span represents a single unit of work within a trace.             |*
*|  Has a start time and duration.                                       |*
*|                                                                         |*
*|  SPAN STRUCTURE:                                                       |*
*|  +-----------------------------------------------------------------+  |*
*|  |  {                                                              |  |*
*|  |    "traceId": "1a2b3c4d5e6f7890",                             |  |*
*|  |    "spanId": "abc123",                                         |  |*
*|  |    "parentSpanId": "parent456",     // null for root span     |  |*
*|  |    "operationName": "HTTP GET /api/orders",                   |  |*
*|  |    "serviceName": "order-service",                            |  |*
*|  |    "startTime": 1640000000000000,   // microseconds           |  |*
*|  |    "duration": 45000,               // microseconds (45ms)    |  |*
*|  |    "tags": {                                                   |  |*
*|  |      "http.method": "GET",                                    |  |*
*|  |      "http.url": "/api/orders/123",                          |  |*
*|  |      "http.status_code": 200,                                 |  |*
*|  |      "user.id": "user_789",                                   |  |*
*|  |      "error": false                                           |  |*
*|  |    },                                                          |  |*
*|  |    "logs": [                                                   |  |*
*|  |      {                                                         |  |*
*|  |        "timestamp": 1640000000010000,                        |  |*
*|  |        "fields": {"event": "cache_miss", "key": "order:123"} |  |*
*|  |      }                                                         |  |*
*|  |    ],                                                          |  |*
*|  |    "process": {                                                |  |*
*|  |      "serviceName": "order-service",                         |  |*
*|  |      "tags": {"hostname": "order-pod-abc", "ip": "10.0.1.5"} |  |*
*|  |    }                                                           |  |*
*|  |  }                                                              |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SPAN RELATIONSHIPS                                                    |*
*|                                                                         |*
*|  1. CHILD_OF (most common)                                            |*
*|     Parent waits for child to complete                                |*
*|     Example: HTTP handler > Database query                           |*
*|                                                                         |*
*|  2. FOLLOWS_FROM                                                       |*
*|     Parent does not wait (async)                                      |*
*|     Example: Request > Queue message > Async processor               |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  CONTEXT PROPAGATION                                                   |*
*|                                                                         |*
*|  How trace context flows between services:                            |*
*|                                                                         |*
*|  HTTP HEADERS (W3C Trace Context):                                    |*
*|  +-----------------------------------------------------------------+  |*
*|  |  traceparent: 00-{trace-id}-{parent-span-id}-{flags}          |  |*
*|  |  traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b...   |  |*
*|  |                                                                 |  |*
*|  |  tracestate: vendor1=value1,vendor2=value2                     |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  JAEGER FORMAT (B3):                                                   |*
*|  +-----------------------------------------------------------------+  |*
*|  |  uber-trace-id: {trace-id}:{span-id}:{parent-id}:{flags}      |  |*
*|  |  uber-trace-id: 1a2b3c:abc123:parent456:1                     |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  gRPC: Passed via metadata                                            |*
*|  Kafka: Passed via message headers                                    |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  BAGGAGE                                                               |*
*|                                                                         |*
*|  Key-value pairs that propagate across ALL spans in a trace.         |*
*|  Use sparingly (adds overhead).                                       |*
*|                                                                         |*
*|  Example: user_id, tenant_id, experiment_id                          |*
*|  Propagates automatically without manual passing.                     |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*COMPARISON WITH SIMILAR SYSTEMS*
*-------------------------------*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  +----------------+-------------+----------------+------------------+ |*
*|  | System         | Origin      | Storage        | Unique Features  | |*
*|  +----------------+-------------+----------------+------------------+ |*
*|  | Jaeger         | Uber        | Cassandra/ES   | CNCF graduated   | |*
*|  | Zipkin         | Twitter     | Cassandra/ES   | Simpler, mature  | |*
*|  | AWS X-Ray      | AWS         | Managed        | AWS integration  | |*
*|  | Google Trace   | Google      | Managed        | GCP integration  | |*
*|  | Datadog APM    | Datadog     | Managed        | Full observability| |*
*|  | Tempo          | Grafana     | Object storage | Cost-effective   | |*
*|  | Lightstep      | Lightstep   | Managed        | Service mesh     | |*
*|  +----------------+-------------+----------------+------------------+ |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF CHAPTER 1
