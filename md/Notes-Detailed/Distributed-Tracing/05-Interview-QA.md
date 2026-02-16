# DISTRIBUTED TRACING SYSTEM DESIGN (JAEGER-LIKE)

CHAPTER 5: INTERVIEW Q&A AND DEEP DIVES
## TABLE OF CONTENTS
*-----------------*
*1. Common Interview Questions*
*2. Design Trade-offs*
*3. Real-World Considerations*
*4. Comparison with Alternatives*
*5. Quick Reference Cheat Sheet*

SECTION 5.1: COMMON INTERVIEW QUESTIONS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  Q1: How would you design a distributed tracing system?               |*
*|  ------------------------------------------------------                |*
*|                                                                         |*
*|  ANSWER FRAMEWORK:                                                     |*
*|                                                                         |*
*|  1. Clarify requirements (5 min)                                      |*
*|     - Scale: How many services? Requests/second?                     |*
*|     - Retention: How long to keep traces?                            |*
*|     - Query patterns: Search by tag? Duration? Error?                |*
*|                                                                         |*
*|  2. High-level design (10 min)                                        |*
*|     - Draw: SDK > Agent > Collector > Storage > Query > UI          |*
*|     - Explain each component's role                                   |*
*|     - Mention context propagation                                     |*
*|                                                                         |*
*|  3. Deep dive (15 min)                                                |*
*|     - Storage choice (Cassandra vs ES vs Object storage)            |*
*|     - Sampling strategies                                             |*
*|     - Data model design                                               |*
*|                                                                         |*
*|  4. Discuss trade-offs (5 min)                                        |*
*|     - Cost vs query flexibility                                       |*
*|     - Head vs tail sampling                                           |*
*|     - Overhead vs coverage                                            |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  Q2: How do you ensure all spans of a trace are collected together?  |*
*|  ----------------------------------------------------------------------|*
*|                                                                         |*
*|  ANSWER:                                                               |*
*|                                                                         |*
*|  Context Propagation:                                                  |*
*|  * Generate unique trace_id at entry point                          |*
*|  * Propagate via HTTP headers (traceparent)                         |*
*|  * Each service extracts and passes along                           |*
*|  * Same trace_id = same trace                                       |*
*|                                                                         |*
*|  For async (queues):                                                   |*
*|  * Embed trace context in message headers                           |*
*|  * Consumer extracts and continues trace                            |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  Q3: How do you handle sampling at scale?                            |*
*|  -----------------------------------------                             |*
*|                                                                         |*
*|  ANSWER:                                                               |*
*|                                                                         |*
*|  Head-based sampling (simple):                                        |*
*|  * Decide at trace start using trace_id hash                        |*
*|  * hash(trace_id) % 100 < sample_rate                               |*
*|  * Consistent across all services                                    |*
*|                                                                         |*
*|  Tail-based sampling (advanced):                                      |*
*|  * Collect all spans first                                           |*
*|  * Decide after seeing: errors, latency, tags                       |*
*|  * Requires consistent hashing to route same trace to same collector|*
*|  * Higher memory usage, but captures all interesting traces         |*
*|                                                                         |*
*|  Best practice: Hybrid                                                 |*
*|  * Head sampling for normal traffic (1%)                            |*
*|  * Always sample errors (100%)                                       |*
*|  * Always sample slow requests (100%)                               |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  Q4: Why use Cassandra for trace storage?                            |*
*|  -----------------------------------------                             |*
*|                                                                         |*
*|  ANSWER:                                                               |*
*|                                                                         |*
*|  Why Cassandra works well:                                            |*
*|  1. High write throughput (LSM tree)                                 |*
*|  2. Linear scalability (add nodes)                                   |*
*|  3. TTL support (automatic expiry)                                   |*
*|  4. Partition by trace_id (fast lookups)                            |*
*|  5. No single point of failure                                       |*
*|                                                                         |*
*|  Schema design:                                                        |*
*|  * Partition key: trace_id                                           |*
*|  * Clustering key: span_id                                           |*
*|  * All spans of a trace in one partition                            |*
*|  * Single read gets complete trace                                   |*
*|                                                                         |*
*|  Limitation: No flexible queries                                      |*
*|  Solution: Dual-write to Elasticsearch for indexing                  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  Q5: How do you search traces by tags efficiently?                   |*
*|  ------------------------------------------------                      |*
*|                                                                         |*
*|  ANSWER:                                                               |*
*|                                                                         |*
*|  Option 1: Secondary index tables (Cassandra)                        |*
*|  CREATE TABLE tag_index (                                            |*
*|    service, tag_key, tag_value, bucket, trace_id                   |*
*|    PRIMARY KEY ((service, tag_key, tag_value, bucket), trace_id)   |*
*|  );                                                                    |*
*|  * Write to index table when span has tag                           |*
*|  * Query: Find trace_ids, then fetch from main table               |*
*|                                                                         |*
*|  Option 2: Elasticsearch (recommended)                                |*
*|  * Store span metadata + tags (not full span)                       |*
*|  * Flexible queries on any field                                     |*
*|  * Return trace_ids, fetch full trace from Cassandra               |*
*|                                                                         |*
*|  Option 3: ClickHouse                                                  |*
*|  * Columnar storage, fast aggregations                              |*
*|  * Good for analytics on trace data                                 |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  Q6: How do you ensure tracing doesn't impact application latency?  |*
*|  ----------------------------------------------------------------------|*
*|                                                                         |*
*|  ANSWER:                                                               |*
*|                                                                         |*
*|  1. Async span submission                                            |*
*|     * Fire-and-forget to agent                                       |*
*|     * Application doesn't wait for ACK                              |*
*|                                                                         |*
*|  2. UDP protocol (SDK > Agent)                                       |*
*|     * No connection overhead                                         |*
*|     * No retries blocking app                                        |*
*|                                                                         |*
*|  3. Local agent                                                        |*
*|     * Localhost communication (fast)                                 |*
*|     * Agent handles batching/retries                                |*
*|                                                                         |*
*|  4. Sampling                                                           |*
*|     * Only process subset of requests                               |*
*|     * Still creates spans but doesn't send                          |*
*|                                                                         |*
*|  5. Graceful degradation                                              |*
*|     * If agent down, SDK drops spans                                |*
*|     * Application continues normally                                 |*
*|                                                                         |*
*|  Target overhead: < 1% latency, < 1% CPU                             |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  Q7: How would you handle clock skew across services?                |*
*|  -----------------------------------------------------                 |*
*|                                                                         |*
*|  ANSWER:                                                               |*
*|                                                                         |*
*|  The problem:                                                          |*
*|  * Service A: start=100, end=150                                     |*
*|  * Service B (called by A): start=90 (clock is behind!)             |*
*|  * B appears to start BEFORE A called it                            |*
*|                                                                         |*
*|  Solutions:                                                            |*
*|                                                                         |*
*|  1. NTP sync (preventive)                                            |*
*|     * Keep all servers synced to same time                          |*
*|     * Typical accuracy: 1-10ms                                       |*
*|                                                                         |*
*|  2. Adjust in UI (corrective)                                        |*
*|     * Jaeger UI detects and adjusts                                 |*
*|     * Child can't start before parent                               |*
*|     * Shift child timestamps if needed                              |*
*|                                                                         |*
*|  3. Hybrid logical clocks                                            |*
*|     * Combine wall clock + logical counter                          |*
*|     * More complex but handles skew                                 |*
*|                                                                         |*
*|  Best practice: Good NTP + UI adjustment                             |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  Q8: How would you build the service dependency graph?               |*
*|  ------------------------------------------------------                |*
*|                                                                         |*
*|  ANSWER:                                                               |*
*|                                                                         |*
*|  Data source: Parent-child relationships in spans                    |*
*|                                                                         |*
*|  Process:                                                              |*
*|  1. For each span, extract:                                          |*
*|     * Parent service name                                            |*
*|     * Child service name                                             |*
*|                                                                         |*
*|  2. Aggregate edges:                                                  |*
*|     * Count calls between service pairs                             |*
*|     * Calculate latency percentiles                                 |*
*|     * Track error rates                                              |*
*|                                                                         |*
*|  Implementation:                                                       |*
*|  * Stream processing (Flink/Spark) on span data                     |*
*|  * Output: (parent, child, count, avg_latency, error_rate)         |*
*|  * Store in time-bucketed table                                     |*
*|                                                                         |*
*|  Query:                                                                |*
*|  SELECT * FROM dependencies WHERE bucket BETWEEN start AND end      |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 5.2: DESIGN TRADE-OFFS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  TRADE-OFF 1: Storage Choice                                          |*
*|  -----------------------------                                         |*
*|                                                                         |*
*|  +------------------------------------------------------------------+ |*
*|  |                        Query Flexibility                          | |*
*|  |         High ^                                                    | |*
*|  |              |      +---------------+                            | |*
*|  |              |      | Elasticsearch |                            | |*
*|  |              |      |   (expensive) |                            | |*
*|  |              |      +---------------+                            | |*
*|  |              |                                                    | |*
*|  |              |          +------------+                           | |*
*|  |              |          | ClickHouse |                           | |*
*|  |              |          | (balanced) |                           | |*
*|  |              |          +------------+                           | |*
*|  |              |                                                    | |*
*|  |              |                      +-------------------+        | |*
*|  |              |                      | Object Storage    |        | |*
*|  |              |                      | (trace ID only)   |        | |*
*|  |         Low  +----------------------+-------------------+--->    | |*
*|  |                    High                              Low  Cost   | |*
*|  +------------------------------------------------------------------+ |*
*|                                                                         |*
*|  RECOMMENDATION BY SCALE:                                             |*
*|  * < 10K spans/s: Elasticsearch only                                 |*
*|  * 10K-100K spans/s: Cassandra + Elasticsearch                      |*
*|  * > 100K spans/s: Object storage (Tempo) + exemplars              |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  TRADE-OFF 2: Head vs Tail Sampling                                   |*
*|  ------------------------------------                                  |*
*|                                                                         |*
*|  +-------------------------+-------------------------+              |*
*|  |     HEAD SAMPLING       |     TAIL SAMPLING       |              |*
*|  +-------------------------+-------------------------+              |*
*|  | Y Simple to implement  | Y Captures all errors   |              |*
*|  | Y Low overhead         | Y Captures slow traces  |              |*
*|  | Y Scales easily        | Y Smarter decisions     |              |*
*|  |                         |                         |              |*
*|  | X May miss errors      | X Higher complexity     |              |*
*|  | X Random selection     | X More memory needed    |              |*
*|  |                         | X Requires affinity    |              |*
*|  +-------------------------+-------------------------+              |*
*|                                                                         |*
*|  RECOMMENDATION:                                                       |*
*|  Start with head sampling + "always sample errors" flag             |*
*|  Move to tail sampling when you need better coverage                |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  TRADE-OFF 3: Agent Deployment Model                                  |*
*|  ------------------------------------                                  |*
*|                                                                         |*
*|  SIDECAR (per pod):                                                    |*
*|  +-----------------------------------------------------------------+  |*
*|  |  Pros:                                                          |  |*
*|  |  * Isolated resources per service                              |  |*
*|  |  * Easy to configure per-service sampling                      |  |*
*|  |  * Service mesh compatible                                     |  |*
*|  |                                                                 |  |*
*|  |  Cons:                                                          |  |*
*|  |  * More resource overhead (CPU/memory per pod)                |  |*
*|  |  * More containers to manage                                   |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  DAEMONSET (per node):                                                 |*
*|  +-----------------------------------------------------------------+  |*
*|  |  Pros:                                                          |  |*
*|  |  * Less overall resource usage                                 |  |*
*|  |  * Fewer containers                                            |  |*
*|  |  * Simpler for small clusters                                 |  |*
*|  |                                                                 |  |*
*|  |  Cons:                                                          |  |*
*|  |  * Shared resource, possible contention                       |  |*
*|  |  * Need to configure node IP discovery                        |  |*
*|  |  * Less isolation                                              |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  RECOMMENDATION:                                                       |*
*|  * K8s: Start with DaemonSet, move to sidecar if needed            |*
*|  * Service mesh (Istio): Use sidecar model                         |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 5.3: REAL-WORLD CONSIDERATIONS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  HIGH AVAILABILITY                                                     |*
*|  ------------------                                                     |*
*|                                                                         |*
*|  Collectors:                                                           |*
*|  * Run 3+ replicas minimum                                           |*
*|  * Load balance with health checks                                   |*
*|  * Auto-scale based on CPU/throughput                               |*
*|                                                                         |*
*|  Storage:                                                              |*
*|  * Cassandra: RF=3, CL=LOCAL_QUORUM                                 |*
*|  * Elasticsearch: 3 master nodes, 3+ data nodes                     |*
*|  * Multi-AZ deployment                                               |*
*|                                                                         |*
*|  Kafka (if used):                                                      |*
*|  * 3+ brokers                                                         |*
*|  * RF=3 for span topic                                               |*
*|  * ISR min = 2                                                        |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SECURITY CONSIDERATIONS                                              |*
*|  ------------------------                                              |*
*|                                                                         |*
*|  1. PII in traces                                                      |*
*|     * Span logs may contain user data                               |*
*|     * Request/response bodies                                        |*
*|     * Query parameters                                               |*
*|                                                                         |*
*|     Solutions:                                                        |*
*|     * Redact sensitive fields in collector                          |*
*|     * Configure SDK to exclude certain tags                         |*
*|     * Use allowlist for logged fields                               |*
*|                                                                         |*
*|  2. Access control                                                     |*
*|     * Not all teams should see all traces                           |*
*|     * Payment traces vs marketing traces                            |*
*|                                                                         |*
*|     Solutions:                                                        |*
*|     * Service-level access control                                   |*
*|     * Separate storage per team/domain                              |*
*|     * Field-level redaction                                         |*
*|                                                                         |*
*|  3. Encryption                                                         |*
*|     * TLS between all components                                     |*
*|     * Encryption at rest for storage                                |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  OPERATIONAL METRICS                                                  |*
*|  ---------------------                                                 |*
*|                                                                         |*
*|  Monitor the tracing system itself:                                   |*
*|                                                                         |*
*|  Collectors:                                                           |*
*|  * jaeger_collector_spans_received_total                            |*
*|  * jaeger_collector_spans_dropped_total                             |*
*|  * jaeger_collector_queue_length                                    |*
*|  * jaeger_collector_save_latency                                    |*
*|                                                                         |*
*|  Storage:                                                              |*
*|  * Write latency (P50, P99)                                         |*
*|  * Read latency                                                       |*
*|  * Storage size                                                       |*
*|  * Index size                                                         |*
*|                                                                         |*
*|  Agents:                                                               |*
*|  * jaeger_agent_reporter_batches_submitted_total                    |*
*|  * jaeger_agent_reporter_batches_failures_total                     |*
*|  * jaeger_agent_reporter_spans_submitted_total                      |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  COST OPTIMIZATION                                                    |*
*|  ------------------                                                    |*
*|                                                                         |*
*|  1. Sampling aggressively                                            |*
*|     * 0.1% for high-volume boring endpoints                        |*
*|     * 100% for critical paths                                       |*
*|                                                                         |*
*|  2. Tiered storage                                                     |*
*|     * Hot: 2 days fast storage                                       |*
*|     * Cold: 30 days object storage                                  |*
*|                                                                         |*
*|  3. Use object storage (Tempo)                                        |*
*|     * 10-100x cheaper than ES                                       |*
*|     * Trade-off: Less query flexibility                             |*
*|                                                                         |*
*|  4. Compress spans                                                     |*
*|     * 5-10x size reduction                                          |*
*|                                                                         |*
*|  5. Reduce tag cardinality                                            |*
*|     * Don't index high-cardinality tags                             |*
*|     * request_id, session_id > don't index                         |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 5.4: COMPARISON WITH ALTERNATIVES
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  TRACING SYSTEMS COMPARISON                                           |*
*|                                                                         |*
*|  +--------------+----------+------------+---------------------------+ |*
*|  | System       | Type     | Storage    | Best For                  | |*
*|  +--------------+----------+------------+---------------------------+ |*
*|  | Jaeger       | OSS      | Cassandra/ | Large scale, self-hosted | |*
*|  |              |          | ES         |                           | |*
*|  +--------------+----------+------------+---------------------------+ |*
*|  | Zipkin       | OSS      | Cassandra/ | Simpler deployments      | |*
*|  |              |          | ES/MySQL   |                           | |*
*|  +--------------+----------+------------+---------------------------+ |*
*|  | Tempo        | OSS      | Object     | Cost-effective at scale  | |*
*|  |              |          | Storage    | (trace ID lookup only)   | |*
*|  +--------------+----------+------------+---------------------------+ |*
*|  | AWS X-Ray    | Managed  | Managed    | AWS-native apps          | |*
*|  +--------------+----------+------------+---------------------------+ |*
*|  | Datadog APM  | SaaS     | Managed    | Full observability stack | |*
*|  +--------------+----------+------------+---------------------------+ |*
*|  | Honeycomb    | SaaS     | Managed    | High-cardinality queries | |*
*|  +--------------+----------+------------+---------------------------+ |*
*|  | Lightstep    | SaaS     | Managed    | Large enterprises        | |*
*|  +--------------+----------+------------+---------------------------+ |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  WHEN TO USE WHAT                                                      |*
*|                                                                         |*
*|  Jaeger + Cassandra/ES:                                               |*
*|  * Need full query flexibility                                       |*
*|  * Can manage infrastructure                                         |*
*|  * Large scale, cost-sensitive                                       |*
*|                                                                         |*
*|  Tempo + Object Storage:                                              |*
*|  * Very high scale (>100K spans/s)                                  |*
*|  * Tight budget                                                       |*
*|  * Using Grafana already                                             |*
*|  * OK with trace-ID-only lookups                                    |*
*|                                                                         |*
*|  Managed (Datadog, AWS X-Ray):                                        |*
*|  * Don't want to manage infrastructure                               |*
*|  * Integrated observability needed                                   |*
*|  * Budget for SaaS                                                    |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 5.5: QUICK REFERENCE CHEAT SHEET
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  ARCHITECTURE AT A GLANCE                                             |*
*|                                                                         |*
*|  Services (SDK) > Agents > Collectors > Kafka > Ingesters > Storage  |*
*|                                                         v              |*
*|                                              Query Service > UI       |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  KEY DATA STRUCTURES                                                  |*
*|                                                                         |*
*|  SPAN: {trace_id, span_id, parent_id, operation, start, duration,    |*
*|         tags, logs, process}                                          |*
*|                                                                         |*
*|  TRACE: Collection of spans with same trace_id, forms a tree         |*
*|                                                                         |*
*|  CONTEXT: Propagated via HTTP headers (traceparent, tracestate)      |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  STORAGE SCHEMA (Cassandra)                                           |*
*|                                                                         |*
*|  traces: PK(trace_id), CK(span_id) > Full span data                 |*
*|  service_name_index: PK(service, bucket), CK(time, trace_id)        |*
*|  tag_index: PK(service, key, value, bucket), CK(time, trace_id)     |*
*|  duration_index: PK(service, op, bucket), CK(duration, trace_id)    |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SAMPLING STRATEGIES                                                  |*
*|                                                                         |*
*|  * Probabilistic: X% of all traces                                   |*
*|  * Rate limiting: N traces/second                                    |*
*|  * Adaptive: Adjust rate based on traffic                           |*
*|  * Per-operation: Different rates per endpoint                      |*
*|  * Tail-based: Decide after seeing full trace                       |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SCALE NUMBERS (Reference)                                            |*
*|                                                                         |*
*|  * Span size: ~500 bytes                                             |*
*|  * Collector capacity: ~50-100K spans/s per instance                |*
*|  * Agent batching: 100 spans or 100ms                               |*
*|  * Typical sampling: 0.1% - 10%                                     |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  INTERVIEW CHECKLIST                                                  |*
*|                                                                         |*
*|  ☐ Clarify scale (services, RPS, retention)                         |*
*|  ☐ Draw high-level architecture                                      |*
*|  ☐ Explain context propagation                                       |*
*|  ☐ Discuss sampling strategies                                       |*
*|  ☐ Choose storage (justify trade-offs)                              |*
*|  ☐ Design schema for common queries                                 |*
*|  ☐ Address overhead concerns                                         |*
*|  ☐ Mention tail sampling for errors                                 |*
*|  ☐ Discuss cost optimization                                         |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF CHAPTER 5 - DISTRIBUTED TRACING SYSTEM DESIGN
