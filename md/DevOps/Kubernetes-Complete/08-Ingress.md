# KUBERNETES INGRESS
*Chapter 8: HTTP Routing and External Access*

Ingress provides HTTP/HTTPS routing to services, including load
balancing, SSL termination, and name-based virtual hosting.

## SECTION 8.1: INGRESS CONCEPTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY INGRESS?                                                          |
|                                                                         |
|  Without Ingress (LoadBalancer per service):                          |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |   Internet                                                      |  |
|  |      |                                                          |  |
|  |      +--> LB --> api-service      (costs $)                    |  |
|  |      +--> LB --> web-service      (costs $)                    |  |
|  |      +--> LB --> admin-service    (costs $)                    |  |
|  |                                                                 |  |
|  |   3 LoadBalancers = 3x cost                                    |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  With Ingress (single entry point):                                   |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |   Internet                                                      |  |
|  |      |                                                          |  |
|  |      +--> LB --> Ingress Controller                            |  |
|  |                       |                                         |  |
|  |                       +--> /api   -> api-service                |  |
|  |                       +--> /      -> web-service                |  |
|  |                       +--> /admin -> admin-service              |  |
|  |                                                                 |  |
|  |   1 LoadBalancer, routes by path/host                         |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY INGRESS OVER LOADBALANCER? (Detailed Comparison)

