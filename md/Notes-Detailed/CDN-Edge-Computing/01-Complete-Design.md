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

## SECTION 8: INTERVIEW QUESTIONS

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
+-------------------------------------------------------------------------+
```
