# API GATEWAY - HIGH LEVEL DESIGN
*Part 2: Core Components Deep Dive*

## SECTION 2.1: ROUTING ENGINE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ROUTING ENGINE                                                         |
|                                                                         |
|  Maps incoming requests to backend services based on rules.             |
|                                                                         |
|  ROUTING TYPES:                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. PATH-BASED ROUTING (Most common)                              |  |
|  |  ===================================                              |  |
|  |                                                                   |  |
|  |  /api/v1/users/*     > User Service                               |  |
|  |  /api/v1/orders/*    > Order Service                              |  |
|  |  /api/v1/products/*  > Product Service                            |  |
|  |                                                                   |  |
|  |  Config (Kong style):                                             |  |
|  |  routes:                                                          |  |
|  |    - name: user-route                                             |  |
|  |      paths:                                                       |  |
|  |        - /api/v1/users                                            |  |
|  |      service: user-service                                        |  |
|  |      strip_path: true                                             |  |
|  |                                                                   |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  2. HOST-BASED ROUTING                                            |  |
|  |  =======================                                          |  |
|  |                                                                   |  |
|  |  api.example.com      > Main API                                  |  |
|  |  admin.example.com    > Admin Service                             |  |
|  |  partner.example.com  > Partner API                               |  |
|  |                                                                   |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  3. HEADER-BASED ROUTING                                          |  |
|  |  ===========================                                      |  |
|  |                                                                   |  |
|  |  X-API-Version: v1  > Service v1                                  |  |
|  |  X-API-Version: v2  > Service v2                                  |  |
|  |                                                                   |  |
|  |  X-Tenant-ID: acme  > Acme's dedicated cluster                    |  |
|  |                                                                   |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  4. METHOD-BASED ROUTING                                          |  |
|  |  ===========================                                      |  |
|  |                                                                   |  |
|  |  GET  /orders  > Read replica (Order Query Service)               |  |
|  |  POST /orders  > Primary (Order Command Service)                  |  |
|  |                                                                   |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  5. WEIGHTED ROUTING (Canary/Blue-Green)                          |  |
|  |  =======================================                          |  |
|  |                                                                   |  |
|  |  /api/v1/users:                                                   |  |
|  |    - service: user-service-v1, weight: 90                         |  |
|  |    - service: user-service-v2, weight: 10  # Canary               |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ROUTE MATCHING ALGORITHM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ROUTE MATCHING PRIORITY                                                |
|                                                                         |
|  When multiple routes could match, priority matters:                    |
|                                                                         |
|  1. Exact path match (highest priority)                                 |
|     /api/v1/users/123                                                   |
|                                                                         |
|  2. Longest prefix match                                                |
|     /api/v1/users/* beats /api/v1/*                                     |
|                                                                         |
|  3. Host specificity                                                    |
|     api.example.com beats *.example.com                                 |
|                                                                         |
|  4. Method specificity                                                  |
|     GET /users beats ANY /users                                         |
|                                                                         |
|  5. Custom priority (explicit config)                                   |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  DATA STRUCTURE: Radix Tree (Trie)                                      |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |                        [/api]                                     |  |
|  |                           |                                       |  |
|  |                        [/v1]                                      |  |
|  |                     /    |    \                                   |  |
|  |                    /     |     \                                  |  |
|  |           [/users]   [/orders]  [/products]                       |  |
|  |               |          |           |                            |  |
|  |         User Svc    Order Svc   Product Svc                       |  |
|  |                                                                   |  |
|  |  Lookup: O(path_length), very fast                                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.2: AUTHENTICATION & AUTHORIZATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  AUTHENTICATION METHODS                                                 |
|                                                                         |
|  1. API KEY AUTHENTICATION                                              |
|  ==========================                                             |
|                                                                         |
|  Request:                                                               |
|  GET /api/v1/users                                                      |
|  X-API-Key: sk_live_abc123xyz                                           |
|                                                                         |
|  Validation:                                                            |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  def validate_api_key(api_key):                                   |  |
|  |      # Check cache first                                          |  |
|  |      cached = redis.get(f"apikey:{hash(api_key)}")                |  |
|  |      if cached:                                                   |  |
|  |          return cached                                            |  |
|  |                                                                   |  |
|  |      # Lookup in database                                         |  |
|  |      key_record = db.query(                                       |  |
|  |          "SELECT * FROM api_keys WHERE key_hash = ?",             |  |
|  |          hash(api_key)                                            |  |
|  |      )                                                            |  |
|  |                                                                   |  |
|  |      if not key_record or key_record.revoked:                     |  |
|  |          raise AuthError("Invalid API key")                       |  |
|  |                                                                   |  |
|  |      # Cache for future requests                                  |  |
|  |      redis.setex(f"apikey:{hash(api_key)}", 300, key_record)      |  |
|  |      return key_record                                            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  SECURITY: Store hash of API key, not plaintext                         |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. JWT TOKEN VALIDATION                                                |
|  ===========================                                            |
|                                                                         |
|  Request:                                                               |
|  GET /api/v1/users                                                      |
|  Authorization: Bearer eyJhbGciOiJSUzI1NiIs...                          |
|                                                                         |
|  Validation:                                                            |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  def validate_jwt(token):                                         |  |
|  |      # 1. Decode header (no verification yet)                     |  |
|  |      header = decode_header(token)                                |  |
|  |                                                                   |  |
|  |      # 2. Get public key (JWKS - cached)                          |  |
|  |      public_key = get_jwks_key(header['kid'])                     |  |
|  |                                                                   |  |
|  |      # 3. Verify signature                                        |  |
|  |      payload = jwt.decode(                                        |  |
|  |          token,                                                   |  |
|  |          public_key,                                              |  |
|  |          algorithms=['RS256'],                                    |  |
|  |          audience='api.example.com',                              |  |
|  |          issuer='auth.example.com'                                |  |
|  |      )                                                            |  |
|  |                                                                   |  |
|  |      # 4. Check expiration (jwt.decode does this)                 |  |
|  |      # 5. Check revocation (optional, check blacklist)            |  |
|  |                                                                   |  |
|  |      return payload  # Contains user_id, scopes, etc.             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  JWT Benefits:                                                          |
|  * Stateless (no DB lookup for every request)                           |
|  * Self-contained (user info in token)                                  |
|  * Verifiable without calling auth server                               |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. OAUTH 2.0 / OPENID CONNECT                                          |
|  ==============================                                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Client          Gateway           Auth Server      Backend       |  |
|  |    |                |                   |              |          |  |
|  |    |--1. /authorize------------------>|              |            |  |
|  |    |                |                   |              |          |  |
|  |    |<-2. Auth code----------------------|              |          |  |
|  |    |                |                   |              |          |  |
|  |    |--3. Exchange code for token------>|              |           |  |
|  |    |                |                   |              |          |  |
|  |    |<-4. Access token + ID token-------|              |           |  |
|  |    |                |                   |              |          |  |
|  |    |--5. API request with token------->|              |           |  |
|  |    |                |                   |              |          |  |
|  |    |                |--6. Validate---->|              |           |  |
|  |    |                |   (or local)      |              |          |  |
|  |    |                |                   |              |          |  |
|  |    |                |--7. Forward to backend-------->|            |  |
|  |    |                |                   |              |          |  |
|  |    |<-8. Response-----------------------------------|             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### AUTHORIZATION (RBAC/ABAC)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ROLE-BASED ACCESS CONTROL (RBAC)                                       |
|                                                                         |
|  User has roles > Roles have permissions > Check permission             |
|                                                                         |
|  JWT Payload:                                                           |
|  {                                                                      |
|    "sub": "user_123",                                                   |
|    "roles": ["admin", "editor"],                                        |
|    "scopes": ["read:users", "write:users", "read:orders"]               |
|  }                                                                      |
|                                                                         |
|  Route Config:                                                          |
|  routes:                                                                |
|    - path: /api/v1/users                                                |
|      methods: [GET]                                                     |
|      required_scopes: ["read:users"]                                    |
|                                                                         |
|    - path: /api/v1/users                                                |
|      methods: [POST, PUT, DELETE]                                       |
|      required_scopes: ["write:users"]                                   |
|                                                                         |
|    - path: /api/v1/admin/*                                              |
|      required_roles: ["admin"]                                          |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  ATTRIBUTE-BASED ACCESS CONTROL (ABAC)                                  |
|                                                                         |
|  More flexible - decisions based on attributes                          |
|                                                                         |
|  Policy:                                                                |
|  {                                                                      |
|    "effect": "allow",                                                   |
|    "action": "delete:order",                                            |
|    "condition": {                                                       |
|      "user.department": "sales",                                        |
|      "resource.status": "pending",                                      |
|      "time.hour": {"gte": 9, "lte": 17}                                 |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
|  > Can delete order if: user is in sales, order is pending,             |
|    and it's business hours                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.3: RATE LIMITING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RATE LIMITING STRATEGIES                                               |
|                                                                         |
|  1. TOKEN BUCKET (Most common for API gateways)                         |
|  ===============================================                        |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Config: 100 requests/minute, burst 10                            |  |
|  |                                                                   |  |
|  |  +-------------------------------------+                          |  |
|  |  |          TOKEN BUCKET              |                           |  |
|  |  |                                     |                          |  |
|  |  |   Tokens added: 100/60 = 1.67/sec  |                           |  |
|  |  |   Max tokens: 10 (burst)           |                           |  |
|  |  |                                     |                          |  |
|  |  |   [o][o][o][o][o][o][o][o][o][o]   | < 10 tokens               |  |
|  |  |                                     |                          |  |
|  |  |   Request arrives:                  |                          |  |
|  |  |   - Token available? Take 1, allow |                           |  |
|  |  |   - No token? Reject (429)         |                           |  |
|  |  |                                     |                          |  |
|  |  +-------------------------------------+                          |  |
|  |                                                                   |  |
|  |  PROS: Allows burst, smooth rate                                  |  |
|  |  CONS: Slightly complex implementation                            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  2. SLIDING WINDOW COUNTER                                              |
|  ==========================                                             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  def check_rate_limit(user_id, limit=100, window=60):             |  |
|  |      now = time.time()                                            |  |
|  |      current_window = int(now // window)                          |  |
|  |      previous_window = current_window - 1                         |  |
|  |                                                                   |  |
|  |      # Get counts from Redis                                      |  |
|  |      current_count = redis.get(f"rl:{user_id}:{current_window}") or 0|
|  |      prev_count = redis.get(f"rl:{user_id}:{previous_window}") or 0  |
|  |                                                                   |  |
|  |      # Calculate weighted count                                   |  |
|  |      elapsed = now - (current_window * window)                    |  |
|  |      weight = (window - elapsed) / window                         |  |
|  |      estimated = (prev_count * weight) + current_count            |  |
|  |                                                                   |  |
|  |      if estimated >= limit:                                       |  |
|  |          return False, limit - estimated                          |  |
|  |                                                                   |  |
|  |      redis.incr(f"rl:{user_id}:{current_window}")                 |  |
|  |      redis.expire(f"rl:{user_id}:{current_window}", window*2)     |  |
|  |      return True, limit - estimated - 1                           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### RATE LIMIT SCOPES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RATE LIMIT BY DIFFERENT DIMENSIONS                                     |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Scope              | Key                | Use Case               |  |
|  |  ------------------------------------------------------------     |  |
|  |  Global             | "global"           | Protect infra          |  |
|  |  Per API Key        | api_key            | Tenant limits          |  |
|  |  Per User           | user_id            | User fairness          |  |
|  |  Per IP             | client_ip          | Anonymous APIs         |  |
|  |  Per Endpoint       | path + method      | Expensive endpoints    |  |
|  |  Per Tenant+Endpoint| tenant + path      | Fine-grained           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  TIERED RATE LIMITS:                                                    |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Plan        | Requests/min | Requests/day | Burst                |  |
|  |  ------------------------------------------------------------     |  |
|  |  Free        | 60           | 1,000        | 5                    |  |
|  |  Starter     | 600          | 50,000       | 20                   |  |
|  |  Pro         | 3,000        | 500,000      | 100                  |  |
|  |  Enterprise  | Custom       | Unlimited    | Custom               |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  RESPONSE HEADERS:                                                      |
|                                                                         |
|  X-RateLimit-Limit: 100                                                 |
|  X-RateLimit-Remaining: 95                                              |
|  X-RateLimit-Reset: 1704067260 (Unix timestamp)                         |
|  Retry-After: 30 (seconds, on 429)                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.4: LOAD BALANCING & SERVICE DISCOVERY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LOAD BALANCING ALGORITHMS                                              |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. ROUND ROBIN                                                   |  |
|  |     Request 1 > Server A                                          |  |
|  |     Request 2 > Server B                                          |  |
|  |     Request 3 > Server C                                          |  |
|  |     Request 4 > Server A (cycle)                                  |  |
|  |                                                                   |  |
|  |  2. WEIGHTED ROUND ROBIN                                          |  |
|  |     Server A (weight 3): Gets 3x requests                         |  |
|  |     Server B (weight 1): Gets 1x requests                         |  |
|  |                                                                   |  |
|  |  3. LEAST CONNECTIONS                                             |  |
|  |     Route to server with fewest active connections                |  |
|  |     Good for long-running requests                                |  |
|  |                                                                   |  |
|  |  4. CONSISTENT HASHING                                            |  |
|  |     Hash(user_id) > Same server for same user                     |  |
|  |     Good for caching, sticky sessions                             |  |
|  |                                                                   |  |
|  |  5. RANDOM                                                        |  |
|  |     Simple, surprisingly effective at scale                       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SERVICE DISCOVERY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HOW DOES GATEWAY KNOW BACKEND ADDRESSES?                               |
|                                                                         |
|  1. STATIC CONFIGURATION                                                |
|  ======================                                                 |
|                                                                         |
|  services:                                                              |
|    user-service:                                                        |
|      url: http://user-svc.internal:8080                                 |
|                                                                         |
|  PROS: Simple                                                           |
|  CONS: Manual updates, doesn't scale                                    |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. DNS-BASED DISCOVERY                                                 |
|  ======================                                                 |
|                                                                         |
|  services:                                                              |
|    user-service:                                                        |
|      host: user-service.namespace.svc.cluster.local                     |
|                                                                         |
|  Gateway resolves DNS > Gets list of IPs                                |
|  Works well with Kubernetes                                             |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. SERVICE REGISTRY (Consul, Eureka, etcd)                             |
|  ===========================================                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Service Instance           Service Registry         Gateway      |  |
|  |        |                          |                     |         |  |
|  |        |--1. Register ----------->|                     |         |  |
|  |        |   (IP, port, health)     |                     |         |  |
|  |        |                          |                     |         |  |
|  |        |--2. Heartbeat ---------->|                     |         |  |
|  |        |   (every 10s)            |                     |         |  |
|  |        |                          |                     |         |  |
|  |        |                          |<-3. Query ----------|         |  |
|  |        |                          |   (user-service)    |         |  |
|  |        |                          |                     |         |  |
|  |        |                          |--4. Return IPs ---->|         |  |
|  |        |                          |                     |         |  |
|  |        |                          |--5. Watch/Subscribe>|         |  |
|  |        |                          |   (real-time updates)|        |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  PROS: Dynamic, real-time, health-aware                                 |
|  CONS: Additional infrastructure                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HEALTH CHECKS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HEALTH CHECK TYPES                                                     |
|                                                                         |
|  PASSIVE (Response-based):                                              |
|  * Track success/failure of actual requests                             |
|  * Remove from pool after N consecutive failures                        |
|  * No extra traffic                                                     |
|                                                                         |
|  ACTIVE (Probe-based):                                                  |
|  * Periodically call /health endpoint                                   |
|  * Faster detection of unhealthy backends                               |
|  * Additional traffic                                                   |
|                                                                         |
|  Config:                                                                |
|  health_checks:                                                         |
|    active:                                                              |
|      path: /health                                                      |
|      interval: 5s                                                       |
|      timeout: 2s                                                        |
|      healthy_threshold: 2      # Consecutive successes to mark healthy  |
|      unhealthy_threshold: 3    # Consecutive failures to mark unhealthy |
|                                                                         |
|    passive:                                                             |
|      healthy:                                                           |
|        successes: 2                                                     |
|      unhealthy:                                                         |
|        http_failures: 5                                                 |
|        tcp_failures: 2                                                  |
|        timeouts: 3                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.5: CIRCUIT BREAKER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CIRCUIT BREAKER PATTERN                                                |
|                                                                         |
|  Prevents cascade failures when backend is unhealthy                    |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |                    CIRCUIT BREAKER STATES                         |  |
|  |                                                                   |  |
|  |         +---------------------------------------------+           |  |
|  |         |                                             |           |  |
|  |         |      Success                Failure         |           |  |
|  |         |        |                      |             |           |  |
|  |         v        |                      v             |           |  |
|  |      +------+    |                 +------+           |           |  |
|  |      |CLOSED|----+---------------->| OPEN |           |           |  |
|  |      |      |  Failure threshold   |      |           |           |  |
|  |      |      |  exceeded            |      |           |           |  |
|  |      +------+                      +--+---+           |           |  |
|  |         ^                             |               |           |  |
|  |         |                    After timeout            |           |  |
|  |         |                             |               |           |  |
|  |         |                             v               |           |  |
|  |         |                       +-----------+         |           |  |
|  |         |      Success          |HALF-OPEN |         |            |  |
|  |         +-----------------------|          |---------+            |  |
|  |                                 |(test)    |  Failure             |  |
|  |                                 +-----------+                     |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  STATES:                                                                |
|                                                                         |
|  CLOSED (Normal operation):                                             |
|  * All requests pass through                                            |
|  * Track failure rate                                                   |
|  * If failures > threshold > OPEN                                       |
|                                                                         |
|  OPEN (Circuit tripped):                                                |
|  * Requests fail immediately (no backend call)                          |
|  * Return 503 or cached response                                        |
|  * After timeout > HALF-OPEN                                            |
|                                                                         |
|  HALF-OPEN (Testing):                                                   |
|  * Allow limited requests through                                       |
|  * If success > CLOSED                                                  |
|  * If failure > OPEN                                                    |
|                                                                         |
|  Config:                                                                |
|  circuit_breaker:                                                       |
|    failure_threshold: 5        # Failures to trip                       |
|    failure_window: 10s         # Time window for failures               |
|    open_timeout: 30s           # Time before half-open                  |
|    half_open_requests: 3       # Test requests in half-open             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF PART 2