```
LOADBALANCER SERVICE - HOW IT WORKS:
-------------------------------------

+-------------------------------------------------------------------------+
|                                                                         |
|  Each LoadBalancer Service = Cloud provisions a NEW Load Balancer     |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |        INTERNET                                                 |   |
|  |            |                                                    |   |
|  |   +-------+-------+---------------+---------------+            |   |
|  |   |               |               |               |            |   |
|  |   v               v               v               v            |   |
|  | +-----+       +-----+       +-----+       +-----+             |   |
|  | | ELB |       | ELB |       | ELB |       | ELB |   ...       |   |
|  | | $18 |       | $18 |       | $18 |       | $18 |             |   |
|  | +--+--+       +--+--+       +--+--+       +--+--+             |   |
|  |    |             |             |             |                 |   |
|  |    v             v             v             v                 |   |
|  | +------+     +------+     +------+     +------+              |   |
|  | | API  |     | Web  |     |Admin |     | Auth |              |   |
|  | | Svc  |     | Svc  |     | Svc  |     | Svc  |              |   |
|  | +------+     +------+     +------+     +------+              |   |
|  |                                                                 |   |
|  |  4 services = 4 LoadBalancers = $72/month (AWS ELB)           |   |
|  |  10 services = $180/month                                      |   |
|  |  50 services = $900/month                                      |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  PROBLEMS:                                                             |
|  * Cost: Each LB costs ~$18-25/month (AWS/GCP/Azure)                 |
|  * IP addresses: Each LB = separate public IP                        |
|  * No path routing: Can't route /api to one service, / to another   |
|  * No host routing: Can't use different domains                      |
|  * SSL: Need separate cert for each LB                               |
|  * Management: More resources to manage                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
INGRESS - HOW IT WORKS:
-----------------------

+-------------------------------------------------------------------------+
|                                                                         |
|  One Ingress Controller = One Load Balancer = Routes ALL traffic      |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |        INTERNET                                                 |   |
|  |            |                                                    |   |
|  |            v                                                    |   |
|  |      +----------+                                              |   |
|  |      |   ELB    |  <- Only ONE LoadBalancer ($18/month)        |   |
|  |      |   $18    |                                              |   |
|  |      +----+-----+                                              |   |
|  |           |                                                     |   |
|  |           v                                                     |   |
|  |  +--------------------------------------------------------+    |   |
|  |  |              INGRESS CONTROLLER                         |    |   |
|  |  |                  (NGINX/Traefik)                        |    |   |
|  |  |                                                         |    |   |
|  |  |  Reads Ingress rules and routes traffic:               |    |   |
|  |  |                                                         |    |   |
|  |  |  api.example.com     -------> api-service              |    |   |
|  |  |  web.example.com     -------> web-service              |    |   |
|  |  |  example.com/admin   -------> admin-service            |    |   |
|  |  |  example.com/auth    -------> auth-service             |    |   |
|  |  |                                                         |    |   |
|  |  +--------------------------------------------------------+    |   |
|  |           |        |        |        |                          |   |
|  |           v        v        v        v                          |   |
|  |       +------+ +------+ +------+ +------+                      |   |
|  |       | API  | | Web  | |Admin | | Auth |                      |   |
|  |       | Svc  | | Svc  | | Svc  | | Svc  |                      |   |
|  |       +------+ +------+ +------+ +------+                      |   |
|  |                                                                 |   |
|  |  50 services = Still just $18/month!                          |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
DETAILED COMPARISON TABLE:
--------------------------

+-------------------------------------------------------------------------+
|                                                                         |
|  +--------------------+--------------------+------------------------+  |
|  | Feature            | LoadBalancer       | Ingress                |  |
|  +--------------------+--------------------+------------------------+  |
|  | COST               | $18-25/service     | $18-25 total           |  |
|  |                    | (expensive!)       | (one LB for all)       |  |
|  +--------------------+--------------------+------------------------+  |
|  | Layer              | L4 (TCP/UDP)       | L7 (HTTP/HTTPS)        |  |
|  |                    |                    |                        |  |
|  +--------------------+--------------------+------------------------+  |
|  | Path routing       | [ ] NOT possible     | [x] /api, /admin, /web  |  |
|  |                    |                    |                        |  |
|  +--------------------+--------------------+------------------------+  |
|  | Host routing       | [ ] NOT possible     | [x] api.com, web.com    |  |
|  |                    |                    |                        |  |
|  +--------------------+--------------------+------------------------+  |
|  | SSL/TLS            | Per LB             | Centralized            |  |
|  |                    | (manage many)      | (manage once)          |  |
|  +--------------------+--------------------+------------------------+  |
|  | IP addresses       | One per service    | One for all            |  |
|  |                    |                    |                        |  |
|  +--------------------+--------------------+------------------------+  |
|  | Protocol support   | Any TCP/UDP        | HTTP/HTTPS only        |  |
|  |                    | (database, etc)    |                        |  |
|  +--------------------+--------------------+------------------------+  |
|  | URL rewriting      | [ ] NO               | [x] YES                  |  |
|  |                    |                    |                        |  |
|  +--------------------+--------------------+------------------------+  |
|  | Rate limiting      | [ ] NO               | [x] YES (annotations)    |  |
|  |                    |                    |                        |  |
|  +--------------------+--------------------+------------------------+  |
|  | Authentication     | [ ] NO               | [x] YES (basic auth,    |  |
|  |                    |                    |   OAuth, etc)          |  |
|  +--------------------+--------------------+------------------------+  |
|  | Header manipulation| [ ] NO               | [x] YES                  |  |
|  |                    |                    |                        |  |
|  +--------------------+--------------------+------------------------+  |
|  | Canary/Blue-Green  | [ ] NO               | [x] YES (traffic split)  |  |
|  |                    |                    |                        |  |
|  +--------------------+--------------------+------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
L4 vs L7 - WHAT DOES IT MEAN?
-----------------------------

+-------------------------------------------------------------------------+
|                                                                         |
|  L4 (LoadBalancer) - TRANSPORT LAYER                                  |
|  ===================================                                   |
|                                                                         |
|  Only sees: IP address + Port                                         |
|  Cannot see: URL path, Host header, HTTP headers                      |
|                                                                         |
|  Packet arrives: 192.168.1.10:443                                     |
|  L4 thinks: "Port 443? Send to backend pool"                         |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  Request: GET https://api.example.com/users/123               |   |
|  |                                                                |   |
|  |  L4 LoadBalancer sees:                                        |   |
|  |  +----------------------------------------------------------+ |   |
|  |  |  Source IP: 203.0.113.50                                  | |   |
|  |  |  Dest IP:   52.14.xxx.xxx                                | |   |
|  |  |  Dest Port: 443                                          | |   |
|  |  |                                                           | |   |
|  |  |  That's ALL it knows! <- Can't read URL or headers        | |   |
|  |  +----------------------------------------------------------+ |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  L7 (Ingress) - APPLICATION LAYER                                     |
|  ================================                                      |
|                                                                         |
|  Sees: Everything! URL, headers, cookies, body                        |
|  Can make smart routing decisions                                     |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  Request: GET https://api.example.com/users/123               |   |
|  |                                                                |   |
|  |  L7 Ingress sees:                                             |   |
|  |  +----------------------------------------------------------+ |   |
|  |  |  Host: api.example.com         <- Can route by domain!   | |   |
|  |  |  Path: /users/123              <- Can route by path!     | |   |
|  |  |  Method: GET                   <- Can check HTTP method   | |   |
|  |  |  Headers: Authorization: Bearer xxx                      | |   |
|  |  |  Cookies: session=abc123                                 | |   |
|  |  |                                                           | |   |
|  |  |  Decision: "api.example.com + /users -> api-service"      | |   |
|  |  +----------------------------------------------------------+ |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
WHEN TO USE LOADBALANCER (not Ingress):
---------------------------------------

+-------------------------------------------------------------------------+
|                                                                         |
|  USE LOADBALANCER WHEN:                                                |
|                                                                         |
|  1. NON-HTTP TRAFFIC                                                   |
|     * Database (MySQL: 3306, PostgreSQL: 5432)                        |
|     * Message queues (RabbitMQ, Kafka)                                |
|     * gRPC (if not using HTTP/2 gateway)                              |
|     * Gaming servers (UDP)                                             |
|     * Any TCP/UDP protocol                                            |
|                                                                         |
|  2. SINGLE SERVICE EXPOSED                                             |
|     * Only one service needs external access                          |
|     * No path/host routing needed                                     |
|                                                                         |
|  3. PERFORMANCE CRITICAL                                               |
|     * L4 is slightly faster (no HTTP parsing)                        |
|     * Direct connection to backend                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXAMPLE: Database needs external access                              |
|                                                                         |
|  apiVersion: v1                                                        |
|  kind: Service                                                         |
|  metadata:                                                             |
|    name: postgres-external                                            |
|  spec:                                                                 |
|    type: LoadBalancer              # Can't use Ingress for TCP!       |
|    selector:                                                           |
|      app: postgres                                                    |
|    ports:                                                              |
|      - port: 5432                                                     |
|        targetPort: 5432                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
WHEN TO USE INGRESS:
--------------------

+-------------------------------------------------------------------------+
|                                                                         |
|  USE INGRESS WHEN:                                                     |
|                                                                         |
|  1. HTTP/HTTPS TRAFFIC (web apps, APIs, REST)                         |
|                                                                         |
|  2. MULTIPLE SERVICES need external access                            |
|                                                                         |
|  3. NEED PATH ROUTING                                                  |
|     * /api -> backend                                                   |
|     * /   -> frontend                                                   |
|                                                                         |
|  4. NEED HOST ROUTING                                                  |
|     * api.example.com -> api-service                                   |
|     * www.example.com -> web-service                                   |
|                                                                         |
|  5. CENTRALIZED SSL                                                    |
|     * One place to manage certificates                                |
|     * Let's Encrypt integration (cert-manager)                        |
|                                                                         |
|  6. ADVANCED FEATURES                                                  |
|     * Rate limiting                                                    |
|     * Authentication                                                   |
|     * URL rewriting                                                    |
|     * Canary deployments                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
REAL-WORLD ARCHITECTURE:
------------------------

+-------------------------------------------------------------------------+
|                                                                         |
|  TYPICAL PRODUCTION SETUP                                              |
|                                                                         |
|                        INTERNET                                        |
|                            |                                            |
|            +---------------+---------------+                           |
|            |                               |                           |
|            v                               v                           |
|    +--------------+              +--------------+                     |
|    | LoadBalancer |              | LoadBalancer |                     |
|    | (Ingress)    |              | (Database)   |                     |
|    +------+-------+              +------+-------+                     |
|           |                             |                              |
|           v                             v                              |
|    +--------------+              +--------------+                     |
|    |   INGRESS    |              |   Postgres   |                     |
|    |  CONTROLLER  |              |   Service    |                     |
|    |              |              |  (TCP:5432)  |                     |
|    |  HTTP/HTTPS  |              +--------------+                     |
|    |  traffic     |                                                    |
|    +------+-------+                                                    |
|           |                                                            |
|     +-----+-----+---------+                                           |
|     |     |     |         |                                           |
|     v     v     v         v                                           |
|  +-----++-----++-----++-----+                                        |
|  | API || Web ||Admin||Auth |  <- ClusterIP services (internal)       |
|  | Svc || Svc || Svc || Svc |                                        |
|  +-----++-----++-----++-----+                                        |
|                                                                         |
|  HTTP traffic  -> 1 LoadBalancer -> Ingress -> Many services            |
|  Database      -> 1 LoadBalancer -> Direct to Postgres                 |
|                                                                         |
|  Cost: $36/month instead of $90+ (5 LoadBalancers)                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
COST COMPARISON (AWS):
----------------------

+-------------------------------------------------------------------------+
|                                                                         |
|  10 MICROSERVICES SCENARIO                                             |
|                                                                         |
|  WITHOUT INGRESS:                                                      |
|  -----------------                                                     |
|  10 LoadBalancer services × $18/month = $180/month                    |
|                                         = $2,160/year                  |
|                                                                         |
|  WITH INGRESS:                                                         |
|  --------------                                                        |
|  1 LoadBalancer (for Ingress) = $18/month                             |
|                                = $216/year                             |
|                                                                         |
|  SAVINGS: $1,944/year (90% reduction!)                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  50 MICROSERVICES SCENARIO                                             |
|                                                                         |
|  WITHOUT INGRESS: 50 × $18 = $900/month = $10,800/year               |
|  WITH INGRESS:    1 × $18 = $18/month  = $216/year                   |
|                                                                         |
|  SAVINGS: $10,584/year! 💰                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
SUMMARY - DECISION FLOWCHART:
-----------------------------

+-------------------------------------------------------------------------+
|                                                                         |
|  Is it HTTP/HTTPS traffic?                                            |
|       |                                                                |
|       +-- NO  ---> Use LoadBalancer (TCP/UDP needs L4)               |
|       |            Examples: Database, Message Queue, gRPC            |
|       |                                                                |
|       +-- YES                                                          |
|            |                                                           |
|            Need path or host routing?                                 |
|            |                                                           |
|            +-- YES ---> Use Ingress [x]                                 |
|            |                                                           |
|            +-- NO                                                      |
|                 |                                                      |
|                 Multiple services?                                    |
|                 |                                                      |
|                 +-- YES ---> Use Ingress (saves cost) [x]              |
|                 |                                                      |
|                 +-- NO ---> LoadBalancer is OK                        |
|                             (but Ingress still works)                 |
|                                                                         |
|  DEFAULT RECOMMENDATION: Use Ingress for HTTP/HTTPS traffic!         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8.2: INGRESS ROUTING TYPES (Detailed)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THREE WAYS TO ROUTE TRAFFIC IN INGRESS                                |
|                                                                         |
|  +---------------+-------------------------------------------------+   |
|  | Routing Type  | What It Checks                                  |   |
|  +---------------+-------------------------------------------------+   |
|  | Host-based    | Domain name (api.example.com vs web.example.com)|   |
|  | Path-based    | URL path (/api vs /admin vs /users)            |   |
|  | Combined      | Both host AND path together                    |   |
|  +---------------+-------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ROUTING TYPE 1: HOST-BASED ROUTING (Virtual Hosting)

```
CONCEPT: Route based on the DOMAIN NAME in the request

