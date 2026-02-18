# CHAPTER 3: LOAD BALANCING
*Distributing Traffic Intelligently*

Load balancing is the technique of distributing incoming requests across
multiple servers. It's essential for scalability, availability, and
performance in any distributed system.

## SECTION 3.1: WHAT IS LOAD BALANCING?

### THE PROBLEM

Without load balancing, a single server handles all requests:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WITHOUT LOAD BALANCING                                                 |
|                                                                         |
|  Client 1 ---+                                                          |
|  Client 2 ---+                                                          |
|  Client 3 ---+---> Single Server ---> Database                          |
|  Client 4 ---+         |                                                |
|  Client N ---+         v                                                |
|                   OVERWHELMED!                                          |
|                                                                         |
|  PROBLEMS:                                                              |
|  * Server becomes bottleneck                                            |
|  * Single point of failure                                              |
|  * No way to scale                                                      |
|  * Poor user experience during high load                                |
|  * Downtime during maintenance                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### THE SOLUTION

A load balancer sits between clients and servers:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WITH LOAD BALANCING                                                    |
|                                                                         |
|                                    +----------+                         |
|  Client 1 ---+                +--->| Server 1 |                         |
|  Client 2 ---+                |    +----------+                         |
|  Client 3 ---+---> Load ------+---> +----------+                        |
|  Client 4 ---+    Balancer    |    | Server 2 |                         |
|  Client N ---+                |    +----------+                         |
|                               +---> +----------+                        |
|                                    | Server 3 |                         |
|                                    +----------+                         |
|                                                                         |
|  BENEFITS:                                                              |
|  Y Distributes load across servers                                      |
|  Y No single point of failure (with redundant LBs)                      |
|  Y Easy to scale (add more servers)                                     |
|  Y Better user experience                                               |
|  Y Can do SSL termination, caching, compression                         |
|  Y Zero-downtime deployments                                            |
|  Y Geographic distribution                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.2: TYPES OF LOAD BALANCERS

### LAYER 4 (TRANSPORT LAYER) LOAD BALANCER

