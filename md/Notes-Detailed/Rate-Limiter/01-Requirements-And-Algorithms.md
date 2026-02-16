# RATE LIMITER SYSTEM DESIGN

CHAPTER 1: REQUIREMENTS AND RATE LIMITING ALGORITHMS
## TABLE OF CONTENTS
*-----------------*
*1. Why Rate Limiting?*
*2. Requirements*
*3. Rate Limiting Algorithms*
*4. Algorithm Comparison*
*5. Choosing the Right Algorithm*

SECTION 1.1: WHY RATE LIMITING?
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHAT IS RATE LIMITING?                                                |*
*|                                                                         |*
*|  Rate limiting controls the rate of requests a client can make to     |*
*|  a service within a specified time window.                            |*
*|                                                                         |*
*|  Example: "Max 100 requests per minute per user"                      |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  WHY DO WE NEED IT?                                                    |*
*|                                                                         |*
*|  1. PREVENT ABUSE / DOS ATTACKS                                       |*
*|     * Malicious actors flooding your service                         |*
*|     * Bot attacks                                                      |*
*|     * Credential stuffing                                              |*
*|                                                                         |*
*|  2. PROTECT RESOURCES                                                  |*
*|     * Prevent server overload                                         |*
*|     * Protect downstream dependencies (databases, APIs)              |*
*|     * Fair resource allocation                                        |*
*|                                                                         |*
*|  3. COST CONTROL                                                       |*
*|     * Prevent runaway API costs                                       |*
*|     * Control cloud resource usage                                    |*
*|     * Limit expensive operations                                      |*
*|                                                                         |*
*|  4. ENSURE FAIR USAGE                                                  |*
*|     * Prevent single user from monopolizing resources                |*
*|     * Multi-tenant systems: isolate tenant impact                    |*
*|     * Maintain SLA for all users                                     |*
*|                                                                         |*
*|  5. MONETIZATION                                                       |*
*|     * API tiers (Free: 100/day, Pro: 10K/day)                       |*
*|     * Upsell to higher tiers                                         |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  REAL-WORLD EXAMPLES                                                  |*
*|                                                                         |*
*|  +----------------+-------------------------------------------------+ |*
*|  | Service        | Rate Limit                                       | |*
*|  +----------------+-------------------------------------------------+ |*
*|  | Twitter API    | 300 requests / 15 min window                    | |*
*|  | GitHub API     | 5000 requests / hour (authenticated)            | |*
*|  | Stripe API     | 100 requests / second                           | |*
*|  | Google Maps    | 50 requests / second                            | |*
*|  | AWS API GW     | 10,000 requests / second (default)              | |*
*|  | Discord        | Varies by endpoint (50/s for messages)          | |*
*|  +----------------+-------------------------------------------------+ |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 1.2: REQUIREMENTS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  FUNCTIONAL REQUIREMENTS                                               |*
*|                                                                         |*
*|  1. Limit requests based on configurable rules                        |*
*|     * Per user / API key / IP address                                |*
*|     * Per endpoint / resource                                         |*
*|     * Global limits                                                    |*
*|                                                                         |*
*|  2. Support different time windows                                    |*
*|     * Per second, minute, hour, day                                  |*
*|     * Sliding vs fixed windows                                        |*
*|                                                                         |*
*|  3. Return appropriate responses                                      |*
*|     * Allow request if within limit                                  |*
*|     * Reject with 429 (Too Many Requests) if exceeded               |*
*|     * Include rate limit headers (X-RateLimit-*)                    |*
*|                                                                         |*
*|  4. Support multiple rate limit rules                                 |*
*|     * Example: 10 req/sec AND 1000 req/hour                         |*
*|     * Hierarchical: user limit + global limit                        |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  NON-FUNCTIONAL REQUIREMENTS                                           |*
*|                                                                         |*
*|  1. LOW LATENCY                                                        |*
*|     * Rate check must be fast (< 1ms)                                |*
*|     * Cannot add significant overhead to requests                    |*
*|                                                                         |*
*|  2. HIGH AVAILABILITY                                                  |*
*|     * Rate limiter down = security risk                              |*
*|     * Must be fault-tolerant                                         |*
*|                                                                         |*
*|  3. SCALABILITY                                                        |*
*|     * Handle millions of requests per second                         |*
*|     * Work across distributed system                                 |*
*|                                                                         |*
*|  4. ACCURACY                                                           |*
*|     * Should be reasonably accurate                                  |*
*|     * Small variance acceptable (not exact)                          |*
*|                                                                         |*
*|  5. DISTRIBUTED                                                        |*
*|     * Work across multiple servers                                   |*
*|     * Consistent limiting regardless of which server handles request |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  RATE LIMIT HEADERS (RFC 6585)                                        |*
*|                                                                         |*
*|  Response headers to inform clients:                                  |*
*|                                                                         |*
*|  HTTP/1.1 200 OK                                                      |*
*|  X-RateLimit-Limit: 100           # Max requests allowed            |*
*|  X-RateLimit-Remaining: 45        # Requests remaining              |*
*|  X-RateLimit-Reset: 1640000000    # Unix timestamp when reset       |*
*|                                                                         |*
*|  HTTP/1.1 429 Too Many Requests                                       |*
*|  Retry-After: 30                  # Seconds until retry OK          |*
*|  X-RateLimit-Limit: 100                                               |*
*|  X-RateLimit-Remaining: 0                                             |*
*|  X-RateLimit-Reset: 1640000000                                        |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 1.3: RATE LIMITING ALGORITHMS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  ALGORITHM 1: TOKEN BUCKET                                            |*
*|  ============================                                          |*
*|                                                                         |*
*|  Concept: Bucket holds tokens, requests consume tokens.               |*
*|           Tokens refill at a constant rate.                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |        +-------------------+                                   |  |*
*|  |        |  Token Bucket     |                                   |  |*
*|  |        |                   |  Capacity: 10 tokens              |  |*
*|  |        |  oooooooooo      |  Current: 7 tokens                |  |*
*|  |        |                   |  Refill: 1 token/second           |  |*
*|  |        +---------+---------+                                   |  |*
*|  |                  |                                              |  |*
*|  |    Tokens -------+                                              |  |*
*|  |    refill                                                       |  |*
*|  |    over time                                                    |  |*
*|  |                                                                 |  |*
*|  |  REQUEST:                                                       |  |*
*|  |  - If tokens >= 1: Remove 1 token, ALLOW request               |  |*
*|  |  - If tokens < 1: DENY request (429)                           |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  PARAMETERS:                                                           |*
*|  * Bucket capacity (burst size)                                       |*
*|  * Refill rate (tokens per second)                                   |*
*|                                                                         |*
*|  IMPLEMENTATION:                                                       |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  class TokenBucket:                                            |  |*
*|  |      def __init__(self, capacity, refill_rate):               |  |*
*|  |          self.capacity = capacity                              |  |*
*|  |          self.tokens = capacity                                |  |*
*|  |          self.refill_rate = refill_rate  # tokens per second  |  |*
*|  |          self.last_refill = time.time()                       |  |*
*|  |                                                                 |  |*
*|  |      def allow_request(self, tokens_needed=1):                |  |*
*|  |          self._refill()                                        |  |*
*|  |                                                                 |  |*
*|  |          if self.tokens >= tokens_needed:                     |  |*
*|  |              self.tokens -= tokens_needed                     |  |*
*|  |              return True                                       |  |*
*|  |          return False                                          |  |*
*|  |                                                                 |  |*
*|  |      def _refill(self):                                        |  |*
*|  |          now = time.time()                                    |  |*
*|  |          elapsed = now - self.last_refill                     |  |*
*|  |          tokens_to_add = elapsed * self.refill_rate          |  |*
*|  |          self.tokens = min(self.capacity,                     |  |*
*|  |                            self.tokens + tokens_to_add)       |  |*
*|  |          self.last_refill = now                               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  REDIS IMPLEMENTATION (Atomic):                                       |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  -- KEYS[1] = bucket key (e.g., "ratelimit:user:123")        |  |*
*|  |  -- ARGV[1] = capacity                                        |  |*
*|  |  -- ARGV[2] = refill_rate                                     |  |*
*|  |  -- ARGV[3] = now (timestamp)                                 |  |*
*|  |  -- ARGV[4] = tokens_needed                                   |  |*
*|  |                                                                 |  |*
*|  |  local bucket = redis.call('HMGET', KEYS[1], 'tokens', 'ts') |  |*
*|  |  local tokens = tonumber(bucket[1]) or tonumber(ARGV[1])     |  |*
*|  |  local last_ts = tonumber(bucket[2]) or tonumber(ARGV[3])    |  |*
*|  |                                                                 |  |*
*|  |  local elapsed = tonumber(ARGV[3]) - last_ts                  |  |*
*|  |  tokens = math.min(tonumber(ARGV[1]),                         |  |*
*|  |                    tokens + elapsed * tonumber(ARGV[2]))      |  |*
*|  |                                                                 |  |*
*|  |  if tokens >= tonumber(ARGV[4]) then                          |  |*
*|  |      tokens = tokens - tonumber(ARGV[4])                      |  |*
*|  |      redis.call('HMSET', KEYS[1], 'tokens', tokens,          |  |*
*|  |                                   'ts', ARGV[3])              |  |*
*|  |      redis.call('EXPIRE', KEYS[1], 3600)                     |  |*
*|  |      return 1  -- allowed                                     |  |*
*|  |  else                                                          |  |*
*|  |      return 0  -- denied                                      |  |*
*|  |  end                                                           |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  PROS:                                                                 |*
*|  Y Allows burst traffic (up to bucket capacity)                      |*
*|  Y Memory efficient (just 2 values per user)                         |*
*|  Y Widely used (AWS, Stripe)                                         |*
*|                                                                         |*
*|  CONS:                                                                 |*
*|  X Two parameters to tune (capacity + rate)                          |*
*|  X Hard to set optimal values                                        |*
*|                                                                         |*
*|  USE WHEN: You want to allow bursts but control average rate         |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  ALGORITHM 2: LEAKY BUCKET                                            |*
*|  ==========================                                            |*
*|                                                                         |*
*|  Concept: Requests enter a queue (bucket). Processed at constant rate.|*
*|           Bucket overflow = rejected requests.                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Requests    +-----------------+                               |  |*
*|  |      |       |                 |  Queue (bucket)               |  |*
*|  |      v       |  # # # # # #   |  Capacity: 10                 |  |*
*|  |   ------>    |                 |                               |  |*
*|  |              +--------+--------+                               |  |*
*|  |                       |                                         |  |*
*|  |                       v  Leak at constant rate                 |  |*
*|  |                    #---->  Process 1 req/second                |  |*
*|  |                                                                 |  |*
*|  |  If bucket full > REJECT (overflow)                           |  |*
*|  |  Else > Add to queue, process at fixed rate                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  DIFFERENCE FROM TOKEN BUCKET:                                        |*
*|  * Token bucket: controls rate of requests ALLOWED                   |*
*|  * Leaky bucket: controls rate of requests PROCESSED                 |*
*|                                                                         |*
*|  IMPLEMENTATION:                                                       |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  class LeakyBucket:                                            |  |*
*|  |      def __init__(self, capacity, leak_rate):                 |  |*
*|  |          self.capacity = capacity                              |  |*
*|  |          self.water = 0  # current queue size                 |  |*
*|  |          self.leak_rate = leak_rate  # requests/second        |  |*
*|  |          self.last_leak = time.time()                         |  |*
*|  |                                                                 |  |*
*|  |      def allow_request(self):                                  |  |*
*|  |          self._leak()                                          |  |*
*|  |                                                                 |  |*
*|  |          if self.water < self.capacity:                       |  |*
*|  |              self.water += 1                                   |  |*
*|  |              return True                                       |  |*
*|  |          return False  # bucket overflow                      |  |*
*|  |                                                                 |  |*
*|  |      def _leak(self):                                          |  |*
*|  |          now = time.time()                                    |  |*
*|  |          elapsed = now - self.last_leak                       |  |*
*|  |          leaked = elapsed * self.leak_rate                    |  |*
*|  |          self.water = max(0, self.water - leaked)             |  |*
*|  |          self.last_leak = now                                 |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  PROS:                                                                 |*
*|  Y Smooth output rate (no bursts)                                    |*
*|  Y Good for rate shaping                                             |*
*|  Y Protects downstream services                                      |*
*|                                                                         |*
*|  CONS:                                                                 |*
*|  X Can queue requests (added latency)                                |*
*|  X Doesn't handle bursts well                                        |*
*|  X May need actual queue (memory)                                    |*
*|                                                                         |*
*|  USE WHEN: Need constant processing rate (e.g., message queues)      |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  ALGORITHM 3: FIXED WINDOW COUNTER                                    |*
*|  =================================                                     |*
*|                                                                         |*
*|  Concept: Divide time into fixed windows. Count requests per window.  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Timeline (1-minute windows, limit=100):                       |  |*
*|  |                                                                 |  |*
*|  |  +--------------+--------------+--------------+------------+  |  |*
*|  |  | 12:00-12:01  | 12:01-12:02  | 12:02-12:03  | 12:03-... |  |  |*
*|  |  |              |              |              |            |  |  |*
*|  |  |  Count: 87   |  Count: 45   |  Count: 100  |  Count: 12|  |  |*
*|  |  |  (allowed)   |  (allowed)   |  (at limit)  |  (allowed)|  |  |*
*|  |  +--------------+--------------+--------------+------------+  |  |*
*|  |                                                                 |  |*
*|  |  When window changes: counter resets to 0                     |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  IMPLEMENTATION:                                                       |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  class FixedWindowCounter:                                     |  |*
*|  |      def __init__(self, limit, window_size_seconds):          |  |*
*|  |          self.limit = limit                                    |  |*
*|  |          self.window_size = window_size_seconds               |  |*
*|  |          self.current_window = 0                               |  |*
*|  |          self.counter = 0                                      |  |*
*|  |                                                                 |  |*
*|  |      def allow_request(self):                                  |  |*
*|  |          window = int(time.time() / self.window_size)        |  |*
*|  |                                                                 |  |*
*|  |          if window != self.current_window:                    |  |*
*|  |              # New window, reset counter                      |  |*
*|  |              self.current_window = window                     |  |*
*|  |              self.counter = 0                                  |  |*
*|  |                                                                 |  |*
*|  |          if self.counter < self.limit:                        |  |*
*|  |              self.counter += 1                                 |  |*
*|  |              return True                                       |  |*
*|  |          return False                                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  REDIS IMPLEMENTATION:                                                 |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  def check_rate_limit(user_id, limit=100, window=60):         |  |*
*|  |      window_key = int(time.time() / window)                   |  |*
*|  |      key = f"ratelimit:{user_id}:{window_key}"               |  |*
*|  |                                                                 |  |*
*|  |      current = redis.incr(key)                                |  |*
*|  |      if current == 1:                                          |  |*
*|  |          redis.expire(key, window)  # Auto-cleanup            |  |*
*|  |                                                                 |  |*
*|  |      return current <= limit                                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|    BOUNDARY PROBLEM:                                                 |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Limit: 100 requests per minute                                |  |*
*|  |                                                                 |  |*
*|  |     Window 1         |        Window 2                         |  |*
*|  |  -------------------+--------------------                      |  |*
*|  |        ...[100 req]  |  [100 req]...                           |  |*
*|  |            +---------+---------+                               |  |*
*|  |              1 sec     1 sec                                   |  |*
*|  |                                                                 |  |*
*|  |  User sends 100 requests at 12:00:59                          |  |*
*|  |  User sends 100 requests at 12:01:01                          |  |*
*|  |  Total: 200 requests in 2 seconds! (2x the intended limit)   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  PROS:                                                                 |*
*|  Y Very simple to implement                                          |*
*|  Y Memory efficient (1 counter per window)                           |*
*|  Y Fast                                                               |*
*|                                                                         |*
*|  CONS:                                                                 |*
*|  X Boundary problem (burst at window edges)                          |*
*|  X Not truly accurate                                                 |*
*|                                                                         |*
*|  USE WHEN: Simplicity matters more than precision                    |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  ALGORITHM 4: SLIDING WINDOW LOG                                      |*
*|  ===============================                                       |*
*|                                                                         |*
*|  Concept: Store timestamp of each request. Count requests in sliding  |*
*|           window looking back from current time.                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Limit: 5 requests per 60 seconds                              |  |*
*|  |  Current time: 12:01:30                                        |  |*
*|  |                                                                 |  |*
*|  |  Request log (sorted by timestamp):                            |  |*
*|  |  [12:00:20, 12:00:45, 12:01:00, 12:01:10, 12:01:25]           |  |*
*|  |      |          |          |          |          |             |  |*
*|  |      v          |          |          |          |             |  |*
*|  |   EXPIRED      |          |          |          |             |  |*
*|  |   (> 60s ago)  +----------+----------+----------+             |  |*
*|  |                        4 requests in window                    |  |*
*|  |                                                                 |  |*
*|  |  Window: [12:00:30 ---------------------------- 12:01:30]     |  |*
*|  |                                                                 |  |*
*|  |  Count = 4 (< 5 limit) > ALLOW new request                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  IMPLEMENTATION:                                                       |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  class SlidingWindowLog:                                       |  |*
*|  |      def __init__(self, limit, window_seconds):               |  |*
*|  |          self.limit = limit                                    |  |*
*|  |          self.window = window_seconds                          |  |*
*|  |          self.timestamps = []  # sorted list                  |  |*
*|  |                                                                 |  |*
*|  |      def allow_request(self):                                  |  |*
*|  |          now = time.time()                                    |  |*
*|  |          window_start = now - self.window                     |  |*
*|  |                                                                 |  |*
*|  |          # Remove expired timestamps                          |  |*
*|  |          self.timestamps = [t for t in self.timestamps       |  |*
*|  |                             if t > window_start]              |  |*
*|  |                                                                 |  |*
*|  |          if len(self.timestamps) < self.limit:                |  |*
*|  |              self.timestamps.append(now)                      |  |*
*|  |              return True                                       |  |*
*|  |          return False                                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  REDIS IMPLEMENTATION (Sorted Set):                                   |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  def check_rate_limit(user_id, limit=100, window=60):         |  |*
*|  |      key = f"ratelimit:{user_id}"                             |  |*
*|  |      now = time.time()                                        |  |*
*|  |      window_start = now - window                               |  |*
*|  |                                                                 |  |*
*|  |      pipe = redis.pipeline()                                   |  |*
*|  |      # Remove old entries                                      |  |*
*|  |      pipe.zremrangebyscore(key, 0, window_start)              |  |*
*|  |      # Count entries in window                                 |  |*
*|  |      pipe.zcard(key)                                           |  |*
*|  |      # Add current request                                     |  |*
*|  |      pipe.zadd(key, {str(uuid4()): now})                      |  |*
*|  |      # Set expiry                                              |  |*
*|  |      pipe.expire(key, window)                                 |  |*
*|  |      results = pipe.execute()                                  |  |*
*|  |                                                                 |  |*
*|  |      count = results[1]                                        |  |*
*|  |      return count < limit                                      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  PROS:                                                                 |*
*|  Y Very accurate (no boundary issues)                                |*
*|  Y True sliding window                                               |*
*|                                                                         |*
*|  CONS:                                                                 |*
*|  X Memory intensive (stores every timestamp)                         |*
*|  X Slower (cleanup operation)                                        |*
*|  X Doesn't scale for high-volume endpoints                          |*
*|                                                                         |*
*|  USE WHEN: Accuracy critical, low-to-medium volume                   |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  ALGORITHM 5: SLIDING WINDOW COUNTER (Hybrid)  RECOMMENDED          |*
*|  ========================================================              |*
*|                                                                         |*
*|  Concept: Combine fixed window counter with sliding window.           |*
*|           Approximate count based on overlap with previous window.    |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Limit: 100 requests per minute                                |  |*
*|  |  Current time: 12:01:20 (20 seconds into current window)      |  |*
*|  |                                                                 |  |*
*|  |     Previous Window    |    Current Window                     |  |*
*|  |       (12:00-12:01)    |    (12:01-12:02)                     |  |*
*|  |     +-----------------++-------------------+                  |  |*
*|  |     |  count = 60     ||  count = 15       |                  |  |*
*|  |     +-----------------++-------------------+                  |  |*
*|  |                        |                                       |  |*
*|  |               +--------+--------+                              |  |*
*|  |                 40 sec | 20 sec                                |  |*
*|  |                        |                                       |  |*
*|  |  Sliding window: [12:00:20 ------------------- 12:01:20]      |  |*
*|  |                                                                 |  |*
*|  |  Estimated count = prev_count * (1 - position) + curr_count   |  |*
*|  |                  = 60 * (40/60) + 15                           |  |*
*|  |                  = 60 * 0.667 + 15                             |  |*
*|  |                  = 40 + 15 = 55                                |  |*
*|  |                                                                 |  |*
*|  |  55 < 100 > ALLOW                                             |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  FORMULA:                                                              |*
*|  count = prev_window_count * overlap_percentage + curr_window_count  |*
*|                                                                         |*
*|  where overlap_percentage = (window_size - elapsed) / window_size    |*
*|                                                                         |*
*|  IMPLEMENTATION:                                                       |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  class SlidingWindowCounter:                                   |  |*
*|  |      def __init__(self, limit, window_seconds):               |  |*
*|  |          self.limit = limit                                    |  |*
*|  |          self.window = window_seconds                          |  |*
*|  |          self.prev_count = 0                                   |  |*
*|  |          self.curr_count = 0                                   |  |*
*|  |          self.curr_window_start = 0                            |  |*
*|  |                                                                 |  |*
*|  |      def allow_request(self):                                  |  |*
*|  |          now = time.time()                                    |  |*
*|  |          window_start = (now // self.window) * self.window    |  |*
*|  |                                                                 |  |*
*|  |          # Check if we moved to a new window                  |  |*
*|  |          if window_start != self.curr_window_start:           |  |*
*|  |              self.prev_count = self.curr_count                |  |*
*|  |              self.curr_count = 0                               |  |*
*|  |              self.curr_window_start = window_start            |  |*
*|  |                                                                 |  |*
*|  |          # Calculate position in current window               |  |*
*|  |          elapsed = now - window_start                         |  |*
*|  |          overlap = (self.window - elapsed) / self.window      |  |*
*|  |                                                                 |  |*
*|  |          # Weighted count                                      |  |*
*|  |          estimated = self.prev_count * overlap + self.curr_count|*
*|  |                                                                 |  |*
*|  |          if estimated < self.limit:                           |  |*
*|  |              self.curr_count += 1                              |  |*
*|  |              return True                                       |  |*
*|  |          return False                                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  REDIS IMPLEMENTATION:                                                 |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  def check_rate_limit(user_id, limit=100, window=60):         |  |*
*|  |      now = time.time()                                        |  |*
*|  |      curr_window = int(now // window)                         |  |*
*|  |      prev_window = curr_window - 1                            |  |*
*|  |                                                                 |  |*
*|  |      curr_key = f"ratelimit:{user_id}:{curr_window}"         |  |*
*|  |      prev_key = f"ratelimit:{user_id}:{prev_window}"         |  |*
*|  |                                                                 |  |*
*|  |      # Get counts (pipeline for efficiency)                   |  |*
*|  |      pipe = redis.pipeline()                                   |  |*
*|  |      pipe.get(prev_key)                                        |  |*
*|  |      pipe.get(curr_key)                                        |  |*
*|  |      prev_count, curr_count = pipe.execute()                  |  |*
*|  |                                                                 |  |*
*|  |      prev_count = int(prev_count or 0)                        |  |*
*|  |      curr_count = int(curr_count or 0)                        |  |*
*|  |                                                                 |  |*
*|  |      # Calculate overlap                                       |  |*
*|  |      elapsed = now - (curr_window * window)                   |  |*
*|  |      overlap = (window - elapsed) / window                    |  |*
*|  |                                                                 |  |*
*|  |      estimated = prev_count * overlap + curr_count            |  |*
*|  |                                                                 |  |*
*|  |      if estimated < limit:                                     |  |*
*|  |          redis.incr(curr_key)                                  |  |*
*|  |          redis.expire(curr_key, window * 2)                   |  |*
*|  |          return True                                           |  |*
*|  |      return False                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  PROS:                                                                 |*
*|  Y Good balance of accuracy and efficiency                          |*
*|  Y Memory efficient (2 counters)                                     |*
*|  Y Smooth rate limiting (no boundary spikes)                        |*
*|  Y Fast                                                               |*
*|                                                                         |*
*|  CONS:                                                                 |*
*|  X Approximation (not exact)                                         |*
*|  X Slightly more complex than fixed window                          |*
*|                                                                         |*
*|  USE WHEN: Need good accuracy without memory cost                    |*
*|            (Most common choice in production)                        |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 1.4: ALGORITHM COMPARISON
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  COMPARISON TABLE                                                      |*
*|                                                                         |*
*|  +-------------------+-----------+-----------+--------+-------------+ |*
*|  | Algorithm         | Memory    | Accuracy  | Burst  | Complexity  | |*
*|  +-------------------+-----------+-----------+--------+-------------+ |*
*|  | Token Bucket      | O(1)      | Good      | Yes    | Medium      | |*
*|  | Leaky Bucket      | O(1)      | Good      | No     | Medium      | |*
*|  | Fixed Window      | O(1)      | Poor      | Yes*   | Simple      | |*
*|  | Sliding Log       | O(N)      | Excellent | No     | Medium      | |*
*|  | Sliding Counter   | O(1)      | Good      | Smooth | Medium      | |*
*|  +-------------------+-----------+-----------+--------+-------------+ |*
*|                                                                         |*
*|  * Fixed window allows 2x burst at window boundary                    |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  VISUAL COMPARISON: Rate Over Time                                    |*
*|                                                                         |*
*|  TOKEN BUCKET (allows burst):                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |  Rate |     __                                                  |  |*
*|  |       |    ####   __      __                                   |  |*
*|  |  -----|--------------------------- limit                       |  |*
*|  |       |  _#####_####___######__                               |  |*
*|  |       +---------------------------------> Time                 |  |*
*|  |         Burst OK, average maintained                           |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  LEAKY BUCKET (smooth output):                                        |*
*|  +-----------------------------------------------------------------+  |*
*|  |  Rate |                                                         |  |*
*|  |       |  ############################                          |  |*
*|  |  -----|------------------------------- limit                   |  |*
*|  |       |                                                         |  |*
*|  |       +---------------------------------> Time                 |  |*
*|  |         Constant rate, no bursts                               |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  FIXED WINDOW (boundary problem):                                     |*
*|  +-----------------------------------------------------------------+  |*
*|  |  Rate |         ____                                           |  |*
*|  |       |         ####                                           |  |*
*|  |  -----|--------######----------------- limit                   |  |*
*|  |       |  ####_###  ###_####                                    |  |*
*|  |       +-----|------|-----------------> Time                   |  |*
*|  |            Window boundaries (spike possible)                  |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  SLIDING WINDOW (smooth, accurate):                                   |*
*|  +-----------------------------------------------------------------+  |*
*|  |  Rate |                                                         |  |*
*|  |       |    ________________________                          |  |*
*|  |  -----|------------------------------- limit                   |  |*
*|  |       |  _########################_                           |  |*
*|  |       +---------------------------------> Time                 |  |*
*|  |         Smooth, no boundary issues                             |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 1.5: CHOOSING THE RIGHT ALGORITHM
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  DECISION FLOWCHART                                                    |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Need to allow burst traffic?                                  |  |*
*|  |       |                                                        |  |*
*|  |       +-- YES > Token Bucket                                  |  |*
*|  |       |                                                        |  |*
*|  |       +-- NO -+-- Need smooth constant rate?                  |  |*
*|  |               |                                                |  |*
*|  |               +-- YES > Leaky Bucket                          |  |*
*|  |               |                                                |  |*
*|  |               +-- NO -+-- Need perfect accuracy?              |  |*
*|  |                       |                                        |  |*
*|  |                       +-- YES + Low volume > Sliding Log      |  |*
*|  |                       |                                        |  |*
*|  |                       +-- NO -+-- Simplicity priority?        |  |*
*|  |                               |                                |  |*
*|  |                               +-- YES > Fixed Window          |  |*
*|  |                               |                                |  |*
*|  |                               +-- NO > Sliding Window Counter |  |*
*|  |                                        (Recommended default)  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  REAL-WORLD USAGE                                                      |*
*|                                                                         |*
*|  +---------------------+-------------------------------------------+ |*
*|  | Company / Service   | Algorithm Used                            | |*
*|  +---------------------+-------------------------------------------+ |*
*|  | Amazon API Gateway  | Token Bucket                              | |*
*|  | Stripe              | Token Bucket                              | |*
*|  | Cloudflare          | Sliding Window Counter                   | |*
*|  | GitHub              | Sliding Window                            | |*
*|  | Kong                | Multiple (configurable)                  | |*
*|  | Envoy               | Token Bucket                              | |*
*|  | NGINX               | Leaky Bucket                              | |*
*|  +---------------------+-------------------------------------------+ |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  INTERVIEW RECOMMENDATION                                             |*
*|                                                                         |*
*|  Default answer: Sliding Window Counter                               |*
*|  * Best balance of accuracy and efficiency                           |*
*|  * Solves boundary problem of fixed window                           |*
*|  * Memory efficient                                                    |*
*|  * Easy to implement in Redis                                        |*
*|                                                                         |*
*|  If asked about bursts: Token Bucket                                  |*
*|  * Common in APIs that want to allow temporary spikes                |*
*|  * Used by AWS, Stripe                                               |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF CHAPTER 1