Same IP, different domains -> different services

+-------------------------------------------------------------------------+
|                                                                         |
|  HOW HOST-BASED ROUTING WORKS                                          |
|                                                                         |
|       User Request                          Where It Goes               |
|       ------------                          -------------               |
|                                                                         |
|   +---------------------+                                              |
|   | api.example.com     |----------------> api-service                |
|   +---------------------+                                              |
|                                                                         |
|   +---------------------+                                              |
|   | web.example.com     |----------------> web-service                |
|   +---------------------+                                              |
|                                                                         |
|   +---------------------+                                              |
|   | admin.example.com   |----------------> admin-service              |
|   +---------------------+                                              |
|                                                                         |
|   All three domains point to SAME Ingress Controller IP!              |
|   Ingress reads "Host" header to decide routing.                      |
|                                                                         |
+-------------------------------------------------------------------------+

HOW IT WORKS INTERNALLY:

+-------------------------------------------------------------------------+
|                                                                         |
|   1. User types: https://api.example.com/users                        |
|                                                                         |
|   2. DNS resolves api.example.com -> 52.14.xxx.xxx (Ingress IP)       |
|                                                                         |
|   3. HTTP request arrives at Ingress Controller with header:          |
|      Host: api.example.com                                            |
|                                                                         |
|   4. Ingress Controller checks rules:                                 |
|      "Host: api.example.com? -> Route to api-service"                 |
|                                                                         |
|   5. Request forwarded to api-service                                 |
|                                                                         |
+-------------------------------------------------------------------------+

