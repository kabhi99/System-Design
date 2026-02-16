# API GATEWAY - HIGH LEVEL DESIGN
*Part 3: Advanced Features and Patterns*

## SECTION 3.1: CACHING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RESPONSE CACHING AT GATEWAY                                           |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Request                                                        |  |
|  |     |                                                           |  |
|  |     v                                                           |  |
|  |  +---------------------+                                       |  |
|  |  |   Check Cache       |                                       |  |
|  |  |   (Redis/In-memory) |                                       |  |
|  |  +---------+-----------+                                       |  |
|  |            |                                                    |  |
|  |     +------+------+                                            |  |
|  |     |             |                                             |  |
|  |   HIT           MISS                                           |  |
|  |     |             |                                             |  |
|  |     |             v                                             |  |
|  |     |      +-------------+                                     |  |
|  |     |      |   Backend   |                                     |  |
|  |     |      |   Service   |                                     |  |
|  |     |      +------+------+                                     |  |
|  |     |             |                                             |  |
|  |     |             v                                             |  |
|  |     |      Store in Cache                                      |  |
|  |     |      (if cacheable)                                      |  |
|  |     |             |                                             |  |
|  |     +------+------+                                            |  |
|  |            |                                                    |  |
|  |            v                                                    |  |
|  |       Return Response                                          |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CACHE KEY GENERATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT MAKES A GOOD CACHE KEY?                                          |
|                                                                         |
|  Components to consider:                                               |
|  * Method (GET, POST - usually only cache GET)                        |
|  * Path (/api/v1/users/123)                                           |
|  * Query parameters (?sort=name&limit=10)                             |
|  * Headers that affect response (Accept-Language, Authorization)      |
|                                                                         |
|  Example key:                                                           |
|  cache_key = hash(                                                     |
|      method + path + sorted(query_params) + vary_headers              |
|  )                                                                     |
|                                                                         |
|  "GET:/api/v1/users:limit=10:lang=en" > "abc123..."                  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  CACHE-CONTROL HEADER HANDLING                                         |
|                                                                         |
|  Response headers from backend:                                        |
|                                                                         |
|  Cache-Control: public, max-age=3600                                  |
|  > Cache for 1 hour, any client can cache                            |
|                                                                         |
|  Cache-Control: private, max-age=60                                   |
|  > Cache for 1 min, only client cache (not gateway)                  |
|                                                                         |
|  Cache-Control: no-store                                              |
|  > Never cache                                                        |
|                                                                         |
|  Cache-Control: no-cache                                              |
|  > Cache but revalidate every time                                   |
|                                                                         |
|  Vary: Accept-Language, Authorization                                 |
|  > Include these headers in cache key                                |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  CACHE INVALIDATION                                                     |
|                                                                         |
|  1. TTL-based (automatic expiry)                                      |
|  2. Event-based (webhook on data change)                             |
|  3. API-based (explicit purge endpoint)                              |
|  4. Tag-based (purge all keys with tag "user:123")                   |
|                                                                         |
|  POST /internal/cache/purge                                           |
|  { "pattern": "/api/v1/users/*" }                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.2: REQUEST/RESPONSE TRANSFORMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TRANSFORMATION CAPABILITIES                                           |
|                                                                         |
|  1. HEADER MANIPULATION                                                |
|  =========================                                              |
|                                                                         |
|  Add headers:                                                           |
|    X-Request-ID: <generated-uuid>                                     |
|    X-Forwarded-For: <client-ip>                                       |
|    X-User-ID: <extracted-from-jwt>                                    |
|                                                                         |
|  Remove headers:                                                        |
|    Authorization (don't forward sensitive headers)                    |
|    Cookie (strip before forwarding)                                   |
|                                                                         |
|  Modify headers:                                                        |
|    Host: backend-service.internal                                     |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. PATH REWRITING                                                     |
|  ===================                                                    |
|                                                                         |
|  External: GET /api/v1/users/123                                      |
|  Internal: GET /users/123 (strip /api/v1 prefix)                     |
|                                                                         |
|  Config:                                                                |
|  routes:                                                               |
|    - path: /api/v1/users                                              |
|      rewrite: /users                                                  |
|      service: user-service                                            |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. BODY TRANSFORMATION                                                |
|  =======================                                                |
|                                                                         |
|  Request:                                                               |
|  * Add fields (timestamps, request IDs)                              |
|  * Remove fields (strip PII before logging)                          |
|  * Format conversion (JSON > XML)                                    |
|                                                                         |
|  Response:                                                              |
|  * Filter fields (remove internal fields)                            |
|  * Rename fields (snake_case > camelCase)                           |
|  * Wrap response ({ data: response, meta: {...} })                   |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. PROTOCOL TRANSLATION                                               |
|  ==========================                                             |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Client --(REST/JSON)--> Gateway --(gRPC/Protobuf)--> Backend |  |
|  |                                                                 |  |
|  |  Gateway handles:                                              |  |
|  |  * JSON ↔ Protobuf serialization                              |  |
|  |  * HTTP methods ↔ gRPC methods                                |  |
|  |  * HTTP status codes ↔ gRPC status codes                     |  |
|  |                                                                 |  |
|  |  Config:                                                        |  |
|  |  routes:                                                        |  |
|  |    - path: /api/v1/users/{id}                                 |  |
|  |      grpc_service: UserService                                |  |
|  |      grpc_method: GetUser                                     |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.3: API VERSIONING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  API VERSIONING STRATEGIES                                             |
|                                                                         |
|  1. URL PATH VERSIONING                                                |
|  =========================                                              |
|                                                                         |
|  /api/v1/users                                                         |
|  /api/v2/users                                                         |
|                                                                         |
|  Gateway routes:                                                        |
|  /api/v1/* > service-v1                                               |
|  /api/v2/* > service-v2                                               |
|                                                                         |
|  PROS: Clear, cacheable, easy to test                                 |
|  CONS: URL pollution, harder to sunset                                |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. HEADER VERSIONING                                                  |
|  =======================                                                |
|                                                                         |
|  GET /api/users                                                        |
|  X-API-Version: 2                                                      |
|  OR                                                                     |
|  Accept: application/vnd.example.v2+json                              |
|                                                                         |
|  Gateway routes based on header:                                       |
|  X-API-Version: 1 > service-v1                                        |
|  X-API-Version: 2 > service-v2                                        |
|                                                                         |
|  PROS: Clean URLs, easier sunset                                      |
|  CONS: Hidden versioning, caching complexity                         |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. QUERY PARAMETER VERSIONING                                        |
|  ==============================                                         |
|                                                                         |
|  /api/users?version=2                                                  |
|                                                                         |
|  PROS: Easy to use                                                     |
|  CONS: Less RESTful, caching issues                                  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  GATEWAY HANDLES VERSION ROUTING:                                      |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  def route_request(request):                                   |  |
|  |      # Check URL path first                                    |  |
|  |      if '/v2/' in request.path:                               |  |
|  |          return route_to_v2(request)                          |  |
|  |                                                                 |  |
|  |      # Check header                                            |  |
|  |      version = request.headers.get('X-API-Version', '1')      |  |
|  |      if version == '2':                                        |  |
|  |          return route_to_v2(request)                          |  |
|  |                                                                 |  |
|  |      # Default to v1                                           |  |
|  |      return route_to_v1(request)                              |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.4: REQUEST AGGREGATION (BFF Pattern)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BACKEND FOR FRONTEND (BFF) PATTERN                                    |
|                                                                         |
|  Problem: Mobile app needs data from 5 services for one screen        |
|  Without aggregation: 5 round trips from mobile                       |
|  With aggregation: 1 round trip, gateway fetches from 5 services     |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  WITHOUT AGGREGATION:                                          |  |
|  |                                                                 |  |
|  |  Mobile --> User Service                                       |  |
|  |  Mobile --> Order Service                                      |  |
|  |  Mobile --> Product Service                                    |  |
|  |  Mobile --> Review Service                                     |  |
|  |  Mobile --> Recommendation Service                             |  |
|  |                                                                 |  |
|  |  5 round trips! Bad for mobile (latency, battery)             |  |
|  |                                                                 |  |
|  |  ------------------------------------------------------------  |  |
|  |                                                                 |  |
|  |  WITH AGGREGATION:                                             |  |
|  |                                                                 |  |
|  |  Mobile --> Gateway/BFF --+--> User Service                   |  |
|  |                           +--> Order Service                   |  |
|  |                           +--> Product Service                 |  |
|  |                           +--> Review Service                  |  |
|  |                           +--> Recommendation Service          |  |
|  |                                                                 |  |
|  |  1 round trip! Gateway aggregates responses                   |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  AGGREGATION ENDPOINT:                                                  |
|                                                                         |
|  GET /api/mobile/home-screen?user_id=123                              |
|                                                                         |
|  Response:                                                              |
|  {                                                                     |
|    "user": { ... from User Service ... },                             |
|    "recent_orders": [ ... from Order Service ... ],                   |
|    "recommended_products": [ ... from Recommendation ... ],          |
|    "notifications": [ ... from Notification ... ]                    |
|  }                                                                     |
|                                                                         |
|  Gateway fetches all in parallel, aggregates, returns single response|
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.5: OBSERVABILITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LOGGING                                                               |
|  =======                                                                |
|                                                                         |
|  Access log for every request:                                        |
|  {                                                                     |
|    "timestamp": "2024-01-01T00:00:00Z",                               |
|    "request_id": "abc-123-xyz",                                       |
|    "trace_id": "trace-456",                                           |
|    "client_ip": "1.2.3.4",                                            |
|    "method": "GET",                                                    |
|    "path": "/api/v1/users/123",                                       |
|    "status": 200,                                                      |
|    "latency_ms": 45,                                                   |
|    "upstream_latency_ms": 40,                                         |
|    "bytes_sent": 1234,                                                |
|    "user_agent": "Mozilla/5.0...",                                   |
|    "api_key": "key_xxx (masked)",                                    |
|    "user_id": "user_123",                                            |
|    "backend_service": "user-service",                                |
|    "backend_host": "10.0.0.5:8080"                                   |
|  }                                                                     |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  METRICS                                                               |
|  ========                                                               |
|                                                                         |
|  Key metrics to expose (Prometheus format):                           |
|                                                                         |
|  # Request rate                                                        |
|  http_requests_total{method, path, status}                           |
|                                                                         |
|  # Latency histogram                                                   |
|  http_request_duration_seconds{method, path, le}                     |
|                                                                         |
|  # Active connections                                                  |
|  http_connections_active                                              |
|                                                                         |
|  # Rate limiting                                                       |
|  rate_limit_requests_total{decision="allow|deny"}                    |
|                                                                         |
|  # Circuit breaker                                                     |
|  circuit_breaker_state{service, state="closed|open|half_open"}       |
|                                                                         |
|  # Backend health                                                      |
|  backend_health{service, instance, status="healthy|unhealthy"}       |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  DISTRIBUTED TRACING                                                   |
|  ====================                                                   |
|                                                                         |
|  Gateway injects/propagates trace headers:                            |
|                                                                         |
|  Incoming request (no trace):                                         |
|  > Generate: X-Request-ID: abc-123                                   |
|  > Generate: traceparent: 00-trace123-span456-01                     |
|                                                                         |
|  Incoming request (with trace):                                       |
|  > Propagate existing traceparent                                    |
|  > Create child span for gateway processing                          |
|                                                                         |
|  Forward to backend with headers:                                     |
|  X-Request-ID: abc-123                                                |
|  traceparent: 00-trace123-span789-01                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.6: SECURITY FEATURES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SECURITY AT THE GATEWAY                                               |
|                                                                         |
|  1. TLS TERMINATION                                                    |
|  =====================                                                  |
|                                                                         |
|  Client --(HTTPS)--> Gateway --(HTTP/mTLS)--> Backend                 |
|                                                                         |
|  * Terminate TLS at gateway                                           |
|  * Use HTTP internally (faster) or mTLS (more secure)                |
|  * Centralized certificate management                                 |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. MUTUAL TLS (mTLS)                                                  |
|  =====================                                                  |
|                                                                         |
|  Both client and server verify certificates                           |
|  Used for: Service-to-service, B2B APIs                              |
|                                                                         |
|  Config:                                                                |
|  tls:                                                                  |
|    client_certificate: required                                       |
|    ca_certificates:                                                   |
|      - /certs/partner-ca.pem                                         |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. WAF (Web Application Firewall)                                    |
|  ==================================                                     |
|                                                                         |
|  Block common attacks:                                                 |
|  * SQL Injection: ' OR '1'='1                                        |
|  * XSS: <script>alert('xss')</script>                                |
|  * Path traversal: ../../etc/passwd                                  |
|  * Request size limits                                                |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. IP FILTERING                                                       |
|  =================                                                      |
|                                                                         |
|  Whitelist:                                                            |
|  ip_whitelist:                                                        |
|    - 10.0.0.0/8        # Internal                                    |
|    - 203.0.113.50      # Partner IP                                  |
|                                                                         |
|  Blacklist:                                                            |
|  ip_blacklist:                                                        |
|    - 198.51.100.0/24   # Known bad actors                           |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  5. CORS (Cross-Origin Resource Sharing)                              |
|  =======================================                                |
|                                                                         |
|  cors:                                                                  |
|    origins:                                                           |
|      - https://app.example.com                                       |
|      - https://admin.example.com                                     |
|    methods: [GET, POST, PUT, DELETE]                                 |
|    headers: [Authorization, Content-Type]                            |
|    credentials: true                                                 |
|    max_age: 3600                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.7: DEPLOYMENT AND HIGH AVAILABILITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HIGH AVAILABILITY ARCHITECTURE                                        |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |                        DNS (Route 53)                          |  |
|  |                     Health-check routing                       |  |
|  |                            |                                    |  |
|  |         +------------------+------------------+                |  |
|  |         |                  |                  |                 |  |
|  |         v                  v                  v                 |  |
|  |  +-----------+      +-----------+      +-----------+          |  |
|  |  |   AZ-1    |      |   AZ-2    |      |   AZ-3    |          |  |
|  |  |           |      |           |      |           |          |  |
|  |  |  +-----+  |      |  +-----+  |      |  +-----+  |          |  |
|  |  |  | NLB |  |      |  | NLB |  |      |  | NLB |  |          |  |
|  |  |  +--+--+  |      |  +--+--+  |      |  +--+--+  |          |  |
|  |  |     |     |      |     |     |      |     |     |          |  |
|  |  |  +--v--+  |      |  +--v--+  |      |  +--v--+  |          |  |
|  |  |  | GW  |  |      |  | GW  |  |      |  | GW  |  |          |  |
|  |  |  | GW  |  |      |  | GW  |  |      |  | GW  |  |          |  |
|  |  |  | GW  |  |      |  | GW  |  |      |  | GW  |  |          |  |
|  |  |  +-----+  |      |  +-----+  |      |  +-----+  |          |  |
|  |  |           |      |           |      |           |          |  |
|  |  +-----------+      +-----------+      +-----------+          |  |
|  |                                                                 |  |
|  |  +---------------------------------------------------------+  |  |
|  |  |                    Redis Cluster                        |  |  |
|  |  |              (Rate limiting, caching)                   |  |  |
|  |  |         [Master]  [Replica]  [Replica]                 |  |  |
|  |  +---------------------------------------------------------+  |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  KEY PRINCIPLES:                                                        |
|  * Stateless gateway nodes (share nothing)                           |
|  * External state in Redis cluster                                   |
|  * Multi-AZ for availability                                         |
|  * Auto-scaling based on CPU/connections                            |
|  * Graceful shutdown (drain connections)                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CONFIGURATION MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HOT RELOAD (No restart for config changes)                           |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Admin API       Config Store        Gateway Nodes             |  |
|  |      |                |                    |                    |  |
|  |      |--1. Update --->|                    |                    |  |
|  |      |   route        |                    |                    |  |
|  |      |                |--2. Notify ------->|                    |  |
|  |      |                |   (watch/pubsub)   |                    |  |
|  |      |                |                    |                    |  |
|  |      |                |                    |--3. Reload config  |  |
|  |      |                |                    |   (atomic swap)    |  |
|  |      |                |                    |                    |  |
|  |                                                                 |  |
|  |  Config Store Options:                                         |  |
|  |  * PostgreSQL (Kong)                                          |  |
|  |  * etcd (Envoy)                                               |  |
|  |  * Consul                                                     |  |
|  |  * File (watched for changes)                                 |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  DECLARATIVE CONFIG (GitOps):                                          |
|  * Config in Git repository                                          |
|  * CI/CD pipeline validates and deploys                             |
|  * Rollback = git revert                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.8: INTERVIEW DISCUSSION POINTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMMON INTERVIEW QUESTIONS                                            |
|                                                                         |
|  Q: Why use an API Gateway instead of letting clients talk directly?  |
|  A: Cross-cutting concerns centralization                             |
|     * Single place for auth, rate limiting, logging                  |
|     * Clients don't need to know service topology                    |
|     * Protocol translation (REST ↔ gRPC)                            |
|     * Response aggregation (reduce round trips)                      |
|                                                                         |
|  Q: How do you prevent the gateway from becoming a bottleneck?        |
|  A: Stateless design + horizontal scaling                            |
|     * No shared state in gateway nodes                               |
|     * External state in Redis cluster                                |
|     * Auto-scaling based on traffic                                  |
|     * Keep processing minimal (offload to backends)                  |
|                                                                         |
|  Q: How do you handle gateway failures?                               |
|  A: Multi-layer redundancy                                            |
|     * Multiple gateway nodes behind load balancer                    |
|     * Multiple AZs                                                    |
|     * Health checks remove unhealthy nodes                          |
|     * Circuit breakers prevent cascade failures                     |
|                                                                         |
|  Q: How do you implement rate limiting across multiple nodes?         |
|  A: Centralized counter (Redis) + local approximation                |
|     * Redis for accurate global count                                |
|     * Local cache to reduce Redis calls                              |
|     * Sync periodically (slight over-limit acceptable)              |
|                                                                         |
|  Q: Gateway vs Service Mesh - what's the difference?                  |
|  A: Different scopes                                                   |
|     * Gateway: North-South traffic (external > services)             |
|     * Service Mesh: East-West traffic (service > service)           |
|     * Often used together (Gateway + Istio)                         |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  KEY TRADEOFFS                                                         |
|                                                                         |
|  1. THIN vs FAT GATEWAY                                               |
|     Thin: Just routing, auth (lower latency)                        |
|     Fat: Aggregation, transformation (more features)                |
|     > Start thin, add features as needed                            |
|                                                                         |
|  2. CENTRALIZED vs DISTRIBUTED RATE LIMITING                          |
|     Centralized: Accurate but Redis dependency                      |
|     Distributed: Approximate but faster                             |
|     > Hybrid: Local cache + periodic sync                           |
|                                                                         |
|  3. INLINE vs ASYNC PROCESSING                                        |
|     Inline: Auth, routing (must be fast)                            |
|     Async: Logging, analytics (can be deferred)                     |
|     > Async for non-critical path                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF API GATEWAY HLD

