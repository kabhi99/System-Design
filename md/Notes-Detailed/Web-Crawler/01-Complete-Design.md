# WEB CRAWLER
*Complete System Design*

A web crawler (spider) systematically browses the internet, downloading
web pages for indexing, analysis, or archiving. It is the backbone of
search engines like Google, Bing, and also used for price monitoring,
content aggregation, and data mining.

## SECTION 1: REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS:                                               |
|  * Crawl web pages starting from a set of seed URLs                     |
|  * Extract and follow links (discover new URLs)                         |
|  * Download and store page content (HTML, metadata)                     |
|  * Respect robots.txt and crawl-delay directives                        |
|  * Handle duplicate URL detection (avoid re-crawling)                   |
|  * Periodic re-crawling of previously seen pages                        |
|  * Support different content types (HTML, PDF, images)                  |
|                                                                         |
|  NON-FUNCTIONAL:                                                        |
|  * Scale: crawl 1 billion pages per day                                 |
|  * Politeness: don't overload any single website                        |
|  * Freshness: re-crawl popular pages more frequently                    |
|  * Robustness: handle malformed HTML, timeouts, traps                   |
|  * Extensibility: pluggable components (parser, storage, filter)        |
|                                                                         |
|  CAPACITY:                                                              |
|  * 1B pages/day = ~12,000 pages/sec                                     |
|  * Avg page size: 100 KB -> 100 TB/day storage                          |
|  * URL frontier: billions of URLs in queue                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: KEY TERMINOLOGY

```
+--------------------------------------------------------------------------+
||                                                                         |
||  URL FRONTIER                                                           |
||  The prioritized queue of URLs waiting to be crawled. Manages           |
||  scheduling priority (which URL next) and per-host politeness           |
||  (rate limiting). The central scheduling structure of any crawler.      |
||                                                                         |
||  SEED URLS                                                              |
||  The initial well-known URLs that bootstrap the crawl process.          |
||  Typically homepages of major sites; the crawler discovers new          |
||  URLs by following outbound links from these starting points.           |
||                                                                         |
||  ROBOTS.TXT                                                             |
||  A per-domain file dictating which paths crawlers may or may not        |
||  access, plus optional crawl-delay directives. Must be fetched          |
||  and cached before any pages on that domain are requested.              |
||                                                                         |
||  POLITENESS                                                             |
||  Limiting crawl rate per host so target servers are not overloaded.     |
||  Enforced via per-domain queues with cooldown timers between            |
||  fetches. Violating politeness risks IP bans or legal action.           |
||                                                                         |
||  URL NORMALIZATION                                                      |
||  Converting URLs to a canonical form for deduplication: lowercase,      |
||  remove fragments, sort query params, strip tracking parameters.        |
||  Without it, the same page is crawled many times under variant URLs.    |
||                                                                         |
||  BLOOM FILTER                                                           |
||  A space-efficient probabilistic structure for set membership tests.    |
||  Used to track billions of seen URLs with ~1% false-positive rate.      |
||  1B URLs need only ~1.2 GB — far cheaper than a full hash set.          |
||                                                                         |
||  CONTENT FINGERPRINT (SIMHASH)                                          |
||  A locality-sensitive hash detecting near-duplicate page content.       |
||  Catches identical articles served at different URLs, complementing     |
||  URL dedup. Pages with similarity >90% are typically skipped.           |
||                                                                         |
||  DNS RESOLUTION                                                         |
||  Translating hostnames to IP addresses before fetching. At 12K          |
||  pages/sec DNS becomes a bottleneck without local per-worker            |
||  caches, batch pre-resolution, and multiple provider fallbacks.         |
||                                                                         |
||  CRAWL DEPTH                                                            |
||  The number of link hops from a seed URL to the current page.           |
||  BFS explores shallow pages first (standard approach). Capping          |
||  depth prevents crawler traps like infinite calendar URLs.              |
||                                                                         |
||  SITEMAP                                                                |
||  An XML file from site owners listing pages with last-modified          |
||  dates. Lets crawlers discover URLs without link-following and          |
||  prioritize recently changed content for fresher indexing.              |
||                                                                         |
+--------------------------------------------------------------------------+
```