YAML EXAMPLE:

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: host-based-ingress
spec:
  ingressClassName: nginx
  rules:
    - host: api.example.com          # Rule 1: API domain
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80

    - host: web.example.com          # Rule 2: Web domain
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-service
                port:
                  number: 80

    - host: admin.example.com        # Rule 3: Admin domain
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: admin-service
                port:
                  number: 80

USE WHEN:
* Different teams/services need their own subdomain
* You want api.company.com and www.company.com
* Multi-tenant applications
```

### ROUTING TYPE 2: PATH-BASED ROUTING

```
CONCEPT: Route based on the URL PATH in the request

Same domain, different paths -> different services

+-------------------------------------------------------------------------+
|                                                                         |
|  HOW PATH-BASED ROUTING WORKS                                          |
|                                                                         |
|       User Request                          Where It Goes               |
|       ------------                          -------------               |
|                                                                         |
|   +---------------------+                                              |
|   | example.com/api     |----------------> api-service                |
|   +---------------------+                                              |
|                                                                         |
|   +---------------------+                                              |
|   | example.com/admin   |----------------> admin-service              |
|   +---------------------+                                              |
|                                                                         |
|   +---------------------+                                              |
|   | example.com/        |----------------> web-service (frontend)     |
|   +---------------------+                                              |
|                                                                         |
|   Single domain, Ingress routes by PATH!                              |
|                                                                         |
+-------------------------------------------------------------------------+