Operates at TCP/UDP level. Doesn't look at packet content.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LAYER 4 LOAD BALANCING                                                 |
|                                                                         |
|  HOW IT WORKS:                                                          |
|  * Looks at: Source IP, Destination IP, Source Port, Destination Port   |
|  * Makes routing decision based on this 4-tuple                         |
|  * Doesn't inspect packet content (can't read HTTP headers)             |
|  * Forwards raw TCP/UDP packets                                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |  TCP Packet Header                                                |  |
|  |  +-------------------------------------------------------------+  |  |
|  |  | Src IP: 1.2.3.4 | Dst IP: 5.6.7.8 | Port: 443               |  |  |
|  |  +-------------------------------------------------------------+  |  |
|  |           v                                                       |  |
|  |  L4 Load Balancer (routes based on header only)                   |  |
|  |           v                                                       |  |
|  |  [Server 1] [Server 2] [Server 3]                                 |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  TWO MODES:                                                             |
|                                                                         |
|  NAT MODE (Network Address Translation):                                |
|  * LB changes destination IP to server IP                               |
|  * Server sees LB as client, LB sees server as destination              |
|  * Return traffic goes through LB                                       |
|                                                                         |
|  DSR MODE (Direct Server Return):                                       |
|  * LB only handles incoming traffic                                     |
|  * Server responds directly to client (faster!)                         |
|  * Great for asymmetric traffic (small request, large response)         |
|                                                                         |
|  PROS:                                                                  |
|  Y Very fast (simple header inspection, no content parsing)             |
|  Y Protocol agnostic (HTTP, HTTPS, gRPC, database, any TCP/UDP)         |
|  Y Lower latency                                                        |
|  Y Less CPU intensive                                                   |
|  Y Can handle millions of connections                                   |
|                                                                         |
|  CONS:                                                                  |
|  X Can't make decisions based on content                                |
|  X Can't do URL-based routing                                           |
|  X No SSL termination at LB (can't inspect HTTPS)                       |
|  X No content caching                                                   |
|  X Limited health checking (TCP only)                                   |
|                                                                         |
|  EXAMPLES:                                                              |
|  * AWS NLB (Network Load Balancer)                                      |
|  * HAProxy (TCP mode)                                                   |
|  * Nginx (stream module)                                                |
|  * LVS (Linux Virtual Server)                                           |
|  * F5 BIG-IP (L4 mode)                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### LAYER 7 (APPLICATION LAYER) LOAD BALANCER

Operates at HTTP/HTTPS level. Inspects request content.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LAYER 7 LOAD BALANCING                                                 |
|                                                                         |
|  HOW IT WORKS:                                                          |
|  * Terminates the TCP connection                                        |
|  * Parses HTTP request (headers, URL, cookies, body)                    |
|  * Makes intelligent routing decisions                                  |
|  * Can modify requests/responses                                        |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |  HTTP Request                                                     |  |
|  |  +-------------------------------------------------------------+  |  |
|  |  | GET /api/users HTTP/1.1                                     |  |  |
|  |  | Host: api.example.com                                       |  |  |
|  |  | Cookie: session=abc123                                      |  |  |
|  |  | X-Tenant-ID: tenant-456                                     |  |  |
|  |  +-------------------------------------------------------------+  |  |
|  |           v                                                       |  |
|  |  L7 Load Balancer (inspects all content)                          |  |
|  |           v                                                       |  |
|  |  ROUTING RULES:                                                   |  |
|  |  /api/users > API Servers (v2)                                    |  |
|  |  /api/v1/*  > API Servers (legacy)                                |  |
|  |  /static/*  > CDN/Static Servers                                  |  |
|  |  /admin/*   > Admin Servers (internal only)                       |  |
|  |  Host: api-beta.* > Beta cluster                                  |  |
|  |  Header X-Tenant-ID: premium > Premium cluster                    |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  CAPABILITIES:                                                          |
|                                                                         |
|  * URL/Path routing: /api/* > API servers                               |
|  * Header routing: X-Version: 2 > v2 servers                            |
|  * Cookie routing: session > same server (sticky)                       |
|  * Host routing: api.example.com vs admin.example.com                   |
|  * Query param routing: ?beta=true > beta servers                       |
|  * Method routing: GET > read replicas, POST > primary                  |
|                                                                         |
|  PROS:                                                                  |
|  Y Content-based routing (URL, headers, cookies)                        |
|  Y SSL/TLS termination (offload crypto from servers)                    |
|  Y Response caching                                                     |
|  Y Response compression (gzip, brotli)                                  |
|  Y Request/response manipulation (add headers, rewrite URLs)            |
|  Y Advanced health checks (HTTP status, response content)               |
|  Y Rate limiting per route/user                                         |
|  Y Web Application Firewall (WAF) capabilities                          |
|  Y Authentication/Authorization                                         |
|                                                                         |
|  CONS:                                                                  |
|  X Slower than L4 (must parse HTTP)                                     |
|  X More CPU intensive                                                   |
|  X Higher latency                                                       |
|  X Only works with HTTP/HTTPS (mostly)                                  |
|  X Limited throughput compared to L4                                    |
|                                                                         |
|  EXAMPLES:                                                              |
|  * AWS ALB (Application Load Balancer)                                  |
|  * Nginx (http module)                                                  |
|  * HAProxy (http mode)                                                  |
|  * Envoy                                                                |
|  * Traefik                                                              |
|  * Kong                                                                 |
|  * Cloudflare                                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

#### WHAT "TERMINATES THE TCP CONNECTION" MEANS

L4 vs L7 handle the client's TCP connection fundamentally differently:

```
L4 (Pass-Through):
  Client <------------- single TCP connection -------------> Server
                    LB just rewrites IP headers
                    and forwards raw packets

L7 (Termination):
  Client <--- TCP conn 1 ---> L7 LB <--- TCP conn 2 ---> Server
                                 ^
                    Client's TCP connection ENDS here
                    LB reads full HTTP request,
                    then opens a NEW connection to backend
```

- Client does a full TCP handshake (SYN, SYN-ACK, ACK) with the **load balancer**
- The LB accepts the connection as if it were the final destination
- The LB reads the complete HTTP request (URL, headers, cookies, body)
- Based on content, it opens a **separate TCP connection** to the chosen backend
- The client never has a direct TCP connection to the backend server
- This is required because reading HTTP content (Layer 7) requires a fully established TCP connection (Layer 4)

#### WHAT "SSL/TLS TERMINATION" MEANS

Direct consequence of TCP termination — since the LB is the endpoint of the client's connection, it can also be the endpoint of the **encryption**.

```
WITHOUT TLS Termination (each server handles crypto):

  Client --HTTPS--> LB --HTTPS--> Server 1 (decrypt, CPU heavy)
                       --HTTPS--> Server 2 (decrypt, CPU heavy)
                       --HTTPS--> Server 3 (decrypt, CPU heavy)
  * SSL certs needed on EVERY server
  * Every server burns CPU on crypto


WITH TLS Termination at LB:

  Client --HTTPS (encrypted)--> L7 LB --HTTP (plain text)--> Server 1
                                   ^                     +--> Server 2
                          Decrypts here                  +--> Server 3
                     (holds SSL certificate)
  * SSL cert managed in ONE place
  * Backend servers freed from crypto overhead
  * LB can now inspect/route based on HTTP content
```

- TLS handshakes + encryption/decryption are **CPU-heavy** operations
- Without TLS termination, every backend server does this crypto work itself
- With TLS termination at LB, backend servers only deal with plain HTTP
- SSL certificates managed in **one place** (the LB) instead of every server
- L4 LBs **cannot** do this — they forward raw packets without understanding them

> **Note:** Internal traffic (LB to servers) is plain HTTP over a trusted private network.
> For zero-trust environments, you can re-encrypt (mTLS) between LB and backends,
> but the LB still terminates and re-establishes — giving it the ability to inspect content.

### WHEN TO USE EACH

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LAYER 4 vs LAYER 7 DECISION MATRIX                                     |
|                                                                         |
|  USE LAYER 4 WHEN:                                                      |
|  * You need raw performance (millions of connections)                   |
|  * Traffic is non-HTTP (database, game servers, MQTT, gRPC)             |
|  * You don't need content inspection                                    |
|  * Lower latency is critical (high-frequency trading)                   |
|  * End-to-end TLS is required (can't terminate at LB)                   |
|                                                                         |
|  USE LAYER 7 WHEN:                                                      |
|  * You need content-based routing                                       |
|  * You want SSL termination at load balancer                            |
|  * You need caching, compression                                        |
|  * You want advanced features (rate limiting, WAF)                      |
|  * A/B testing or canary deployments                                    |
|  * Multi-tenant routing                                                 |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  COMMON PATTERN: USE BOTH                                               |
|                                                                         |
|  Internet                                                               |
|      v                                                                  |
|  L4 Load Balancer (NLB) - High performance, SSL passthrough             |
|      v                                                                  |
|  L7 Load Balancers (ALB/Nginx) - Content routing, SSL termination       |
|      v                                                                  |
|  Application Servers                                                    |
|                                                                         |
|  NETFLIX ARCHITECTURE:                                                  |
|  +-------------------------------------------------------------------+  |
|  |  Internet > AWS NLB > Zuul (L7) > Microservices                   |  |
|  |                                                                   |  |
|  |  NLB: High throughput, handles millions of connections            |  |
|  |  Zuul: Routing, rate limiting, auth, canary                       |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.3: LOAD BALANCING ALGORITHMS

### ROUND ROBIN

The simplest algorithm. Rotate through servers sequentially.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ROUND ROBIN                                                            |
|                                                                         |
|  Request 1 > Server A                                                   |
|  Request 2 > Server B                                                   |
|  Request 3 > Server C                                                   |
|  Request 4 > Server A (cycle repeats)                                   |
|  Request 5 > Server B                                                   |
|  ...                                                                    |
|                                                                         |
|  IMPLEMENTATION:                                                        |
|  counter = 0                                                            |
|  def get_server():                                                      |
|      server = servers[counter % len(servers)]                           |
|      counter += 1                                                       |
|      return server                                                      |
|                                                                         |
|  PROS:                                                                  |
|  Y Simple to implement                                                  |
|  Y Even distribution (if servers are equal)                             |
|  Y No server state tracking needed                                      |
|  Y Low overhead                                                         |
|                                                                         |
|  CONS:                                                                  |
|  X Ignores server capacity (some servers may be more powerful)          |
|  X Ignores current load (server might be busy)                          |
|  X Long requests can pile up on one server                              |
|  X Doesn't consider server health                                       |
|                                                                         |
|  USE WHEN: Servers are identical and requests are similar               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WEIGHTED ROUND ROBIN

Accounts for different server capacities.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WEIGHTED ROUND ROBIN                                                   |
|                                                                         |
|  Server A (weight: 5) - powerful server (16 CPU)                        |
|  Server B (weight: 3) - medium server (8 CPU)                           |
|  Server C (weight: 2) - smaller server (4 CPU)                          |
|                                                                         |
|  Distribution pattern (weights 5:3:2):                                  |
|  Requests 1-5   > Server A                                              |
|  Requests 6-8   > Server B                                              |
|  Requests 9-10  > Server C                                              |
|  Requests 11-15 > Server A (cycle repeats)                              |
|  ...                                                                    |
|                                                                         |
|  Result: 50% to A, 30% to B, 20% to C                                   |
|                                                                         |
|  SMOOTH WEIGHTED ROUND ROBIN (Better distribution):                     |
|  Instead of consecutive requests to same server,                        |
|  interleave: A, A, B, A, C, B, A, B, A, C                               |
|                                                                         |
|  USE WHEN: Servers have different capacities                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### LEAST CONNECTIONS

Send to the server with fewest active connections.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LEAST CONNECTIONS                                                      |
|                                                                         |
|  Current state:                                                         |
|  Server A: 50 active connections                                        |
|  Server B: 30 active connections  < Least connections                   |
|  Server C: 80 active connections                                        |
|                                                                         |
|  New request > Server B (has least connections)                         |
|                                                                         |
|  After routing:                                                         |
|  Server A: 50 connections                                               |
|  Server B: 31 connections                                               |
|  Server C: 80 connections                                               |
|                                                                         |
|  PROS:                                                                  |
|  Y Adapts to varying request durations                                  |
|  Y Better for long-lived connections (WebSockets, streaming)            |
|  Y Dynamic load distribution                                            |
|  Y Naturally handles slow servers (they accumulate connections)         |
|                                                                         |
|  CONS:                                                                  |
|  X Requires tracking connection state                                   |
|  X Slightly more overhead                                               |
|  X New servers get flooded (0 connections initially)                    |
|                                                                         |
|  USE WHEN: Requests have variable processing times                      |
|                                                                         |
|  REAL-WORLD: Netflix uses least connections for long streaming          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WEIGHTED LEAST CONNECTIONS

Combines capacity weights with connection count.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WEIGHTED LEAST CONNECTIONS                                             |
|                                                                         |
|  Score = active_connections / weight (lower is better)                  |
|                                                                         |
|  Server A: 100 connections, weight 10 > Score: 100/10 = 10.0            |
|  Server B:  30 connections, weight 5  > Score: 30/5 = 6.0 < Best!       |
|  Server C:  80 connections, weight 8  > Score: 80/8 = 10.0              |
|                                                                         |
|  New request > Server B (lowest score)                                  |
|                                                                         |
|  USE WHEN: Servers have different capacities AND variable requests      |
|                                                                         |
+-------------------------------------------------------------------------+
```

IP HASH
-------

Hash client IP to determine server. Same client always hits same server.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IP HASH (SESSION PERSISTENCE)                                          |
|                                                                         |
|  Client IP: 192.168.1.100                                               |
|  hash("192.168.1.100") % 3 = 1                                          |
|  > Always routes to Server B                                            |
|                                                                         |
|  Client IP: 10.0.0.50                                                   |
|  hash("10.0.0.50") % 3 = 0                                              |
|  > Always routes to Server A                                            |
|                                                                         |
|  PROS:                                                                  |
|  Y Session stickiness without cookies                                   |
|  Y Good for stateful applications                                       |
|  Y Predictable routing                                                  |
|                                                                         |
|  CONS:                                                                  |
|  X Uneven distribution if IP distribution is uneven                     |
|  X Server removal/addition breaks sessions (rehashing)                  |
|  X Clients behind NAT share same server                                 |
|  X Mobile users changing networks lose affinity                         |
|                                                                         |
|  USE WHEN: Need sticky sessions without cookie support                  |
|                                                                         |
|  BETTER ALTERNATIVE: Consistent hashing (minimizes rehashing)           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### LEAST RESPONSE TIME

Route to server with lowest response time + fewest connections.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LEAST RESPONSE TIME                                                    |
|                                                                         |
|  Server A: Avg response 50ms, 50 connections                            |
|  Server B: Avg response 30ms, 30 connections < Best!                    |
|  Server C: Avg response 40ms, 80 connections                            |
|                                                                         |
|  Considers both speed and load.                                         |
|                                                                         |
|  FORMULA OPTIONS:                                                       |
|  * response_time x connections                                          |
|  * response_time + (connections x weight)                               |
|  * Just response_time (ignoring connections)                            |
|                                                                         |
|  PROS:                                                                  |
|  Y Routes to fastest, healthiest server                                 |
|  Y Adapts to server performance changes                                 |
|  Y Great for heterogeneous environments                                 |
|                                                                         |
|  CONS:                                                                  |
|  X Requires response time tracking                                      |
|  X More complex implementation                                          |
|  X Response times can be noisy                                          |
|                                                                         |
|  USED BY: Nginx (least_time), HAProxy                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

RANDOM
------

Simple but surprisingly effective for large clusters.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RANDOM LOAD BALANCING                                                  |
|                                                                         |
|  Just pick a random server.                                             |
|                                                                         |
|  WHY IT WORKS:                                                          |
|  With enough requests, random distribution approaches even              |
|  distribution (Law of Large Numbers)                                    |
|                                                                         |
|  PROS:                                                                  |
|  Y Extremely simple                                                     |
|  Y No state tracking                                                    |
|  Y No coordination between LB instances                                 |
|  Y Works well at scale                                                  |
|                                                                         |
|  CONS:                                                                  |
|  X Can be uneven for small request counts                               |
|  X Ignores server health/capacity                                       |
|                                                                         |
|  POWER OF TWO CHOICES (Better random):                                  |
|  Pick 2 random servers, choose the one with fewer connections           |
|  Gets most benefits of least-connections with simple implementation     |
|  Used by: Envoy, many modern load balancers                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ALGORITHM COMPARISON

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHOOSING THE RIGHT ALGORITHM                                           |
|                                                                         |
|  +---------------------+----------------------------------------------+ |
|  | Algorithm           | Best For                                     | |
|  +---------------------+----------------------------------------------+ |
|  | Round Robin         | Identical servers, similar requests          | |
|  | Weighted RR         | Different server capacities                  | |
|  | Least Connections   | Long-lived connections, variable requests    | |
|  | Weighted LC         | Different capacities + variable requests     | |
|  | IP Hash             | Session affinity without cookies             | |
|  | Least Response Time | Heterogeneous performance                    | |
|  | Random              | Very large clusters, simplicity              | |
|  | Power of Two        | Balance of simplicity and effectiveness      | |
|  +---------------------+----------------------------------------------+ |
|                                                                         |
|  DEFAULT RECOMMENDATION: Start with Round Robin or Least Connections    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.4: HEALTH CHECKS

Load balancers must know if servers are healthy:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HEALTH CHECK TYPES                                                     |
|                                                                         |
|  1. TCP HEALTH CHECK (L4)                                               |
|  --------------------------                                             |
|  Just check if port is open (TCP handshake succeeds)                    |
|                                                                         |
|  LB > SYN > Server                                                      |
|  LB < SYN-ACK < Server  (healthy!)                                      |
|  or                                                                     |
|  LB < timeout (unhealthy!)                                              |
|  or                                                                     |
|  LB < RST (connection refused - unhealthy!)                             |
|                                                                         |
|  PROS: Fast, simple, works for any TCP service                          |
|  CONS: Port open ! app working (process might be hung)                  |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. HTTP HEALTH CHECK (L7)                                              |
|  ---------------------------                                            |
|  Make HTTP request to health endpoint                                   |
|                                                                         |
|  LB > GET /health HTTP/1.1                                              |
|  LB < 200 OK < Server  (healthy!)                                       |
|  or                                                                     |
|  LB < 500 Internal Server Error (unhealthy!)                            |
|  or                                                                     |
|  LB < timeout (unhealthy!)                                              |
|                                                                         |
|  PROS: Checks application health, not just connectivity                 |
|  CONS: More overhead, only for HTTP services                            |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. DEEP HEALTH CHECK                                                   |
|  ------------------------                                               |
|  Actually test application functionality                                |
|                                                                         |
|  GET /health/deep                                                       |
|                                                                         |
|  Health endpoint checks:                                                |
|  Y Database connectivity (SELECT 1)                                     |
|  Y Redis connectivity (PING)                                            |
|  Y Disk space (> 10% free)                                              |
|  Y Memory usage (< 90%)                                                 |
|  Y Critical downstream services                                         |
|                                                                         |
|  EXAMPLE RESPONSE:                                                      |
|  {                                                                      |
|    "status": "healthy",                                                 |
|    "checks": {                                                          |
|      "database": {"status": "healthy", "latency_ms": 5},                |
|      "redis": {"status": "healthy", "latency_ms": 1},                   |
|      "disk": {"status": "healthy", "free_pct": 45},                     |
|      "memory": {"status": "healthy", "used_pct": 62}                    |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
|  PROS: Most accurate health assessment                                  |
|  CONS: More expensive, can slow down LB                                 |
|                                                                         |
|  BEST PRACTICE: Use shallow for LB, deep for monitoring                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HEALTH CHECK PARAMETERS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONFIGURING HEALTH CHECKS                                              |
|                                                                         |
|  PARAMETERS:                                                            |
|                                                                         |
|  Interval: How often to check (e.g., every 10 seconds)                  |
|  Timeout: How long to wait for response (e.g., 5 seconds)               |
|  Healthy threshold: Consecutive successes to mark healthy (e.g., 2)     |
|  Unhealthy threshold: Consecutive failures to mark unhealthy (e.g., 3)  |
|                                                                         |
|  EXAMPLE CONFIGURATIONS:                                                |
|                                                                         |
|  AGGRESSIVE (Fast detection, more overhead):                            |
|  * Interval: 5 seconds                                                  |
|  * Timeout: 2 seconds                                                   |
|  * Unhealthy after: 2 failures                                          |
|  * Detection time: 10 seconds                                           |
|                                                                         |
|  CONSERVATIVE (Slower detection, less overhead):                        |
|  * Interval: 30 seconds                                                 |
|  * Timeout: 10 seconds                                                  |
|  * Unhealthy after: 3 failures                                          |
|  * Detection time: 90 seconds                                           |
|                                                                         |
|  AWS ALB EXAMPLE:                                                       |
|  -----------------                                                      |
|  HealthCheckPath: /health                                               |
|  HealthCheckIntervalSeconds: 30                                         |
|  HealthCheckTimeoutSeconds: 5                                           |
|  HealthyThresholdCount: 2                                               |
|  UnhealthyThresholdCount: 3                                             |
|  Matcher: { HttpCode: "200-299" }                                       |
|                                                                         |
|  NGINX EXAMPLE:                                                         |
|  ---------------                                                        |
|  upstream backend {                                                     |
|      server 10.0.0.1:8080;                                              |
|      server 10.0.0.2:8080;                                              |
|      health_check interval=10 fails=3 passes=2 uri=/health;             |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.5: SSL/TLS TERMINATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SSL/TLS TERMINATION                                                    |
|                                                                         |
|  WHERE TO TERMINATE SSL?                                                |
|                                                                         |
|  OPTION 1: AT LOAD BALANCER (Recommended for most cases)                |
|  ---------------------------------------------------------              |
|                                                                         |
|  Client --HTTPS--> LB (terminates SSL) --HTTP--> Servers                |
|                                                                         |
|  PROS:                                                                  |
|  Y Offloads CPU-intensive crypto from app servers                       |
|  Y Centralized certificate management                                   |
|  Y LB can inspect HTTP content for routing                              |
|  Y Caching possible                                                     |
|  Y Simpler server configuration                                         |
|                                                                         |
|  CONS:                                                                  |
|  X Internal traffic is unencrypted (OK in private network)              |
|  X LB must have access to private keys                                  |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  OPTION 2: END-TO-END (SSL passthrough or re-encryption)                |
|  ----------------------------------------------------------             |
|                                                                         |
|  SSL PASSTHROUGH:                                                       |
|  Client --HTTPS--> LB (doesn't decrypt) --HTTPS--> Servers              |
|  LB routes based on SNI (Server Name Indication) only                   |
|                                                                         |
|  SSL RE-ENCRYPTION:                                                     |
|  Client --HTTPS--> LB (decrypt, inspect) --HTTPS--> Servers             |
|  Two TLS sessions: client-LB, LB-server                                 |
|                                                                         |
|  PROS:                                                                  |
|  Y Traffic encrypted at all times                                       |
|  Y Compliance with strict security requirements                         |
|  Y Defense in depth                                                     |
|                                                                         |
|  CONS:                                                                  |
|  X More CPU usage (encryption everywhere)                               |
|  X Certificate management on every server                               |
|  X No content-based routing with passthrough                            |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  MUTUAL TLS (mTLS)                                                      |
|  ------------------                                                     |
|  Both client AND server present certificates                            |
|  Used for service-to-service authentication                             |
|                                                                         |
|  Client > presents cert > Server validates                              |
|  Server > presents cert > Client validates                              |
|                                                                         |
|  Common in:                                                             |
|  * Service meshes (Istio, Linkerd)                                      |
|  * Zero-trust architectures                                             |
|  * Internal microservices                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.6: SESSION PERSISTENCE (STICKY SESSIONS)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SESSION PERSISTENCE                                                    |
|                                                                         |
|  WHY NEEDED:                                                            |
|  Some applications store session state in server memory                 |
|  All requests from a user must go to the same server                    |
|                                                                         |
|  METHODS:                                                               |
|                                                                         |
|  1. COOKIE-BASED (L7 only)                                              |
|  -------------------------                                              |
|  LB sets a cookie with server identifier                                |
|                                                                         |
|  First request:                                                         |
|  Client > LB (picks Server A) > Response + Set-Cookie: SRV=A            |
|                                                                         |
|  Subsequent requests:                                                   |
|  Client (Cookie: SRV=A) > LB > Server A                                 |
|                                                                         |
|  PROS: Survives server IP changes, works across LB instances            |
|  CONS: Cookie overhead, requires L7 LB                                  |
|                                                                         |
|  2. IP-BASED (L4)                                                       |
|  -----------------                                                      |
|  Hash client IP to determine server                                     |
|                                                                         |
|  hash(client_ip) % num_servers > server index                           |
|                                                                         |
|  PROS: Works at L4, no cookies needed                                   |
|  CONS: NAT issues, mobile users, server changes break sessions          |
|                                                                         |
|  3. APPLICATION COOKIE                                                  |
|  ---------------------                                                  |
|  App sets session cookie, LB reads it for routing                       |
|                                                                         |
|  Cookie: JSESSIONID=abc123                                              |
|  LB: "abc123 maps to Server B"                                          |
|                                                                         |
|  PROS: Application controls sessions                                    |
|  CONS: More complex                                                     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  BETTER APPROACH: STATELESS SESSIONS                                    |
|  -------------------------------------                                  |
|                                                                         |
|  Instead of sticky sessions, externalize state:                         |
|                                                                         |
|  * Store sessions in Redis/Memcached                                    |
|  * Use JWT tokens (stateless)                                           |
|                                                                         |
|  BENEFITS:                                                              |
|  Y Any server can handle any request                                    |
|  Y Server failures don't lose sessions                                  |
|  Y Easy scaling (add/remove servers freely)                             |
|  Y Better load distribution                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.7: HIGH AVAILABILITY FOR LOAD BALANCERS

The load balancer itself can be a single point of failure:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MAKING LOAD BALANCERS HIGHLY AVAILABLE                                 |
|                                                                         |
|  PATTERN 1: ACTIVE-PASSIVE (Failover)                                   |
|  ------------------------------------                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                        Virtual IP (VIP)                           |  |
|  |                             |                                     |  |
|  |               +-------------+-------------+                       |  |
|  |               v                           v                       |  |
|  |         +---------+                +---------+                    |  |
|  |         | Active  | <-- heartbeat --> Passive|                    |  |
|  |         |   LB    |      (VRRP)       |   LB    |                 |  |
|  |         +---------+                +---------+                    |  |
|  |               |                           |                       |  |
|  |               v                           |                       |  |
|  |         [Servers]               (standby, ready)                  |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  HOW IT WORKS:                                                          |
|  * Both LBs share a Virtual IP (VIP)                                    |
|  * Active LB handles all traffic                                        |
|  * Passive monitors Active via heartbeat                                |
|  * If Active fails, Passive takes over VIP                              |
|  * Uses VRRP (Virtual Router Redundancy Protocol)                       |
|                                                                         |
|  Failover time: 1-30 seconds                                            |
|  Pro: Simple                                                            |
|  Con: Passive LB sits idle (waste of resources)                         |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  PATTERN 2: ACTIVE-ACTIVE                                               |
|  --------------------------                                             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                         DNS                                       |  |
|  |           +--------------+--------------+                         |  |
|  |           v                             v                         |  |
|  |     +---------+                   +---------+                     |  |
|  |     |  LB 1   |                   |  LB 2   |                     |  |
|  |     | Active  |                   | Active  |                     |  |
|  |     +---------+                   +---------+                     |  |
|  |           |                             |                         |  |
|  |           +--------------+--------------+                         |  |
|  |                          v                                        |  |
|  |                     [Servers]                                     |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  HOW IT WORKS:                                                          |
|  * DNS returns multiple LB IPs                                          |
|  * Both LBs handle traffic simultaneously                               |
|  * If one fails, DNS health check removes it                            |
|                                                                         |
|  Pro: Better resource utilization                                       |
|  Pro: No failover delay                                                 |
|  Con: DNS TTL can cause delays in failure detection                     |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  PATTERN 3: CLOUD MANAGED LBs (RECOMMENDED)                             |
|  -------------------------------------------                            |
|                                                                         |
|  AWS ALB/NLB, Google Cloud LB, Azure Load Balancer                      |
|                                                                         |
|  BENEFITS:                                                              |
|  Y Fully managed, HA by default                                         |
|  Y Automatically scales with traffic                                    |
|  Y Built-in health checks                                               |
|  Y No infrastructure to manage                                          |
|  Y Multi-AZ redundancy                                                  |
|  Y DDoS protection                                                      |
|  Y Integration with cloud services                                      |
|                                                                         |
|  AWS ALB/NLB:                                                           |
|  * Spans multiple Availability Zones                                    |
|  * Auto-scales to millions of requests                                  |
|  * 99.99% SLA                                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.8: GLOBAL LOAD BALANCING (GSLB)

Distribute traffic across multiple geographic regions:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  GLOBAL SERVER LOAD BALANCING                                           |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |                        User in Europe                             |  |
|  |                             |                                     |  |
|  |                             v                                     |  |
|  |                         DNS Query                                 |  |
|  |                   "Where is api.example.com?"                     |  |
|  |                             |                                     |  |
|  |                             v                                     |  |
|  |         +---------- GSLB/DNS ----------+                          |  |
|  |         |  Intelligent DNS Resolution  |                          |  |
|  |         |                              |                          |  |
|  |         |  User in Europe > EU IP      |                          |  |
|  |         |  User in Asia > APAC IP      |                          |  |
|  |         |  User in US > US IP          |                          |  |
|  |         +------------------------------+                          |  |
|  |                             |                                     |  |
|  |              +--------------+--------------+                      |  |
|  |              v              v              v                      |  |
|  |         +--------+    +--------+    +--------+                    |  |
|  |         | EU-WEST|    |  APAC  |    |US-EAST |                    |  |
|  |         |   LB   |    |   LB   |    |   LB   |                    |  |
|  |         +--------+    +--------+    +--------+                    |  |
|  |              |              |              |                      |  |
|  |         [EU Servers] [APAC Servers] [US Servers]                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  GSLB ROUTING METHODS:                                                  |
|                                                                         |
|  1. GEOLOCATION                                                         |
|  -----------------                                                      |
|  Route based on user's geographic location (IP geo-lookup)              |
|  User in Paris > EU datacenter                                          |
|  User in Tokyo > APAC datacenter                                        |
|                                                                         |
|  2. LATENCY-BASED                                                       |
|  -----------------                                                      |
|  Route to datacenter with lowest latency                                |
|  Measured by DNS resolver probing                                       |
|  Better than geo when network topology differs from geography           |
|                                                                         |
|  3. WEIGHTED                                                            |
|  -------------                                                          |
|  Distribute traffic by percentage                                       |
|  70% to US, 20% to EU, 10% to APAC                                      |
|  Useful during migrations or capacity management                        |
|                                                                         |
|  4. FAILOVER                                                            |
|  ------------                                                           |
|  Primary datacenter, with backup if primary fails                       |
|  Active-passive across regions                                          |
|                                                                         |
|  5. HEALTH-BASED                                                        |
|  -----------------                                                      |
|  Remove unhealthy datacenters from DNS responses                        |
|  Combine with other methods                                             |
|                                                                         |
|  EXAMPLES:                                                              |
|  * AWS Route 53                                                         |
|  * Cloudflare                                                           |
|  * Akamai                                                               |
|  * Google Cloud DNS                                                     |
|  * Azure Traffic Manager                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.9: SERVICE DISCOVERY

How do load balancers and services find each other?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICE DISCOVERY                                                      |
|                                                                         |
|  THE PROBLEM:                                                           |
|  In dynamic environments (Kubernetes, auto-scaling), servers            |
|  come and go. How does the LB know about them?                          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  OPTION 1: STATIC CONFIGURATION                                         |
|  --------------------------------                                       |
|                                                                         |
|  # nginx.conf                                                           |
|  upstream backend {                                                     |
|      server 10.0.1.1:8080;                                              |
|      server 10.0.1.2:8080;                                              |
|      server 10.0.1.3:8080;                                              |
|  }                                                                      |
|                                                                         |
|  PROS: Simple                                                           |
|  CONS: Doesn't handle dynamic environments                              |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  OPTION 2: DNS-BASED DISCOVERY                                          |
|  ------------------------------                                         |
|                                                                         |
|  Services register with DNS, LB queries DNS                             |
|                                                                         |
|  backend.service.local > [10.0.1.1, 10.0.1.2, 10.0.1.3]                 |
|                                                                         |
|  PROS: Simple, universal                                                |
|  CONS: DNS caching can delay updates                                    |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  OPTION 3: SERVICE REGISTRY                                             |
|  ---------------------------                                            |
|                                                                         |
|  Dedicated service for tracking instances                               |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |    Service Instance --register--> Service Registry               |   |
|  |         |                              |                         |   |
|  |    (on startup)                   +----+----+                    |   |
|  |                                   | Consul  |                    |   |
|  |    Load Balancer <---query------ |  etcd   |                     |   |
|  |                                   |ZooKeeper|                    |   |
|  |                                   +---------+                    |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  POPULAR SERVICE REGISTRIES:                                            |
|  * Consul (HashiCorp) - Full service mesh                               |
|  * etcd - Key-value store (Kubernetes uses this)                        |
|  * ZooKeeper - Distributed coordination                                 |
|  * Eureka (Netflix) - REST-based discovery                              |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  OPTION 4: KUBERNETES NATIVE                                            |
|  ----------------------------                                           |
|                                                                         |
|  Kubernetes has built-in service discovery:                             |
|                                                                         |
|  apiVersion: v1                                                         |
|  kind: Service                                                          |
|  metadata:                                                              |
|    name: my-service                                                     |
|  spec:                                                                  |
|    selector:                                                            |
|      app: myapp                                                         |
|    ports:                                                               |
|    - port: 80                                                           |
|      targetPort: 8080                                                   |
|                                                                         |
|  * Service automatically tracks pods with matching labels               |
|  * DNS: my-service.namespace.svc.cluster.local                          |
|  * kube-proxy handles load balancing                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.10: RATE LIMITING AT LOAD BALANCER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RATE LIMITING                                                          |
|                                                                         |
|  WHY AT LOAD BALANCER:                                                  |
|  * First line of defense                                                |
|  * Protects all backend services                                        |
|  * Centralized configuration                                            |
|                                                                         |
|  COMMON ALGORITHMS:                                                     |
|                                                                         |
|  1. TOKEN BUCKET                                                        |
|  ------------------                                                     |
|  Bucket fills with tokens at fixed rate                                 |
|  Each request consumes a token                                          |
|  No tokens > rejected                                                   |
|                                                                         |
|  Config: 100 tokens/minute, burst of 20                                 |
|  Allows: 100 steady + occasional bursts up to 20 extra                  |
|                                                                         |
|  2. SLIDING WINDOW                                                      |
|  -----------------                                                      |
|  Count requests in rolling time window                                  |
|                                                                         |
|  Config: 1000 requests per 60 seconds                                   |
|  Check: count(requests in last 60s) < 1000?                             |
|                                                                         |
|  3. FIXED WINDOW                                                        |
|  -----------------                                                      |
|  Count requests in fixed intervals                                      |
|                                                                         |
|  Config: 1000 requests per minute                                       |
|  Problem: Boundary spikes (1000 at :59, 1000 at :01)                    |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  NGINX EXAMPLE:                                                         |
|                                                                         |
|  limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;            |
|                                                                         |
|  location /api/ {                                                       |
|      limit_req zone=api burst=20 nodelay;                               |
|      proxy_pass http://backend;                                         |
|  }                                                                      |
|                                                                         |
|  RATE LIMITING DIMENSIONS:                                              |
|  * Per IP address                                                       |
|  * Per API key                                                          |
|  * Per user ID                                                          |
|  * Per endpoint                                                         |
|  * Global                                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LOAD BALANCING - KEY TAKEAWAYS                                         |
|                                                                         |
|  TYPES                                                                  |
|  -----                                                                  |
|  * L4: Fast, simple, protocol agnostic                                  |
|  * L7: Intelligent, content-aware, more features                        |
|  * Use both: L4 at edge, L7 for routing                                 |
|                                                                         |
|  ALGORITHMS                                                             |
|  ----------                                                             |
|  * Round Robin: Simple, equal distribution                              |
|  * Weighted Round Robin: Accounts for capacity                          |
|  * Least Connections: Adapts to request duration                        |
|  * IP Hash: Sticky sessions (use sparingly)                             |
|  * Least Response Time: Routes to fastest                               |
|  * Power of Two: Good balance of simplicity and effectiveness           |
|                                                                         |
|  HEALTH CHECKS                                                          |
|  -------------                                                          |
|  * TCP: Fast, shallow                                                   |
|  * HTTP: Checks app health                                              |
|  * Deep: Checks dependencies (use for monitoring, not LB)               |
|                                                                         |
|  SSL/TLS                                                                |
|  -------                                                                |
|  * Terminate at LB: Usually best (offload crypto)                       |
|  * End-to-end: For strict security requirements                         |
|  * mTLS: Service-to-service authentication                              |
|                                                                         |
|  HIGH AVAILABILITY                                                      |
|  -----------------                                                      |
|  * Active-Passive: Failover on failure                                  |
|  * Active-Active: Both handle traffic                                   |
|  * Cloud managed: Best option for most (AWS ALB/NLB)                    |
|                                                                         |
|  GLOBAL (GSLB)                                                          |
|  ------------                                                           |
|  * Geolocation: Route by user location                                  |
|  * Latency-based: Route to fastest datacenter                           |
|  * Failover: Primary/backup regions                                     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  INTERVIEW TIPS                                                         |
|  --------------                                                         |
|                                                                         |
|  1. Know when to use L4 vs L7:                                          |
|     "For database traffic, L4 since we don't need content routing"      |
|     "For API, L7 to route by URL path and do rate limiting"             |
|                                                                         |
|  2. Discuss health checks:                                              |
|     "We'd use HTTP health checks at /health to verify app status"       |
|                                                                         |
|  3. Consider HA for the LB:                                             |
|     "We'd use managed ALB which is inherently highly available"         |
|                                                                         |
|  4. Session handling:                                                   |
|     "Prefer stateless design with Redis sessions over sticky"           |
|                                                                         |
|  5. Scale numbers:                                                      |
|     * AWS NLB: millions of requests per second                          |
|     * AWS ALB: hundreds of thousands per second                         |
|     * Nginx: 10K-100K connections per instance                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 3

