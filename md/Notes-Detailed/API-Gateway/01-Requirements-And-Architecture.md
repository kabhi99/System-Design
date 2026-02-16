# API GATEWAY - HIGH LEVEL DESIGN
*Part 1: Requirements and Architecture*

## SECTION 1.1: WHAT IS AN API GATEWAY?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  API GATEWAY                                                           |
|                                                                         |
|  Single entry point for all client requests in a microservices        |
|  architecture. Acts as reverse proxy + cross-cutting concerns.        |
|                                                                         |
|  WITHOUT API GATEWAY:                                                   |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Mobile App -------------------------> User Service            |  |
|  |       |                                                         |  |
|  |       +------------------------------> Order Service           |  |
|  |       |                                                         |  |
|  |       +------------------------------> Payment Service         |  |
|  |       |                                                         |  |
|  |       +------------------------------> Notification Service    |  |
|  |                                                                 |  |
|  |  PROBLEMS:                                                      |  |
|  |  * Client knows all service URLs                               |  |
|  |  * Auth logic duplicated in every service                     |  |
|  |  * No central rate limiting                                   |  |
|  |  * Protocol coupling (all must be HTTP)                       |  |
|  |  * Multiple round trips from client                           |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  WITH API GATEWAY:                                                      |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |                     +-------------------------------------+    |  |
|  |                     |         API GATEWAY                 |    |  |
|  |                     |                                     |    |  |
|  |  Mobile App ------->|  * Authentication                  |    |  |
|  |  Web App ---------->|  * Rate Limiting                   |    |  |
|  |  Partner API ------>|  * Request Routing                 |    |  |
|  |                     |  * Protocol Translation            |    |  |
|  |                     |  * Response Aggregation            |    |  |
|  |                     |  * Caching                         |    |  |
|  |                     |  * Logging/Monitoring              |    |  |
|  |                     |                                     |    |  |
|  |                     +----------+--------------------------+    |  |
|  |                                |                               |  |
|  |           +--------------------+--------------------+         |  |
|  |           |                    |                    |          |  |
|  |           v                    v                    v          |  |
|  |    User Service         Order Service        Payment Service  |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### EXAMPLES OF API GATEWAYS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMMERCIAL / MANAGED                                                  |
|  * AWS API Gateway                                                     |
|  * Google Cloud Endpoints / Apigee                                    |
|  * Azure API Management                                               |
|  * Kong Enterprise                                                     |
|                                                                         |
|  OPEN SOURCE                                                           |
|  * Kong (Nginx-based, Lua plugins)                                    |
|  * NGINX Plus                                                          |
|  * Envoy (service mesh data plane)                                    |
|  * Traefik                                                             |
|  * Express Gateway (Node.js)                                          |
|  * Spring Cloud Gateway (Java)                                        |
|  * KrakenD (Go, high performance)                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.2: FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CORE FUNCTIONALITY                                                    |
|                                                                         |
|  1. REQUEST ROUTING                                                    |
|     ===================                                                 |
|     * Route requests to appropriate backend service                   |
|     * Path-based routing (/users/* -> User Service)                   |
|     * Header-based routing (version, tenant)                         |
|     * Query param routing                                             |
|                                                                         |
|  2. AUTHENTICATION & AUTHORIZATION                                     |
|     ===================================                                 |
|     * Validate API keys                                               |
|     * JWT token validation                                            |
|     * OAuth 2.0 / OpenID Connect                                     |
|     * mTLS for service-to-service                                    |
|     * RBAC / Scope-based authorization                               |
|                                                                         |
|  3. RATE LIMITING & THROTTLING                                        |
|     ===============================                                     |
|     * Per-client rate limits                                         |
|     * Per-endpoint limits                                            |
|     * Burst handling                                                  |
|     * Quota management (daily/monthly)                               |
|                                                                         |
|  4. LOAD BALANCING                                                     |
|     ====================                                                |
|     * Round-robin, least connections, weighted                       |
|     * Health checks                                                   |
|     * Circuit breaking                                                |
|                                                                         |
|  5. REQUEST/RESPONSE TRANSFORMATION                                    |
|     ===================================                                 |
|     * Header manipulation (add/remove/modify)                        |
|     * Payload transformation                                          |
|     * Protocol translation (REST ↔ gRPC)                            |
|                                                                         |
|  6. CACHING                                                            |
|     ===========                                                         |
|     * Response caching                                                |
|     * Cache invalidation                                              |
|     * Cache-Control header handling                                  |
|                                                                         |
|  7. RESPONSE AGGREGATION (BFF Pattern)                                |
|     ==================================                                  |
|     * Combine responses from multiple services                       |
|     * Reduce client round-trips                                      |
|                                                                         |
|  8. OBSERVABILITY                                                      |
|     ===============                                                     |
|     * Request/response logging                                       |
|     * Metrics collection                                              |
|     * Distributed tracing                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.3: NON-FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NON-FUNCTIONAL REQUIREMENTS                                           |
|                                                                         |
|  1. LATENCY                                                             |
|     ==========                                                          |
|     * Add minimal overhead (< 10ms p99)                               |
|     * Gateway should NOT be bottleneck                               |
|     * Target: < 5ms for simple routing                               |
|                                                                         |
|  2. THROUGHPUT                                                          |
|     ============                                                        |
|     * 100,000+ requests per second per node                          |
|     * Linear horizontal scaling                                       |
|                                                                         |
|  3. AVAILABILITY                                                        |
|     ==============                                                      |
|     * 99.99% uptime (critical path for all traffic)                  |
|     * No single point of failure                                     |
|     * Graceful degradation                                           |
|                                                                         |
|  4. SCALABILITY                                                         |
|     =============                                                       |
|     * Stateless design (horizontal scaling)                          |
|     * Handle traffic spikes                                          |
|     * Auto-scaling support                                           |
|                                                                         |
|  5. SECURITY                                                            |
|     ===========                                                         |
|     * TLS termination                                                 |
|     * DDoS protection                                                 |
|     * WAF integration                                                 |
|     * IP whitelisting/blacklisting                                   |
|                                                                         |
|  6. CONFIGURABILITY                                                     |
|     =================                                                   |
|     * Hot reload (no restart for config changes)                     |
|     * Declarative configuration                                      |
|     * Version controlled configs                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.4: SCALE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALE ASSUMPTIONS (Large-scale system)                                |
|                                                                         |
|  TRAFFIC:                                                               |
|  * Peak RPS: 100,000 requests/second                                  |
|  * Average RPS: 20,000 requests/second                                |
|  * Daily requests: 1.7 billion                                        |
|                                                                         |
|  LATENCY BUDGET:                                                        |
|  * Gateway overhead: < 5ms (p50), < 10ms (p99)                        |
|  * Total request latency: depends on backend                         |
|                                                                         |
|  CONFIGURATION:                                                         |
|  * Routes: 1,000+                                                      |
|  * Backend services: 100+                                             |
|  * API consumers: 10,000+                                             |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  CAPACITY PLANNING                                                      |
|                                                                         |
|  Single node capacity (Kong/Envoy):                                   |
|  * 10,000-50,000 RPS depending on plugins                            |
|                                                                         |
|  For 100K RPS peak:                                                    |
|  * Minimum: 100K / 10K = 10 nodes                                    |
|  * With 2x headroom: 20 nodes                                        |
|  * Across 2 AZs: 10 nodes each                                       |
|                                                                         |
|  STORAGE:                                                               |
|  * Configuration: < 100 MB (in-memory)                               |
|  * Rate limit counters: Redis cluster                                |
|  * Logs: 1 KB per request × 1.7B = 1.7 TB/day                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.5: HIGH-LEVEL ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  API GATEWAY - HIGH LEVEL ARCHITECTURE                                 |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                         CLIENTS                                 |  |
|  |  +---------+  +---------+  +---------+  +---------+           |  |
|  |  | Mobile  |  |   Web   |  | Partner |  |Internal |           |  |
|  |  |  Apps   |  |  Apps   |  |  APIs   |  |Services |           |  |
|  |  +----+----+  +----+----+  +----+----+  +----+----+           |  |
|  +-------+------------+------------+------------+-----------------+  |
|          +------------+-----+------+------------+                     |
|                             |                                          |
|                             v                                          |
|  +-----------------------------------------------------------------+  |
|  |                   GLOBAL LOAD BALANCER                          |  |
|  |                  (DNS / Anycast / CDN)                          |  |
|  +--------------------------+--------------------------------------+  |
|                             |                                          |
|          +------------------+------------------+                      |
|          |                  |                  |                       |
|          v                  v                  v                       |
|  +---------------------------------------------------------------+   |
|  |                    API GATEWAY CLUSTER                        |   |
|  |                                                               |   |
|  |  +-------------+  +-------------+  +-------------+          |   |
|  |  |   Gateway   |  |   Gateway   |  |   Gateway   |          |   |
|  |  |   Node 1    |  |   Node 2    |  |   Node N    |          |   |
|  |  |             |  |             |  |             |          |   |
|  |  | +---------+ |  | +---------+ |  | +---------+ |          |   |
|  |  | | Plugins | |  | | Plugins | |  | | Plugins | |          |   |
|  |  | +---------+ |  | +---------+ |  | +---------+ |          |   |
|  |  +------+------+  +------+------+  +------+------+          |   |
|  |         |                |                |                  |   |
|  +---------+----------------+----------------+------------------+   |
|            |                |                |                       |
|            +----------------+----------------+                       |
|                             |                                         |
|          +------------------+------------------+                     |
|          |                  |                  |                      |
|          v                  v                  v                      |
|  +-------------+    +-------------+    +-------------+              |
|  |    Redis    |    |  PostgreSQL |    |   Config    |              |
|  |  (Rate Lim) |    |  (Analytics)|    |   Store     |              |
|  +-------------+    +-------------+    +-------------+              |
|                                                                       |
|  =================================================================== |
|                                                                       |
|                         BACKEND SERVICES                              |
|                                                                       |
|  +-------------+  +-------------+  +-------------+  +----------+  |
|  |    User     |  |   Order     |  |   Product   |  |  Payment |  |
|  |   Service   |  |   Service   |  |   Service   |  |  Service |  |
|  +-------------+  +-------------+  +-------------+  +----------+  |
|                                                                       |
+-----------------------------------------------------------------------+
```

## SECTION 1.6: REQUEST FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REQUEST LIFECYCLE THROUGH API GATEWAY                                 |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Client Request                                                 |  |
|  |       |                                                         |  |
|  |       v                                                         |  |
|  |  +---------------------------------------------------------+  |  |
|  |  | 1. TLS TERMINATION                                      |  |  |
|  |  |    Decrypt HTTPS, validate certificate                 |  |  |
|  |  +-------------------------+-------------------------------+  |  |
|  |                            |                                   |  |
|  |                            v                                   |  |
|  |  +---------------------------------------------------------+  |  |
|  |  | 2. IP FILTERING / WAF                                   |  |  |
|  |  |    Block malicious IPs, SQL injection, XSS             |  |  |
|  |  +-------------------------+-------------------------------+  |  |
|  |                            |                                   |  |
|  |                            v                                   |  |
|  |  +---------------------------------------------------------+  |  |
|  |  | 3. AUTHENTICATION                                       |  |  |
|  |  |    Validate API key / JWT / OAuth token                |  |  |
|  |  |    Extract user identity                               |  |  |
|  |  +-------------------------+-------------------------------+  |  |
|  |                            |                                   |  |
|  |                            v                                   |  |
|  |  +---------------------------------------------------------+  |  |
|  |  | 4. RATE LIMITING                                        |  |  |
|  |  |    Check quota, apply throttling                       |  |  |
|  |  |    Return 429 if limit exceeded                        |  |  |
|  |  +-------------------------+-------------------------------+  |  |
|  |                            |                                   |  |
|  |                            v                                   |  |
|  |  +---------------------------------------------------------+  |  |
|  |  | 5. REQUEST VALIDATION                                   |  |  |
|  |  |    Validate headers, body schema                       |  |  |
|  |  +-------------------------+-------------------------------+  |  |
|  |                            |                                   |  |
|  |                            v                                   |  |
|  |  +---------------------------------------------------------+  |  |
|  |  | 6. REQUEST TRANSFORMATION                               |  |  |
|  |  |    Add headers, modify path, transform body            |  |  |
|  |  +-------------------------+-------------------------------+  |  |
|  |                            |                                   |  |
|  |                            v                                   |  |
|  |  +---------------------------------------------------------+  |  |
|  |  | 7. ROUTING                                              |  |  |
|  |  |    Match route, select backend service                 |  |  |
|  |  +-------------------------+-------------------------------+  |  |
|  |                            |                                   |  |
|  |                            v                                   |  |
|  |  +---------------------------------------------------------+  |  |
|  |  | 8. LOAD BALANCING                                       |  |  |
|  |  |    Select healthy backend instance                     |  |  |
|  |  +-------------------------+-------------------------------+  |  |
|  |                            |                                   |  |
|  |                            v                                   |  |
|  |  +---------------------------------------------------------+  |  |
|  |  | 9. PROXY TO BACKEND                                     |  |  |
|  |  |    Forward request, handle timeout/retry               |  |  |
|  |  +-------------------------+-------------------------------+  |  |
|  |                            |                                   |  |
|  |                            v                                   |  |
|  |  +---------------------------------------------------------+  |  |
|  |  | 10. RESPONSE TRANSFORMATION                             |  |  |
|  |  |     Modify headers, transform body                     |  |  |
|  |  +-------------------------+-------------------------------+  |  |
|  |                            |                                   |  |
|  |                            v                                   |  |
|  |  +---------------------------------------------------------+  |  |
|  |  | 11. LOGGING & METRICS                                   |  |  |
|  |  |     Record latency, status, trace ID                   |  |  |
|  |  +-------------------------+-------------------------------+  |  |
|  |                            |                                   |  |
|  |                            v                                   |  |
|  |                     Return to Client                          |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF PART 1