YAML EXAMPLE:

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-based-ingress
spec:
  ingressClassName: nginx
  rules:
    - host: example.com
      http:
        paths:
          - path: /api                # /api/* goes to api-service
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 8080

          - path: /admin              # /admin/* goes to admin-service
            pathType: Prefix
            backend:
              service:
                name: admin-service
                port:
                  number: 80

          - path: /                   # Everything else goes to web
            pathType: Prefix
            backend:
              service:
                name: web-service
                port:
                  number: 80

⚠️  ORDER MATTERS! Most specific paths should come FIRST.
    /api matches before / because it's more specific.

USE WHEN:
* Monolithic frontend with microservice backend
* Single domain for entire application
* Don't want to manage multiple DNS entries
```

### PATH TYPES: Prefix vs Exact vs ImplementationSpecific

```
+-------------------------------------------------------------------------+
|                                                                         |
|  pathType: Prefix                                                      |
|  ================                                                       |
|                                                                         |
|  Matches the path AND everything under it                             |
|                                                                         |
|  path: /api                                                            |
|  ---------------------------------------------                         |
|  /api        -> MATCHES [x]                                              |
|  /api/       -> MATCHES [x]                                              |
|  /api/users  -> MATCHES [x]                                              |
|  /api/v1/orders -> MATCHES [x]                                           |
|  /apikeys    -> NO MATCH [ ] (no / after api)                           |
|  /api-docs   -> NO MATCH [ ] (no / after api)                           |
|                                                                         |
|  NOTE: Prefix matching is based on / separated path elements         |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  pathType: Exact                                                       |
|  ===============                                                        |
|                                                                         |
|  Matches ONLY the exact path, nothing else                            |
|                                                                         |
|  path: /api                                                            |
|  ---------------------------------------------                         |
|  /api        -> MATCHES [x]                                              |
|  /api/       -> NO MATCH [ ]                                             |
|  /api/users  -> NO MATCH [ ]                                             |
|                                                                         |
|  USE WHEN: You want a specific endpoint only                          |
|  Example: /health or /ready endpoints                                 |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  pathType: ImplementationSpecific                                      |
|  ================================                                       |
|                                                                         |
|  Matching depends on the IngressClass/Controller                      |
|  NGINX, Traefik, HAProxy may behave differently                       |
|                                                                         |
|  AVOID this unless you need controller-specific features              |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
COMPARISON EXAMPLE:

