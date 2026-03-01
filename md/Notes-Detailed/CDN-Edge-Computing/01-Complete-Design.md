# CDN AND EDGE COMPUTING
*Complete System Design*

A Content Delivery Network (CDN) is a geographically distributed network of
servers that delivers content to users from the nearest location, reducing
latency and offloading origin servers.

## SECTION 1: REQUIREMENTS AND SCALE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS:                                               |
|  * Serve static content (images, CSS, JS, videos) from edge             |
|  * Cache dynamic content with short TTLs                                |
|  * SSL/TLS termination at the edge                                      |
|  * Custom domain support (CNAME mapping)                                |
|  * Cache invalidation / purge API                                       |
|  * Origin failover and health checks                                    |
|  * Geo-based routing (route user to nearest PoP)                        |
|  * DDoS protection and WAF at edge                                      |
|                                                                         |
|  NON-FUNCTIONAL:                                                        |
|  * Latency: < 50ms for cached content (p99)                             |
|  * Availability: 99.99% uptime                                          |
|  * Cache hit ratio: > 95% for static assets                             |
|  * Scale: 100+ Tbps aggregate bandwidth globally                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: HIGH-LEVEL ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CDN ARCHITECTURE                                                       |
|                                                                         |
|  User (NYC) --> DNS Resolver --> CDN DNS (returns nearest PoP IP)       |
|                                      |                                  |
|                                      v                                  |
|                               +-------------+                           |
|                               | Edge PoP    |                           |
|                               | (New York)  |                           |
|                               |             |                           |
|                               | Cache HIT?  |                           |
|                               +------+------+                           |
|                                YES/  \NO                                |
|                                 /     \                                 |
|                                v       v                                |
|                         Return     Mid-Tier Cache                       |
|                         cached     (Regional)                           |
|                         content         |                               |
|                                    HIT? |                               |
|                                   YES/  \NO                             |
|                                    /     \                              |
|                                   v       v                             |
|                              Return    Origin Server                    |
|                              cached    (your server)                    |
|                              content        |                           |
|                                             v                           |
|                                      Response cached                    |
|                                      at edge + mid-tier                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### PoP (POINT OF PRESENCE) INTERNALS

