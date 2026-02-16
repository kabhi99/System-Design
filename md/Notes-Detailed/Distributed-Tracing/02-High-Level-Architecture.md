# DISTRIBUTED TRACING SYSTEM DESIGN (JAEGER-LIKE)

CHAPTER 2: HIGH-LEVEL ARCHITECTURE
## TABLE OF CONTENTS
*-----------------*
*1. System Overview*
*2. Core Components*
*3. Data Flow*
*4. Component Details*
*5. Deployment Architectures*

SECTION 2.1: SYSTEM OVERVIEW
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  HIGH-LEVEL ARCHITECTURE                                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |     INSTRUMENTED SERVICES (Your microservices)                 |  |*
*|  |  +----------+  +----------+  +----------+  +----------+      |  |*
*|  |  | Service  |  | Service  |  | Service  |  | Service  |      |  |*
*|  |  |    A     |  |    B     |  |    C     |  |    D     |      |  |*
*|  |  | (SDK)    |  | (SDK)    |  | (SDK)    |  | (SDK)    |      |  |*
*|  |  +----+-----+  +----+-----+  +----+-----+  +----+-----+      |  |*
*|  |       |             |             |             |             |  |*
*|  |       |   Spans     |   Spans     |   Spans     |   Spans    |  |*
*|  |       v             v             v             v             |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                    JAEGER AGENTS                        |  |  |*
*|  |  |              (Sidecar or DaemonSet)                     |  |  |*
*|  |  |  * Receives spans via UDP (low overhead)               |  |  |*
*|  |  |  * Batches spans                                        |  |  |*
*|  |  |  * Handles sampling decisions                          |  |  |*
*|  |  +------------------------+--------------------------------+  |  |*
*|  |                           |                                   |  |*
*|  |                           | gRPC/HTTP (batched)              |  |*
*|  |                           v                                   |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                    COLLECTORS                           |  |  |*
*|  |  |              (Stateless, scalable)                      |  |  |*
*|  |  |  * Validates and processes spans                       |  |  |*
*|  |  |  * Enriches with additional data                       |  |  |*
*|  |  |  * Writes to storage                                   |  |  |*
*|  |  +------------------------+--------------------------------+  |  |*
*|  |                           |                                   |  |*
*|  |         +-----------------+-----------------+                |  |*
*|  |         |                 |                 |                |  |*
*|  |         v                 v                 v                |  |*
*|  |  +-----------+    +-----------+    +---------------+        |  |*
*|  |  |   Kafka   |    |   Kafka   |    |    Direct     |        |  |*
*|  |  |  (spans)  |    |  (spans)  |    |    Write      |        |  |*
*|  |  +-----+-----+    +-----------+    +-------+-------+        |  |*
*|  |        |                                   |                 |  |*
*|  |        v                                   |                 |  |*
*|  |  +-----------+                            |                 |  |*
*|  |  |  Ingester |                            |                 |  |*
*|  |  |  (Kafka>  |                            |                 |  |*
*|  |  |  Storage) |                            |                 |  |*
*|  |  +-----+-----+                            |                 |  |*
*|  |        |                                   |                 |  |*
*|  |        +---------------+------------------+                 |  |*
*|  |                        v                                     |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                    STORAGE                              |  |  |*
*|  |  |  +-------------+  +-------------+  +-----------------+ |  |  |*
*|  |  |  | Cassandra   |  |Elasticsearch|  |  Object Store   | |  |  |*
*|  |  |  | (spans)     |  | (indices)   |  |  (Tempo/cold)   | |  |  |*
*|  |  |  +-------------+  +-------------+  +-----------------+ |  |  |*
*|  |  +------------------------+--------------------------------+  |  |*
*|  |                           |                                   |  |*
*|  |                           | Query                            |  |*
*|  |                           v                                   |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                    QUERY SERVICE                        |  |  |*
*|  |  |  * REST/gRPC API                                       |  |  |*
*|  |  |  * Trace retrieval                                     |  |  |*
*|  |  |  * Search functionality                                |  |  |*
*|  |  +------------------------+--------------------------------+  |  |*
*|  |                           |                                   |  |*
*|  |                           v                                   |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                    JAEGER UI                            |  |  |*
*|  |  |  * Trace visualization                                 |  |  |*
*|  |  |  * Service dependency graph                            |  |  |*
*|  |  |  * Compare traces                                      |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2.2: CORE COMPONENTS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  1. INSTRUMENTATION SDK / CLIENT LIBRARIES                            |*
*|  ---------------------------------------------                         |*
*|                                                                         |*
*|  Purpose: Generate spans in your application code                      |*
*|                                                                         |*
*|  TYPES OF INSTRUMENTATION:                                             |*
*|                                                                         |*
*|  AUTO-INSTRUMENTATION (Recommended):                                   |*
*|  * Framework integrations (Spring, Express, Django)                   |*
*|  * Zero code changes                                                   |*
*|  * Instruments HTTP, DB, messaging automatically                      |*
*|                                                                         |*
*|  # Python auto-instrumentation                                        |*
*|  from opentelemetry.instrumentation.flask import FlaskInstrumentor   |*
*|  from opentelemetry.instrumentation.requests import RequestsInstru...|*
*|                                                                         |*
*|  FlaskInstrumentor().instrument()  # Auto-traces all HTTP handlers   |*
*|  RequestsInstrumentor().instrument()  # Auto-traces outgoing HTTP    |*
*|                                                                         |*
*|  MANUAL INSTRUMENTATION:                                               |*
*|  * For custom business logic                                          |*
*|  * Adding custom tags/logs                                            |*
*|                                                                         |*
*|  # Python manual span creation                                        |*
*|  from opentelemetry import trace                                      |*
*|                                                                         |*
*|  tracer = trace.get_tracer(__name__)                                 |*
*|                                                                         |*
*|  def process_order(order_id):                                         |*
*|      with tracer.start_as_current_span("process_order") as span:     |*
*|          span.set_attribute("order.id", order_id)                    |*
*|          span.set_attribute("order.type", "premium")                 |*
*|          # ... business logic                                        |*
*|          span.add_event("validation_complete")                       |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  2. JAEGER AGENT                                                       |*
*|  -----------------                                                     |*
*|                                                                         |*
*|  Purpose: Local daemon that receives spans from SDKs                  |*
*|                                                                         |*
*|  DEPLOYMENT OPTIONS:                                                   |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  SIDECAR (per pod):                                            |  |*
*|  |  +-----------------------------------------+                   |  |*
*|  |  |            Kubernetes Pod               |                   |  |*
*|  |  |  +-------------+  +-----------------+  |                   |  |*
*|  |  |  | App         |  | Jaeger Agent    |  |                   |  |*
*|  |  |  | Container   |->| Container       |  |                   |  |*
*|  |  |  |             |  | (localhost:6831)|  |                   |  |*
*|  |  |  +-------------+  +-----------------+  |                   |  |*
*|  |  +-----------------------------------------+                   |  |*
*|  |                                                                 |  |*
*|  |  Pros: Isolated, easy configuration                           |  |*
*|  |  Cons: More resource usage                                    |  |*
*|  |                                                                 |  |*
*|  |  ---------------------------------------------------------    |  |*
*|  |                                                                 |  |*
*|  |  DAEMONSET (per node):                                        |  |*
*|  |  +-------------------------------------------------------+    |  |*
*|  |  |                   Kubernetes Node                      |    |  |*
*|  |  |  +-------------+  +-------------+  +---------------+  |    |  |*
*|  |  |  | Pod A       |  | Pod B       |  | Jaeger Agent  |  |    |  |*
*|  |  |  |             |--+             |--+ DaemonSet     |  |    |  |*
*|  |  |  +-------------+  +-------------+  | (node IP:6831)|  |    |  |*
*|  |  |                                    +---------------+  |    |  |*
*|  |  +-------------------------------------------------------+    |  |*
*|  |                                                                 |  |*
*|  |  Pros: Less resource usage                                    |  |*
*|  |  Cons: Shared, need to configure node IP discovery           |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  KEY FEATURES:                                                         |*
*|  * Receives spans via UDP (port 6831) - fire and forget             |*
*|  * Batches multiple spans together                                   |*
*|  * Handles sampling decisions locally                                |*
*|  * Forwards to collectors via gRPC                                   |*
*|  * Buffers if collectors temporarily unavailable                    |*
*|                                                                         |*
*|  WHY UDP?                                                              |*
*|  * No connection overhead                                            |*
*|  * Fire-and-forget (app doesn't block)                              |*
*|  * App continues even if agent is down                              |*
*|  * Minimal latency impact                                            |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  3. COLLECTOR                                                          |*
*|  -------------                                                         |*
*|                                                                         |*
*|  Purpose: Central component that processes and stores spans          |*
*|                                                                         |*
*|  RESPONSIBILITIES:                                                     |*
*|  * Receive spans from agents (gRPC/HTTP)                            |*
*|  * Validate span data                                                |*
*|  * Enrich spans (add metadata)                                       |*
*|  * Apply post-sampling                                               |*
*|  * Write to storage                                                   |*
*|                                                                         |*
*|  SCALING:                                                              |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |                    Load Balancer                               |  |*
*|  |                         |                                       |  |*
*|  |      +------------------+------------------+                   |  |*
*|  |      |                  |                  |                   |  |*
*|  |      v                  v                  v                   |  |*
*|  |  +--------+        +--------+        +--------+               |  |*
*|  |  |Collector|       |Collector|       |Collector|              |  |*
*|  |  |   1    |        |   2    |        |   3    |               |  |*
*|  |  +--------+        +--------+        +--------+               |  |*
*|  |                                                                 |  |*
*|  |  * Stateless - easy horizontal scaling                        |  |*
*|  |  * Scale based on span ingestion rate                        |  |*
*|  |  * Typical: 50,000-100,000 spans/sec per instance           |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  4. KAFKA (Optional but recommended for scale)                        |*
*|  ------------------------------------------------                      |*
*|                                                                         |*
*|  Purpose: Buffer between collectors and storage                       |*
*|                                                                         |*
*|  WITHOUT KAFKA:                                                        |*
*|  Collectors > Storage (direct write)                                 |*
*|  * Simple                                                             |*
*|  * Storage backpressure affects collectors                          |*
*|  * Potential data loss if storage is slow                           |*
*|                                                                         |*
*|  WITH KAFKA:                                                           |*
*|  Collectors > Kafka > Ingesters > Storage                            |*
*|  * Decouples ingestion from storage                                 |*
*|  * Handles traffic spikes gracefully                                |*
*|  * Enables replay/reprocessing                                       |*
*|  * Multiple consumers (storage, analytics, streaming)               |*
*|                                                                         |*
*|  KAFKA TOPIC DESIGN:                                                   |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Topic: jaeger-spans                                           |  |*
*|  |  Partitions: 32 (based on throughput needs)                   |  |*
*|  |  Partition Key: trace_id (spans of same trace > same partition)|  |*
*|  |  Retention: 24-48 hours (buffer for reprocessing)             |  |*
*|  |                                                                 |  |*
*|  |  Why partition by trace_id?                                    |  |*
*|  |  * Related spans processed together                           |  |*
*|  |  * Better write batching to storage                          |  |*
*|  |  * Maintains ordering within a trace                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  5. INGESTER                                                           |*
*|  ------------                                                          |*
*|                                                                         |*
*|  Purpose: Consume from Kafka, write to storage                        |*
*|                                                                         |*
*|  RESPONSIBILITIES:                                                     |*
*|  * Read span batches from Kafka                                      |*
*|  * Batch writes to storage for efficiency                           |*
*|  * Handle storage failures with retries                             |*
*|  * Commit Kafka offsets after successful write                      |*
*|                                                                         |*
*|  SCALING:                                                              |*
*|  * Scale with Kafka partitions                                       |*
*|  * 1 ingester per partition (max parallelism)                       |*
*|  * Auto-rebalance when instances added/removed                      |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  6. STORAGE                                                            |*
*|  -----------                                                           |*
*|                                                                         |*
*|  Purpose: Persistent storage for traces                               |*
*|                                                                         |*
*|  OPTIONS:                                                              |*
*|  +----------------+-----------------------------------------------+  |*
*|  | Storage        | Characteristics                               |  |*
*|  +----------------+-----------------------------------------------+  |*
*|  | Cassandra      | * High write throughput                       |  |*
*|  |                | * Excellent scalability                       |  |*
*|  |                | * Limited query flexibility                   |  |*
*|  |                | * Jaeger's original choice                   |  |*
*|  +----------------+-----------------------------------------------+  |*
*|  | Elasticsearch  | * Flexible queries                            |  |*
*|  |                | * Full-text search on logs                   |  |*
*|  |                | * Higher resource usage                       |  |*
*|  |                | * Better for tag-based search               |  |*
*|  +----------------+-----------------------------------------------+  |*
*|  | Object Storage | * Cheapest (S3, GCS)                         |  |*
*|  | (Tempo)        | * Only lookup by trace ID                    |  |*
*|  |                | * Excellent for high volume                  |  |*
*|  |                | * Pairs with external index                  |  |*
*|  +----------------+-----------------------------------------------+  |*
*|  | ClickHouse     | * Column-oriented, fast analytics           |  |*
*|  |                | * Good compression                           |  |*
*|  |                | * Newer option, gaining popularity           |  |*
*|  +----------------+-----------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  7. QUERY SERVICE                                                      |*
*|  ----------------                                                      |*
*|                                                                         |*
*|  Purpose: API for retrieving and searching traces                     |*
*|                                                                         |*
*|  API ENDPOINTS:                                                        |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  GET /api/traces/{traceId}                                    |  |*
*|  |  Returns complete trace with all spans                        |  |*
*|  |                                                                 |  |*
*|  |  GET /api/traces?service={name}&operation={op}&tags={k:v}    |  |*
*|  |  Search traces by criteria                                     |  |*
*|  |                                                                 |  |*
*|  |  GET /api/services                                            |  |*
*|  |  List all services reporting traces                           |  |*
*|  |                                                                 |  |*
*|  |  GET /api/services/{service}/operations                       |  |*
*|  |  List operations for a service                                 |  |*
*|  |                                                                 |  |*
*|  |  GET /api/dependencies?endTs={ts}&lookback={duration}        |  |*
*|  |  Service dependency graph                                      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  8. JAEGER UI                                                          |*
*|  ------------                                                          |*
*|                                                                         |*
*|  Purpose: Web interface for exploring traces                          |*
*|                                                                         |*
*|  FEATURES:                                                             |*
*|  * Search traces by service, operation, tags, duration               |*
*|  * Timeline view (Gantt chart of spans)                              |*
*|  * Span details (tags, logs, errors)                                 |*
*|  * Service dependency graph                                           |*
*|  * Compare two traces side-by-side                                   |*
*|  * Deep link to specific traces                                       |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2.3: DATA FLOW
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WRITE PATH (Span Ingestion)                                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. REQUEST ARRIVES                                            |  |*
*|  |     |                                                          |  |*
*|  |     |  User request > Service A                               |  |*
*|  |     |  SDK creates root span (start timer)                    |  |*
*|  |     v                                                          |  |*
*|  |  2. CONTEXT PROPAGATION                                        |  |*
*|  |     |                                                          |  |*
*|  |     |  Service A calls Service B                              |  |*
*|  |     |  Injects trace context into HTTP headers:               |  |*
*|  |     |  traceparent: 00-{traceId}-{spanId}-01                  |  |*
*|  |     v                                                          |  |*
*|  |  3. CHILD SPAN CREATION                                        |  |*
*|  |     |                                                          |  |*
*|  |     |  Service B extracts context                             |  |*
*|  |     |  Creates child span (same traceId, new spanId)         |  |*
*|  |     v                                                          |  |*
*|  |  4. SPAN COMPLETION                                            |  |*
*|  |     |                                                          |  |*
*|  |     |  When operation completes:                              |  |*
*|  |     |  - Set duration                                         |  |*
*|  |     |  - Add final tags                                       |  |*
*|  |     |  - Send to Jaeger Agent (UDP, async)                   |  |*
*|  |     v                                                          |  |*
*|  |  5. AGENT BATCHING                                             |  |*
*|  |     |                                                          |  |*
*|  |     |  Agent collects spans in memory                        |  |*
*|  |     |  Every 100ms or 100 spans > send batch to collector    |  |*
*|  |     |  Uses gRPC (more reliable than UDP)                    |  |*
*|  |     v                                                          |  |*
*|  |  6. COLLECTOR PROCESSING                                       |  |*
*|  |     |                                                          |  |*
*|  |     |  - Validate span structure                              |  |*
*|  |     |  - Apply sampling rules                                 |  |*
*|  |     |  - Enrich with metadata                                 |  |*
*|  |     |  - Serialize for storage                                |  |*
*|  |     v                                                          |  |*
*|  |  7. KAFKA (if enabled)                                         |  |*
*|  |     |                                                          |  |*
*|  |     |  - Write to kafka topic                                 |  |*
*|  |     |  - Partition by traceId                                 |  |*
*|  |     v                                                          |  |*
*|  |  8. INGESTER > STORAGE                                         |  |*
*|  |                                                                 |  |*
*|  |     - Consume from Kafka                                      |  |*
*|  |     - Batch write to Cassandra/ES                            |  |*
*|  |     - Index for querying                                      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  READ PATH (Trace Query)                                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. USER QUERY                                                  |  |*
*|  |     |                                                          |  |*
*|  |     |  Jaeger UI > Query Service                              |  |*
*|  |     |  "Find traces for order-service with error=true"       |  |*
*|  |     v                                                          |  |*
*|  |  2. INDEX LOOKUP                                               |  |*
*|  |     |                                                          |  |*
*|  |     |  Query Elasticsearch:                                   |  |*
*|  |     |  service=order-service AND error=true AND time>24h    |  |*
*|  |     |  Returns: list of trace IDs                            |  |*
*|  |     v                                                          |  |*
*|  |  3. TRACE RETRIEVAL                                            |  |*
*|  |     |                                                          |  |*
*|  |     |  For each trace ID:                                     |  |*
*|  |     |  Fetch all spans from Cassandra                        |  |*
*|  |     |  (Primary key lookup - fast)                           |  |*
*|  |     v                                                          |  |*
*|  |  4. TRACE ASSEMBLY                                             |  |*
*|  |     |                                                          |  |*
*|  |     |  Assemble spans into trace tree                        |  |*
*|  |     |  Sort by timestamp                                      |  |*
*|  |     |  Build parent-child relationships                      |  |*
*|  |     v                                                          |  |*
*|  |  5. RESPONSE                                                    |  |*
*|  |                                                                 |  |*
*|  |     Return to UI for visualization                            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2.4: DEPLOYMENT ARCHITECTURES
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  DEPLOYMENT OPTION 1: ALL-IN-ONE (Development)                        |*
*|  ----------------------------------------------                        |*
*|                                                                         |*
*|  Single process with all components:                                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |                 Jaeger All-in-One                              |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |  Agent | Collector | Query | UI | In-Memory Storage      ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  docker run jaegertracing/all-in-one:latest                   |  |*
*|  |                                                                 |  |*
*|  |  Pros: Simple, fast to start                                  |  |*
*|  |  Cons: No persistence, single instance, not scalable         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DEPLOYMENT OPTION 2: PRODUCTION (Direct to Storage)                  |*
*|  -----------------------------------------------------                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Services with SDK                                             |  |*
*|  |        |                                                        |  |*
*|  |        v                                                        |  |*
*|  |  Jaeger Agents (DaemonSet)                                     |  |*
*|  |        |                                                        |  |*
*|  |        v                                                        |  |*
*|  |  Collectors (3+ replicas, behind LB)                          |  |*
*|  |        |                                                        |  |*
*|  |        v                                                        |  |*
*|  |  Cassandra Cluster + Elasticsearch                            |  |*
*|  |        |                                                        |  |*
*|  |        v                                                        |  |*
*|  |  Query Service (2+ replicas)                                  |  |*
*|  |        |                                                        |  |*
*|  |        v                                                        |  |*
*|  |  Jaeger UI                                                     |  |*
*|  |                                                                 |  |*
*|  |  Pros: Production-ready, good for medium scale               |  |*
*|  |  Cons: Storage can be bottleneck under very high load        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DEPLOYMENT OPTION 3: PRODUCTION (With Kafka)                         |*
*|  -------------------------------------------------                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Services with SDK                                             |  |*
*|  |        |                                                        |  |*
*|  |        v                                                        |  |*
*|  |  Jaeger Agents (DaemonSet)                                     |  |*
*|  |        |                                                        |  |*
*|  |        v                                                        |  |*
*|  |  Collectors (5+ replicas) ---------------+                    |  |*
*|  |        |                                  |                    |  |*
*|  |        v                                  |                    |  |*
*|  |  Kafka Cluster <--------------------------+                    |  |*
*|  |  (Topic: jaeger-spans)                                        |  |*
*|  |        |                                                        |  |*
*|  |        v                                                        |  |*
*|  |  Ingesters (match Kafka partitions)                          |  |*
*|  |        |                                                        |  |*
*|  |        v                                                        |  |*
*|  |  Cassandra + Elasticsearch                                    |  |*
*|  |        |                                                        |  |*
*|  |        v                                                        |  |*
*|  |  Query Service + UI                                           |  |*
*|  |                                                                 |  |*
*|  |  Pros: Handles very high scale, resilient to storage issues  |  |*
*|  |  Cons: More complexity, more infrastructure                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DEPLOYMENT OPTION 4: MODERN (Tempo + Object Storage)                 |*
*|  -----------------------------------------------------                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  OpenTelemetry Collector                                       |  |*
*|  |        |                                                        |  |*
*|  |        v                                                        |  |*
*|  |  Grafana Tempo                                                 |  |*
*|  |        |                                                        |  |*
*|  |        +----------> S3/GCS/Azure Blob (traces)               |  |*
*|  |        |                                                        |  |*
*|  |        +----------> Prometheus (metrics from traces)          |  |*
*|  |                                                                 |  |*
*|  |  Query via: Grafana (Tempo datasource)                        |  |*
*|  |                                                                 |  |*
*|  |  Search via:                                                   |  |*
*|  |  - Exemplars (metrics > traces)                              |  |*
*|  |  - Logs (log > trace ID > full trace)                        |  |*
*|  |  - TraceQL (Tempo's query language)                          |  |*
*|  |                                                                 |  |*
*|  |  Pros: Very cost-effective, scales infinitely               |  |*
*|  |  Cons: Limited search (mostly trace ID lookup)               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF CHAPTER 2
