# MICROSERVICES ARCHITECTURE - HIGH LEVEL DESIGN

CHAPTER 3: RESILIENCE, DEPLOYMENT & OBSERVABILITY
SECTION 1: RESILIENCE PATTERNS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHY RESILIENCE MATTERS                                                |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  In microservices, you have:                                    |  |*
*|  |  * 50+ services                                                 |  |*
*|  |  * 100+ instances                                               |  |*
*|  |  * Thousands of network calls per second                       |  |*
*|  |                                                                 |  |*
*|  |  Something WILL fail:                                           |  |*
*|  |  * Network partitions                                          |  |*
*|  |  * Service crashes                                             |  |*
*|  |  * Database overload                                           |  |*
*|  |  * Dependency timeouts                                         |  |*
*|  |                                                                 |  |*
*|  |  Goal: System should gracefully handle partial failures        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  PATTERN 1: TIMEOUTS                                                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  NEVER make a call without a timeout                            |  |*
*|  |                                                                 |  |*
*|  |  WITHOUT TIMEOUT:                                               |  |*
*|  |                                                                 |  |*
*|  |  Service A -----------------------------> Service B (hung)     |  |*
*|  |      |                                        |                 |  |*
*|  |      | Waiting...                            | Processing...   |  |*
*|  |      | Waiting...                            | (forever)       |  |*
*|  |      | (thread blocked forever)              |                 |  |*
*|  |      v                                                          |  |*
*|  |  Thread pool exhausted > Service A dies                        |  |*
*|  |                                                                 |  |*
*|  |  WITH TIMEOUT:                                                  |  |*
*|  |                                                                 |  |*
*|  |  Service A -----------------------------> Service B (hung)     |  |*
*|  |      |                                                          |  |*
*|  |      | Wait max 2 seconds                                      |  |*
*|  |      |                                                          |  |*
*|  |      | TIMEOUT!                                                |  |*
*|  |      v                                                          |  |*
*|  |  Return error or fallback, thread freed                        |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  TIMEOUT TYPES:                                                 |  |*
*|  |                                                                 |  |*
*|  |  Connection Timeout: Max time to establish connection          |  |*
*|  |  (Usually short: 1-3 seconds)                                  |  |*
*|  |                                                                 |  |*
*|  |  Read/Response Timeout: Max time to receive response           |  |*
*|  |  (Depends on operation: 2-30 seconds)                          |  |*
*|  |                                                                 |  |*
*|  |  Overall Timeout: Total time including retries                 |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  PATTERN 2: RETRIES WITH EXPONENTIAL BACKOFF                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Transient failures (network blip) often succeed on retry.     |  |*
*|  |  But naive retries can cause thundering herd.                  |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  EXPONENTIAL BACKOFF + JITTER                            ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Attempt 1: Immediate                                    ||  |*
*|  |  |      |                                                    ||  |*
*|  |  |      | Failed                                            ||  |*
*|  |  |      v                                                    ||  |*
*|  |  |  Wait: 1s + random(0, 0.5s)                              ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Attempt 2:                                               ||  |*
*|  |  |      |                                                    ||  |*
*|  |  |      | Failed                                            ||  |*
*|  |  |      v                                                    ||  |*
*|  |  |  Wait: 2s + random(0, 1s)                                ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Attempt 3:                                               ||  |*
*|  |  |      |                                                    ||  |*
*|  |  |      | Failed                                            ||  |*
*|  |  |      v                                                    ||  |*
*|  |  |  Wait: 4s + random(0, 2s)                                ||  |*
*|  |  |                                                           ||  |*
*|  |  |  ... up to max_retries or max_delay                      ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  WHY JITTER?                                                   |  |*
*|  |  Without jitter: 1000 clients retry at exactly 1s, 2s, 4s     |  |*
*|  |  > Synchronized retry storm                                    |  |*
*|  |                                                                 |  |*
*|  |  With jitter: Retries spread out randomly                      |  |*
*|  |  > Smoother load on recovering service                         |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  RETRY ONLY IDEMPOTENT OPERATIONS:                              |  |*
*|  |  * GET requests: Always safe                                   |  |*
*|  |  * PUT/DELETE with same ID: Usually safe                      |  |*
*|  |  * POST creating resource: Dangerous! (might duplicate)       |  |*
*|  |                                                                 |  |*
*|  |  For non-idempotent: Use idempotency keys                      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  PATTERN 3: CIRCUIT BREAKER                                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Stop calling a failing service to let it recover.             |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |                    CIRCUIT BREAKER STATES                 ||  |*
*|  |  |                                                           ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  |              +--------------+                       | ||  |*
*|  |  |  |              |    CLOSED    |                       | ||  |*
*|  |  |  |              | (Normal)     |                       | ||  |*
*|  |  |  |              +------+-------+                       | ||  |*
*|  |  |  |                     |                               | ||  |*
*|  |  |  |                     | Failure threshold reached     | ||  |*
*|  |  |  |                     | (e.g., 50% failures in 10s)  | ||  |*
*|  |  |  |                     v                               | ||  |*
*|  |  |  |              +--------------+                       | ||  |*
*|  |  |  |              |     OPEN     |                       | ||  |*
*|  |  |  |              | (Fail Fast)  |                       | ||  |*
*|  |  |  |              +------+-------+                       | ||  |*
*|  |  |  |                     |                               | ||  |*
*|  |  |  |                     | After timeout (e.g., 30s)    | ||  |*
*|  |  |  |                     v                               | ||  |*
*|  |  |  |              +--------------+                       | ||  |*
*|  |  |  |              |  HALF-OPEN   |                       | ||  |*
*|  |  |  |              | (Testing)    |                       | ||  |*
*|  |  |  |              +------+-------+                       | ||  |*
*|  |  |  |                     |                               | ||  |*
*|  |  |  |         +----------+----------+                    | ||  |*
*|  |  |  |         |                     |                    | ||  |*
*|  |  |  |    Success               Failure                   | ||  |*
*|  |  |  |         |                     |                    | ||  |*
*|  |  |  |         v                     v                    | ||  |*
*|  |  |  |    > CLOSED             > OPEN                     | ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  WHEN OPEN:                                                    |  |*
*|  |  * Don't even try to call the service                         |  |*
*|  |  * Return cached response or fallback immediately              |  |*
*|  |  * Fail fast instead of waiting for timeout                   |  |*
*|  |                                                                 |  |*
*|  |  BENEFITS:                                                     |  |*
*|  |  * Prevents cascading failures                                 |  |*
*|  |  * Gives failing service time to recover                      |  |*
*|  |  * Fails fast > better user experience                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  PATTERN 4: BULKHEAD                                                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Isolate failures to prevent spreading. Like compartments in   |  |*
*|  |  a ship - one leak doesn't sink the whole ship.               |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  WITHOUT BULKHEAD:                                        ||  |*
*|  |  |                                                           ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |  |            Shared Thread Pool (100 threads)         | ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  |  Service A calls (slow) > Uses 80 threads          | ||  |*
*|  |  |  |  Service B calls > Uses 15 threads                 | ||  |*
*|  |  |  |  Service C calls > Only 5 threads left!            | ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  |  > Slow Service A starves Service B and C          | ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |                                                           ||  |*
*|  |  |  WITH BULKHEAD:                                           ||  |*
*|  |  |                                                           ||  |*
*|  |  |  +----------------+ +----------------+ +----------------+||  |*
*|  |  |  | Pool A: 40    | | Pool B: 40    | | Pool C: 20    |||  |*
*|  |  |  | Service A     | | Service B     | | Service C     |||  |*
*|  |  |  | (can max out) | | (still works) | | (still works) |||  |*
*|  |  |  +----------------+ +----------------+ +----------------+||  |*
*|  |  |                                                           ||  |*
*|  |  |  > Slow Service A can only affect its own pool           ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  BULKHEAD TYPES:                                               |  |*
*|  |  * Thread pool isolation (separate pools per dependency)       |  |*
*|  |  * Semaphore isolation (limit concurrent calls)               |  |*
*|  |  * Process isolation (separate containers)                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  PATTERN 5: FALLBACK                                                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  When a service fails, provide degraded but working response.  |  |*
*|  |                                                                 |  |*
*|  |  FALLBACK STRATEGIES:                                           |  |*
*|  |                                                                 |  |*
*|  |  1. CACHED RESPONSE                                            |  |*
*|  |     Recommendation Service down?                               |  |*
*|  |     > Return cached/popular recommendations                    |  |*
*|  |                                                                 |  |*
*|  |  2. DEFAULT VALUE                                              |  |*
*|  |     Feature flag service down?                                 |  |*
*|  |     > Return default flag values                               |  |*
*|  |                                                                 |  |*
*|  |  3. ALTERNATIVE SERVICE                                        |  |*
*|  |     Primary payment processor down?                            |  |*
*|  |     > Route to backup processor                                |  |*
*|  |                                                                 |  |*
*|  |  4. GRACEFUL DEGRADATION                                       |  |*
*|  |     Review service down?                                       |  |*
*|  |     > Show product page without reviews                        |  |*
*|  |                                                                 |  |*
*|  |  5. QUEUE FOR LATER                                            |  |*
*|  |     Email service down?                                        |  |*
*|  |     > Queue email to send when service recovers                |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  PATTERN 6: HEALTH CHECKS                                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Services expose endpoints for health monitoring                |  |*
*|  |                                                                 |  |*
*|  |  LIVENESS CHECK: "Is the service running?"                     |  |*
*|  |  GET /health/live > 200 OK or 503 Service Unavailable         |  |*
*|  |  * Simple: Just returns OK if process is alive                 |  |*
*|  |  * If fails: Kubernetes restarts the container                 |  |*
*|  |                                                                 |  |*
*|  |  READINESS CHECK: "Can the service handle traffic?"            |  |*
*|  |  GET /health/ready > 200 OK or 503 Service Unavailable        |  |*
*|  |  * Checks: Database connection, cache, dependencies            |  |*
*|  |  * If fails: Load balancer stops routing traffic to it        |  |*
*|  |                                                                 |  |*
*|  |  DEEP HEALTH CHECK: Detailed status for monitoring             |  |*
*|  |  GET /health > Returns JSON with component status             |  |*
*|  |  {                                                              |  |*
*|  |    "status": "UP",                                             |  |*
*|  |    "components": {                                              |  |*
*|  |      "database": { "status": "UP", "responseTime": "5ms" },   |  |*
*|  |      "redis": { "status": "UP" },                              |  |*
*|  |      "externalAPI": { "status": "DOWN", "error": "timeout" }  |  |*
*|  |    }                                                            |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2: OBSERVABILITY
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  THREE PILLARS OF OBSERVABILITY                                        |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  +-----------------+  +-----------------+  +-----------------+|  |*
*|  |  |     METRICS     |  |     LOGS        |  |    TRACES       ||  |*
*|  |  |                 |  |                 |  |                 ||  |*
*|  |  | * Request rate  |  | * What happened |  | * Request flow  ||  |*
*|  |  | * Error rate    |  | * Error details |  | * Cross-service ||  |*
*|  |  | * Latency       |  | * Audit trail   |  | * Bottlenecks   ||  |*
*|  |  | * Saturation    |  | * Debug info    |  | * Dependencies  ||  |*
*|  |  |                 |  |                 |  |                 ||  |*
*|  |  | Prometheus      |  | ELK Stack       |  | Jaeger/Zipkin   ||  |*
*|  |  | Grafana         |  | Fluentd         |  | OpenTelemetry   ||  |*
*|  |  | DataDog         |  | Loki            |  |                 ||  |*
*|  |  |                 |  |                 |  |                 ||  |*
*|  |  +-----------------+  +-----------------+  +-----------------+|  |*
*|  |                                                                 |  |*
*|  |  WHEN TO USE:                                                  |  |*
*|  |                                                                 |  |*
*|  |  Metrics: "Is something wrong?" (alerting, dashboards)        |  |*
*|  |  Logs: "What went wrong?" (debugging, audit)                  |  |*
*|  |  Traces: "Where is the problem?" (distributed debugging)      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  DISTRIBUTED TRACING                                                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  HOW IT WORKS:                                                  |  |*
*|  |                                                                 |  |*
*|  |  Request enters system with unique Trace ID                    |  |*
*|  |  Each service creates a Span with:                             |  |*
*|  |  * Trace ID (same for entire request)                          |  |*
*|  |  * Span ID (unique for this service call)                      |  |*
*|  |  * Parent Span ID (who called me)                              |  |*
*|  |  * Start time, duration, status                                |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  Request: GET /checkout                                   ||  |*
*|  |  |  Trace ID: abc-123                                        ||  |*
*|  |  |                                                           ||  |*
*|  |  |  API Gateway -----------------------------------------    ||  |*
*|  |  |  Span: 1, Duration: 500ms                                 ||  |*
*|  |  |       |                                                   ||  |*
*|  |  |       |                                                   ||  |*
*|  |  |       +-- Order Service -------------------------         ||  |*
*|  |  |           Span: 2, Parent: 1, Duration: 300ms             ||  |*
*|  |  |                |                                          ||  |*
*|  |  |                |                                          ||  |*
*|  |  |                +-- Inventory Service -----                ||  |*
*|  |  |                |   Span: 3, Parent: 2, Duration: 50ms     ||  |*
*|  |  |                |                                          ||  |*
*|  |  |                +-- Payment Service -----------            ||  |*
*|  |  |                    Span: 4, Parent: 2, Duration: 200ms    ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  BENEFITS:                                                     |  |*
*|  |  * See entire request flow across services                    |  |*
*|  |  * Identify slow services (Payment took 200ms)                |  |*
*|  |  * Find failures in the chain                                 |  |*
*|  |  * Understand dependencies                                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  KEY METRICS TO MONITOR (RED & USE Methods)                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  RED METHOD (for services):                                     |  |*
*|  |                                                                 |  |*
*|  |  Rate:     Requests per second                                 |  |*
*|  |  Errors:   Failed requests per second                          |  |*
*|  |  Duration: Time taken per request (latency)                    |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  USE METHOD (for resources):                                    |  |*
*|  |                                                                 |  |*
*|  |  Utilization:  % of resource being used (CPU, memory)         |  |*
*|  |  Saturation:   Amount of work waiting (queue length)          |  |*
*|  |  Errors:       Number of errors                                |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  GOLDEN SIGNALS (Google SRE):                                   |  |*
*|  |                                                                 |  |*
*|  |  Latency:    Time to serve a request                          |  |*
*|  |  Traffic:    Request volume                                   |  |*
*|  |  Errors:     Rate of failed requests                          |  |*
*|  |  Saturation: How "full" the service is                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3: DEPLOYMENT STRATEGIES
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  DEPLOYMENT STRATEGIES FOR MICROSERVICES                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. ROLLING DEPLOYMENT                                         |  |*
*|  |                                                                 |  |*
*|  |  Gradually replace old instances with new ones                 |  |*
*|  |                                                                 |  |*
*|  |  Before:  [v1] [v1] [v1] [v1]                                 |  |*
*|  |                                                                 |  |*
*|  |  Step 1:  [v2] [v1] [v1] [v1]                                 |  |*
*|  |  Step 2:  [v2] [v2] [v1] [v1]                                 |  |*
*|  |  Step 3:  [v2] [v2] [v2] [v1]                                 |  |*
*|  |  Step 4:  [v2] [v2] [v2] [v2]                                 |  |*
*|  |                                                                 |  |*
*|  |  Pros: Zero downtime, easy rollback                           |  |*
*|  |  Cons: Mixed versions during deployment, slow                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  2. BLUE-GREEN DEPLOYMENT                                      |  |*
*|  |                                                                 |  |*
*|  |  Two identical environments, switch traffic instantly          |  |*
*|  |                                                                 |  |*
*|  |  +--------------------------------------------------------+   |  |*
*|  |  |                                                        |   |  |*
*|  |  |              Load Balancer                            |   |  |*
*|  |  |                   |                                    |   |  |*
*|  |  |         +---------+---------+                         |   |  |*
*|  |  |         |                   |                         |   |  |*
*|  |  |         v                   v                         |   |  |*
*|  |  |  +------------+      +------------+                  |   |  |*
*|  |  |  |   BLUE     |      |   GREEN    |                  |   |  |*
*|  |  |  |   (v1)     |      |   (v2)     |                  |   |  |*
*|  |  |  |  ACTIVE    |      |   IDLE     |                  |   |  |*
*|  |  |  +------------+      +------------+                  |   |  |*
*|  |  |                                                        |   |  |*
*|  |  |  Deploy v2 to Green > Test > Switch traffic to Green  |   |  |*
*|  |  |                                                        |   |  |*
*|  |  +--------------------------------------------------------+   |  |*
*|  |                                                                 |  |*
*|  |  Pros: Instant switch, easy rollback, test in production-like |  |*
*|  |  Cons: Requires 2x infrastructure                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  3. CANARY DEPLOYMENT                                          |  |*
*|  |                                                                 |  |*
*|  |  Release to small subset first, monitor, then expand          |  |*
*|  |                                                                 |  |*
*|  |  Stage 1:  5% traffic > v2 (canary)                           |  |*
*|  |           95% traffic > v1                                     |  |*
*|  |           Monitor error rate, latency...                       |  |*
*|  |                                                                 |  |*
*|  |  Stage 2:  25% traffic > v2                                   |  |*
*|  |           75% traffic > v1                                     |  |*
*|  |           Still looks good...                                  |  |*
*|  |                                                                 |  |*
*|  |  Stage 3:  50% > v2                                            |  |*
*|  |  Stage 4:  100% > v2                                           |  |*
*|  |                                                                 |  |*
*|  |  If problems detected > Rollback (shift 100% to v1)           |  |*
*|  |                                                                 |  |*
*|  |  Pros: Minimize blast radius, real traffic testing            |  |*
*|  |  Cons: Requires traffic splitting, longer rollout              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  4. A/B TESTING (Feature-based)                                |  |*
*|  |                                                                 |  |*
*|  |  Route specific users/segments to new version                  |  |*
*|  |                                                                 |  |*
*|  |  * Users in region=EU > v2                                    |  |*
*|  |  * Users with premium subscription > v2                       |  |*
*|  |  * Users with user_id % 10 < 2 > v2                           |  |*
*|  |                                                                 |  |*
*|  |  Pros: Target specific users, gather feedback                 |  |*
*|  |  Cons: Complex routing logic, session affinity needed         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4: CONTAINER ORCHESTRATION (Kubernetes)
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHY KUBERNETES FOR MICROSERVICES?                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CHALLENGES WITHOUT ORCHESTRATION:                              |  |*
*|  |                                                                 |  |*
*|  |  * 50 services x 3 instances = 150 containers to manage       |  |*
*|  |  * How to deploy, scale, restart, monitor all of them?        |  |*
*|  |  * How to handle container failures?                          |  |*
*|  |  * How to do service discovery?                               |  |*
*|  |  * How to manage configuration and secrets?                   |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  KUBERNETES PROVIDES:                                           |  |*
*|  |                                                                 |  |*
*|  |  * Automatic deployment and scaling                           |  |*
*|  |  * Self-healing (restart failed containers)                   |  |*
*|  |  * Service discovery and load balancing (built-in)            |  |*
*|  |  * Configuration and secret management                        |  |*
*|  |  * Rolling updates and rollbacks                              |  |*
*|  |  * Resource management (CPU/memory limits)                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  KUBERNETES CONCEPTS FOR MICROSERVICES                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  POD                                                            |  |*
*|  |  * Smallest deployable unit                                    |  |*
*|  |  * One or more containers sharing network/storage             |  |*
*|  |  * Usually one microservice per pod                           |  |*
*|  |                                                                 |  |*
*|  |  DEPLOYMENT                                                     |  |*
*|  |  * Defines desired state (replicas, image version)            |  |*
*|  |  * Handles rolling updates                                     |  |*
*|  |  * ReplicaSet ensures desired number of pods running          |  |*
*|  |                                                                 |  |*
*|  |  SERVICE                                                        |  |*
*|  |  * Stable network endpoint for pods                           |  |*
*|  |  * Load balances across pod replicas                          |  |*
*|  |  * Service discovery via DNS                                  |  |*
*|  |    (order-service.default.svc.cluster.local)                  |  |*
*|  |                                                                 |  |*
*|  |  INGRESS                                                        |  |*
*|  |  * External access to services                                |  |*
*|  |  * URL routing (/api/users > user-service)                   |  |*
*|  |  * TLS termination                                            |  |*
*|  |                                                                 |  |*
*|  |  CONFIG MAP & SECRET                                           |  |*
*|  |  * Externalize configuration                                  |  |*
*|  |  * Secrets encrypted at rest                                  |  |*
*|  |  * Mount as files or environment variables                    |  |*
*|  |                                                                 |  |*
*|  |  HORIZONTAL POD AUTOSCALER (HPA)                               |  |*
*|  |  * Auto-scale based on CPU/memory/custom metrics              |  |*
*|  |  * Scale up during traffic spikes                             |  |*
*|  |  * Scale down during low traffic                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 5: INTERVIEW Q&A
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  Q1: How do you handle distributed transactions?                       |*
*|                                                                         |*
*|  A: Avoid distributed transactions. Instead:                           |*
*|  * Use Saga pattern (choreography or orchestration)                   |*
*|  * Each service has local transaction                                 |*
*|  * Compensating transactions for rollback                              |*
*|  * Accept eventual consistency                                         |*
*|  * Use Outbox pattern for reliable event publishing                   |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  Q2: How do services communicate? REST vs gRPC vs Events?              |*
*|                                                                         |*
*|  A:                                                                     |*
*|  * REST: Simple CRUD, public APIs, browser clients                    |*
*|  * gRPC: High performance internal calls, strong typing, streaming    |*
*|  * Events (Kafka): Async, decoupling, event sourcing, audit           |*
*|                                                                         |*
*|  Often mixed: REST for external, gRPC for internal sync,              |*
*|  Events for async operations                                           |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  Q3: How do you handle service failures?                               |*
*|                                                                         |*
*|  A: Combination of patterns:                                           |*
*|  * Timeouts on all external calls                                     |*
*|  * Retries with exponential backoff (for transient failures)          |*
*|  * Circuit breaker (stop calling failing service)                     |*
*|  * Fallback responses (cached/default)                                |*
*|  * Bulkhead (isolate failures)                                        |*
*|  * Health checks + load balancer (remove unhealthy instances)        |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  Q4: How do you debug issues in microservices?                         |*
*|                                                                         |*
*|  A: Observability is key:                                              |*
*|  * Distributed tracing (Jaeger/Zipkin) for request flow               |*
*|  * Correlation ID across all logs                                     |*
*|  * Centralized logging (ELK) with search                              |*
*|  * Metrics dashboards (Grafana)                                       |*
*|  * Alerting on anomalies                                              |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  Q5: How do you ensure data consistency across services?               |*
*|                                                                         |*
*|  A:                                                                     |*
*|  * Accept eventual consistency (most cases)                           |*
*|  * Saga pattern for multi-service operations                          |*
*|  * Idempotency keys for duplicate requests                            |*
*|  * Outbox pattern for reliable event publishing                       |*
*|  * CQRS for read/write separation                                     |*
*|  * Event sourcing for audit trail                                     |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  Q6: When NOT to use microservices?                                    |*
*|                                                                         |*
*|  A:                                                                     |*
*|  * Small team (< 10 people)                                           |*
*|  * Simple domain, few features                                        |*
*|  * Early startup (domain not understood)                              |*
*|  * Limited DevOps maturity                                            |*
*|  * Strong ACID requirements                                           |*
*|  * Tight deadlines                                                    |*
*|                                                                         |*
*|  Start with modular monolith, extract services when needed.           |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  Q7: How do you version microservices APIs?                            |*
*|                                                                         |*
*|  A: Multiple strategies:                                               |*
*|  * URL path: /api/v1/users, /api/v2/users                            |*
*|  * Header: Accept: application/vnd.api+json;version=2                |*
*|  * Query param: /api/users?version=2                                  |*
*|                                                                         |*
*|  Best practice:                                                        |*
*|  * Support backward compatibility (additive changes)                  |*
*|  * Deprecation period before removing old versions                    |*
*|  * Consumer-driven contract testing                                   |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  Q8: How do you handle authentication across services?                 |*
*|                                                                         |*
*|  A:                                                                     |*
*|  * API Gateway validates JWT token                                    |*
*|  * Gateway passes user context (headers) to services                 |*
*|  * Services trust internal network (mTLS for extra security)         |*
*|  * Service-to-service auth via service accounts/tokens               |*
*|                                                                         |*
*|  Pattern:                                                              |*
*|  Client > JWT > Gateway > validates > User context headers > Service |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  Q9: What's the "distributed monolith" anti-pattern?                   |*
*|                                                                         |*
*|  A: Microservices that are:                                            |*
*|  * Deployed together (can't deploy independently)                     |*
*|  * Share database (tight data coupling)                               |*
*|  * Synchronous calls everywhere (tight temporal coupling)             |*
*|  * Must be updated together (tight API coupling)                      |*
*|                                                                         |*
*|  > Worst of both worlds: complexity of distributed + constraints      |*
*|    of monolith                                                         |*
*|                                                                         |*
*|  Solution: True bounded contexts, async communication,                |*
*|  database per service                                                 |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  Q10: How do you test microservices?                                   |*
*|                                                                         |*
*|  A: Testing pyramid:                                                   |*
*|                                                                         |*
*|  * Unit tests: Test service logic in isolation                        |*
*|                                                                         |*
*|  * Integration tests: Test with real DB, mock external services       |*
*|                                                                         |*
*|  * Contract tests: Verify API contracts between services             |*
*|    (Pact, Spring Cloud Contract)                                      |*
*|                                                                         |*
*|  * End-to-End tests: Full flow through multiple services             |*
*|    (Slow, flaky - minimize these)                                     |*
*|                                                                         |*
*|  * Chaos testing: Inject failures, verify resilience                 |*
*|    (Chaos Monkey, Litmus)                                             |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF MICROSERVICES ARCHITECTURE HLD
