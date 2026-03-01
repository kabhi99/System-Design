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

## SECTION 2: HIGH-LEVEL ARCHITECTURE

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

## SECTION 3: URL FRONTIER

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

## SECTION 4: URL DEDUPLICATION

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

## SECTION 5: FETCHER AND CONTENT PARSING

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

## SECTION 6: SCALING THE CRAWLER

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

## SECTION 7: RE-CRAWL AND FRESHNESS

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

## SECTION 8: DESIGN ALTERNATIVES AND TRADE-OFFS

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

## SECTION 9: COMMON ISSUES AND FAILURE SCENARIOS

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

## SECTION 10: MONITORING AND OPERATIONS

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

## SECTION 11: INTERVIEW QUESTIONS

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