## SECTION 3: HIGH-LEVEL ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WEB CRAWLER ARCHITECTURE                                               |
|                                                                         |
|  +----------+     +----------+     +-----------+     +----------+       |
|  | Seed     | --> | URL      | --> | URL       | --> | Fetcher  |       |
|  | URLs     |     | Frontier |     | Filter /  |     | (HTTP    |       |
|  |          |     | (Priority|     | Dedup     |     |  Client) |       |
|  +----------+     |  Queue)  |     +-----------+     +----+-----+       |
|                   +----------+                            |             |
|                        ^                                  v             |
|                        |                           +------+------+      |
|                        |                           | DNS Resolver |     |
|                        |                           +------+------+      |
|                        |                                  |             |
|                        |                                  v             |
|                        |                           +------+------+      |
|                        |                           | Content     |      |
|                   +----+------+                    | Parser      |      |
|                   | Link      |                    | (Extract    |      |
|                   | Extractor | <------------------| links, text)|      |
|                   +-----------+                    +------+------+      |
|                                                          |              |
|                                                          v              |
|                                                   +------+------+       |
|                                                   | Content     |       |
|                                                   | Store       |       |
|                                                   | (S3, HDFS)  |       |
|                                                   +-------------+       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: URL FRONTIER

```
+--------------------------------------------------------------------------+
|                                                                          |
|  URL FRONTIER = The queue of URLs to be crawled                          |
|                                                                          |
|  Two key concerns: PRIORITY and POLITENESS                               |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  PRIORITY (which URL to crawl first):                                    |
|                                                                          |
|  Priority based on:                                                      |
|  * PageRank or domain authority (important pages first)                  |
|  * Freshness (how recently was it updated?)                              |
|  * Change frequency (news sites > static corporate sites)                |
|  * Depth from seed (shallow pages often more important)                  |
|                                                                          |
|  Implementation: Multiple priority queues                                |
|  [High Priority] -> [Medium Priority] -> [Low Priority]                  |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  POLITENESS (don't overload any single host):                            |
|                                                                          |
|  Rule: Only 1 request per host at a time, with delay between requests.   |
|                                                                          |
|  Implementation: Per-host queues                                         |
|                                                                          |
|  +----------+  +----------+  +----------+  +----------+                  |
|  | cnn.com  |  | bbc.com  |  |amazon.com|  | wiki.org |                  |
|  | /page1   |  | /article |  | /product |  | /topic   |                  |
|  | /page2   |  | /news    |  | /search  |  | /main    |                  |
|  | /page3   |  |          |  | /deals   |  |          |                  |
|  +----------+  +----------+  +----------+  +----------+                  |
|                                                                          |
|  Each host queue has a timer: next allowed crawl time.                   |
|  Worker picks host where timer has expired + highest priority URL.       |
|                                                                          |
|  ROBOTS.TXT:                                                             |
|  * Fetch and cache robots.txt per domain (respect crawl-delay)           |
|  * Skip disallowed paths                                                 |
|  * Re-fetch robots.txt periodically (24h)                                |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 5: URL DEDUPLICATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROBLEM: The web has many duplicate URLs                               |
|  * Same page at http:// and https://                                    |
|  * Trailing slashes: /page vs /page/                                    |
|  * Query param order: ?a=1&b=2 vs ?b=2&a=1                              |
|  * Anchor fragments: /page#section (same content)                       |
|  * URL shorteners and redirects                                         |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  URL NORMALIZATION:                                                     |
|  1. Lowercase scheme and host                                           |
|  2. Remove default ports (80, 443)                                      |
|  3. Remove fragment (#...)                                              |
|  4. Sort query parameters                                               |
|  5. Remove trailing slash                                               |
|  6. Resolve relative URLs to absolute                                   |
|  7. Remove tracking parameters (utm_source, fbclid, etc.)               |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  SEEN-URL DETECTION:                                                    |
|                                                                         |
|  Option 1: BLOOM FILTER (approximate, memory-efficient)                 |
|  * 1B URLs, 1% false positive rate = ~1.2 GB memory                     |
|  * False positive = skip a URL we haven't seen (acceptable)             |
|  * No false negatives = never re-crawl a seen URL                       |
|                                                                         |
|  Option 2: HASH SET (exact, more memory)                                |
|  * Store MD5/SHA hash of normalized URL                                 |
|  * 1B URLs x 16 bytes = ~16 GB (fits in memory or Redis)                |
|                                                                         |
|  Option 3: DATABASE (persistent, queryable)                             |
|  * RocksDB or LevelDB for on-disk hash lookup                           |
|  * Scales to trillions of URLs                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6: FETCHER AND CONTENT PARSING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FETCHER:                                                               |
|                                                                         |
|  * Async HTTP client (non-blocking I/O for high concurrency)            |
|  * Configurable timeouts (connect: 5s, read: 30s)                       |
|  * Follow redirects (limit to 5 hops)                                   |
|  * Handle HTTP status codes:                                            |
|    200 OK -> parse content                                              |
|    301/302 -> follow redirect, update URL                               |
|    404 -> mark as dead, remove from frontier                            |
|    429 -> back off, respect Retry-After header                          |
|    5xx -> retry with exponential backoff                                |
|  * User-Agent header identifying the crawler                            |
|  * DNS caching (avoid repeated lookups for same domain)                 |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  CONTENT PARSER:                                                        |
|                                                                         |
|  1. Detect content type (HTML, PDF, image, etc.)                        |
|  2. Parse HTML (extract text, title, meta tags)                         |
|  3. Extract links (href, src attributes)                                |
|  4. Resolve relative links to absolute URLs                             |
|  5. Extract structured data (Open Graph, JSON-LD, microdata)            |
|  6. Detect language and encoding                                        |
|  7. Compute content hash (for change detection on re-crawl)             |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  CRAWLER TRAPS:                                                         |
|                                                                         |
|  * Infinite URL spaces: /page/1, /page/2, ..., /page/999999             |
|  * Calendar URLs: /calendar/2024/01/01, /calendar/2024/01/02, ...       |
|  * Session IDs in URLs: /page?sid=abc123 (new URL each time)            |
|  * Soft 404s (200 status but "page not found" content)                  |
|                                                                         |
|  SOLUTIONS:                                                             |
|  * Max depth limit from seed URL                                        |
|  * Max pages per domain                                                 |
|  * URL pattern detection (identify auto-generated URLs)                 |
|  * Content similarity detection (skip near-duplicate pages)             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7: SCALING THE CRAWLER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DISTRIBUTED CRAWLER ARCHITECTURE:                                      |
|                                                                         |
|  +----------+     +------------------------------------------+          |
|  | URL      |     |  Worker Pool (100s of machines)          |          |
|  | Frontier | --> |                                          |          |
|  | (Kafka/  |     |  Worker 1: fetch + parse + store         |          |
|  |  Redis)  |     |  Worker 2: fetch + parse + store         |          |
|  |          | <-- |  Worker 3: fetch + parse + store         |          |
|  | new URLs |     |  ...                                     |          |
|  +----------+     |  Worker N: fetch + parse + store         |          |
|                   +------------------------------------------+          |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  PARTITIONING STRATEGY:                                                 |
|                                                                         |
|  Partition by DOMAIN (host):                                            |
|  * hash(domain) % N_workers -> each worker handles specific domains     |
|  * Ensures politeness: one worker per domain = natural rate limiting    |
|  * Worker has local per-host queue and timer                            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  COMPONENTS AT SCALE:                                                   |
|                                                                         |
|  * URL Frontier: Kafka (durable, partitioned by domain hash)            |
|  * Seen URLs: Bloom filter (in-memory) + RocksDB (persistent)           |
|  * DNS Cache: Local cache per worker + shared Redis                     |
|  * Content Store: S3 or HDFS (compressed, partitioned by date)          |
|  * Metadata DB: Postgres or Cassandra (URL, last crawl, hash, status)   |
|  * Monitoring: crawl rate, error rate, queue depth, per-domain stats    |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  BANDWIDTH MATH:                                                        |
|  1B pages/day x 100KB avg = 100 TB/day = ~10 Gbps sustained             |
|  With compression (50%): ~5 Gbps network throughput                     |
|  Workers: ~500 machines at 1000 pages/sec each                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8: RE-CRAWL AND FRESHNESS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NOT ALL PAGES NEED THE SAME CRAWL FREQUENCY:                           |
|                                                                         |
|  +-------------------+------------------+----------------------------+  |
|  | Page Type         | Re-crawl Period  | Priority                   |  |
|  +-------------------+------------------+----------------------------+  |
|  | News homepages    | Every 5-15 min   | Highest                    |  |
|  | News articles     | Daily            | High (first 48h)           |  |
|  | E-commerce prices | Every 1-6 hours  | High                       |  |
|  | Wikipedia         | Weekly           | Medium                     |  |
|  | Corporate sites   | Monthly          | Low                        |  |
|  | Personal blogs    | Monthly          | Low                        |  |
|  +-------------------+------------------+----------------------------+  |
|                                                                         |
|  CHANGE DETECTION:                                                      |
|  * HTTP ETag / If-Modified-Since (304 Not Modified = no change)         |
|  * Content hash comparison (MD5 of page body)                           |
|  * Sitemap.xml (lists pages with lastmod date)                          |
|                                                                         |
|  ADAPTIVE FREQUENCY:                                                    |
|  * Track change rate per URL over time                                  |
|  * If page changed on last 3 crawls: increase frequency                 |
|  * If page unchanged for 5 crawls: decrease frequency                   |
|  * Budget allocation: spend more crawl budget on frequently-changing    |
|    and high-value pages                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: DESIGN ALTERNATIVES AND TRADE-OFFS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ALTERNATIVE 1: BFS vs DFS Crawling Strategy                            |
|                                                                         |
|  * BFS (breadth-first): discover many sites quickly, shallow            |
|    coverage. Standard approach for web-scale crawlers.                  |
|  * DFS (depth-first): go deep into one site before moving on.           |
|    Risk of crawler traps (infinite depth).                              |
|  * Best practice: BFS with priority (important/fresh pages first).      |
|    DFS only for focused crawls (single-site archiving).                 |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  ALTERNATIVE 2: Bloom Filter vs Hash Set vs Database for URL Dedup      |
|                                                                         |
|  +--------------+--------+----------+----------+---------+              |
|  | Method       | Memory | FP Rate  | Persist? | Speed   |              |
|  +--------------+--------+----------+----------+---------+              |
|  | Bloom Filter | 1.2 GB | ~1%      | No       | O(k)    |              |
|  | Hash (Redis) | 16 GB  | Exact    | In-mem   | O(1)    |              |
|  | RocksDB      | Unlim  | Exact    | Yes      | Slower  |              |
|  +--------------+--------+----------+----------+---------+              |
|                                                                         |
|  Best: Bloom filter in-memory + RocksDB for persistent backup.          |
|  Redis if budget allows for exact dedup with fast lookups.              |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  ALTERNATIVE 3: Single Machine vs Distributed Crawler                   |
|                                                                         |
|  * Single machine: simpler, 100-1000 pages/sec, fine for focused        |
|    crawls (one site, small dataset).                                    |
|  * Distributed (Kafka + workers): millions of pages/sec, needed         |
|    for web-scale crawling (billions of pages).                          |
|  * Trade-off: distributed adds coordination complexity (dedup           |
|    across workers, politeness enforcement across machines).             |
|  * Partition by domain hash: simplifies politeness (each worker         |
|    owns specific domains, natural rate limiting).                       |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  ALTERNATIVE 4: Headless Browser vs HTTP Client                         |
|                                                                         |
|  * HTTP client only: fast (1000+ pages/sec), simple, but misses         |
|    JS-rendered content (SPAs, dynamic pages).                           |
|  * Headless browser (Puppeteer/Playwright): renders JS, sees full       |
|    DOM, but 10-50x slower and high resource cost.                       |
|  * Hybrid (Google's approach): HTTP first pass for link discovery,      |
|    headless browser for JS-heavy pages only.                            |
|  * Budget: rendering 1B pages/day with headless Chrome is               |
|    impractical. Render selectively based on JS detection.               |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  ALTERNATIVE 5: Centralized vs Decentralized URL Frontier               |
|                                                                         |
|  * Centralized (single Kafka cluster): simpler, consistent              |
|    priority ordering, single source of truth.                           |
|  * Decentralized (per-worker local queues + coordinator):               |
|    lower latency, less network overhead.                                |
|  * Hybrid: Kafka for inter-worker URL distribution + local              |
|    priority queue per worker for scheduling.                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10: COMMON ISSUES AND FAILURE SCENARIOS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ISSUE 1: Crawler Traps (Infinite URL Spaces)                           |
|                                                                         |
|  Problem: calendar pages, session IDs, query parameter permutations     |
|  generate infinite URLs.                                                |
|                                                                         |
|  Solution: max URL depth, max pages per domain, URL regex pattern       |
|  detection, content fingerprint dedup (same content at many URLs).      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  ISSUE 2: DNS Resolution Bottleneck                                     |
|                                                                         |
|  Problem: 12,000 pages/sec = 12,000 DNS lookups/sec. Public DNS         |
|  can't handle this.                                                     |
|                                                                         |
|  Solution: local DNS cache per worker, pre-resolve domains in batch,    |
|  cache TTL-aware, fallback to multiple DNS providers.                   |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  ISSUE 3: Politeness Violation Causing IP Ban                           |
|                                                                         |
|  Problem: crawl too fast, website bans your IP. Or multiple workers     |
|  crawl same domain simultaneously.                                      |
|                                                                         |
|  Solution: per-domain rate limiter (shared across workers), respect     |
|  robots.txt crawl-delay, rotate IPs (ethically), use                    |
|  domain-partitioned workers.                                            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  ISSUE 4: Content Duplication Across Different URLs                     |
|                                                                         |
|  Problem: same article at /news/123 and /articles/123 and               |
|  /amp/123.                                                              |
|                                                                         |
|  Solution: Content fingerprinting (SimHash/MinHash), canonical URL      |
|  detection (rel=canonical), near-duplicate detection                    |
|  (similarity > 90% = skip).                                             |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  ISSUE 5: Stale Frontier (URLs become invalid over time)                |
|                                                                         |
|  Problem: URLs queued weeks ago, site has changed, pages deleted.       |
|  Wasting crawl budget on dead links.                                    |
|                                                                         |
|  Solution: TTL on frontier entries, exponential backoff for             |
|  repeatedly-failing domains, priority decay (old URLs lose              |
|  priority), periodic frontier cleanup.                                  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  ISSUE 6: Handling Rate-Limited or Slow Websites                        |
|                                                                         |
|  Problem: some sites respond in 10+ seconds, blocking the worker        |
|  thread.                                                                |
|                                                                         |
|  Solution: async I/O (don't block on slow sites), per-domain            |
|  timeout config, deprioritize slow domains, move to slow-queue          |
|  with longer intervals.                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11: MONITORING AND OPERATIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY METRICS TO MONITOR:                                                |
|                                                                         |
|  * Crawl rate (pages/sec overall and per domain)                        |
|  * URL frontier depth (growing = falling behind)                        |
|  * Error rate by type (DNS failures, timeouts, 4xx, 5xx)                |
|  * Content duplication rate (% of pages are near-duplicates)            |
|  * Cache hit rates (DNS cache, robots.txt cache)                        |
|  * Freshness (avg age of last crawl per domain tier)                    |
|  * Storage growth rate                                                  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  OPERATIONAL CONCERNS:                                                  |
|                                                                         |
|  * Alerting: frontier growing faster than drain rate                    |
|  * Capacity planning: bandwidth vs workers vs storage                   |
|  * Graceful shutdown: finish in-progress fetches, persist               |
|    frontier state                                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DETAILED WRITE/READ PATHS AND STATE MANAGEMENT

```
+--------------------------------------------------------------------------+
|                                                                          |
|  1. ENTITY STATE MACHINE (URL Lifecycle)                                 |
|                                                                          |
|    [DISCOVERED] --> [QUEUED] --> [FETCHING] --> [FETCHED] --> [PARSED]    |
|         |              |            |               |                    |
|         |              |            +---> [FAILED] -+---> [RETRY]        |
|         |              |                                    |            |
|         |              +------------------------------------+            |
|         |              (re-enqueue with backoff, max 3 retries)          |
|         |                                                                |
|         +---> [DUPLICATE] (Bloom filter says "already seen")             |
|                                                                          |
|    On re-crawl cycle:                                                    |
|    [PARSED] --> [STALE] --> [QUEUED]  (freshness score triggers          |
|                              re-crawl after adaptive interval)           |
|                                                                          |
|    DISCOVERED:  Link extractor found new URL in a crawled page           |
|    QUEUED:      Normalized URL added to URL frontier                     |
|    FETCHING:    Worker assigned, HTTP GET in progress                    |
|    FETCHED:     HTTP 200 received, raw HTML in memory                    |
|    PARSED:      Content extracted, links discovered, stored in S3        |
|    FAILED:      DNS error, timeout, 5xx, robots.txt blocked             |
|    DUPLICATE:   Bloom filter match -- skip (no DB/network hit)           |
|                                                                          |
|  ======================================================================  |
|                                                                          |
|  2. CRITICAL WRITE PATH (URL Discovery + Deduplication)                  |
|                                                                          |
|    Link Extractor finds new URL in a crawled page:                       |
|      |                                                                   |
|      v                                                                   |
|    Step 1: Normalize URL                                                 |
|      |     Lowercase host, remove fragment, sort query params,           |
|      |     strip tracking params (utm_source, fbclid),                   |
|      |     remove trailing slash, resolve relative to absolute           |
|      v                                                                   |
|    Step 2: Bloom filter check (in-memory, ~1.2 GB for 1B URLs)          |
|      |     bloom.contains(normalized_url)                                |
|      |     TRUE  -> SKIP (probably seen, accept 1% false positive)       |
|      |     FALSE -> definitely new, continue                             |
|      v                                                                   |
|    Step 3: Add to Bloom filter                                           |
|      |     bloom.add(normalized_url)                                     |
|      |     (immediately prevents other workers from re-adding)           |
|      v                                                                   |
|    Step 4: Persist to seen-URL store (durable backup)                    |
|      |     RocksDB: PUT url_hash -> { url, discovered_at, depth }        |
|      |     (on-disk, survives restarts, Bloom filter rebuilt from it)    |
|      v                                                                   |
|    Step 5: Compute priority and assign to URL frontier                   |
|      |     Priority = f(PageRank, domain_authority, depth, freshness)    |
|      |     Kafka produce -> topic: url_frontier                          |
|      |       Key: domain_hash (partition by domain for politeness)       |
|      |       Value: { url, priority, depth, discovered_at }              |
|      v                                                                   |
|    Step 6: URL enters per-domain politeness queue                        |
|      |     Each domain has its own sub-queue:                            |
|      |       domain_queue:{cnn.com} = [url1, url2, url3]                 |
|      |     Timer: next_allowed_fetch:{cnn.com} = timestamp               |
|      |     Worker picks URL only if timer has expired                    |
|                                                                          |
|    WRITE ORDER: Bloom filter (memory) -> RocksDB (disk) -> Kafka         |
|    If Bloom filter full: Expand or partition across workers              |
|    If Kafka down: Buffer in local RocksDB, drain on recovery            |
|                                                                          |
|  ======================================================================  |
|                                                                          |
|  3. READ PATH (Politeness Check + Rate Limit Per Domain)                 |
|                                                                          |
|    Worker ready to fetch next URL:                                       |
|      |                                                                   |
|      v                                                                   |
|    Step 1: Check robots.txt cache                                        |
|      |     GET robots_cache:{domain}                                     |
|      |     HIT  -> parse rules, check if path is allowed                |
|      |     MISS -> fetch https://{domain}/robots.txt                     |
|      |             parse and cache with TTL 24h                          |
|      |     DISALLOWED -> skip URL, mark as FILTERED                      |
|      v                                                                   |
|    Step 2: Politeness rate limit check                                   |
|      |     GET next_allowed_fetch:{domain}                               |
|      |     If now < next_allowed_time -> wait (don't fetch yet)          |
|      |     crawl-delay from robots.txt (default: 1 request/sec)          |
|      v                                                                   |
|    Step 3: DNS resolution (cached)                                       |
|      |     Local DNS cache per worker: domain -> IP                      |
|      |     Cache TTL: min(DNS TTL, 1 hour)                               |
|      |     Cache miss -> resolve via DNS server, cache result            |
|      v                                                                   |
|    Step 4: HTTP fetch with timeouts                                      |
|      |     Connect timeout: 5s, Read timeout: 30s                        |
|      |     Follow redirects (max 5 hops)                                 |
|      |     Capture: status, headers, body, response_time                 |
|      |     Set next_allowed_fetch:{domain} = now + crawl_delay           |
|      v                                                                   |
|    Step 5: Content processing                                            |
|      |     Parse HTML, extract links (-> new DISCOVERED URLs)            |
|      |     Compute content fingerprint (SimHash for near-dedup)          |
|      |     Store page content: S3 PUT s3://crawl-data/{url_hash}         |
|      |     Store metadata: RocksDB { url, status_code, fetch_time,       |
|      |       content_hash, last_crawled_at }                             |
|                                                                          |
|  ======================================================================  |
|                                                                          |
|  4. FAILURE SCENARIOS                                                    |
|                                                                          |
|  What Fails               | Impact & Recovery                            |
|  -------------------------+----------------------------------------------+
|  DNS resolution failure   | URL stays in QUEUED. Retry after 5 min.      |
|                           | If persistent, mark domain as unreachable.   |
|                           | Per-worker DNS cache reduces blast radius.   |
|  -------------------------+----------------------------------------------+
|  HTTP 5xx / timeout       | Retry with exponential backoff (1m, 5m, 30m).|
|                           | After 3 retries, mark URL as FAILED.          |
|                           | Don't penalize other URLs on same domain.    |
|  -------------------------+----------------------------------------------+
|  Worker crash mid-fetch   | Kafka offset not committed. URL is re-        |
|                           | delivered to another worker. Bloom filter     |
|                           | already has it (no duplicate storage). At     |
|                           | worst, page fetched twice (idempotent).      |
|  -------------------------+----------------------------------------------+
|  Bloom filter OOM /       | Rebuild from RocksDB seen-URL store on        |
|  corruption               | restart. During rebuild, temporary increase   |
|                           | in duplicate fetches (acceptable). Partition  |
|                           | Bloom filter across workers to limit size.   |
|  -------------------------+----------------------------------------------+
|                                                                          |
|  ======================================================================  |
|                                                                          |
|  5. CLEANUP / EXPIRY                                                     |
|                                                                          |
|    URL Frontier Pruning:                                                 |
|      URLs older than 30 days in queue without being fetched              |
|      are dropped (low-priority URLs that never got processed)            |
|                                                                          |
|    Robots.txt Cache Refresh:                                             |
|      Re-fetch robots.txt per domain every 24 hours                       |
|      Stale entries auto-expire via TTL on cache keys                     |
|                                                                          |
|    DNS Cache Expiry:                                                     |
|      Per-worker local cache, TTL = min(DNS record TTL, 1 hour)           |
|      Evict on memory pressure (LRU)                                      |
|                                                                          |
|    Content Storage Lifecycle (S3/HDFS):                                   |
|      Keep latest version of each page                                    |
|      Archive older versions after 90 days to cold storage               |
|      Delete pages for domains removed from crawl scope                   |
|                                                                          |
|    Re-Crawl Scheduling:                                                  |
|      Adaptive re-crawl interval per URL based on change frequency        |
|      News sites: re-crawl every 15 min                                   |
|      Blogs: re-crawl every 7 days                                        |
|      Static corporate pages: re-crawl every 30 days                      |
|      If content_hash unchanged on re-crawl, extend interval              |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 12: INTERVIEW QUESTIONS

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Q: How do you handle politeness at scale?                               |
|  A: Per-domain rate limiting. Partition work by domain hash so each      |
|     worker owns specific domains. Respect robots.txt crawl-delay.        |
|     Max 1 concurrent request per domain with configurable delay.         |
|                                                                          |
|  Q: How do you avoid crawling the same URL twice?                        |
|  A: URL normalization + Bloom filter for fast lookup (1.2 GB for 1B      |
|     URLs). Backed by persistent store (RocksDB) for exact dedup.         |
|     Content hash dedup catches same content at different URLs.           |
|                                                                          |
|  Q: How do you prioritize which URLs to crawl first?                     |
|  A: Multi-level priority queue. Priority based on: PageRank, domain      |
|     authority, freshness score, change frequency. News > blog > static.  |
|                                                                          |
|  Q: How do you detect and avoid crawler traps?                           |
|  A: Max URL depth limit, max pages per domain, URL pattern detection     |
|     (regex for auto-generated paths), content similarity (near-dup       |
|     detection with SimHash), blacklist known trap patterns.              |
|                                                                          |
|  Q: How would you design a crawler for 10 billion pages?                 |
|  A: Kafka-backed URL frontier partitioned by domain. 1000+ workers,      |
|     each handling ~10K pages/sec. Bloom filter + RocksDB for seen        |
|     URLs. S3 for content storage. Re-crawl scheduler with adaptive       |
|     frequency. Total: ~100 Gbps bandwidth, ~10 PB storage/month.         |
|                                                                          |
|  Q: How does Googlebot handle JavaScript-rendered pages?                 |
|  A: Two-phase crawl: first fetch raw HTML (fast, discover links).        |
|     Second pass: render with headless Chrome (expensive, queued).        |
|     Cache rendered DOM. Only render if page seems JS-heavy.              |
|                                                                          |
+--------------------------------------------------------------------------+
```