+-------------------------------------------------------------------------+
|                                                                         |
|  Request URL: /api/users/123                                          |
|                                                                         |
|  +-------------------+---------------+----------------+               |
|  | Rule Path         | pathType      | Matches?       |               |
|  +-------------------+---------------+----------------+               |
|  | /api              | Prefix        | YES [x]          |               |
|  | /api              | Exact         | NO [ ]           |               |
|  | /api/users        | Prefix        | YES [x]          |               |
|  | /api/users        | Exact         | NO [ ]           |               |
|  | /api/users/123    | Exact         | YES [x]          |               |
|  | /                 | Prefix        | YES [x]          |               |
|  +-------------------+---------------+----------------+               |
|                                                                         |
|  Multiple rules match? -> Most specific (longest) path wins!           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ROUTING TYPE 3: COMBINED (Host + Path)

```
CONCEPT: Use BOTH host AND path for routing

+-------------------------------------------------------------------------+
|                                                                         |
|  COMBINED ROUTING EXAMPLE                                              |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  api.example.com/v1/users  ---->  api-v1-service              |   |
|  |  api.example.com/v2/users  ---->  api-v2-service              |   |
|  |                                                                 |   |
|  |  web.example.com/          ---->  frontend-service            |   |
|  |  web.example.com/static    ---->  cdn-service                 |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+

YAML EXAMPLE:

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: combined-routing-ingress
spec:
  ingressClassName: nginx
  rules:
    # API domain with version paths
    - host: api.example.com
      http:
        paths:
          - path: /v1
            pathType: Prefix
            backend:
              service:
                name: api-v1-service
                port:
                  number: 80
          - path: /v2
            pathType: Prefix
            backend:
              service:
                name: api-v2-service
                port:
                  number: 80

    # Web domain with different paths
    - host: web.example.com
      http:
        paths:
          - path: /static
            pathType: Prefix
            backend:
              service:
                name: cdn-service
                port:
                  number: 80
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80

USE WHEN:
* API versioning (v1, v2) on same domain
* Complex microservice architectures
* Need fine-grained control
```

### DEFAULT BACKEND (Catch-All)

```
CONCEPT: Handle requests that don't match any rule

+-------------------------------------------------------------------------+
|                                                                         |
|  If NO host and NO path matches -> defaultBackend handles it           |
|                                                                         |
|  Useful for:                                                           |
|  * Custom 404 pages                                                    |
|  * Catch-all service                                                   |
|  * Health checks                                                       |
|                                                                         |
+-------------------------------------------------------------------------+

YAML:

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ingress-with-default
spec:
  ingressClassName: nginx
  defaultBackend:                    # Catch-all
    service:
      name: default-service
      port:
        number: 80
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80
```

