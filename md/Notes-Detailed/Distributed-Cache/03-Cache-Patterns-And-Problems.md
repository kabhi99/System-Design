# DISTRIBUTED CACHE SYSTEM DESIGN
*Chapter 3: Cache Patterns and Common Problems*

This chapter covers advanced caching patterns and solutions to common
problems like cache stampede, thundering herd, and consistency issues.

## SECTION 3.1: CACHE STAMPEDE (Thundering Herd)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM                                                           |
|                                                                         |
|  Popular key expires -> many requests hit database simultaneously     |
|                                                                         |
|  Time: 12:00:00 - Cache key "popular_product" expires                 |
|                                                                         |
|  Request 1 -+                                                          |
|  Request 2 -+-> All see cache miss -> All query database!            |
|  Request 3 -+                                                          |
|  ...        |                                                          |
|  Request 100+                                                          |
|                                                                         |
|  Database overwhelmed by duplicate queries.                           |
|  Response time spikes.                                                |
|  Can cause cascading failures.                                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION 1: LOCKING                                                   |
|  ====================                                                   |
|                                                                         |
|  Only one request fetches from database.                             |
|  Others wait for cache to be populated.                              |
|                                                                         |
|  def get_with_lock(key):                                              |
|      value = cache.get(key)                                           |
|      if value:                                                         |
|          return value                                                  |
|                                                                         |
|      # Try to acquire lock                                            |
|      lock_key = f"lock:{key}"                                         |
|      if cache.setnx(lock_key, "1", ttl=10):                          |
|          try:                                                          |
|              # We got the lock, fetch from DB                        |
|              value = db.get(key)                                      |
|              cache.set(key, value, ttl=3600)                         |
|              return value                                              |
|          finally:                                                      |
|              cache.delete(lock_key)                                   |
|      else:                                                             |
|          # Someone else is fetching, wait and retry                  |
|          time.sleep(0.1)                                              |
|          return get_with_lock(key)  # Retry                          |
|                                                                         |
|  PROS: Prevents duplicate DB queries                                  |
|  CONS: Adds latency for waiting requests                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION 2: PROBABILISTIC EARLY EXPIRATION                           |
|  ===========================================                            |
|                                                                         |
|  Refresh cache BEFORE it expires.                                    |
|  Each request has small chance to refresh.                           |
|                                                                         |
|  def get_with_early_refresh(key, ttl=3600, beta=1):                  |
|      value, expiry = cache.get_with_ttl(key)                         |
|                                                                         |
|      if value is None:                                                 |
|          # Cache miss, must fetch                                    |
|          value = db.get(key)                                          |
|          cache.set(key, value, ttl=ttl)                              |
|          return value                                                  |
|                                                                         |
|      # Probabilistic early refresh                                    |
|      remaining_ttl = expiry - time.now()                             |
|      if remaining_ttl < beta * random.random() * ttl:                |
|          # Refresh in background                                      |
|          async_refresh(key)                                           |
|                                                                         |
|      return value                                                      |
|                                                                         |
|  As TTL approaches, probability of refresh increases.                |
|  Only one request likely to refresh.                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION 3: CACHE-ASIDE WITH STALE DATA                              |
|  ========================================                               |
|                                                                         |
|  Return stale data while refreshing in background.                   |
|                                                                         |
|  Store: { value, timestamp, soft_ttl, hard_ttl }                     |
|                                                                         |
|  def get_with_stale(key):                                             |
|      data = cache.get(key)                                            |
|                                                                         |
|      if data is None:                                                  |
|          # Hard miss                                                  |
|          return fetch_and_cache(key)                                  |
|                                                                         |
|      if data.timestamp + soft_ttl < now():                           |
|          # Soft expired - return stale, refresh async                |
|          async_refresh(key)                                           |
|          return data.value  # Return stale data                      |
|                                                                         |
|      return data.value  # Fresh data                                  |
|                                                                         |
|  User gets fast response (stale but acceptable).                     |
|  Background refresh updates for next request.                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.2: HOT KEY PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM                                                           |
|                                                                         |
|  One key gets disproportionate traffic.                              |
|  That cache node becomes bottleneck.                                  |
|                                                                         |
|  Examples:                                                             |
|  * Celebrity's profile during news event                             |
|  * Product during flash sale                                         |
|  * Breaking news article                                             |
|                                                                         |
|  Normal load:                                                          |
|  Key A: 1,000 req/s                                                    |
|  Key B: 1,000 req/s                                                    |
|  Key C: 1,000 req/s                                                    |
|                                                                         |
|  Hot key event:                                                        |
|  Key A: 500,000 req/s  <- Single node can't handle!                  |
|  Key B: 1,000 req/s                                                    |
|  Key C: 1,000 req/s                                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION 1: LOCAL CACHE                                               |
|  ========================                                               |
|                                                                         |
|  Cache hot keys in application memory.                               |
|  Reduce requests to distributed cache.                               |
|                                                                         |
|  class MultiLevelCache:                                                |
|      def __init__(self):                                               |
|          self.local = LRUCache(maxsize=1000)  # In-process           |
|          self.distributed = redis_client                              |
|                                                                         |
|      def get(self, key):                                               |
|          # Check local first                                          |
|          value = self.local.get(key)                                  |
|          if value:                                                     |
|              return value                                              |
|                                                                         |
|          # Check distributed                                           |
|          value = self.distributed.get(key)                            |
|          if value:                                                     |
|              # Store in local for subsequent requests                |
|              self.local.set(key, value, ttl=10)  # Short TTL         |
|              return value                                              |
|                                                                         |
|          return None                                                   |
|                                                                         |
|  CHALLENGE: Local cache invalidation                                  |
|  * Use very short TTL (10-30 seconds)                                |
|  * Or use Pub/Sub for invalidation broadcast                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION 2: KEY REPLICATION                                           |
|  ============================                                           |
|                                                                         |
|  Replicate hot key across multiple cache nodes.                      |
|  Client randomly selects which copy to read.                        |
|                                                                         |
|  Original: product:123                                                 |
|  Replicas: product:123:0, product:123:1, product:123:2               |
|                                                                         |
|  def get_hot_key(key, replicas=3):                                   |
|      suffix = random.randint(0, replicas - 1)                        |
|      replica_key = f"{key}:{suffix}"                                 |
|      return cache.get(replica_key)                                   |
|                                                                         |
|  def set_hot_key(key, value, replicas=3):                            |
|      for i in range(replicas):                                        |
|          replica_key = f"{key}:{i}"                                   |
|          cache.set(replica_key, value)                                |
|                                                                         |
|  With consistent hashing, replicas go to different nodes.           |
|  Load spread across 3 nodes instead of 1.                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION 3: DETECT AND HANDLE                                        |
|  ==============================                                        |
|                                                                         |
|  Monitor for hot keys.                                                |
|  When detected, automatically apply mitigations.                     |
|                                                                         |
|  Detection methods:                                                    |
|  * Redis HOTKEYS command                                             |
|  * Client-side request counting                                      |
|  * Prometheus metrics                                                 |
|                                                                         |
|  # redis-cli --hotkeys                                                |
|  # Shows most accessed keys                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.3: CACHE PENETRATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM                                                           |
|                                                                         |
|  Queries for non-existent data always miss cache.                    |
|  Every request hits database.                                        |
|                                                                         |
|  Attacker queries:                                                     |
|  GET /user/-1    (doesn't exist)                                     |
|  GET /user/-2    (doesn't exist)                                     |
|  GET /user/-3    (doesn't exist)                                     |
|  ...                                                                    |
|                                                                         |
|  Cache can't help (nothing to cache).                                |
|  All requests hit database.                                          |
|  Potential DoS attack vector.                                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION 1: CACHE NULL VALUES                                        |
|  ==============================                                        |
|                                                                         |
|  When database returns nothing, cache the "nothing".                 |
|                                                                         |
|  def get_user(user_id):                                               |
|      cached = cache.get(f"user:{user_id}")                           |
|                                                                         |
|      if cached == "NULL_MARKER":                                      |
|          return None  # Cached non-existence                         |
|                                                                         |
|      if cached:                                                        |
|          return cached                                                 |
|                                                                         |
|      user = db.get_user(user_id)                                      |
|                                                                         |
|      if user:                                                          |
|          cache.set(f"user:{user_id}", user, ttl=3600)               |
|      else:                                                             |
|          # Cache the non-existence                                    |
|          cache.set(f"user:{user_id}", "NULL_MARKER", ttl=300)       |
|                                                                         |
|      return user                                                       |
|                                                                         |
|  Use shorter TTL for null values (data might be created).           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION 2: BLOOM FILTER                                              |
|  =========================                                              |
|                                                                         |
|  Probabilistic data structure to check membership.                   |
|  "Definitely not in set" or "Probably in set".                      |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Request: GET user:12345                                       |  |
|  |       |                                                         |  |
|  |       v                                                         |  |
|  |  +--------------+                                               |  |
|  |  | Bloom Filter |                                               |  |
|  |  | "Does user   |                                               |  |
|  |  |  exist?"     |                                               |  |
|  |  +------+-------+                                               |  |
|  |         |                                                       |  |
|  |    +----+----+                                                  |  |
|  |    v         v                                                  |  |
|  |   NO      MAYBE                                                |  |
|  |    |         |                                                  |  |
|  |    v         v                                                  |  |
|  |  Return   Check cache/DB                                       |  |
|  |  null     as normal                                            |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  BLOOM FILTER PROPERTIES:                                             |
|  * No false negatives (if says NO, definitely not there)            |
|  * Small false positive rate (might say MAYBE incorrectly)         |
|  * Space efficient (1% error rate = ~10 bits/element)              |
|                                                                         |
|  from pybloom_live import BloomFilter                                 |
|                                                                         |
|  # Initialize with all valid IDs                                      |
|  valid_users = BloomFilter(capacity=1000000, error_rate=0.01)        |
|  for user_id in db.get_all_user_ids():                               |
|      valid_users.add(user_id)                                         |
|                                                                         |
|  def get_user(user_id):                                               |
|      # Quick check                                                    |
|      if user_id not in valid_users:                                  |
|          return None  # Definitely doesn't exist                    |
|                                                                         |
|      # Might exist, check cache/DB                                   |
|      return normal_get_user(user_id)                                 |
|                                                                         |
|  Update bloom filter when users created/deleted.                     |
|  Rebuild periodically for accuracy.                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.4: CACHE CONSISTENCY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM                                                           |
|                                                                         |
|  Cache and database can get out of sync.                             |
|                                                                         |
|  RACE CONDITION EXAMPLE:                                               |
|  -------------------------                                              |
|                                                                         |
|  Thread A                      Thread B                               |
|     |                             |                                   |
|     | UPDATE db SET val=2        |                                   |
|     |-------------------->       |                                   |
|     |                             | SELECT val FROM db                |
|     |                             | (returns 2)                       |
|     |                             | SET cache val=2                  |
|     |                             |-------------------->             |
|     | DELETE cache key           |                                   |
|     |-------------------->       |                                   |
|     |                             |                                   |
|     v                             v                                   |
|                                                                         |
|  Result: Cache has val=2, but that's from BEFORE Thread A's delete! |
|  Cache now stale (Thread A's change not reflected).                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION 1: DELETE AFTER WRITE                                       |
|  ===============================                                        |
|                                                                         |
|  1. Update database                                                   |
|  2. Delete cache key                                                  |
|  3. Next read will fetch fresh data from DB                         |
|                                                                         |
|  def update_user(user_id, data):                                      |
|      db.update("users", user_id, data)                               |
|      cache.delete(f"user:{user_id}")                                 |
|                                                                         |
|  PROS: Simple, works for most cases                                   |
|  CONS: Still has race conditions (shown above)                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION 2: WRITE-THROUGH                                            |
|  ==========================                                            |
|                                                                         |
|  Update both cache and database in same transaction.                 |
|                                                                         |
|  def update_user(user_id, data):                                      |
|      with db.transaction():                                           |
|          db.update("users", user_id, data)                           |
|          fresh_data = db.get("users", user_id)                       |
|          cache.set(f"user:{user_id}", fresh_data)                   |
|                                                                         |
|  PROS: Cache always consistent after write                           |
|  CONS: Higher write latency, cache may hold unused data            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION 3: VERSIONING                                                |
|  =======================                                                |
|                                                                         |
|  Include version number in cache key.                                |
|  Increment version on write.                                          |
|                                                                         |
|  Cache key: user:{id}:v{version}                                      |
|                                                                         |
|  def get_user(user_id):                                               |
|      version = db.get_version("users", user_id)                      |
|      cache_key = f"user:{user_id}:v{version}"                        |
|      return cache.get(cache_key) or fetch_and_cache(user_id)        |
|                                                                         |
|  def update_user(user_id, data):                                      |
|      db.update_with_version_increment("users", user_id, data)       |
|      # Old cache entries become orphaned, naturally expire          |
|                                                                         |
|  PROS: Strong consistency, no explicit invalidation                  |
|  CONS: Need version lookup, orphaned cache entries                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION 4: CDC (Change Data Capture)                                |
|  =====================================                                  |
|                                                                         |
|  Database publishes changes.                                          |
|  Separate service invalidates cache.                                 |
|                                                                         |
|  Database --> Debezium --> Kafka --> Cache Invalidator --> Cache    |
|                                                                         |
|  PROS: Decoupled, reliable, handles complex invalidations           |
|  CONS: More infrastructure, eventual consistency                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.5: CACHE WARMING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM                                                           |
|                                                                         |
|  Empty cache = all requests hit database.                            |
|  Happens after: deployment, cache restart, scaling up.               |
|                                                                         |
|  "Cold cache" can overwhelm database.                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SOLUTION: PRE-WARMING                                                 |
|  ======================                                                |
|                                                                         |
|  Load popular data into cache before traffic arrives.                |
|                                                                         |
|  def warm_cache():                                                     |
|      # Get list of popular items                                      |
|      popular_products = analytics.get_popular_products(limit=10000) |
|      popular_users = analytics.get_active_users(limit=50000)        |
|                                                                         |
|      # Load into cache                                                |
|      for product_id in popular_products:                             |
|          product = db.get_product(product_id)                        |
|          cache.set(f"product:{product_id}", product, ttl=3600)      |
|                                                                         |
|      for user_id in popular_users:                                    |
|          user = db.get_user(user_id)                                  |
|          cache.set(f"user:{user_id}", user, ttl=3600)               |
|                                                                         |
|  Run before:                                                           |
|  * Deployment (as part of release process)                           |
|  * Cache cluster restart                                              |
|  * Adding new cache nodes                                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  GRADUAL TRAFFIC SHIFT                                                 |
|  ======================                                                |
|                                                                         |
|  For new cache nodes, gradually shift traffic:                       |
|                                                                         |
|  1. Deploy new node with 0% traffic                                  |
|  2. Route 1% -> 5% -> 10% -> ... -> 100%                                |
|  3. Each step allows cache to warm naturally                        |
|                                                                         |
|  def route_request(key):                                              |
|      new_node_percentage = config.get("new_node_percentage")        |
|                                                                         |
|      if random.random() * 100 < new_node_percentage:                 |
|          return new_cache_node.get(key)                              |
|      else:                                                             |
|          return old_cache_node.get(key)                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CACHE PATTERNS - KEY TAKEAWAYS                                       |
|                                                                         |
|  CACHE STAMPEDE                                                        |
|  --------------                                                        |
|  * Problem: Popular key expires, many DB queries                     |
|  * Solutions: Locking, early refresh, stale-while-revalidate        |
|                                                                         |
|  HOT KEY                                                               |
|  -------                                                               |
|  * Problem: One key overwhelms single node                           |
|  * Solutions: Local cache, key replication                          |
|                                                                         |
|  CACHE PENETRATION                                                     |
|  -----------------                                                     |
|  * Problem: Non-existent keys bypass cache                          |
|  * Solutions: Cache null values, bloom filter                       |
|                                                                         |
|  CONSISTENCY                                                           |
|  -----------                                                           |
|  * Problem: Cache and DB out of sync                                 |
|  * Solutions: Delete after write, versioning, CDC                   |
|                                                                         |
|  CACHE WARMING                                                         |
|  -------------                                                         |
|  * Problem: Cold cache overwhelms DB                                 |
|  * Solutions: Pre-warm, gradual traffic shift                       |
|                                                                         |
|  INTERVIEW TIP                                                         |
|  -------------                                                         |
|  Know stampede solutions (locking vs probabilistic).                |
|  Explain bloom filter for penetration.                               |
|  Discuss consistency trade-offs.                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 3

