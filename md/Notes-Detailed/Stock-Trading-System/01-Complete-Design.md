# STOCK TRADING SYSTEM
*Complete System Design*

A stock trading platform handles order placement, matching, execution,
and real-time market data distribution for millions of concurrent users
with strict latency and consistency requirements.

## SECTION 1: REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS:                                               |
|  * Place orders (market, limit, stop-loss)                              |
|  * Cancel and modify pending orders                                     |
|  * Real-time order book and price updates                               |
|  * Portfolio view (holdings, P&L, positions)                            |
|  * Trade history and account statements                                 |
|  * Watchlists and price alerts                                          |
|  * Market data feed (bid/ask, last price, volume)                       |
|                                                                         |
|  NON-FUNCTIONAL:                                                        |
|  * Latency: order placement < 10ms, matching < 1ms                      |
|  * Throughput: 100K+ orders/sec during peak                             |
|  * Consistency: NO double-execution, NO lost orders                     |
|  * Availability: 99.99% during market hours                             |
|  * Auditability: every order/trade logged immutably                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: HIGH-LEVEL ARCHITECTURE

```
+--------------------------------------------------------------------------+
|                                                                          |
|  STOCK TRADING ARCHITECTURE                                              |
|                                                                          |
|  +--------+    +-----------+    +---------------+                        |
|  | Mobile  | -> | API       | -> | Order         |                       |
|  | Web App |    | Gateway   |    | Management    |                       |
|  +--------+    | (Auth,    |    | Service       |                        |
|                | Rate Limit|    | (validate,    |                        |
|                +-----------+    |  risk check)  |                        |
|                                 +-------+-------+                        |
|                                         |                                |
|                                         v                                |
|                                 +---------------+                        |
|                                 | MATCHING      |  <-- THE CORE          |
|                                 | ENGINE        |                        |
|                                 | (Order Book)  |                        |
|                                 +-------+-------+                        |
|                                         |                                |
|                          +--------------+--------------+                 |
|                          |              |              |                 |
|                          v              v              v                 |
|                   +-----------+  +-----------+  +-----------+            |
|                   | Trade     |  | Market    |  | Settlement|            |
|                   | Execution |  | Data      |  | & Clearing|            |
|                   | Service   |  | Service   |  | Service   |            |
|                   +-----------+  +-----------+  +-----------+            |
|                                       |                                  |
|                                       v                                  |
|                                 WebSocket to clients                     |
|                                 (real-time prices)                       |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 3: MATCHING ENGINE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE MATCHING ENGINE = Heart of the trading system                      |
|                                                                         |
|  ORDER BOOK (per stock symbol):                                         |
|                                                                         |
|  BUY ORDERS (BIDS)          |    SELL ORDERS (ASKS)                     |
|  sorted: highest first      |    sorted: lowest first                   |
|  -------------------------  |  ---------------------------              |
|  Price    Qty    Time       |  Price    Qty    Time                     |
|  $150.10  500    10:01:03   |  $150.15  300    10:01:01                 |
|  $150.05  200    10:01:01   |  $150.20  700    10:01:02                 |
|  $150.00  1000   10:00:58   |  $150.25  400    10:00:59                 |
|                             |                                           |
|  SPREAD = $150.15 - $150.10 = $0.05                                     |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  MATCHING ALGORITHM (Price-Time Priority):                              |
|                                                                         |
|  1. New buy order arrives at $150.20 for 500 shares                     |
|  2. Check asks: best ask = $150.15 (300 shares)                         |
|     -> MATCH: 300 shares at $150.15                                     |
|  3. Remaining: 200 shares at $150.20                                    |
|     Next ask: $150.20 (700 shares)                                      |
|     -> MATCH: 200 shares at $150.20                                     |
|  4. Order fully filled. Remaining ask: 500 shares at $150.20            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  DATA STRUCTURES:                                                       |
|  * Red-black tree or skip list for price levels (O(log N))              |
|  * FIFO queue at each price level (time priority)                       |
|  * HashMap for O(1) order lookup by order ID                            |
|  * Typically in-memory, single-threaded for consistency                 |
|                                                                         |
|  PERFORMANCE:                                                           |
|  * LMAX Exchange: 6 million orders/sec on single thread                 |
|  * Key: no locks, no I/O on hot path, mechanical sympathy               |
|  * Event sourcing: log all events, replay to rebuild state              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: ORDER TYPES AND RISK MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ORDER TYPES:                                                           |
|                                                                         |
|  MARKET ORDER: Execute immediately at best available price.             |
|  LIMIT ORDER:  Execute at specified price or better.                    |
|  STOP ORDER:   Becomes market order when price hits trigger.            |
|  STOP-LIMIT:   Becomes limit order when price hits trigger.             |
|  IOC:          Immediate-or-Cancel (fill what you can, cancel rest).    |
|  FOK:          Fill-or-Kill (fill entirely or cancel entirely).         |
|  GTC:          Good-Till-Cancelled (stays open until filled/cancelled). |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  PRE-TRADE RISK CHECKS:                                                 |
|                                                                         |
|  Before order reaches matching engine:                                  |
|  * Account balance sufficient?                                          |
|  * Position limits not exceeded?                                        |
|  * Price within circuit breaker limits? (e.g., +/- 20% from open)       |
|  * Order size within allowed range?                                     |
|  * User not restricted or banned?                                       |
|  * Rate limit check (prevent order flooding)                            |
|                                                                         |
|  Must be FAST (< 1ms) -- these are on the critical path.                |
|  Typically: in-memory checks with cached account data.                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5: REAL-TIME MARKET DATA

```
+--------------------------------------------------------------------------+
|                                                                          |
|  MARKET DATA DISTRIBUTION:                                               |
|                                                                          |
|  Matching Engine --> Kafka Topic "trades" --> Market Data Service        |
|                                                   |                      |
|                                    +--------------+---------+            |
|                                    |              |         |            |
|                                    v              v         v            |
|                               WebSocket       REST API   Third-party     |
|                               (real-time)     (polling)  (Bloomberg)     |
|                                                                          |
|  DATA TYPES:                                                             |
|  * Level 1: Best bid/ask, last price, volume                             |
|  * Level 2: Full order book depth (all price levels)                     |
|  * Trade tape: every executed trade (price, qty, time)                   |
|  * OHLCV candles: Open, High, Low, Close, Volume per interval            |
|                                                                          |
|  SCALE:                                                                  |
|  * 5000+ stocks, each updating multiple times per second                 |
|  * 1M+ WebSocket connections for real-time prices                        |
|  * Fan-out: 1 trade event -> 100K+ subscriber notifications              |
|                                                                          |
|  OPTIMIZATION:                                                           |
|  * Batch updates (send every 100ms, not every tick)                      |
|  * Delta encoding (send only changed fields)                             |
|  * Binary protocol (protobuf, not JSON)                                  |
|  * Sharded WebSocket servers by symbol range                             |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 6: SETTLEMENT AND RELIABILITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  POST-TRADE PIPELINE:                                                   |
|                                                                         |
|  Trade Executed -> Event Log (immutable) -> Settlement Service          |
|                                                |                        |
|                                    +-----------+-----------+            |
|                                    |           |           |            |
|                                    v           v           v            |
|                              Update       Update     Regulatory         |
|                              Portfolio    Balances   Reporting          |
|                              (holdings)  (cash)     (audit trail)       |
|                                                                         |
|  T+1 or T+2 Settlement (actual asset/cash transfer)                     |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  RELIABILITY GUARANTEES:                                                |
|                                                                         |
|  * EVENT SOURCING: Every order, modification, trade is an immutable     |
|    event. Can rebuild any state by replaying events.                    |
|  * WAL (Write-Ahead Log): Orders logged before processing.              |
|    On crash, replay log to recover in-flight orders.                    |
|  * IDEMPOTENCY: Every order has unique ID. Retries are safe.            |
|  * EXACTLY-ONCE: Use Kafka transactions for trade -> settlement.        |
|  * RECONCILIATION: Periodic check that all systems agree on state.      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7: SCALE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ASSUMPTIONS:                                                           |
|  * 5000 stocks listed                                                   |
|  * 100K orders/sec at peak (market open, news events)                   |
|  * 10M trades/day                                                       |
|  * 1M+ concurrent WebSocket connections                                 |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ORDER THROUGHPUT:                                                      |
|  * 100K orders/sec x avg 200 bytes = 20 MB/sec ingestion                |
|  * Gateway must handle this with horizontal scaling                     |
|  * Matching engine per stock: ~20 orders/sec avg (100K / 5000)          |
|    but bursty -- top stocks may see 10K+ orders/sec                     |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  MARKET DATA FAN-OUT:                                                   |
|  * 5000 stocks x 10 updates/sec = 50K messages/sec produced             |
|  * Each message fanned out to subscribers                               |
|  * 1M users x avg 5 stocks watched = 5M subscriptions                   |
|  * Fan-out ratio: ~100K notifications per trade event                   |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  TRADE STORAGE:                                                         |
|  * 10M trades/day x 500 bytes per trade = 5 GB/day                      |
|  * 5 GB x 365 = 1.8 TB/year                                             |
|  * Must be immutable (event sourcing) + queryable                       |
|  * Hot storage: last 90 days (~450 GB) in fast DB                       |
|  * Cold storage: older data in S3/HDFS for compliance                   |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  ORDER BOOK MEMORY:                                                     |
|  * All in-memory for speed                                              |
|  * ~50 MB per stock (all price levels + queues)                         |
|  * 5000 stocks x 50 MB = 250 GB total                                   |
|  * Sharded across matching engine instances                             |
|  * Each instance handles ~500 stocks = ~25 GB RAM                       |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  WEBSOCKET BANDWIDTH:                                                   |
|  * 1M connections x 1 KB/sec avg = 1 GB/sec outbound                    |
|  * Sharded across ~100 WebSocket servers                                |
|  * Each server: 10K connections, 10 MB/sec outbound                     |
|  * Binary protocol (protobuf) reduces payload by ~60% vs JSON           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8: DESIGN ALTERNATIVES AND TRADE-OFFS

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ALTERNATIVE 1: Single-Threaded vs Multi-Threaded Matching Engine        |
|                                                                          |
|  +---+-------------------------------------------+---------------------+ |
|  |   | Single-Threaded (LMAX Style)              | Multi-Threaded      | |
|  +---+-------------------------------------------+---------------------+ |
|  | Y | Deterministic ordering, no locks          | Higher throughput   | |
|  | Y | 6M orders/sec on single core              | Uses all cores      | |
|  | Y | Simpler recovery (replay log sequentially) | Parallel matching  | |
|  | X | Limited to 1 core                         | Lock contention     | |
|  | X |                                           | Non-deterministic   | |
|  +---+-------------------------------------------+---------------------+ |
|                                                                          |
|  BEST: Partition by symbol -- each stock gets its own single-threaded    |
|  engine. Gets benefits of both: deterministic per stock, scales          |
|  horizontally across stocks.                                             |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  ALTERNATIVE 2: Event Sourcing vs Traditional CRUD                       |
|                                                                          |
|  +---+-------------------------------------------+---------------------+ |
|  |   | Event Sourcing                            | Traditional CRUD    | |
|  +---+-------------------------------------------+---------------------+ |
|  | Y | Every order/trade is immutable event      | Simpler to build    | |
|  | Y | Rebuild state by replaying events          | Less storage       | |
|  | Y | Perfect audit trail (regulatory)          | Familiar pattern    | |
|  | X | Complexity (event store, snapshots)        | Lose history       | |
|  | X | Eventual consistency for read models      | Hard to audit       | |
|  +---+-------------------------------------------+---------------------+ |
|                                                                          |
|  Event sourcing adds complexity but is critical for financial systems.   |
|  Used by LMAX, major exchanges. Can't replay or audit with CRUD.         |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  ALTERNATIVE 3: In-Memory vs Persistent Order Book                       |
|                                                                          |
|  +---+-------------------------------------------+---------------------+ |
|  |   | In-Memory (Redis/Custom)                  | Persistent (DB)     | |
|  +---+-------------------------------------------+---------------------+ |
|  | Y | Ultra-low latency (< 1ms)                 | Durable by default  | |
|  | Y | Simple data structures (trees, maps)      | ACID guarantees     | |
|  | X | Needs recovery strategy on crash          | Slower (5-50ms)     | |
|  | X | RAM cost for large books                  | I/O bottleneck      | |
|  +---+-------------------------------------------+---------------------+ |
|                                                                          |
|  HYBRID (most exchanges): in-memory for active matching, WAL for         |
|  durability, periodic snapshots to disk. Fast recovery by loading        |
|  last snapshot + replaying WAL.                                          |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  ALTERNATIVE 4: WebSocket vs SSE vs Polling for Market Data              |
|                                                                          |
|  +---+-------------------------------------------+---------------------+ |
|  |   | WebSocket                                 | SSE / Polling       | |
|  +---+-------------------------------------------+---------------------+ |
|  | Y | Bidirectional, true real-time             | SSE: simpler setup  | |
|  | Y | 1M+ connections manageable                | SSE: auto-reconnect | |
|  | Y | Binary protocol support (protobuf)        | Polling: cacheable  | |
|  | X | More complex server infrastructure        | SSE: server->client | |
|  | X | Connection management overhead            | Polling: high load  | |
|  +---+-------------------------------------------+---------------------+ |
|                                                                          |
|  BEST: WebSocket with binary protocol (protobuf), batched updates        |
|  every 100ms. SSE acceptable for simple price feeds. Long polling        |
|  is worst option for real-time data -- avoid.                            |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  ALTERNATIVE 5: Centralized Exchange vs Distributed Matching             |
|                                                                          |
|  +---+-------------------------------------------+---------------------+ |
|  |   | Centralized (Single Matcher/Stock)        | Distributed         | |
|  +---+-------------------------------------------+---------------------+ |
|  | Y | Deterministic, consistent ordering        | Higher availability | |
|  | Y | Used by NYSE, NASDAQ, all major exchanges | No single point     | |
|  | Y | Simple failover (primary/backup)          | Geographic spread   | |
|  | X | Single point of failure per stock         | Consensus = slower  | |
|  | X | Requires fast failover mechanism          | Ordering is harder  | |
|  +---+-------------------------------------------+---------------------+ |
|                                                                          |
|  Real exchanges ALWAYS choose centralized + fast failover.               |
|  Distributed consensus (Raft/Paxos) too slow for matching.               |
|  Correct answer: centralized per stock, replicated for DR.               |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 9: COMMON ISSUES AND FAILURE SCENARIOS

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ISSUE 1: Split-Brain in Matching Engine Failover                        |
|                                                                          |
|  Problem: Primary and backup both think they're primary. Both accept     |
|  orders. Different match results. Data divergence.                       |
|                                                                          |
|  Solution:                                                               |
|  * Fencing tokens: new primary gets monotonically increasing token       |
|  * ZooKeeper/etcd for leader election with session expiry                |
|  * WAL sequence number check: backup only accepts if WAL is current      |
|  * Kill switch: old primary must be fenced before new one activates      |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  ISSUE 2: Order Stuck in "Pending" (Phantom Orders)                      |
|                                                                          |
|  Problem: Order accepted by gateway but lost before reaching matching    |
|  engine (network partition, crash, queue overflow).                      |
|                                                                          |
|  Solution:                                                               |
|  * WAL at gateway: log order before ACK to client                        |
|  * Reconciliation job: compare gateway log vs matching engine log        |
|  * Alert on mismatch: orphaned orders get resubmitted or cancelled       |
|  * Timeout: if no match response in N seconds, flag for review           |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  ISSUE 3: Flash Crash / Price Manipulation                               |
|                                                                          |
|  Problem: Algorithm sends millions of orders in seconds, crashes         |
|  price. Spoofing or fat-finger error.                                    |
|                                                                          |
|  Solution:                                                               |
|  * Circuit breakers: halt if price moves > 10% in 5 minutes              |
|  * Per-user rate limits (max orders/sec)                                 |
|  * Order-to-trade ratio checks (flag if submitting many, filling few)    |
|  * Market-wide halt (Level 1/2/3 circuit breakers like NYSE)             |
|  * Kill switch: ability to cancel all orders from a single user          |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  ISSUE 4: WebSocket Connection Storm After Outage                        |
|                                                                          |
|  Problem: System restarts, 1M clients reconnect simultaneously.          |
|  Thundering herd overwhelms servers.                                     |
|                                                                          |
|  Solution:                                                               |
|  * Jittered reconnect: client waits random 0-30s before reconnecting     |
|  * Connection rate limiting at load balancer level                       |
|  * Priority for authenticated sessions over anonymous                    |
|  * Graceful degradation: serve cached data while connections ramp up     |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  ISSUE 5: Clock Skew Affecting Order Priority                            |
|                                                                          |
|  Problem: Orders timestamped on different servers with different         |
|  clocks. Unfair matching (earlier order loses priority).                 |
|                                                                          |
|  Solution:                                                               |
|  * NTP sync with < 1ms tolerance across all servers                      |
|  * Sequence numbers assigned at gateway (not wall-clock time)            |
|  * Centralized sequencer: single point assigns global order              |
|  * If using distributed gateways, use Hybrid Logical Clocks (HLC)        |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  ISSUE 6: Settlement Failure / Reconciliation Mismatch                   |
|                                                                          |
|  Problem: Trade executed but settlement fails. Insufficient funds        |
|  discovered post-trade. Positions don't match between systems.           |
|                                                                          |
|  Solution:                                                               |
|  * Pre-trade risk checks: validate margin/balance before matching        |
|  * T+1 settlement with netting (aggregate trades, reduce transfers)      |
|  * Reconciliation between matching engine, settlement, and clearing      |
|  * Breaks dashboard: flag mismatches for manual resolution               |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  ISSUE 7: Market Data Lag During Peak                                    |
|                                                                          |
|  Problem: Kafka consumer falls behind during peak volume. Users see      |
|  stale prices and make bad trading decisions.                            |
|                                                                          |
|  Solution:                                                               |
|  * Separate fast path (in-process pub/sub) and slow path (Kafka)         |
|  * Fast path: matching engine directly publishes to WebSocket layer      |
|  * Conflation: only send latest price per stock, skip intermediate       |
|  * Priority queues: real-time feed > historical persistence              |
|  * Auto-scale Kafka consumers during peak hours                          |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 10: INTERVIEW QUESTIONS

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Q: Why is the matching engine single-threaded?                          |
|  A: Deterministic ordering without locks. A single thread with           |
|     in-memory data structures can process millions of orders/sec.        |
|     Locks and multi-threading add latency and complexity.                |
|     See: LMAX Disruptor pattern.                                         |
|                                                                          |
|  Q: How do you handle 1M+ concurrent WebSocket connections?              |
|  A: Shard WebSocket servers by symbol or user. Each server handles       |
|     ~100K connections. Use pub/sub (Redis or Kafka) to fan out           |
|     trade events to the right server. Binary protocol (protobuf).        |
|                                                                          |
|  Q: How do you prevent double-execution?                                 |
|  A: Unique order ID + idempotent matching. Event sourcing ensures        |
|     every state change is logged. On recovery, replay events and         |
|     skip already-processed orders.                                       |
|                                                                          |
|  Q: How would you handle a flash crash / circuit breaker?                |
|  A: Price circuit breakers: halt trading if price moves > X% in Y        |
|     minutes. Volume circuit breakers: throttle if order rate > limit.    |
|     Market-wide halt if index drops > threshold.                         |
|                                                                          |
|  Q: How does the system scale for thousands of stocks?                   |
|  A: Each stock has its own matching engine instance (or partition).      |
|     Shard by symbol. Each shard is single-threaded but independent.      |
|     Gateway routes orders to the correct shard.                          |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  Q: How would you design the system for crypto (24/7 trading)?           |
|  A: No market hours = no maintenance window. Blue-green deployments      |
|     for zero-downtime upgrades. Matching engine must be always-on.       |
|     Settlement is immediate (no T+1). Higher volatility = more           |
|     aggressive circuit breakers.                                         |
|                                                                          |
|  Q: How do you ensure fairness in order matching?                        |
|  A: Strict price-time priority enforced by single-threaded matching      |
|     engine. Timestamp assigned at gateway (before network to matcher).   |
|     Sequence numbers prevent reordering. Colocation available to all     |
|     (equal physical access to matching engine).                          |
|                                                                          |
|  Q: What's the difference between designing for a brokerage vs an        |
|     exchange?                                                            |
|  A: Exchange: owns the matching engine, handles all order books.         |
|     Brokerage: routes orders TO exchanges, focuses on user experience,   |
|     portfolio management, margin calculations. Brokerage is simpler      |
|     (no matching engine, just an API client to exchange).                |
|                                                                          |
+--------------------------------------------------------------------------+
```