### ROUTING COMPARISON SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHEN TO USE WHAT                                                      |
|                                                                         |
|  +--------------+---------------------------------------------------+  |
|  | Scenario     | Routing Type                                      |  |
|  +--------------+---------------------------------------------------+  |
|  | Different    | HOST-BASED                                        |  |
|  | subdomains   | api.example.com, web.example.com                 |  |
|  | for services |                                                   |  |
|  +--------------+---------------------------------------------------+  |
|  | Single domain| PATH-BASED                                        |  |
|  | multiple     | example.com/api, example.com/admin               |  |
|  | services     |                                                   |  |
|  +--------------+---------------------------------------------------+  |
|  | API version- | COMBINED                                          |  |
|  | ing + multiple| api.example.com/v1, api.example.com/v2          |  |
|  | services     |                                                   |  |
|  +--------------+---------------------------------------------------+  |
|  | Exact        | pathType: Exact                                   |  |
|  | endpoints    | /health, /ready, /metrics                        |  |
|  +--------------+---------------------------------------------------+  |
|  | Wildcard     | pathType: Prefix                                  |  |
|  | paths        | /api/* matches /api/users, /api/orders           |  |
|  +--------------+---------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

```bash
QUICK COMMANDS:
---------------

# List all ingress
kubectl get ingress

# Describe ingress (see rules)
kubectl describe ingress <name>

# Get ingress with details
kubectl get ingress -o wide

# Test routing (from inside cluster)
kubectl run test --rm -it --image=busybox -- wget -qO- http://<service>
```

## SECTION 8.3: INGRESS RESOURCE EXAMPLES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BASIC INGRESS                                                         |
|  =============                                                          |
|                                                                         |
|  apiVersion: networking.k8s.io/v1                                     |
|  kind: Ingress                                                          |
|  metadata:                                                              |
|    name: my-ingress                                                    |
|  spec:                                                                  |
|    ingressClassName: nginx                                             |
|    rules:                                                               |
|      - host: myapp.example.com                                        |
|        http:                                                            |
|          paths:                                                         |
|            - path: /                                                   |
|              pathType: Prefix                                          |
|              backend:                                                   |
|                service:                                                 |
|                  name: web-service                                     |
|                  port:                                                  |
|                    number: 80                                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PATH-BASED ROUTING                                                    |
|  ===================                                                    |
|                                                                         |
|  spec:                                                                  |
|    rules:                                                               |
|      - host: myapp.example.com                                        |
|        http:                                                            |
|          paths:                                                         |
|            - path: /api                                               |
|              pathType: Prefix                                          |
|              backend:                                                   |
|                service:                                                 |
|                  name: api-service                                     |
|                  port:                                                  |
|                    number: 8080                                        |
|            - path: /                                                   |
|              pathType: Prefix                                          |
|              backend:                                                   |
|                service:                                                 |
|                  name: web-service                                     |
|                  port:                                                  |
|                    number: 80                                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HOST-BASED ROUTING                                                    |
|  ===================                                                    |
|                                                                         |
|  spec:                                                                  |
|    rules:                                                               |
|      - host: api.example.com                                          |
|        http:                                                            |
|          paths:                                                         |
|            - path: /                                                   |
|              pathType: Prefix                                          |
|              backend:                                                   |
|                service:                                                 |
|                  name: api-service                                     |
|                  port:                                                  |
|                    number: 80                                          |
|      - host: web.example.com                                          |
|        http:                                                            |
|          paths:                                                         |
|            - path: /                                                   |
|              pathType: Prefix                                          |
|              backend:                                                   |
|                service:                                                 |
|                  name: web-service                                     |
|                  port:                                                  |
|                    number: 80                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8.3: TLS/HTTPS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TLS TERMINATION                                                       |
|  ===============                                                        |
|                                                                         |
|  # Create TLS secret                                                   |
|  kubectl create secret tls my-tls \                                   |
|    --cert=tls.crt --key=tls.key                                       |
|                                                                         |
|  # Ingress with TLS                                                    |
|  apiVersion: networking.k8s.io/v1                                     |
|  kind: Ingress                                                          |
|  metadata:                                                              |
|    name: tls-ingress                                                   |
|  spec:                                                                  |
|    tls:                                                                 |
|      - hosts:                                                           |
|          - myapp.example.com                                          |
|        secretName: my-tls                                              |
|    rules:                                                               |
|      - host: myapp.example.com                                        |
|        http:                                                            |
|          paths:                                                         |
|            - path: /                                                   |
|              pathType: Prefix                                          |
|              backend:                                                   |
|                service:                                                 |
|                  name: web-service                                     |
|                  port:                                                  |
|                    number: 80                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8.4: INGRESS CONTROLLERS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  POPULAR CONTROLLERS                                                   |
|                                                                         |
|  * NGINX Ingress Controller (most common)                            |
|  * Traefik                                                            |
|  * HAProxy                                                            |
|  * AWS ALB Ingress Controller                                        |
|  * GKE Ingress Controller                                            |
|                                                                         |
|  INSTALL NGINX INGRESS                                                |
|  ======================                                                |
|                                                                         |
|  # Using Helm                                                          |
|  helm repo add ingress-nginx \                                        |
|    https://kubernetes.github.io/ingress-nginx                         |
|  helm install ingress-nginx ingress-nginx/ingress-nginx              |
|                                                                         |
|  # Or kubectl                                                          |
|  kubectl apply -f \                                                     |
|    https://raw.githubusercontent.com/kubernetes/ingress-nginx/\       |
|    controller-v1.8.0/deploy/static/provider/cloud/deploy.yaml        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INGRESS - KEY TAKEAWAYS                                              |
|                                                                         |
|  COMPONENTS                                                            |
|  ----------                                                            |
|  * Ingress Resource: Routing rules                                   |
|  * Ingress Controller: Implements rules                              |
|                                                                         |
|  ROUTING                                                               |
|  -------                                                               |
|  * Path-based: /api -> api-service                                   |
|  * Host-based: api.example.com -> api-service                        |
|                                                                         |
|  TLS                                                                   |
|  ---                                                                   |
|  * Create TLS secret with cert/key                                   |
|  * Reference in spec.tls                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 8

