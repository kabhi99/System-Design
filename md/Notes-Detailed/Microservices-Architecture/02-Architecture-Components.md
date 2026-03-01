# MICROSERVICES ARCHITECTURE - HIGH LEVEL DESIGN

CHAPTER 2: ARCHITECTURE COMPONENTS

## FULL HIGH-LEVEL DESIGN DIAGRAM

```
+----------------------------------------------------------------------------------+
|                                                                                  |
|                    MICROSERVICES ARCHITECTURE - COMPLETE HLD                     |
|                                                                                  |
+----------------------------------------------------------------------------------+
+----------------------------------------------------------------------------------+
|      CLIENTS                                                                     |
| (Web/Mobile/Partner)                                                             |
+----------+-----------------------------------------------------------------------+
                                                                                   |
| HTTPS                                                                             
 v                                                                                  
+----------------------------------------------------------------------------------+
|                                                                                  |
|                              EDGE LAYER                                          |
|                                                                                  |
|  +-----------------------------------------------------------------------------+ |
|  |                                                                             | |
|  |                         CDN (CloudFront / Akamai)                           | |
|  |                                                                             | |
|  |   * Static assets (JS, CSS, images)                                         | |
|  |   * API response caching (for GET requests)                                 | |
|  |   * DDoS protection                                                         | |
|  |   * TLS termination                                                         | |
|  |                                                                             | |
|  +----------------------------------+------------------------------------------+ |
|                                     |                                            |
|  +----------------------------------v------------------------------------------+ |
|  |                                                                             | |
|  |                         GLOBAL LOAD BALANCER                                | |
|  |                                                                             | |
|  |   * GeoDNS routing to nearest region                                        | |
|  |   * Health-based failover                                                   | |
|  |                                                                             | |
|  +----------------------------------+------------------------------------------+ |
|                                     |                                            |
+-------------------------------------+--------------------------------------------+
                                                                                   |
+-----------------+----------------------------------------------------------------+
|                 |                                                                |
 v                 v                 v                                              
+---------------+ +---------------+ +----------------------------------------------+
|   Region US   | |   Region EU   | |  Region Asia                                 |
+-------+-------+ +---------------+ +----------------------------------------------+
                                                                                   |
 v                                                                                  
+----------------------------------------------------------------------------------+
|                                                                                  |
|                            API GATEWAY LAYER                                     |
|                                                                                  |
|  +-----------------------------------------------------------------------------+ |
|  |                                                                             | |
|  |                    API GATEWAY (Kong / AWS API Gateway)                     | |
|  |                                                                             | |
|  |   +----------------------------------------------------------------------+  | |
|  |   |                                                                      |  | |
|  |   |  RESPONSIBILITIES:                                                   |  | |
|  |   |                                                                      |  | |
|  |   |  * Request routing to backend services                               |  | |
|  |   |  * Authentication / JWT validation                                   |  | |
|  |   |  * Rate limiting                                                     |  | |
|  |   |  * Request/Response transformation                                   |  | |
|  |   |  * API versioning                                                    |  | |
|  |   |  * Request logging and metrics                                       |  | |
|  |   |  * SSL termination                                                   |  | |
|  |   |                                                                      |  | |
|  |   +----------------------------------------------------------------------+  | |
|  |                                                                             | |
|  +----------------------------------+------------------------------------------+ |
|                                     |                                            |
+-------------------------------------+--------------------------------------------+
                                                                                   |
| Routes requests                                                                   
 v                                                                                  
+----------------------------------------------------------------------------------+
|                                                                                  |
|                          SERVICE MESH / COMMUNICATION                            |
|                                                                                  |
|  +-----------------------------------------------------------------------------+ |
|  |                                                                             | |
|  |              SERVICE DISCOVERY (Consul / Eureka / K8s DNS)                  | |
|  |                                                                             | |
|  |   * Service registration and discovery                                      | |
|  |   * Health checking                                                         | |
|  |   * Load balancing between service instances                                | |
|  |                                                                             | |
|  +-----------------------------------------------------------------------------+ |
|                                                                                  |
|  +-----------------------------------------------------------------------------+ |
|  |                                                                             | |
|  |              SERVICE MESH SIDECAR (Istio / Linkerd) [Optional]              | |
|  |                                                                             | |
|  |   * mTLS between services                                                   | |
|  |   * Traffic management (retries, timeouts, circuit breaking)                | |
|  |   * Observability (distributed tracing)                                     | |
|  |                                                                             | |
|  +-----------------------------------------------------------------------------+ |
|                                                                                  |
+-------------------------------------+--------------------------------------------+
                                                                                   |
 v                                                                                  
+----------------------------------------------------------------------------------+
|                                                                                  |
|                           MICROSERVICES LAYER                                    |
|                                                                                  |
|  +---------------------------------------------------------------------------+   |
|  |                                                                           |   |
|  |  +-------------+  +-------------+  +-------------+  +----------------+    |   |
|  |  |    User     |  |   Product   |  |    Order    |  |   Payment      |    |   |
|  |  |   Service   |  |   Service   |  |   Service   |  |   Service      |    |   |
|  |  |             |  |             |  |             |  |                |    |   |
|  |  | * Auth      |  | * Catalog   |  | * Cart      |  | * Process      |    |   |
|  |  | * Profile   |  | * Search    |  | * Checkout  |  | * Refund       |    |   |
|  |  | * Prefs     |  | * Reviews   |  | * History   |  | * Wallet       |    |   |
|  |  +------+------+  +------+------+  +------+------+  +------+---------+    |   |
|  |         |                |                |                |              |   |
|  |         v                v                v                v              |   |
|  |  +-------------+  +-------------+  +-------------+  +----------------+    |   |
|  |  |  User DB    |  | Product DB  |  |  Order DB   |  | Payment DB     |    |   |
|  |  | (Postgres)  |  |(Elasticsearch)| | (MongoDB)  |  | (Postgres)     |    |   |
|  |  +-------------+  +-------------+  +-------------+  +----------------+    |   |
|  |                                                                           |   |
|  |  +-------------+  +-------------+  +-------------+  +----------------+    |   |
|  |  |  Inventory  |  |  Shipping   |  |Notification |  |   Search       |    |   |
|  |  |   Service   |  |   Service   |  |   Service   |  |   Service      |    |   |
|  |  |             |  |             |  |             |  |                |    |   |
|  |  | * Stock     |  | * Tracking  |  | * Email     |  | * Index        |    |   |
|  |  | * Reserve   |  | * Carriers  |  | * SMS       |  | * Query        |    |   |
|  |  | * Warehouse |  | * Routes    |  | * Push      |  | * Suggest      |    |   |
|  |  +------+------+  +------+------+  +------+------+  +------+---------+    |   |
|  |         |                |                |                |              |   |
|  |         v                v                v                v              |   |
|  |  +-------------+  +-------------+  +-------------+  +----------------+    |   |
|  |  |Inventory DB |  | Shipping DB |  |   Redis     |  |Elasticsearch   |    |   |
|  |  | (Postgres)  |  | (Postgres)  |  |  (Queue)    |  |                |    |   |
|  |  +-------------+  +-------------+  +-------------+  +----------------+    |   |
|  |                                                                           |   |
|  +---------------------------------------------------------------------------+   |
|                                                                                  |
|         |                    |                    |                              |
|         | Produce events     |                    |                              |
|         v                    v                    v                              |
|  +-----------------------------------------------------------------------------+ |
|  |                                                                             | |
|  |                    MESSAGE BROKER (Kafka / RabbitMQ)                        | |
|  |                                                                             | |
|  |   Topics:                                                                   | |
|  |   * user.events (registered, updated, deleted)                              | |
|  |   * order.events (created, confirmed, shipped, delivered)                   | |
|  |   * inventory.events (reserved, released, low-stock)                        | |
|  |   * payment.events (succeeded, failed, refunded)                            | |
|  |                                                                             | |
|  +-----------------------------------------------------------------------------+ |
|                                                                                  |
+----------------------------------------------------------------------------------+
+----------------------------------------------------------------------------------+
|                                                                                  |
|                          CROSS-CUTTING SERVICES                                  |
|                                                                                  |
|  +---------------------------------------------------------------------------+   |
|  |                                                                           |   |
|  |  +-----------------+  +-----------------+  +-----------------+            |   |
|  |  |   Config        |  |   Secrets       |  |   Auth          |            |   |
|  |  |   Service       |  |   Manager       |  |   Service       |            |   |
|  |  |                 |  |                 |  |                 |            |   |
|  |  | * Feature flags |  | * Vault/AWS SM  |  | * OAuth2/OIDC   |            |   |
|  |  | * Dynamic config|  | * API keys      |  | * JWT issuing   |            |   |
|  |  | * Per-env config|  | * DB passwords  |  | * RBAC          |            |   |
|  |  |                 |  | * Certificates  |  |                 |            |   |
|  |  +-----------------+  +-----------------+  +-----------------+            |   |
|  |                                                                           |   |
|  +---------------------------------------------------------------------------+   |
|                                                                                  |
+----------------------------------------------------------------------------------+
+----------------------------------------------------------------------------------+
|                                                                                  |
|                          OBSERVABILITY LAYER                                     |
|                                                                                  |
|  +---------------------------------------------------------------------------+   |
|  |                                                                           |   |
|  |  +-----------------+  +-----------------+  +-----------------+            |   |
|  |  |    Metrics      |  |    Logging      |  |   Tracing       |            |   |
|  |  |                 |  |                 |  |                 |            |   |
|  |  | * Prometheus    |  | * ELK Stack     |  | * Jaeger        |            |   |
|  |  | * Grafana       |  | * Fluentd       |  | * Zipkin        |            |   |
|  |  | * Alerts        |  | * Kibana        |  | * OpenTelemetry |            |   |
|  |  |                 |  |                 |  |                 |            |   |
|  |  +-----------------+  +-----------------+  +-----------------+            |   |
|  |                                                                           |   |
|  +---------------------------------------------------------------------------+   |
|                                                                                  |
+----------------------------------------------------------------------------------+
```

