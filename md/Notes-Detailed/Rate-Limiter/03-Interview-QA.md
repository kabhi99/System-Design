# RATE LIMITER SYSTEM DESIGN

CHAPTER 3: INTERVIEW Q&A AND DEEP DIVES
## TABLE OF CONTENTS
*-----------------*
*1. Common Interview Questions*
*2. Rules Configuration*
*3. Multi-Tier Rate Limiting*
*4. Monitoring and Observability*
*5. Quick Reference Cheat Sheet*

## SECTION 3.1: COMMON INTERVIEW QUESTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q1: Design a rate limiter for an API                                   |
|  --------------------------------------                                 |
|                                                                         |
|  FRAMEWORK FOR ANSWERING:                                               |
|                                                                         |
|  1. Clarify Requirements (2-3 min)                                      |
|     * What to limit? (User, IP, API key, endpoint)                      |
|     * What rate? (X requests per Y seconds)                             |
|     * Single server or distributed?                                     |
|     * Hard limit or soft limit with throttling?                         |
|                                                                         |
|  2. High-Level Design (5 min)                                           |
|     * Where to place: API Gateway / Middleware                          |
|     * Storage: Redis for distributed counters                           |
|     * Algorithm: Sliding Window Counter (default choice)                |
|                                                                         |
|  3. Deep Dive Algorithm (10 min)                                        |
|     * Explain sliding window counter                                    |
|     * Show Redis implementation                                         |
|     * Discuss race conditions > atomic operations                       |
|                                                                         |
|  4. Handle Edge Cases (5 min)                                           |
|     * Redis down > fail open with local cache                           |
|     * Race conditions > Lua scripts                                     |
|     * Multiple rules > check all, deny if any exceeded                  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  Q2: What algorithm would you use and why?                              |
|  --------------------------------------------                           |
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  "I'd use Sliding Window Counter because:                               |
|   1. Solves the boundary problem of fixed window                        |
|   2. Memory efficient (just 2 counters per user)                        |
|   3. Good accuracy without storing every timestamp                      |
|   4. Easy to implement in Redis                                         |
|                                                                         |
|   If they need burst handling, Token Bucket is better."                 |
|                                                                         |
|  FOLLOW-UP: "Explain the boundary problem"                              |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Fixed window: 100 req/min                                        |  |
|  |                                                                   |  |
|  |  Window 1       |       Window 2                                  |  |
|  |  ---------------+---------------                                  |  |
|  |      [100 req]  |  [100 req]                                      |  |
|  |          +------+------+                                          |  |
|  |           2 seconds                                               |  |
|  |                                                                   |  |
|  |  200 requests in 2 seconds - 2x the intended rate!                |  |
|  |                                                                   |  |
|  |  Sliding window prevents this by considering overlap.             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  Q3: How do you handle distributed rate limiting?                       |
|  -------------------------------------------------                      |
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  "Use centralized counter store like Redis:                             |
|                                                                         |
|   1. All servers share same Redis instance/cluster                      |
|   2. Use atomic operations (INCR, Lua scripts) for race conditions      |
|   3. Redis Cluster for high availability and scalability                |
|                                                                         |
|   Trade-off: Added latency (1 Redis call per request)                   |
|   Mitigation: Local cache with async sync for very high volume"         |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  Q4: What happens if Redis goes down?                                   |
|  ---------------------------------------                                |
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  "Three strategies:                                                     |
|                                                                         |
|   1. Fail Open: Allow all requests (risky but available)                |
|      Use for: Non-critical APIs                                         |
|                                                                         |
|   2. Fail Closed: Deny all requests (secure but unavailable)            |
|      Use for: Payment APIs, sensitive operations                        |
|                                                                         |
|   3. Fallback to local rate limiting (recommended)                      |
|      Divide limit by number of servers                                  |
|      If 100 req/min and 10 servers > 10 req/min per server              |
|      Not perfect but degraded functionality"                            |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  Q5: How do you handle race conditions?                                 |
|  ---------------------------------------                                |
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  "Race condition example:                                               |
|   - Current count: 99, Limit: 100                                       |
|   - Server A reads 99, allows request                                   |
|   - Server B reads 99 (before A writes), allows request                 |
|   - Both increment to 100, but we allowed 101 requests!                 |
|                                                                         |
|   Solution: Atomic operations in Redis                                  |
|                                                                         |
|   Option 1: Use INCR (atomic increment)                                 |
|   count = INCR key                                                      |
|   if count > limit: DENY                                                |
|                                                                         |
|   Option 2: Lua script for complex logic                                |
|   Entire script executes atomically on Redis server"                    |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  Q6: How would you rate limit by different dimensions?                  |
|  ------------------------------------------------------                 |
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  "Use different keys for different dimensions:                          |
|                                                                         |
|   By User:    ratelimit:user:{user_id}:{window}                         |
|   By IP:      ratelimit:ip:{ip_address}:{window}                        |
|   By API Key: ratelimit:apikey:{api_key}:{window}                       |
|   By Endpoint: ratelimit:endpoint:{path}:{window}                       |
|   Combined:   ratelimit:user:{id}:endpoint:{path}:{window}              |
|                                                                         |
|   Check all applicable rules, deny if ANY exceeded."                    |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  Q7: How to implement different limits for different user tiers?        |
|  -----------------------------------------------------------------------|
|                                                                         |
|  ANSWER:                                                                |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  # Config (stored in DB or config service)                        |  |
|  |  rate_limits = {                                                  |  |
|  |      "free":      {"requests": 100,   "window": 3600},            |  |
|  |      "basic":     {"requests": 1000,  "window": 3600},            |  |
|  |      "premium":   {"requests": 10000, "window": 3600},            |  |
|  |      "enterprise": {"requests": 100000, "window": 3600}           |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  |  def check_rate_limit(user):                                      |  |
|  |      tier = get_user_tier(user.id)  # from DB/cache               |  |
|  |      config = rate_limits[tier]                                   |  |
|  |      return check_limit(                                          |  |
|  |          key=f"ratelimit:user:{user.id}",                         |  |
|  |          limit=config["requests"],                                |  |
|  |          window=config["window"]                                  |  |
|  |      )                                                            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  Q8: Where should rate limiting be implemented?                         |
|  -------------------------------------------------                      |
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  "Depends on requirements:                                              |
|                                                                         |
|   API Gateway (recommended for most):                                   |
|   + Centralized, all services protected                                 |
|   + No code changes in services                                         |
|   - Can't access app-level context                                      |
|                                                                         |
|   Application middleware:                                               |
|   + Access to user context, business logic                              |
|   + Fine-grained control                                                |
|   - Each service needs implementation                                   |
|                                                                         |
|   Best practice: Both (layered defense)                                 |
|   - Gateway: Global limits, DDoS protection                             |
|   - App: Business-specific limits (posts/day, etc.)"                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.2: RULES CONFIGURATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RULES ENGINE DESIGN                                                    |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  RULE SCHEMA:                                                     |  |
|  |                                                                   |  |
|  |  {                                                                |  |
|  |    "id": "rule_001",                                              |  |
|  |    "name": "Default API limit",                                   |  |
|  |    "enabled": true,                                               |  |
|  |    "priority": 100,        // Lower = higher priority             |  |
|  |                                                                   |  |
|  |    // Matching conditions                                         |  |
|  |    "conditions": {                                                |  |
|  |      "path": "/api/v1/*",                                         |  |
|  |      "method": ["GET", "POST"],                                   |  |
|  |      "user_tier": ["free", "basic"],                              |  |
|  |      "source_ip": "0.0.0.0/0"    // all IPs                       |  |
|  |    },                                                             |  |
|  |                                                                   |  |
|  |    // Rate limit config                                           |  |
|  |    "limit": {                                                     |  |
|  |      "requests": 100,                                             |  |
|  |      "window_seconds": 60,                                        |  |
|  |      "key_by": ["user_id"],   // dimension to limit by            |  |
|  |      "algorithm": "sliding_window"                                |  |
|  |    },                                                             |  |
|  |                                                                   |  |
|  |    // Actions                                                     |  |
|  |    "on_exceed": {                                                 |  |
|  |      "status_code": 429,                                          |  |
|  |      "retry_after": true,                                         |  |
|  |      "log_level": "warn"                                          |  |
|  |    }                                                              |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  EXAMPLE RULES                                                          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  RULE 1: Global DDoS protection (lowest priority check)           |  |
|  |  {                                                                |  |
|  |    "path": "/*",                                                  |  |
|  |    "key_by": ["ip"],                                              |  |
|  |    "limit": 1000,                                                 |  |
|  |    "window": 60                                                   |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  |  RULE 2: Login endpoint (prevent brute force)                     |  |
|  |  {                                                                |  |
|  |    "path": "/api/auth/login",                                     |  |
|  |    "key_by": ["ip"],                                              |  |
|  |    "limit": 5,                                                    |  |
|  |    "window": 60                                                   |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  |  RULE 3: Password reset (prevent enumeration)                     |  |
|  |  {                                                                |  |
|  |    "path": "/api/auth/reset-password",                            |  |
|  |    "key_by": ["ip"],                                              |  |
|  |    "limit": 3,                                                    |  |
|  |    "window": 3600                                                 |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  |  RULE 4: Free tier users                                          |  |
|  |  {                                                                |  |
|  |    "path": "/api/*",                                              |  |
|  |    "user_tier": "free",                                           |  |
|  |    "key_by": ["user_id"],                                         |  |
|  |    "limit": 100,                                                  |  |
|  |    "window": 3600                                                 |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  |  RULE 5: Premium tier users                                       |  |
|  |  {                                                                |  |
|  |    "path": "/api/*",                                              |  |
|  |    "user_tier": "premium",                                        |  |
|  |    "key_by": ["user_id"],                                         |  |
|  |    "limit": 10000,                                                |  |
|  |    "window": 3600                                                 |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  |  RULE 6: Expensive endpoint                                       |  |
|  |  {                                                                |  |
|  |    "path": "/api/export/report",                                  |  |
|  |    "key_by": ["user_id"],                                         |  |
|  |    "limit": 5,                                                    |  |
|  |    "window": 86400  // 5 per day                                  |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  RULE EVALUATION                                                        |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  def check_request(request, user):                                |  |
|  |      # Get all matching rules                                     |  |
|  |      rules = get_matching_rules(request.path, request.method,     |  |
|  |                                 user.tier, request.ip)            |  |
|  |                                                                   |  |
|  |      # Sort by priority                                           |  |
|  |      rules.sort(key=lambda r: r.priority)                         |  |
|  |                                                                   |  |
|  |      # Check ALL applicable rules                                 |  |
|  |      for rule in rules:                                           |  |
|  |          key = build_key(rule, request, user)                     |  |
|  |          allowed = check_rate_limit(key, rule.limit,              |  |
|  |                                     rule.window)                  |  |
|  |          if not allowed:                                          |  |
|  |              return RateLimitExceeded(rule)                       |  |
|  |                                                                   |  |
|  |      return Allowed()                                             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.3: MULTI-TIER RATE LIMITING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HIERARCHICAL RATE LIMITS                                               |
|                                                                         |
|  Apply multiple limits simultaneously:                                  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  USER: john@example.com                                           |  |
|  |                                                                   |  |
|  |  +-----------------------------------------------------------+    |  |
|  |  | LIMIT 1: 10 requests per second                          |     |  |
|  |  | Purpose: Prevent rapid bursts                            |     |  |
|  |  +-----------------------------------------------------------+    |  |
|  |  | LIMIT 2: 500 requests per minute                         |     |  |
|  |  | Purpose: Sustained rate limit                            |     |  |
|  |  +-----------------------------------------------------------+    |  |
|  |  | LIMIT 3: 10,000 requests per hour                        |     |  |
|  |  | Purpose: Quota management                                |     |  |
|  |  +-----------------------------------------------------------+    |  |
|  |  | LIMIT 4: 100,000 requests per day                        |     |  |
|  |  | Purpose: Daily quota                                     |     |  |
|  |  +-----------------------------------------------------------+    |  |
|  |                                                                   |  |
|  |  ALL limits must pass for request to be allowed                   |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  IMPLEMENTATION:                                                        |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  def check_multi_tier(user_id):                                   |  |
|  |      limits = [                                                   |  |
|  |          ("second", 10, 1),                                       |  |
|  |          ("minute", 500, 60),                                     |  |
|  |          ("hour", 10000, 3600),                                   |  |
|  |          ("day", 100000, 86400)                                   |  |
|  |      ]                                                            |  |
|  |                                                                   |  |
|  |      for name, limit, window in limits:                           |  |
|  |          key = f"ratelimit:{user_id}:{name}"                      |  |
|  |          if not check_sliding_window(key, limit, window):         |  |
|  |              return False, f"Exceeded {name}ly limit"             |  |
|  |      return True, None                                            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  COST-BASED RATE LIMITING                                               |
|                                                                         |
|  Different endpoints have different "costs":                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  endpoint_costs = {                                               |  |
|  |      "GET /api/users":      1,    # Cheap read                    |  |
|  |      "POST /api/users":     5,    # Moderate write                |  |
|  |      "POST /api/search":    10,   # Expensive query               |  |
|  |      "POST /api/export":    100,  # Very expensive                |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  |  User quota: 1000 points per hour                                 |  |
|  |                                                                   |  |
|  |  def check_with_cost(user_id, endpoint):                          |  |
|  |      cost = endpoint_costs.get(endpoint, 1)                       |  |
|  |      key = f"ratelimit:cost:{user_id}"                            |  |
|  |                                                                   |  |
|  |      # Use token bucket with variable cost                        |  |
|  |      return token_bucket_check(key, cost,                         |  |
|  |                                capacity=1000,                     |  |
|  |                                refill_rate=1000/3600)             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.4: MONITORING AND OBSERVABILITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY METRICS TO TRACK                                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. RATE LIMIT METRICS                                            |  |
|  |                                                                   |  |
|  |  ratelimit_requests_total{status="allowed|denied"}                |  |
|  |  ratelimit_denied_total{rule="...", user_tier="..."}              |  |
|  |  ratelimit_current_usage{user_id="...", limit="..."}              |  |
|  |                                                                   |  |
|  |  2. LATENCY METRICS                                               |  |
|  |                                                                   |  |
|  |  ratelimit_check_duration_seconds (histogram)                     |  |
|  |  redis_command_duration_seconds                                   |  |
|  |                                                                   |  |
|  |  3. REDIS HEALTH                                                  |  |
|  |                                                                   |  |
|  |  redis_connection_pool_size                                       |  |
|  |  redis_connection_errors_total                                    |  |
|  |  redis_command_errors_total                                       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ALERTING                                                               |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  ALERT: High Rate Limit Denials                                   |  |
|  |  IF rate(ratelimit_denied_total[5m]) > 100                        |  |
|  |  FOR 5 minutes                                                    |  |
|  |  > Possible attack or need to adjust limits                       |  |
|  |                                                                   |  |
|  |  ALERT: Rate Limiter Latency High                                 |  |
|  |  IF histogram_quantile(0.99, ratelimit_check_duration) > 10ms     |  |
|  |  FOR 5 minutes                                                    |  |
|  |  > Redis performance issue                                        |  |
|  |                                                                   |  |
|  |  ALERT: Redis Connection Failures                                 |  |
|  |  IF rate(redis_connection_errors_total[1m]) > 0                   |  |
|  |  FOR 1 minute                                                     |  |
|  |  > Redis connectivity issue                                       |  |
|  |                                                                   |  |
|  |  ALERT: User Approaching Limit                                    |  |
|  |  IF ratelimit_current_usage / ratelimit_limit > 0.8               |  |
|  |  > Notify user to upgrade or slow down                            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  LOGGING                                                                |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  // Log rate limit denials                                        |  |
|  |  {                                                                |  |
|  |    "event": "rate_limit_exceeded",                                |  |
|  |    "user_id": "user_123",                                         |  |
|  |    "ip": "1.2.3.4",                                               |  |
|  |    "endpoint": "/api/search",                                     |  |
|  |    "rule": "hourly_limit",                                        |  |
|  |    "current_count": 1001,                                         |  |
|  |    "limit": 1000,                                                 |  |
|  |    "retry_after": 3599,                                           |  |
|  |    "timestamp": "2024-01-15T10:30:00Z"                            |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  |  // Log suspicious patterns                                       |  |
|  |  {                                                                |  |
|  |    "event": "suspicious_activity",                                |  |
|  |    "ip": "1.2.3.4",                                               |  |
|  |    "pattern": "repeated_rate_limit_hits",                         |  |
|  |    "denials_last_hour": 500,                                      |  |
|  |    "recommendation": "consider_blocking"                          |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.5: QUICK REFERENCE CHEAT SHEET

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RATE LIMITER DESIGN SUMMARY                                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  ALGORITHMS:                                                      |  |
|  |  * Token Bucket - Allows bursts, used by AWS/Stripe               |  |
|  |  * Leaky Bucket - Smooth output, used by NGINX                    |  |
|  |  * Fixed Window - Simple but has boundary problem                 |  |
|  |  * Sliding Log - Accurate but memory intensive                    |  |
|  |  * Sliding Window Counter -  Best balance (recommended)           |  |
|  |                                                                   |  |
|  |  PLACEMENT:                                                       |  |
|  |  * API Gateway - Centralized, no app changes needed               |  |
|  |  * Application Middleware - Access to user context                |  |
|  |  * Both (layered) - Best practice                                 |  |
|  |                                                                   |  |
|  |  STORAGE:                                                         |  |
|  |  * Redis -  Best choice (fast, atomic, TTL, clustering)           |  |
|  |  * Local Memory - Single server only                              |  |
|  |  * Database - Too slow                                            |  |
|  |                                                                   |  |
|  |  DISTRIBUTED CHALLENGES:                                          |  |
|  |  * Race conditions > Atomic ops (INCR, Lua scripts)               |  |
|  |  * Redis down > Fail open with local fallback                     |  |
|  |  * Latency > Pipeline commands, local cache                       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  REDIS KEY PATTERNS                                                     |
|                                                                         |
|  Fixed Window:    ratelimit:{user}:{window_number}                      |
|  Sliding Window:  ratelimit:{user}:{curr_window}                        |
|                   ratelimit:{user}:{prev_window}                        |
|  Token Bucket:    ratelimit:{user} > {tokens, last_refill}              |
|  Sliding Log:     ratelimit:{user} > sorted set of timestamps           |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  RESPONSE HEADERS                                                       |
|                                                                         |
|  X-RateLimit-Limit: 100       # Max allowed                             |
|  X-RateLimit-Remaining: 45    # Remaining quota                         |
|  X-RateLimit-Reset: 164000..  # Unix timestamp of reset                 |
|  Retry-After: 30              # Seconds until OK to retry               |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  INTERVIEW CHECKLIST                                                    |
|                                                                         |
|  o Clarify: What to limit? What rate? Distributed?                      |
|  o Choose algorithm (default: Sliding Window Counter)                   |
|  o Design: Client > Gateway > Rate Limiter > Service                    |
|  o Storage: Redis (centralized counters)                                |
|  o Handle race conditions (atomic ops)                                  |
|  o Handle Redis failure (fail open + local fallback)                    |
|  o Support multiple dimensions (user, IP, API key)                      |
|  o Support tiered limits (free vs premium)                              |
|  o Return proper headers (429, Retry-After)                             |
|  o Monitoring and alerting                                              |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  SLIDING WINDOW COUNTER CODE                                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  def check_rate_limit(user_id, limit=100, window=60):             |  |
|  |      now = time.time()                                            |  |
|  |      curr_window = int(now // window)                             |  |
|  |      prev_window = curr_window - 1                                |  |
|  |                                                                   |  |
|  |      curr_key = f"rl:{user_id}:{curr_window}"                     |  |
|  |      prev_key = f"rl:{user_id}:{prev_window}"                     |  |
|  |                                                                   |  |
|  |      prev_count = int(redis.get(prev_key) or 0)                   |  |
|  |      curr_count = int(redis.get(curr_key) or 0)                   |  |
|  |                                                                   |  |
|  |      elapsed = now - (curr_window * window)                       |  |
|  |      overlap = (window - elapsed) / window                        |  |
|  |                                                                   |  |
|  |      estimated = prev_count * overlap + curr_count                |  |
|  |                                                                   |  |
|  |      if estimated >= limit:                                       |  |
|  |          return False                                             |  |
|  |                                                                   |  |
|  |      redis.incr(curr_key)                                         |  |
|  |      redis.expire(curr_key, window * 2)                           |  |
|  |      return True                                                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## ADVANCED TOPICS & REAL-WORLD PROBLEMS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HOT KEY / HOT PARTITION PROBLEM                                        |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Problem: Popular API key (e.g., Twitter API) generates           |  |
|  |           millions of requests > single Redis key hammered        |  |
|  |                                                                   |  |
|  |  +-----------------------------------------------------------+    |  |
|  |  |                                                           |    |  |
|  |  |  API Key "twitter_official" > 100,000 req/sec            |     |  |
|  |  |       |                                                   |    |  |
|  |  |       v                                                   |    |  |
|  |  |  Redis Key: ratelimit:twitter_official                   |     |  |
|  |  |  This single key gets 100K INCR/sec > Hot key!           |     |  |
|  |  |                                                           |    |  |
|  |  +-----------------------------------------------------------+    |  |
|  |                                                                   |  |
|  |  Solutions:                                                       |  |
|  |                                                                   |  |
|  |  1. KEY SHARDING                                                  |  |
|  |     * Split into N sub-keys: ratelimit:twitter:0, :1, :2...       |  |
|  |     * Each request randomly picks a shard                         |  |
|  |     * Sum all shards for total count                              |  |
|  |     * Trade-off: Less accuracy, more complex                      |  |
|  |                                                                   |  |
|  |  2. LOCAL COUNTING + SYNC                                         |  |
|  |     * Count locally on each server                                |  |
|  |     * Sync to Redis every 1 second                                |  |
|  |     * Global count = local counts + last synced Redis count       |  |
|  |     * Trade-off: Up to 1 second inaccuracy                        |  |
|  |                                                                   |  |
|  |  3. PROBABILISTIC COUNTING                                        |  |
|  |     * Only check Redis with probability P (e.g., 10%)             |  |
|  |     * Other 90% allowed locally                                   |  |
|  |     * Effective limit: actual_limit / P                           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  THUNDERING HERD PROBLEM                                                |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Problem: Rate limit window resets > all blocked requests         |  |
|  |           retry at exactly same moment > spike                    |  |
|  |                                                                   |  |
|  |  +-----------------------------------------------------------+    |  |
|  |  |                                                           |    |  |
|  |  |  Window 1        |        Window 2                        |    |  |
|  |  |  -----------------+-----------------                       |   |  |
|  |  |      [100 req]    |                                        |   |  |
|  |  |  [BLOCKED] [BLOCKED] [BLOCKED]                            |    |  |
|  |  |                   |                                        |   |  |
|  |  |                   | < All retries hit here!               |    |  |
|  |  |                   |   [SPIKE of 500 requests]             |    |  |
|  |  |                                                           |    |  |
|  |  +-----------------------------------------------------------+    |  |
|  |                                                                   |  |
|  |  Solutions:                                                       |  |
|  |                                                                   |  |
|  |  1. JITTERED RETRY-AFTER                                          |  |
|  |     * Don't return exact reset time                               |  |
|  |     * Add random jitter: Retry-After: 30 + random(0, 10)          |  |
|  |     * Spreads retries over 10 second window                       |  |
|  |                                                                   |  |
|  |  2. SLIDING WINDOW (Built-in solution)                            |  |
|  |     * No hard reset point > gradual limit recovery                |  |
|  |     * Requests naturally spread                                   |  |
|  |                                                                   |  |
|  |  3. EXPONENTIAL BACKOFF ON CLIENT                                 |  |
|  |     * Clients should implement exponential backoff                |  |
|  |     * First retry: 1s, then 2s, 4s, 8s...                         |  |
|  |     * With jitter                                                 |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  DDoS PROTECTION (Beyond Rate Limiting)                                 |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Rate limiting is NOT enough for DDoS:                            |  |
|  |  * Attacker uses millions of IPs > each under limit               |  |
|  |  * Total traffic still overwhelms system                          |  |
|  |                                                                   |  |
|  |  Additional Layers:                                               |  |
|  |                                                                   |  |
|  |  1. CDN/WAF (Cloudflare, AWS WAF)                                 |  |
|  |     * Absorb traffic at edge                                      |  |
|  |     * Geographic blocking                                         |  |
|  |     * Known bad IP lists                                          |  |
|  |                                                                   |  |
|  |  2. BOT DETECTION                                                 |  |
|  |     * CAPTCHA for suspicious traffic                              |  |
|  |     * JavaScript challenge (bots can't execute JS)                |  |
|  |     * Device fingerprinting                                       |  |
|  |     * Behavioral analysis (mouse movements, timing)               |  |
|  |                                                                   |  |
|  |  3. GLOBAL RATE LIMITS                                            |  |
|  |     * Not just per-user, but total requests/second                |  |
|  |     * If global > threshold, enable CAPTCHA for all               |  |
|  |     * Shed load by priority (logged-in users first)               |  |
|  |                                                                   |  |
|  |  4. CIRCUIT BREAKER                                               |  |
|  |     * If error rate > 50%, stop accepting new requests            |  |
|  |     * Return 503 to preserve system                               |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ADAPTIVE / DYNAMIC RATE LIMITING                                       |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Static limits are suboptimal:                                    |  |
|  |  * Off-peak: Limit 100/min but system can handle 1000             |  |
|  |  * Peak: Limit 100/min but system overloaded                      |  |
|  |                                                                   |  |
|  |  ADAPTIVE LIMITING:                                               |  |
|  |                                                                   |  |
|  |  Adjust limits based on system health:                            |  |
|  |                                                                   |  |
|  |  def get_dynamic_limit(base_limit):                               |  |
|  |      cpu_usage = get_avg_cpu()                                    |  |
|  |      latency_p99 = get_latency_p99()                              |  |
|  |      error_rate = get_error_rate()                                |  |
|  |                                                                   |  |
|  |      # Healthy system: allow more                                 |  |
|  |      if cpu_usage < 50 and latency_p99 < 100 and err < 1%:        |  |
|  |          return base_limit * 2                                    |  |
|  |                                                                   |  |
|  |      # Stressed system: reduce limit                              |  |
|  |      if cpu_usage > 80 or latency_p99 > 500 or err > 5%:          |  |
|  |          return base_limit * 0.5                                  |  |
|  |                                                                   |  |
|  |      return base_limit                                            |  |
|  |                                                                   |  |
|  |  AIMD (Additive Increase, Multiplicative Decrease):               |  |
|  |  * Similar to TCP congestion control                              |  |
|  |  * Slowly increase limit when healthy                             |  |
|  |  * Quickly decrease when issues detected                          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  COST-BASED RATE LIMITING                                               |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Problem: Not all requests are equal                              |  |
|  |  * GET /users/123 > Cheap (cache hit)                             |  |
|  |  * POST /search > Expensive (full-text search)                    |  |
|  |  * POST /export > Very expensive (generate large report)          |  |
|  |                                                                   |  |
|  |  Solution: Cost-based limiting                                    |  |
|  |                                                                   |  |
|  |  +--------------------+-----------------------------------------+ |  |
|  |  | Endpoint           | Cost (units)                            | |  |
|  |  +--------------------+-----------------------------------------+ |  |
|  |  | GET /users/{id}    | 1                                       | |  |
|  |  | GET /users/search  | 5                                       | |  |
|  |  | POST /users        | 3                                       | |  |
|  |  | POST /export       | 50                                      | |  |
|  |  | POST /bulk-import  | 100                                     | |  |
|  |  +--------------------+-----------------------------------------+ |  |
|  |                                                                   |  |
|  |  User limit: 1000 units/minute (not 1000 requests)                |  |
|  |                                                                   |  |
|  |  * 1000 simple GETs = at limit                                    |  |
|  |  * 200 searches = at limit                                        |  |
|  |  * 20 exports = at limit                                          |  |
|  |                                                                   |  |
|  |  Implementation: Token bucket with variable deduction             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  RATE LIMITING BY MULTIPLE DIMENSIONS                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Real systems need multiple overlapping limits:                   |  |
|  |                                                                   |  |
|  |  +-----------------------------------------------------------+    |  |
|  |  |                                                           |    |  |
|  |  |  REQUEST                                                  |    |  |
|  |  |     |                                                     |    |  |
|  |  |     v                                                     |    |  |
|  |  |  [IP Limit: 100/min] --> FAIL if exceeded                |     |  |
|  |  |     |                                                     |    |  |
|  |  |     v                                                     |    |  |
|  |  |  [User Limit: 1000/min] --> FAIL if exceeded             |     |  |
|  |  |     |                                                     |    |  |
|  |  |     v                                                     |    |  |
|  |  |  [API Key Limit: 10000/min] --> FAIL if exceeded         |     |  |
|  |  |     |                                                     |    |  |
|  |  |     v                                                     |    |  |
|  |  |  [Endpoint Limit: 50/min for /export] --> FAIL           |     |  |
|  |  |     |                                                     |    |  |
|  |  |     v                                                     |    |  |
|  |  |  [Global Limit: 100K/min total] --> FAIL                 |     |  |
|  |  |     |                                                     |    |  |
|  |  |     v                                                     |    |  |
|  |  |  ALLOW                                                    |    |  |
|  |  |                                                           |    |  |
|  |  +-----------------------------------------------------------+    |  |
|  |                                                                   |  |
|  |  Must pass ALL limits to proceed.                                 |  |
|  |  Response should indicate which limit was hit.                    |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  BYPASS / WHITELIST FOR TRUSTED SERVICES                                |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Not everyone should be rate limited:                             |  |
|  |                                                                   |  |
|  |  * Internal services (service mesh)                               |  |
|  |  * Health check endpoints (/health, /ready)                       |  |
|  |  * Premium partners with SLA                                      |  |
|  |  * Admin/ops traffic                                              |  |
|  |                                                                   |  |
|  |  Implementation:                                                  |  |
|  |                                                                   |  |
|  |  def should_rate_limit(request):                                  |  |
|  |      # Skip for health checks                                     |  |
|  |      if request.path in ["/health", "/ready"]:                    |  |
|  |          return False                                             |  |
|  |                                                                   |  |
|  |      # Skip for internal services                                 |  |
|  |      if request.header("X-Internal-Service"):                     |  |
|  |          if verify_internal_token(request):                       |  |
|  |              return False                                         |  |
|  |                                                                   |  |
|  |      # Skip for whitelisted IPs                                   |  |
|  |      if request.client_ip in WHITELIST:                           |  |
|  |          return False                                             |  |
|  |                                                                   |  |
|  |      return True                                                  |  |
|  |                                                                   |  |
|  |  Security: Whitelist bypass must be secured!                      |  |
|  |  * Don't trust headers from public internet                       |  |
|  |  * Verify at load balancer / ingress level                        |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  GRACEFUL DEGRADATION                                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  When rate limited, don't just reject - degrade gracefully:       |  |
|  |                                                                   |  |
|  |  1. THROTTLING (Slow down instead of reject)                      |  |
|  |     * Queue requests, process slowly                              |  |
|  |     * User waits longer but gets response                         |  |
|  |     * Good for background jobs                                    |  |
|  |                                                                   |  |
|  |  2. QUALITY DEGRADATION                                           |  |
|  |     * Return cached/stale data instead of fresh                   |  |
|  |     * Return simplified response (fewer fields)                   |  |
|  |     * "Results limited due to high traffic"                       |  |
|  |                                                                   |  |
|  |  3. PRIORITY SHEDDING                                             |  |
|  |     * When overloaded, serve by priority:                         |  |
|  |       1. Logged-in users                                          |  |
|  |       2. Paid users                                               |  |
|  |       3. Anonymous users (rate limit first)                       |  |
|  |                                                                   |  |
|  |  4. RETRY QUEUE                                                   |  |
|  |     * Don't reject, queue for later processing                    |  |
|  |     * Return 202 Accepted with callback URL                       |  |
|  |     * Async notification when processed                           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

END OF CHAPTER 3 - RATE LIMITER SYSTEM DESIGN