```
+--------------------------------------------------------------------------+
|                                                                          |
|  EACH PoP CONTAINS:                                                      |
|                                                                          |
|  +---------------------------------------------------------------+       |
|  |  EDGE PoP (e.g., NYC)                                         |       |
|  |                                                                 |     |
|  |  +----------+  +----------+  +----------+  +----------+        |      |
|  |  | LB / DNS |  | WAF /    |  | Cache    |  | TLS      |        |      |
|  |  | Router   |  | DDoS     |  | Servers  |  | Terminator|       |      |
|  |  |          |  | Filter   |  | (Varnish |  |           |       |      |
|  |  | Anycast  |  |          |  |  Nginx)  |  | Cert Mgmt |       |      |
|  |  +----------+  +----------+  +----------+  +----------+        |      |
|  |                                                                 |     |
|  |  +----------+  +----------+                                     |     |
|  |  | Compute  |  | Log /    |                                     |     |
|  |  | (Edge    |  | Metrics  |                                     |     |
|  |  |  Workers)|  | Collector|                                     |     |
|  |  +----------+  +----------+                                     |     |
|  +---------------------------------------------------------------+       |
|                                                                          |
|  TYPICAL CDN: 200-300 PoPs globally                                      |
|  Cloudflare: 300+ cities, AWS CloudFront: 400+ PoPs                      |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 3: ROUTING AND DNS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HOW USERS REACH THE NEAREST PoP:                                       |
|                                                                         |
|  1. ANYCAST (most common for CDNs)                                      |
|     Same IP address advertised from ALL PoPs via BGP.                   |
|     Internet routing sends packets to the nearest PoP.                  |
|     Used by: Cloudflare, Google Cloud CDN.                              |
|                                                                         |
|  2. DNS-BASED ROUTING                                                   |
|     CDN DNS server returns the IP of the nearest PoP based on:          |
|     * Client resolver IP (geographic lookup)                            |
|     * Latency measurements                                              |
|     * PoP health and load                                               |
|     Used by: AWS CloudFront, Akamai.                                    |
|                                                                         |
|  3. HTTP REDIRECT                                                       |
|     Client hits a central server, gets 302 redirect to nearest PoP.     |
|     Adds latency (extra round trip). Rarely used alone.                 |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  DNS FLOW:                                                              |
|                                                                         |
|  User types cdn.example.com                                             |
|    -> DNS resolves CNAME to cdn-provider.net                            |
|    -> CDN DNS returns IP of nearest PoP based on client location        |
|    -> User connects directly to edge server                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: CACHING STRATEGIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CACHE CONTROL HEADERS:                                                 |
|                                                                         |
|  Cache-Control: public, max-age=31536000    (cache 1 year)              |
|  Cache-Control: private, no-cache           (don't cache at edge)       |
|  Cache-Control: s-maxage=3600               (CDN caches 1 hour)         |
|  Cache-Control: stale-while-revalidate=60   (serve stale, refresh bg)   |
|  Vary: Accept-Encoding                      (cache per encoding)        |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  CACHE KEY COMPOSITION:                                                 |
|  Default: URL + Host header                                             |
|  Custom: URL + query params + cookies + headers + device type           |
|                                                                         |
|  EXAMPLE:                                                               |
|  https://cdn.example.com/api/products?page=2&sort=price                 |
|  Cache key = host + path + query string (sorted)                        |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  CACHE INVALIDATION:                                                    |
|                                                                         |
|  1. TTL EXPIRY (passive, simplest)                                      |
|     Content expires after max-age, edge fetches fresh on next request.  |
|                                                                         |
|  2. PURGE API (active, immediate)                                       |
|     POST /purge {"urls": ["https://cdn.example.com/image.png"]}         |
|     CDN removes from all PoPs (propagation: 1-30 seconds).              |
|                                                                         |
|  3. VERSIONED URLs (recommended for assets)                             |
|     /static/app.v3.2.1.js  -- new deploy = new URL = no stale cache     |
|     Content-hash: /static/app.abc123.js (webpack/vite output)           |
|                                                                         |
|  4. SOFT PURGE (stale-while-revalidate)                                 |
|     Mark as stale, serve stale while fetching fresh in background.      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5: EDGE COMPUTING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  EDGE COMPUTING = Run code AT the edge, not just cache content.         |
|                                                                         |
|  +-------------------+----------------------------------------------+   |
|  | Platform          | Runtime                                      |   |
|  +-------------------+----------------------------------------------+   |
|  | Cloudflare Workers| V8 isolates (JS/WASM), < 5ms cold start      |   |
|  | AWS Lambda@Edge   | Node.js/Python, runs at CloudFront PoPs      |   |
|  | AWS CloudFront Fn | Lightweight JS, sub-ms, viewer/origin hooks  |   |
|  | Vercel Edge Fn    | V8 isolates, integrated with Next.js         |   |
|  | Fastly Compute    | WASM-based, Rust/Go/JS                       |   |
|  | Deno Deploy       | V8 isolates, TypeScript native               |   |
|  +-------------------+----------------------------------------------+   |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  USE CASES:                                                             |
|                                                                         |
|  * A/B TESTING: Route 50% of users to variant B at edge                 |
|  * AUTH VALIDATION: Verify JWT at edge, reject before hitting origin    |
|  * GEO-PERSONALIZATION: Show local prices, language, content            |
|  * API GATEWAY: Rate limiting, request validation at edge               |
|  * IMAGE OPTIMIZATION: Resize/compress per device at edge               |
|  * BOT DETECTION: Block scrapers and bots at edge                       |
|  * FEATURE FLAGS: Toggle features per region without redeploy           |
|  * REDIRECTS: Handle URL rewrites at edge (no origin trip)              |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  EDGE vs ORIGIN vs SERVERLESS:                                          |
|                                                                         |
|  +------------------+------------+-----------+------------------+       |
|  | Aspect           | Edge       | Origin    | Serverless (FaaS)|       |
|  +------------------+------------+-----------+------------------+       |
|  | Latency          | < 50ms     | 100-500ms | 50-200ms         |       |
|  | Cold start       | < 5ms      | N/A       | 100ms-2s         |       |
|  | Compute power    | Limited    | Full      | Medium           |       |
|  | Data access      | Limited    | Full DB   | Network to DB    |       |
|  | Use case         | Transform  | Business  | Event-driven     |       |
|  |                  | + route    | logic     | workloads        |       |
|  +------------------+------------+-----------+------------------+       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6: CDN FOR VIDEO AND LARGE FILES

```
+--------------------------------------------------------------------------+
|                                                                          |
|  BYTE-RANGE REQUESTS (video/large files):                                |
|                                                                          |
|  Client: GET /video.mp4                                                  |
|          Range: bytes=1048576-2097151   (request 1MB chunk)              |
|                                                                          |
|  CDN serves partial content (HTTP 206).                                  |
|  * Enables seeking in video without downloading entire file              |
|  * CDN caches chunks independently                                       |
|  * Large files cached in segments, not whole files                       |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  ADAPTIVE BITRATE STREAMING:                                             |
|                                                                          |
|  HLS / DASH: Video split into small segments (2-10 sec each)             |
|  + Manifest file (M3U8 / MPD) listing all segments and qualities         |
|                                                                          |
|  /video/manifest.m3u8                                                    |
|  /video/720p/segment-001.ts                                              |
|  /video/720p/segment-002.ts                                              |
|  /video/1080p/segment-001.ts                                             |
|  /video/1080p/segment-002.ts                                             |
|                                                                          |
|  Player requests manifest -> picks quality based on bandwidth            |
|  -> requests segments from CDN -> adapts quality in real-time            |
|                                                                          |
|  CDN BENEFITS:                                                           |
|  * Each segment cached independently                                     |
|  * Popular segments stay hot in cache                                    |
|  * Different PoPs serve different users                                  |
|  * Origin only hit once per segment (then cached globally)               |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 7: SECURITY AT THE EDGE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DDoS PROTECTION:                                                       |
|  * Edge absorbs volumetric attacks (Tbps capacity)                      |
|  * Rate limiting per IP / geo / ASN                                     |
|  * Challenge pages (CAPTCHA) for suspicious traffic                     |
|  * Always-on mitigation (no manual intervention)                        |
|                                                                         |
|  WAF (Web Application Firewall):                                        |
|  * SQL injection, XSS, CSRF detection                                   |
|  * OWASP Top 10 rulesets                                                |
|  * Custom rules per endpoint                                            |
|  * Bot management (good bots vs bad bots)                               |
|                                                                         |
|  TLS AT EDGE:                                                           |
|  * Terminate TLS at PoP (user-to-edge is encrypted)                     |
|  * Edge-to-origin can be HTTP or TLS (configurable)                     |
|  * Auto-managed certificates (Let's Encrypt, ACM)                       |
|  * Support for TLS 1.3, HTTP/2, HTTP/3 (QUIC)                           |
|                                                                         |
|  SIGNED URLs / TOKENS:                                                  |
|  * Protect premium content from unauthorized access                     |
|  * URL valid for limited time / limited IP                              |
|  * Token verified at edge (no origin hit for auth)                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8: SCALE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ASSUMPTIONS:                                                           |
|  Serving for a top-50 website, 1B requests/day, 50 TB content cached    |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  REQUEST MATH:                                                          |
|  * 1B req/day = ~12K req/sec avg, 50K req/sec peak                      |
|                                                                         |
|  BANDWIDTH:                                                             |
|  * Avg response 50 KB x 12K/sec = 600 MB/sec = 4.8 Gbps avg             |
|  * Peak ~20 Gbps                                                        |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  CACHE HIT RATIO TARGET: 95%+                                           |
|  * Only 5% goes to origin = 600 req/sec to origin                       |
|                                                                         |
|  EDGE STORAGE:                                                          |
|  * 50 TB across 200 PoPs, but not all content at all PoPs               |
|  * Hot content maybe 500 GB per PoP                                     |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  GLOBAL CDN SCALE (Cloudflare reference):                               |
|  * 300+ PoPs                                                            |
|  * 200+ Tbps capacity                                                   |
|  * Billions of requests/day                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: DESIGN ALTERNATIVES AND TRADE-OFFS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ALTERNATIVE 1: ANYCAST vs DNS-BASED ROUTING                            |
|                                                                         |
|  Anycast: same IP from all PoPs, BGP routing. Simple client config,     |
|  fast failover (BGP converges). But routing is coarse (BGP doesn't      |
|  know about load).                                                      |
|                                                                         |
|  DNS-based: different IP per PoP, DNS resolves based on location /      |
|  health / load. More control but DNS TTL caching causes stickiness      |
|  (30-300s stale routing).                                               |
|                                                                         |
|  Most CDNs: Anycast for primary (Cloudflare), DNS for large CDNs        |
|  (CloudFront, Akamai). Some use both.                                   |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ALTERNATIVE 2: PUSH CDN vs PULL CDN                                    |
|                                                                         |
|  Push: origin uploads content to CDN proactively. Full control,         |
|  guaranteed warm cache. But complex workflow, wastes storage for        |
|  unpopular content.                                                     |
|                                                                         |
|  Pull: CDN fetches from origin on cache miss. Simple, automatic,        |
|  but first request is slow (cache miss).                                |
|                                                                         |
|  Best: pull for most content + push/pre-warm for predicted popular      |
|  content (new movie releases, product launches).                        |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ALTERNATIVE 3: SINGLE-TIER vs MULTI-TIER CACHE                         |
|                                                                         |
|  Single-tier (edge only): each PoP fetches from origin on miss.         |
|  Simpler but origin gets hit from 300 PoPs.                             |
|                                                                         |
|  Multi-tier (edge -> shield/regional -> origin): shield absorbs         |
|  misses from many edges. Origin only hit once per shield region.        |
|                                                                         |
|  Trade-off: multi-tier adds latency on miss (extra hop) but             |
|  dramatically reduces origin load. Essential at scale.                  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ALTERNATIVE 4: BUILD YOUR OWN CDN vs THIRD-PARTY                       |
|                                                                         |
|  Third-party (Cloudflare, Akamai, CloudFront): instant global           |
|  coverage, pay-per-use. $0.02-0.08/GB.                                  |
|                                                                         |
|  Own CDN (Netflix Open Connect): boxes in ISP data centers, massive     |
|  savings at scale. $5-10M/month vs $50M+ for third-party at Netflix     |
|  scale. But huge upfront investment, ISP relationships needed.          |
|                                                                         |
|  Hybrid: own CDN for top markets + third-party for tail regions.        |
|  Break-even: typically > 100 Gbps sustained before owning makes         |
|  financial sense.                                                       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ALTERNATIVE 5: EDGE WORKERS vs TRADITIONAL CDN CONFIG                  |
|                                                                         |
|  Traditional: cache rules via config (headers, regex patterns).         |
|  Limited logic.                                                         |
|                                                                         |
|  Edge workers (Cloudflare Workers, Lambda@Edge): full                   |
|  programmability at edge. Can rewrite requests, personalize,            |
|  A/B test. But limited runtime (CPU time, memory).                      |
|                                                                         |
|  Trade-off: workers add cost per invocation, harder to debug            |
|  (300 PoPs), cold start issues. Use for logic that saves an             |
|  origin trip.                                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10: COMMON ISSUES AND FAILURE SCENARIOS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ISSUE 1: CACHE STAMPEDE (THUNDERING HERD)                              |
|                                                                         |
|  Problem: popular object expires, 1000s of concurrent requests hit      |
|  origin simultaneously.                                                 |
|  Solution: request coalescing (only 1 request to origin per PoP),       |
|  stale-while-revalidate, lock-based refill (one thread fetches,         |
|  others wait).                                                          |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  ISSUE 2: CACHE POISONING                                               |
|                                                                         |
|  Problem: attacker manipulates cache key to serve wrong content         |
|  (e.g., injecting via Host header or unkeyed query params).             |
|  Solution: strict cache key composition, normalize/validate headers,    |
|  security headers (X-Cache-Key audit), WAF rules.                       |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  ISSUE 3: ORIGIN OVERLOAD DURING CDN OUTAGE                             |
|                                                                         |
|  Problem: CDN PoP goes down, traffic fails over to another PoP or       |
|  directly to origin. Origin can't handle the load.                      |
|  Solution: multi-tier cache (shield absorbs), origin auto-scaling,      |
|  circuit breaker (return stale/error page instead of overwhelming       |
|  origin), pre-provisioned origin capacity.                              |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  ISSUE 4: STALE CONTENT AFTER DEPLOY                                    |
|                                                                         |
|  Problem: new app deployed but CDN still serving old JS/CSS. Users      |
|  see broken UI (new HTML + old JS).                                     |
|  Solution: content-hash filenames (app.abc123.js), purge API on         |
|  deploy, immutable assets with long TTL + versioned URLs.               |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  ISSUE 5: CERTIFICATE RENEWAL FAILURE                                   |
|                                                                         |
|  Problem: TLS cert expires at edge, users get SSL errors. Or: cert      |
|  mismatch for custom domains.                                           |
|  Solution: automated cert renewal (Let's Encrypt + ACME), monitoring    |
|  for expiring certs (alert 30 days before), wildcard certs for          |
|  subdomains, fallback cert.                                             |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  ISSUE 6: GEO-ROUTING INACCURACY                                        |
|                                                                         |
|  Problem: user routed to wrong PoP because DNS resolver IP doesn't      |
|  match user location (VPN, corporate DNS).                              |
|  Solution: EDNS Client Subnet (ECS) sends client IP prefix to CDN       |
|  DNS, Anycast routing (doesn't depend on DNS), client-side latency      |
|  measurement for PoP selection.                                         |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  ISSUE 7: CACHE STORAGE EXHAUSTION AT EDGE                              |
|                                                                         |
|  Problem: PoP disk fills up, must evict content. If eviction is         |
|  wrong (evict popular content), cache hit ratio drops.                  |
|  Solution: LRU/LFU eviction with admission policy (don't cache          |
|  content accessed only once), tiered storage (SSD for hot, HDD for      |
|  warm), monitor eviction rate and cache churn.                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11: INTERVIEW QUESTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How does a CDN reduce latency?                                      |
|  A: Content served from PoP physically close to user (< 50ms RTT)       |
|     vs origin server that may be 200-500ms away. Also: TLS              |
|     termination at edge, connection reuse, HTTP/2 multiplexing.         |
|                                                                         |
|  Q: How do you handle cache invalidation for a CDN?                     |
|  A: Versioned URLs for assets (/app.abc123.js), TTL for API             |
|     responses, purge API for immediate invalidation, stale-while-       |
|     revalidate for smooth transitions.                                  |
|                                                                         |
|  Q: CDN cache miss storm (origin overload)?                             |
|  A: Request coalescing -- CDN groups identical concurrent cache-miss    |
|     requests into a single origin fetch. Also: shield/mid-tier cache    |
|     between edge and origin, stale-while-revalidate.                    |
|                                                                         |
|  Q: How would you serve region-specific content?                        |
|  A: Edge workers read geo headers (CF-IPCountry), serve localized       |
|     content without origin trip. Or: cache key includes country.        |
|                                                                         |
|  Q: Push vs Pull CDN?                                                   |
|  A: Pull: CDN fetches from origin on cache miss (most common).          |
|     Push: You upload content directly to CDN storage (S3 origin).       |
|     Pull is simpler. Push gives more control for large static sites.    |
|                                                                         |
|  Q: How does a CDN handle dynamic content?                              |
|  A: Short TTL (1-60s) + stale-while-revalidate. Edge-side includes      |
|     (ESI) for mixing cached + dynamic fragments. Edge compute for       |
|     personalization. TCP/TLS optimization to origin for uncacheable.    |
|                                                                         |
|  Q: How would you design a CDN from scratch for a startup?              |
|  A: Start with third-party CDN (CloudFront or Cloudflare). Configure    |
|     cache headers properly. Use versioned asset URLs. Set up a          |
|     multi-tier cache (CloudFront origin shield). Add edge functions     |
|     only when needed (A/B testing, geo-routing). Monitor cache hit      |
|     ratio -- if < 90%, fix cache key configuration.                     |
|                                                                         |
|  Q: How does Netflix's Open Connect work?                               |
|  A: Netflix places custom hardware (Open Connect Appliances) inside     |
|     ISP data centers. During off-peak hours, popular content is         |
|     pre-positioned. During streaming, 95%+ of traffic is served from    |
|     within the ISP network (zero transit cost). Appliances are free     |
|     to ISPs (Netflix saves on bandwidth, ISP saves on peering).         |
|                                                                         |
+-------------------------------------------------------------------------+
```