## SECTION 1: API GATEWAY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS AN API GATEWAY?                                                |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Single entry point for all client requests to backend            |  |
|  |  microservices. Acts as a reverse proxy.                          |  |
|  |                                                                   |  |
|  |  WITHOUT API GATEWAY:                                             |  |
|  |                                                                   |  |
|  |  Client must know about all services:                             |  |
|  |  * Call user-service.example.com                                  |  |
|  |  * Call order-service.example.com                                 |  |
|  |  * Call payment-service.example.com                               |  |
|  |  > Complex, coupled, security nightmare                           |  |
|  |                                                                   |  |
|  |  WITH API GATEWAY:                                                |  |
|  |                                                                   |  |
|  |  Client calls single endpoint:                                    |  |
|  |  * api.example.com/users                                          |  |
|  |  * api.example.com/orders                                         |  |
|  |  * api.example.com/payments                                       |  |
|  |  > Gateway routes to appropriate service                          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
+-------------------------------------------------------------------------+
|                                                                         |
|  API GATEWAY RESPONSIBILITIES                                           |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. REQUEST ROUTING                                               |  |
|  |     * Route based on URL path, method, headers                    |  |
|  |     * /api/v1/users > User Service                                |  |
|  |     * /api/v1/orders > Order Service                              |  |
|  |                                                                   |  |
|  |  2. AUTHENTICATION & AUTHORIZATION                                |  |
|  |     * Validate JWT tokens                                         |  |
|  |     * Check API keys                                              |  |
|  |     * Pass user context to services                               |  |
|  |                                                                   |  |
|  |  3. RATE LIMITING                                                 |  |
|  |     * Per user/API key limits                                     |  |
|  |     * Prevent abuse and DDoS                                      |  |
|  |                                                                   |  |
|  |  4. REQUEST/RESPONSE TRANSFORMATION                               |  |
|  |     * Add/remove headers                                          |  |
|  |     * Transform payloads                                          |  |
|  |     * Protocol translation (REST - gRPC)                          |  |
|  |                                                                   |  |
|  |  5. LOAD BALANCING                                                |  |
|  |     * Distribute requests across service instances                |  |
|  |     * Health check integration                                    |  |
|  |                                                                   |  |
|  |  6. CACHING                                                       |  |
|  |     * Cache responses for GET requests                            |  |
|  |     * Reduce backend load                                         |  |
|  |                                                                   |  |
|  |  7. CIRCUIT BREAKING                                              |  |
|  |     * Stop sending to failing services                            |  |
|  |     * Return fallback responses                                   |  |
|  |                                                                   |  |
|  |  8. LOGGING & MONITORING                                          |  |
|  |     * Request/response logging                                    |  |
|  |     * Metrics collection                                          |  |
|  |     * Distributed tracing context                                 |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
+-------------------------------------------------------------------------+
|                                                                         |
|  API GATEWAY PATTERNS                                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  PATTERN 1: SINGLE GATEWAY                                        |  |
|  |                                                                   |  |
|  |  All clients (web, mobile, partner) use same gateway              |  |
|  |                                                                   |  |
|  |  +------------------------------------------+                     |  |
|  |  |           ALL CLIENTS                    |                     |  |
|  |  +--------------------+---------------------+                     |  |
|  |                       |                                           |  |
|  |                       v                                           |  |
|  |           +-----------------------+                               |  |
|  |           |    API GATEWAY        |                               |  |
|  |           +-----------------------+                               |  |
|  |                       |                                           |  |
|  |           +-----------+-----------+                               |  |
|  |           v           v           v                               |  |
|  |       Services    Services    Services                            |  |
|  |                                                                   |  |
|  |  Pros: Simple, single point of management                         |  |
|  |  Cons: Becomes bottleneck, one-size-fits-all                      |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  PATTERN 2: BACKEND FOR FRONTEND (BFF)                            |  |
|  |                                                                   |  |
|  |  Separate gateway for each client type                            |  |
|  |                                                                   |  |
|  |  +---------+    +---------+    +---------+                        |  |
|  |  |   Web   |    | Mobile  |    | Partner |                        |  |
|  |  |  Client |    |  App    |    |   API   |                        |  |
|  |  +----+----+    +----+----+    +----+----+                        |  |
|  |       |              |              |                             |  |
|  |       v              v              v                             |  |
|  |  +---------+    +---------+    +---------+                        |  |
|  |  |  Web    |    | Mobile  |    | Partner |                        |  |
|  |  |   BFF   |    |   BFF   |    |   BFF   |                        |  |
|  |  +----+----+    +----+----+    +----+----+                        |  |
|  |       |              |              |                             |  |
|  |       +--------------+--------------+                             |  |
|  |                      v                                            |  |
|  |               Microservices                                       |  |
|  |                                                                   |  |
|  |  Benefits:                                                        |  |
|  |  * Web BFF: Aggregates data for rich web UI                       |  |
|  |  * Mobile BFF: Optimizes for bandwidth (smaller payloads)         |  |
|  |  * Partner BFF: Stricter rate limits, different auth              |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
+-------------------------------------------------------------------------+
|                                                                         |
|  API GATEWAY TECHNOLOGIES                                               |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  TECHNOLOGY        BEST FOR                 KEY FEATURES          |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  Kong              Self-hosted,             Plugins, Lua          |  |
|  |                    Kubernetes               extensible            |  |
|  |                                                                   |  |
|  |  AWS API Gateway   AWS ecosystem            Serverless, Lambda    |  |
|  |                                             integration           |  |
|  |                                                                   |  |
|  |  NGINX             High performance,        Low latency,          |  |
|  |                    Simple routing           battle-tested         |  |
|  |                                                                   |  |
|  |  Envoy             Service mesh,            gRPC native,          |  |
|  |                    Cloud-native             observability         |  |
|  |                                                                   |  |
|  |  Traefik           Kubernetes,              Auto-discovery,       |  |
|  |                    Docker                   simple config         |  |
|  |                                                                   |  |
|  |  Apigee            Enterprise,              Analytics,            |  |
|  |                    API monetization         developer portal      |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: SERVICE DISCOVERY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY SERVICE DISCOVERY?                                                 |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  PROBLEM:                                                         |  |
|  |                                                                   |  |
|  |  In microservices, service instances are dynamic:                 |  |
|  |  * Instances scale up/down based on load                          |  |
|  |  * Instances can fail and be replaced                             |  |
|  |  * Containers get new IPs on restart                              |  |
|  |                                                                   |  |
|  |  How does Service A find Service B's current address?             |  |
|  |                                                                   |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  SOLUTION: Service Discovery                                      |  |
|  |                                                                   |  |
|  |  A registry that tracks:                                          |  |
|  |  * Which services exist                                           |  |
|  |  * Where their instances are running (IP:port)                    |  |
|  |  * Health status of each instance                                 |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICE DISCOVERY PATTERNS                                             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  PATTERN 1: CLIENT-SIDE DISCOVERY                                 |  |
|  |                                                                   |  |
|  |  +---------------+         +-----------------------+              |  |
|  |  |   Service A   |         |   Service Registry    |              |  |
|  |  |   (Client)    |         |   (Consul/Eureka)     |              |  |
|  |  +-------+-------+         +-----------+-----------+              |  |
|  |          |                             |                          |  |
|  |          | 1. Query: "Where is        |                           |  |
|  |          |    Order Service?"         |                           |  |
|  |          | -------------------------->|                           |  |
|  |          |                             |                          |  |
|  |          | 2. Response:               |                           |  |
|  |          |    [10.0.1.5:8080,         |                           |  |
|  |          |     10.0.1.6:8080]         |                           |  |
|  |          | <--------------------------|                           |  |
|  |          |                                                        |  |
|  |          | 3. Client picks one (load balancing logic)             |  |
|  |          |                                                        |  |
|  |          | 4. Direct call to chosen instance                      |  |
|  |          | ---------------------------------->                    |  |
|  |                                            Order Service          |  |
|  |                                            Instance               |  |
|  |                                                                   |  |
|  |  Pros: Client can do smart load balancing, no extra hop           |  |
|  |  Cons: Client needs discovery logic, language-specific            |  |
|  |                                                                   |  |
|  |  Examples: Netflix Eureka + Ribbon, Consul + client library       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  PATTERN 2: SERVER-SIDE DISCOVERY                                 |  |
|  |                                                                   |  |
|  |  +---------------+      +---------------+      +-------------+    |  |
|  |  |   Service A   |      | Load Balancer |      |  Registry   |    |  |
|  |  |   (Client)    |      | (Router)      |      |             |    |  |
|  |  +-------+-------+      +-------+-------+      +------+------+    |  |
|  |          |                      |                     |           |  |
|  |          | 1. Request to        |                     |           |  |
|  |          |    "order-service"   |                     |           |  |
|  |          | --------------------->                     |           |  |
|  |          |                      |                     |           |  |
|  |          |                      | 2. Lookup instances |           |  |
|  |          |                      | -------------------->           |  |
|  |          |                      |                     |           |  |
|  |          |                      | 3. Returns list    |            |  |
|  |          |                      | <--------------------           |  |
|  |          |                      |                                 |  |
|  |          |                      | 4. Routes to instance           |  |
|  |          |                      | ------------------------>       |  |
|  |          |                                     Order Service      |  |
|  |                                                                   |  |
|  |  Pros: Client is simple, discovery logic centralized              |  |
|  |  Cons: Extra network hop, load balancer is bottleneck             |  |
|  |                                                                   |  |
|  |  Examples: Kubernetes DNS + Service, AWS ELB + Service Discovery  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICE REGISTRATION                                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  SELF-REGISTRATION (Service registers itself)                     |  |
|  |                                                                   |  |
|  |  Service starts up:                                               |  |
|  |  1. Connect to registry                                           |  |
|  |  2. Register: "I am order-service at 10.0.1.5:8080"               |  |
|  |  3. Send heartbeats every N seconds                               |  |
|  |  4. On shutdown: Deregister                                       |  |
|  |                                                                   |  |
|  |  If heartbeat stops > Registry removes instance                   |  |
|  |                                                                   |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  THIRD-PARTY REGISTRATION (External process registers)            |  |
|  |                                                                   |  |
|  |  In Kubernetes:                                                   |  |
|  |  1. Pod starts                                                    |  |
|  |  2. Kubernetes control plane registers pod IP with Service        |  |
|  |  3. Service gets updated endpoints                                |  |
|  |  4. kube-proxy or CoreDNS routes traffic                          |  |
|  |                                                                   |  |
|  |  Service doesn't need to know about discovery!                    |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICE DISCOVERY TECHNOLOGIES                                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  TECHNOLOGY        TYPE               KEY FEATURES                |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  Consul            Dedicated          Health checks, KV store,    |  |
|  |                    registry           Multi-DC, Service mesh      |  |
|  |                                                                   |  |
|  |  Eureka            Dedicated          Netflix OSS, Java focus,    |  |
|  |                    registry           Self-preservation mode      |  |
|  |                                                                   |  |
|  |  etcd              KV store           Kubernetes backend,         |  |
|  |                    + discovery        Strong consistency          |  |
|  |                                                                   |  |
|  |  ZooKeeper         Coordination       Leader election,            |  |
|  |                    + discovery        Distributed locks           |  |
|  |                                                                   |  |
|  |  Kubernetes        Built-in           CoreDNS, Services,          |  |
|  |  DNS               (K8s native)       No external dependency      |  |
|  |                                                                   |  |
|  |  AWS Cloud Map     Managed            AWS native, ECS/EKS         |  |
|  |                    (AWS native)       integration                 |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3: CONFIGURATION MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONFIGURATION CHALLENGES IN MICROSERVICES                              |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  CHALLENGES:                                                      |  |
|  |                                                                   |  |
|  |  * 50 services x 4 environments = 200 config files                |  |
|  |  * Config changes require redeployment (bad)                      |  |
|  |  * Secrets mixed with config (security risk)                      |  |
|  |  * Hard to audit who changed what                                 |  |
|  |  * Inconsistent config across services                            |  |
|  |                                                                   |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  SOLUTION: Externalized Configuration                             |  |
|  |                                                                   |  |
|  |  * Store config outside the service code                          |  |
|  |  * Central config server or store                                 |  |
|  |  * Services fetch config at startup or runtime                    |  |
|  |  * Secrets managed separately                                     |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
+-------------------------------------------------------------------------+
|                                                                         |
|  CONFIGURATION HIERARCHY                                                |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Priority (highest to lowest):                                    |  |
|  |                                                                   |  |
|  |  1. ENVIRONMENT VARIABLES (container/pod level)                   |  |
|  |     * Secrets, per-instance overrides                             |  |
|  |                                                                   |  |
|  |  2. COMMAND LINE ARGUMENTS                                        |  |
|  |     * Runtime overrides                                           |  |
|  |                                                                   |  |
|  |  3. CONFIG SERVER (Spring Cloud Config, Consul KV)                |  |
|  |     * Environment-specific config (dev/staging/prod)              |  |
|  |                                                                   |  |
|  |  4. APPLICATION CONFIG FILE (application.yml)                     |  |
|  |     * Service-specific defaults                                   |  |
|  |                                                                   |  |
|  |  5. DEFAULT VALUES IN CODE                                        |  |
|  |     * Hardcoded fallbacks                                         |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
+-------------------------------------------------------------------------+
|                                                                         |
|  SECRETS MANAGEMENT                                                     |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  NEVER DO:                                                        |  |
|  |  * Store secrets in code or config files                          |  |
|  |  * Commit secrets to Git                                          |  |
|  |  * Pass secrets as command line args (visible in ps)              |  |
|  |                                                                   |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  SECRETS MANAGEMENT TOOLS:                                        |  |
|  |                                                                   |  |
|  |  HashiCorp Vault                                                  |  |
|  |  * Dynamic secrets (short-lived credentials)                      |  |
|  |  * Encryption as a service                                        |  |
|  |  * Audit logging                                                  |  |
|  |  * Secret rotation                                                |  |
|  |                                                                   |  |
|  |  AWS Secrets Manager / Parameter Store                            |  |
|  |  * AWS native                                                     |  |
|  |  * Automatic rotation                                             |  |
|  |  * IAM integration                                                |  |
|  |                                                                   |  |
|  |  Kubernetes Secrets                                               |  |
|  |  * Native K8s (but base64, not encrypted by default)              |  |
|  |  * Use with Sealed Secrets or External Secrets Operator           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
+-------------------------------------------------------------------------+
|                                                                         |
|  FEATURE FLAGS                                                          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Toggle features without code deployment                          |  |
|  |                                                                   |  |
|  |  USE CASES:                                                       |  |
|  |  * Gradual rollout (10% > 50% > 100% of users)                    |  |
|  |  * A/B testing                                                    |  |
|  |  * Kill switch for problematic features                           |  |
|  |  * Beta features for specific users                               |  |
|  |                                                                   |  |
|  |  TOOLS:                                                           |  |
|  |  * LaunchDarkly (SaaS)                                            |  |
|  |  * Unleash (open source)                                          |  |
|  |  * ConfigCat                                                      |  |
|  |  * Custom (Consul KV, Redis)                                      |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: LOAD BALANCING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LOAD BALANCING IN MICROSERVICES                                        |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  LAYER 4 (Transport) vs LAYER 7 (Application)                     |  |
|  |                                                                   |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  LAYER 4 (TCP/UDP):                                               |  |
|  |  * Routes based on IP and port                                    |  |
|  |  * No inspection of payload                                       |  |
|  |  * Very fast, low latency                                         |  |
|  |  * Use for: Database connections, internal services               |  |
|  |                                                                   |  |
|  |  LAYER 7 (HTTP/gRPC):                                             |  |
|  |  * Routes based on URL, headers, cookies                          |  |
|  |  * Can do content-based routing                                   |  |
|  |  * SSL termination                                                |  |
|  |  * Use for: API gateway, user-facing traffic                      |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  LOAD BALANCING ALGORITHMS                                        |  |
|  |                                                                   |  |
|  |  ROUND ROBIN                                                      |  |
|  |  * Requests distributed evenly in rotation                        |  |
|  |  * Simple, works when all instances equal                         |  |
|  |                                                                   |  |
|  |  LEAST CONNECTIONS                                                |  |
|  |  * Route to instance with fewest active connections               |  |
|  |  * Good when request duration varies                              |  |
|  |                                                                   |  |
|  |  WEIGHTED                                                         |  |
|  |  * Some instances get more traffic                                |  |
|  |  * Use for canary deployments or mixed hardware                   |  |
|  |                                                                   |  |
|  |  IP HASH / CONSISTENT HASHING                                     |  |
|  |  * Same client always goes to same server                         |  |
|  |  * Good for session affinity                                      |  |
|  |                                                                   |  |
|  |  LEAST RESPONSE TIME                                              |  |
|  |  * Route to fastest responding instance                           |  |
|  |  * Requires health monitoring                                     |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

END OF CHAPTER 2
