# CHAPTER 10: OBSERVABILITY
*Understanding System Behavior in Production*

Observability lets you understand what's happening inside your system
by examining its outputs. The three pillars: Metrics, Logs, and Traces.

## SECTION 10.1: THE THREE PILLARS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THREE PILLARS OF OBSERVABILITY                                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  +----------+      +----------+      +----------+                 |  |
|  |  | METRICS  |      |  LOGS    |      | TRACES   |                 |  |
|  |  |          |      |          |      |          |                 |  |
|  |  | Numbers  |      |  Events  |      | Requests |                 |  |
|  |  | over     |      |  with    |      | across   |                 |  |
|  |  | time     |      |  context |      | services |                 |  |
|  |  +----------+      +----------+      +----------+                 |  |
|  |       |                 |                 |                       |  |
|  |       v                 v                 v                       |  |
|  |  "What's the      "What           "Why is this                    |  |
|  |   error rate?"     happened?"      request slow?"                 |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  METRICS                                                                |
|  ---------                                                              |
|  Numeric measurements over time. Aggregated, cheap to store.            |
|                                                                         |
|  Examples:                                                              |
|  * Request count: 1,000 req/sec                                         |
|  * Error rate: 0.1%                                                     |
|  * Latency P99: 200ms                                                   |
|  * CPU usage: 45%                                                       |
|                                                                         |
|  LOGS                                                                   |
|  ------                                                                 |
|  Immutable records of discrete events.                                  |
|                                                                         |
|  Example:                                                               |
|  2024-01-15T10:30:00Z INFO  [order-service] Order created               |
|    order_id=12345 user_id=67890 total=99.99                             |
|                                                                         |
|  TRACES                                                                 |
|  --------                                                               |
|  Track a request as it flows through multiple services.                 |
|                                                                         |
|  User Request --> Gateway --> Order Service --> Payment Service         |
|       |              |              |                |                  |
|       +--------------+--------------+----------------+                  |
|                     trace_id: abc123                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10.2: METRICS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  METRIC TYPES                                                           |
|                                                                         |
|  1. COUNTER                                                             |
|  -----------                                                            |
|  Monotonically increasing value. Only goes up (or resets).              |
|                                                                         |
|  http_requests_total{method="GET", status="200"} 150432                 |
|                                                                         |
|  Use for: Request counts, error counts, bytes transferred               |
|                                                                         |
|  To get rate: rate(http_requests_total[5m])                             |
|  > Requests per second over last 5 minutes                              |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. GAUGE                                                               |
|  ----------                                                             |
|  Value that can go up or down.                                          |
|                                                                         |
|  temperature_celsius{room="server"} 22.5                                |
|  active_connections 847                                                 |
|  queue_depth 15                                                         |
|                                                                         |
|  Use for: Current state, queue sizes, temperatures                      |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. HISTOGRAM                                                           |
|  --------------                                                         |
|  Distribution of values in buckets.                                     |
|                                                                         |
|  http_request_duration_seconds_bucket{le="0.1"} 50000                   |
|  http_request_duration_seconds_bucket{le="0.5"} 80000                   |
|  http_request_duration_seconds_bucket{le="1.0"} 95000                   |
|  http_request_duration_seconds_bucket{le="+Inf"} 100000                 |
|                                                                         |
|  Use for: Latency distributions, request sizes                          |
|  Calculate percentiles: histogram_quantile(0.99, ...)                   |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  4. SUMMARY                                                             |
|  -----------                                                            |
|  Pre-calculated percentiles.                                            |
|                                                                         |
|  http_request_duration_seconds{quantile="0.5"} 0.05                     |
|  http_request_duration_seconds{quantile="0.9"} 0.12                     |
|  http_request_duration_seconds{quantile="0.99"} 0.25                    |
|                                                                         |
|  HISTOGRAM vs SUMMARY:                                                  |
|  * Histogram: Calculate percentiles server-side, aggregatable           |
|  * Summary: Pre-calculated, NOT aggregatable across instances           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### KEY METRICS TO MONITOR

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE FOUR GOLDEN SIGNALS (Google SRE)                                   |
|                                                                         |
|  1. LATENCY                                                             |
|     Time to service a request                                           |
|     Track: P50, P90, P99, P999                                          |
|     Separate success vs error latency                                   |
|                                                                         |
|  2. TRAFFIC                                                             |
|     Demand on your system                                               |
|     HTTP: requests/second                                               |
|     Database: queries/second                                            |
|     Streaming: records/second                                           |
|                                                                         |
|  3. ERRORS                                                              |
|     Rate of failed requests                                             |
|     HTTP 5xx, explicit failures, wrong results                          |
|                                                                         |
|  4. SATURATION                                                          |
|     How "full" your service is                                          |
|     CPU, memory, disk I/O, network                                      |
|     Queue depth (if saturated, queues grow)                             |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  RED METHOD (For services)                                              |
|  --------------------------                                             |
|  * Rate: Requests per second                                            |
|  * Errors: Failed requests per second                                   |
|  * Duration: Request latency                                            |
|                                                                         |
|  USE METHOD (For resources)                                             |
|  -----------------------------                                          |
|  * Utilization: % time resource is busy                                 |
|  * Saturation: Work waiting (queue depth)                               |
|  * Errors: Error events                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10.3: LOGGING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STRUCTURED LOGGING                                                     |
|                                                                         |
|  UNSTRUCTURED (Bad):                                                    |
|  2024-01-15 10:30:00 Order 12345 created for user 67890                 |
|                                                                         |
|  STRUCTURED (Good):                                                     |
|  {                                                                      |
|    "timestamp": "2024-01-15T10:30:00Z",                                 |
|    "level": "INFO",                                                     |
|    "service": "order-service",                                          |
|    "message": "Order created",                                          |
|    "order_id": "12345",                                                 |
|    "user_id": "67890",                                                  |
|    "total": 99.99,                                                      |
|    "trace_id": "abc123"                                                 |
|  }                                                                      |
|                                                                         |
|  WHY STRUCTURED:                                                        |
|  * Easy to search: order_id:12345                                       |
|  * Easy to aggregate: count by service                                  |
|  * Easy to filter: level:ERROR AND service:payment                      |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  LOG LEVELS                                                             |
|                                                                         |
|  DEBUG   Detailed info for debugging (off in production)                |
|  INFO    Normal operations (request handled, job completed)             |
|  WARN    Something unexpected but recoverable                           |
|  ERROR   Something failed, needs attention                              |
|  FATAL   System cannot continue                                         |
|                                                                         |
|  GUIDELINES:                                                            |
|  * DEBUG: Only enable when debugging                                    |
|  * INFO: Significant business events                                    |
|  * WARN: Degraded behavior, potential issues                            |
|  * ERROR: Failures that need investigation                              |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  WHAT TO LOG                                                            |
|                                                                         |
|  DO LOG:                                                                |
|  Y Request start/end with duration                                      |
|  Y Business events (order created, payment processed)                   |
|  Y Errors with stack traces                                             |
|  Y External service calls                                               |
|  Y Decision points (why a branch was taken)                             |
|                                                                         |
|  DON'T LOG:                                                             |
|  X Passwords or secrets                                                 |
|  X PII (credit cards, SSN) unless required                              |
|  X Every loop iteration                                                 |
|  X Large payloads (log IDs, not full objects)                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### LOG AGGREGATION ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CENTRALIZED LOGGING                                                    |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Service A -+                                                     |  |
|  |  Service B -+--> Log Shipper --> Message Queue --> Log Store      |  |
|  |  Service C -+   (Filebeat)      (Kafka)           (Elastic)       |  |
|  |                                                                   |  |
|  |                                       |                           |  |
|  |                                       v                           |  |
|  |                                  +-------------+                  |  |
|  |                                  |  Dashboard  |                  |  |
|  |                                  |  (Kibana)   |                  |  |
|  |                                  +-------------+                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  TOOLS:                                                                 |
|  * Collection: Fluentd, Filebeat, Vector                                |
|  * Processing: Logstash, Kafka                                          |
|  * Storage: Elasticsearch, Loki, CloudWatch Logs                        |
|  * Visualization: Kibana, Grafana                                       |
|                                                                         |
|  POPULAR STACKS:                                                        |
|  * ELK: Elasticsearch + Logstash + Kibana                               |
|  * EFK: Elasticsearch + Fluentd + Kibana                                |
|  * PLG: Promtail + Loki + Grafana (lightweight)                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10.4: DISTRIBUTED TRACING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS DISTRIBUTED TRACING?                                           |
|                                                                         |
|  Track a request as it propagates through multiple services.            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  User Request (trace_id: abc123)                                  |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  +----------+ ------------------------------------------------    |  |
|  |  | Gateway  | [====]                              span A          |  |
|  |  +----+-----+                                                     |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  +----------+   ------------------------------------------        |  |
|  |  |  Order   |   [==========]                   span B             |  |
|  |  | Service  |        |                                            |  |
|  |  +----+-----+        |                                            |  |
|  |       |              |                                            |  |
|  |       +--------------+                                            |  |
|  |       v              v                                            |  |
|  |  +----------+   +----------+                                      |  |
|  |  | Payment  |   |Inventory |                                      |  |
|  |  | Service  |   | Service  |                                      |  |
|  |  |[======]  |   |[====]    |    spans C, D                        |  |
|  |  +----------+   +----------+                                      |  |
|  |                                                                   |  |
|  |  Timeline: -------------------------------------------->          |  |
|  |            0ms      50ms     100ms    150ms    200ms              |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  KEY CONCEPTS:                                                          |
|                                                                         |
|  TRACE                                                                  |
|  -------                                                                |
|  End-to-end journey of a request                                        |
|  Identified by trace_id                                                 |
|                                                                         |
|  SPAN                                                                   |
|  ------                                                                 |
|  A single operation within a trace                                      |
|  Has: span_id, trace_id, parent_span_id, name, timing, tags             |
|                                                                         |
|  CONTEXT PROPAGATION                                                    |
|  ---------------------                                                  |
|  Pass trace_id between services (headers, message properties)           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### IMPLEMENTING TRACING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONTEXT PROPAGATION                                                    |
|                                                                         |
|  HTTP Headers:                                                          |
|  traceparent: 00-abc123-def456-01                                       |
|  tracestate: vendor=value                                               |
|                                                                         |
|  Or custom headers:                                                     |
|  X-Trace-ID: abc123                                                     |
|  X-Span-ID: def456                                                      |
|                                                                         |
|  OPENTELEMETRY STANDARD:                                                |
|  -------------------------                                              |
|  W3C Trace Context format (widely adopted)                              |
|                                                                         |
|  traceparent: {version}-{trace-id}-{parent-id}-{flags}                  |
|  Example: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  SPAN ATTRIBUTES                                                        |
|                                                                         |
|  {                                                                      |
|    "trace_id": "abc123",                                                |
|    "span_id": "def456",                                                 |
|    "parent_span_id": "ghi789",                                          |
|    "operation_name": "POST /orders",                                    |
|    "service_name": "order-service",                                     |
|    "start_time": "2024-01-15T10:30:00Z",                                |
|    "duration_ms": 150,                                                  |
|    "status": "OK",                                                      |
|    "tags": {                                                            |
|      "http.method": "POST",                                             |
|      "http.status_code": 201,                                           |
|      "db.type": "postgresql"                                            |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  TRACING TOOLS                                                          |
|                                                                         |
|  * Jaeger (open source, CNCF)                                           |
|  * Zipkin (open source)                                                 |
|  * AWS X-Ray                                                            |
|  * Datadog APM                                                          |
|  * Honeycomb                                                            |
|                                                                         |
|  STANDARD: OpenTelemetry (vendor-neutral, recommended)                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10.5: ALERTING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ALERTING BEST PRACTICES                                                |
|                                                                         |
|  1. ALERT ON SYMPTOMS, NOT CAUSES                                       |
|  ---------------------------------                                      |
|  X Alert: CPU > 80%                                                     |
|  Y Alert: Error rate > 1% or Latency P99 > 500ms                        |
|                                                                         |
|  Users care about: Can they use the service?                            |
|  Not: How busy is the CPU?                                              |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. REDUCE ALERT FATIGUE                                                |
|  -------------------------                                              |
|  Too many alerts = ignored alerts                                       |
|                                                                         |
|  * Page only for user-facing issues                                     |
|  * Use severity levels (P1-P4)                                          |
|  * Aggregate related alerts                                             |
|  * Auto-resolve when fixed                                              |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. ACTIONABLE ALERTS                                                   |
|  ----------------------                                                 |
|  Every alert should have clear action                                   |
|                                                                         |
|  Include:                                                               |
|  * What's wrong (high error rate)                                       |
|  * Impact (10% users affected)                                          |
|  * Runbook link (how to fix)                                            |
|  * Dashboard link (more context)                                        |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ALERT SEVERITY LEVELS                                                  |
|                                                                         |
|  P1 (Critical): User-facing, requires immediate response                |
|     - Site down, payment failures                                       |
|     - Action: Page on-call immediately                                  |
|                                                                         |
|  P2 (High): Degraded but functional                                     |
|     - High latency, partial feature failure                             |
|     - Action: Respond within 30 minutes                                 |
|                                                                         |
|  P3 (Medium): No immediate impact                                       |
|     - Disk filling up, certificate expiring soon                        |
|     - Action: Next business day                                         |
|                                                                         |
|  P4 (Low): Informational                                                |
|     - Capacity planning, optimization opportunities                     |
|     - Action: Review in weekly meeting                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OBSERVABILITY - KEY TAKEAWAYS                                          |
|                                                                         |
|  THREE PILLARS                                                          |
|  -------------                                                          |
|  * Metrics: Numbers over time (counters, gauges, histograms)            |
|  * Logs: Events with context (structured JSON)                          |
|  * Traces: Requests across services (trace_id propagation)              |
|                                                                         |
|  KEY METRICS                                                            |
|  ------------                                                           |
|  * Four Golden Signals: Latency, Traffic, Errors, Saturation            |
|  * RED: Rate, Errors, Duration (for services)                           |
|  * USE: Utilization, Saturation, Errors (for resources)                 |
|                                                                         |
|  LOGGING BEST PRACTICES                                                 |
|  -----------------------                                                |
|  * Use structured logging (JSON)                                        |
|  * Include trace_id for correlation                                     |
|  * Don't log sensitive data                                             |
|  * Centralize logs (ELK, Loki)                                          |
|                                                                         |
|  TRACING                                                                |
|  --------                                                               |
|  * Propagate context via headers                                        |
|  * Use OpenTelemetry standard                                           |
|  * Tools: Jaeger, Zipkin, Datadog                                       |
|                                                                         |
|  ALERTING                                                               |
|  --------                                                               |
|  * Alert on symptoms, not causes                                        |
|  * Make alerts actionable (runbook, dashboard)                          |
|  * Avoid alert fatigue (severity levels)                                |
|                                                                         |
|  INTERVIEW TIP                                                          |
|  -------------                                                          |
|  When discussing production systems:                                    |
|  * Mention the three pillars                                            |
|  * Discuss how you'd debug a latency issue (traces)                     |
|  * Explain correlation via trace_id                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 10

