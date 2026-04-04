# STOCK TRADING SYSTEM
*Complete System Design*

A stock trading platform handles order placement, matching, execution,
and real-time market data distribution for millions of concurrent users
with strict latency and consistency requirements.

## SECTION 1: SCOPING THE PROBLEM WITH THE INTERVIEWER

```
+---------------------------------------------------------------------------+
|                                                                           |
|  INTERVIEWER: "Design a stock trading system."                            |
|                                                                           |
|  Q1: "What type of exchange are we building -- equities only, or          |
|       multi-asset (options, futures, crypto)?"                            |
|  A1: "Focus on equities (stocks) only. A single national exchange         |
|       like NASDAQ or NYSE. No derivatives or crypto for now."             |
|                                                                           |
|  Q2: "Which order types do we need to support?"                           |
|  A2: "Market orders, limit orders, and stop orders at minimum.            |
|       Time-in-force variants like IOC (Immediate-or-Cancel) and           |
|       GTC (Good-Till-Cancelled) are in scope too."                        |
|                                                                           |
|  Q3: "Are we designing the matching engine itself, or a brokerage         |
|       that routes orders to an external exchange?"                        |
|  A3: "The full exchange, including the matching engine. This is the       |
|       core differentiator -- we own the order book and matching           |
|       logic. The brokerage layer is out of scope."                        |
|                                                                           |
|  Q4: "What scale should we target for orders and users?"                  |
|  A4: "Peak of 100K orders/sec, 10M trades/day. Millions of                |
|       registered users with 1M+ concurrent during market hours.           |
|       Around 5000 listed stocks."                                         |
|                                                                           |
|  Q5: "What are the latency requirements for order matching?"              |
|  A5: "Sub-millisecond for the matching engine itself. End-to-end          |
|       order-to-acknowledgement under 10ms including network hops          |
|       and gateway validation."                                            |
|                                                                           |
|  Q6: "Do we need to handle regulatory requirements like audit             |
|       trails and fair ordering guarantees?"                               |
|  A6: "Yes. Every order and trade must be logged immutably for             |
|       SEC/FINRA compliance. Strict price-time priority enforced           |
|       through a sequencer for fair ordering. Must retain trade            |
|       records for 7+ years."                                              |
|                                                                           |
|  Q7: "How should we distribute real-time market data to clients?"         |
|  A7: "WebSocket for real-time price feeds. Support Level 1 (best          |
|       bid/ask) and Level 2 (full book depth). Fan-out to 1M+              |
|       concurrent subscribers with batched binary updates."                |
|                                                                           |
|  Q8: "Should we cover settlement and clearing, or just matching?"         |
|  A8: "Include post-trade settlement at a high level. T+1 settlement       |
|       with netting. The focus is matching engine and market data,         |
|       but we should show the full post-trade pipeline."                   |
|                                                                           |
|  -----------------------------------------------------------------------  |
|                                                                           |
|  AGREED SCOPE:                                                            |
|                                                                           |
|  * Equities-only exchange (stocks, not options/futures/crypto)            |
|  * Order types: market, limit, stop, IOC, GTC                             |
|  * Full matching engine with price-time priority (sub-ms latency)         |
|  * Scale: 100K orders/sec peak, 10M trades/day, 1M+ connections           |
|  * Sequencer for deterministic fair ordering of all orders                |
|  * Immutable event log for SEC/FINRA audit trail compliance               |
|  * Real-time market data fan-out via WebSocket (L1 + L2 data)             |
|  * Post-trade pipeline: settlement (T+1), portfolio, reporting            |
|                                                                           |
+---------------------------------------------------------------------------+
```

## SECTION 2: REQUIREMENTS

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

## SECTION 3: KEY TERMINOLOGY

```
+--------------------------------------------------------------------------+
||                                                                         |
||  ORDER BOOK                                                             |
||  A per-stock data structure listing all outstanding buy (bid) and       |
||  sell (ask) orders at every price level. Bids are sorted highest        |
||  first, asks lowest first. The core state of a matching engine.         |
||                                                                         |
||  BID / ASK (SPREAD)                                                     |
||  Bid is the highest price a buyer will pay; ask is the lowest a         |
||  seller will accept. The spread (ask − bid) reflects liquidity.         |
||  Tighter spreads indicate a more liquid, actively traded stock.         |
||                                                                         |
||  MATCHING ENGINE                                                        |
||  The component that pairs buy and sell orders using price-time          |
||  priority (FIFO at each price level). Typically single-threaded         |
||  and in-memory for determinism and sub-millisecond latency.             |
||                                                                         |
||  LIMIT ORDER                                                            |
||  An order to buy or sell at a specified price or better. Stays in       |
||  the order book until filled, cancelled, or expired. The most           |
||  common order type on exchanges.                                        |
||                                                                         |
||  MARKET ORDER                                                           |
||  An order executed immediately at the best available price.             |
||  Guarantees execution but not price. Can cause slippage in              |
||  illiquid markets where the book is thin.                               |
||                                                                         |
||  STOP ORDER                                                             |
||  A dormant order that activates when a stock reaches a trigger          |
||  price, then converts into a market or limit order. Used for            |
||  loss protection or breakout entry strategies.                          |
||                                                                         |
||  TRADE EXECUTION                                                        |
||  The completed match between a buy and sell order, producing a          |
||  trade record (price, quantity, timestamp). Generates events for        |
||  settlement, market data, and portfolio updates.                        |
||                                                                         |
||  SETTLEMENT (T+1 / T+2)                                                 |
||  The process of transferring cash and securities after a trade.         |
||  T+1 means settlement occurs one business day after trade date.         |
||  Until settled, the trade is a legal obligation, not a transfer.        |
||                                                                         |
||  TICKER SYMBOL                                                          |
||  A unique short code identifying a publicly traded security             |
||  (e.g., AAPL, TSLA). Used as the partition key for routing              |
||  orders to the correct matching engine shard.                           |
||                                                                         |
||  ORDER GATEWAY                                                          |
||  The entry point that receives client orders, validates them,           |
||  runs pre-trade risk checks (balance, limits, circuit breakers),        |
||  and routes valid orders to the correct matching engine.                |
||                                                                         |
||  CIRCUIT BREAKER                                                        |
||  A safety mechanism that halts trading when a stock or market           |
||  moves beyond a threshold (e.g., ±10% in 5 min). Prevents flash         |
||  crashes and gives the market time to absorb information.               |
||                                                                         |
+--------------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

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

## SECTION 5: MATCHING ENGINE

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

## SECTION 6: ORDER TYPES AND RISK MANAGEMENT

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

## SECTION 7: REAL-TIME MARKET DATA

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

## SECTION 8: SETTLEMENT AND RELIABILITY

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

## SECTION 9: SCALE ESTIMATION

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
|    WHY FAST DB (PostgreSQL/TimescaleDB): Recent trades queried          |
|    constantly (portfolio value, P&L, trade history). Need sub-100ms     |
|    reads with complex filters (by stock, date range, type).             |
|  * Cold storage: older data in S3/HDFS for compliance                   |
|    WHY S3: Regulatory requirement to retain 7+ years of trades.         |
|    S3 is cheapest durable storage ($0.023/GB/mo vs $0.10+ for DB).      |
|    Rarely queried - batch analytics via Spark/Athena when needed.       |
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

## SECTION 10: DESIGN ALTERNATIVES AND TRADE-OFFS

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

## SECTION 11: COMMON ISSUES AND FAILURE SCENARIOS

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

## SECTION 12: DETAILED WRITE/READ PATHS AND STATE MANAGEMENT

```
+--------------------------------------------------------------------------+
||                                                                         |
||  1. ENTITY STATE MACHINE (Order)                                        |
||                                                                         |
||  PENDING ──> OPEN ──> PARTIALLY_FILLED ──> FILLED                       |
||    │           │            │                                           |
||    │           │            └──> CANCELLED (user cancel remaining qty)  |
||    │           │                                                        |
||    │           └──> CANCELLED (user cancel before any fill)             |
||    │           │                                                        |
||    │           └──> EXPIRED (GTC timeout, end-of-day for day orders)    |
||    │                                                                    |
||    └──> REJECTED (failed pre-trade risk check)                          |
||                                                                         |
||  For stop orders:                                                       |
||  PENDING_TRIGGER ──> TRIGGERED ──> OPEN ──> (same as above)             |
||                                                                         |
||  Transition rules:                                                      |
||  * PENDING: validated by gateway, awaiting matching engine              |
||  * OPEN: in the order book, eligible for matching                       |
||  * PARTIALLY_FILLED: some qty matched, remainder still in book          |
||  * FILLED: fully matched, terminal state                                |
||  * Each fill generates a Trade record (immutable event)                 |
||                                                                         |
||  ================================================================       |
||                                                                         |
||  2. CRITICAL WRITE PATH (Order Matching in the Order Book)              |
||                                                                         |
||  Client        API GW       Order Mgmt      Matching Engine             |
||    |              |             |                  |                    |
||    |-- place ---->|             |                  |                    |
||    |  order       |-- validate->|                  |                    |
||    |  (AAPL,      |             |                  |                    |
||    |   BUY,       |  Pre-trade risk checks:        |                    |
||    |   150.20,    |  * balance >= order_value       |                   |
||    |   500 qty)   |  * position limits OK           |                   |
||    |              |  * circuit breaker check         |                  |
||    |              |  * rate limit per user           |                  |
||    |              |             |                  |                    |
||    |              |  WAL: log order before ACK      |                   |
||    |              |             |                  |                    |
||    |              |             |-- route to       |                    |
||    |              |             |   AAPL engine -->|                    |
||    |              |             |                  |                    |
||    |              |  Matching engine (single-threaded, in-memory):      |
||    |              |                                                     |
||    |              |  // BUY $150.20 x 500 arrives                       |
||    |              |  best_ask = asks.peek()  // $150.15 x 300           |
||    |              |  if buy.price >= best_ask.price:                    |
||    |              |    trade(300 @ $150.15)  // partial fill            |
||    |              |    emit TradeExecuted event                         |
||    |              |    remaining = 200                                  |
||    |              |    next_ask = asks.peek()  // $150.20 x 700         |
||    |              |    trade(200 @ $150.20)  // fill complete           |
||    |              |    emit TradeExecuted event                         |
||    |              |    order status = FILLED                            |
||    |              |                                                     |
||    |              |  Events written to WAL (append-only log):           |
||    |              |    { type: TRADE, order_id, price, qty, ts }        |
||    |              |                  |                                  |
||    |              |  Kafka: emit events to downstream                   |
||    |              |    -> Trade Execution Svc (update portfolio)        |
||    |              |    -> Market Data Svc (update best bid/ask)         |
||    |              |    -> Settlement Svc (T+1 queue)                    |
||    |              |    -> Regulatory audit log                          |
||    |              |                  |                                  |
||    |<-- fills ----|<-- ack ---------|                                   |
||                                                                         |
||  Data structures in matching engine:                                    |
||  * Red-black tree: price levels (O(log N) insert/remove)                |
||  * FIFO queue per price level: time priority                            |
||  * HashMap: order_id -> Order (O(1) cancel/lookup)                      |
||                                                                         |
||  ================================================================       |
||                                                                         |
||  3. READ PATH                                                           |
||                                                                         |
||  ORDER BOOK (Level 2 market data):                                      |
||    Matching Engine -> in-memory snapshot -> Market Data Svc             |
||    -> WebSocket push to subscribers (batched every 100ms)               |
||    * No DB read - purely in-memory from matching engine state           |
||                                                                         |
||  PORTFOLIO / HOLDINGS:                                                  |
||    Client --> Portfolio Svc --> PostgreSQL/TimescaleDB                  |
||    * Read replica for display queries                                   |
||    * Updated async via Kafka TradeExecuted events                       |
||                                                                         |
||  TRADE HISTORY:                                                         |
||    Client --> Trade Svc --> Hot: PostgreSQL (last 90 days)              |
||                         --> Cold: S3 Parquet (via Athena)               |
||    * Immutable event log, append-only                                   |
||                                                                         |
||  LAST PRICE / TICKER:                                                   |
||    WebSocket -> Market Data Svc -> in-memory cache (latest)             |
||    * Binary protobuf for 60% smaller payload than JSON                  |
||    * Delta encoding: send only changed fields                           |
||                                                                         |
||  ================================================================       |
||                                                                         |
||  4. FAILURE SCENARIOS                                                   |
||                                                                         |
||  +------------------------------+-----------------------------------+   |
||  | What Fails                   | Impact & Recovery                 |   |
||  +------------------------------+-----------------------------------+   |
||  | Matching engine crashes      | Standby engine promoted via       |   |
||  |                              | ZooKeeper leader election.        |   |
||  |                              | Replay WAL from last snapshot     |   |
||  |                              | to rebuild order book state.      |   |
||  |                              | Fencing token prevents split-     |   |
||  |                              | brain (old primary rejected).     |   |
||  +------------------------------+-----------------------------------+   |
||  | Order accepted by gateway    | Reconciliation job compares       |   |
||  | but lost before matching     | gateway WAL vs engine WAL.        |   |
||  | engine                       | Orphan orders resubmitted or      |   |
||  |                              | cancelled with user notification. |   |
||  +------------------------------+-----------------------------------+   |
||  | Trade executed but Kafka     | WAL contains all trades. Replay   |   |
||  | event lost                   | from WAL offset on consumer       |   |
||  |                              | restart. Idempotent consumers     |   |
||  |                              | (unique trade_id) prevent dupes.  |   |
||  +------------------------------+-----------------------------------+   |
||  | WebSocket storm after outage | Jittered reconnect (0-30s) on     |   |
||  | (1M clients reconnect)       | client. Rate-limit connections    |   |
||  |                              | at LB. Serve cached market data   |   |
||  |                              | while connections ramp up.        |   |
||  +------------------------------+-----------------------------------+   |
||                                                                         |
||  ================================================================       |
||                                                                         |
||  5. CLEANUP / EXPIRY                                                    |
||                                                                         |
||  EXPIRED ORDERS:                                                        |
||  * Day orders: cancelled at market close (4:00 PM ET)                   |
||  * GTC orders: expire after 90 days if unfilled                         |
||  * Matching engine sweep at end-of-day: remove all DAY orders           |
||  * Emit OrderExpired events to Kafka for portfolio/balance release      |
||                                                                         |
||  WAL COMPACTION:                                                        |
||  * Periodic snapshots of order book state to disk                       |
||  * WAL entries before last snapshot can be truncated                    |
||  * Snapshot frequency: every 10 minutes during market hours             |
||                                                                         |
||  TRADE DATA LIFECYCLE:                                                  |
||  * Hot: last 90 days in PostgreSQL/TimescaleDB (SSD)                    |
||  * Cold: >90 days archived to S3 in Parquet format                      |
||  * Regulatory retention: 7 years minimum (SEC/FINRA)                    |
||  * Queryable via Spark/Athena for compliance audits                     |
||                                                                         |
||  MARKET DATA CACHE:                                                     |
||  * In-memory only for real-time feeds (no persistence needed)           |
||  * OHLCV candles: computed by Market Data Svc, stored in                |
||    TimescaleDB for historical charting queries                          |
||                                                                         |
+--------------------------------------------------------------------------+
```

## SECTION 13: WRAP-UP

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SUMMARY OF KEY DESIGN DECISIONS:                                       |
|                                                                         |
|  1. SINGLE-THREADED MATCHING ENGINE                                     |
|     Price-time priority enforced deterministically without locks.       |
|     LMAX Disruptor pattern: one thread processes millions of            |
|     orders/sec from a ring buffer. Sharded by symbol.                   |
|                                                                         |
|  2. ORDER BOOK AS SORTED DATA STRUCTURE                                 |
|     Buy orders in max-heap (highest bid first), sell orders in          |
|     min-heap (lowest ask first). In-memory for sub-microsecond          |
|     matching. Persistent event log for durability.                      |
|                                                                         |
|  3. SEQUENCER FOR FAIR ORDERING                                         |
|     All incoming orders pass through a sequencer that assigns           |
|     monotonic sequence numbers before reaching the matching             |
|     engine. Guarantees fair time-priority regardless of network         |
|     path.                                                               |
|                                                                         |
|  4. EVENT SOURCING FOR AUDIT TRAIL                                      |
|     Every order placement, match, cancellation, and fill is an          |
|     immutable event. State is reconstructable by replaying events.      |
|     Critical for regulatory compliance and crash recovery.              |
|                                                                         |
|  5. MARKET DATA FAN-OUT VIA PUB/SUB                                     |
|     Trade events and order book snapshots published to Kafka            |
|     topics. WebSocket gateway subscribes and pushes to millions         |
|     of clients. Binary protocol (protobuf) for minimal latency.         |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  KEY TRADE-OFFS:                                                        |
|                                                                         |
|  * LATENCY vs THROUGHPUT: Single-threaded matching minimizes            |
|    latency (microseconds) but caps throughput per symbol. Sharding      |
|    by symbol parallelizes across symbols while keeping per-symbol       |
|    ordering strict.                                                     |
|                                                                         |
|  * IN-MEMORY vs DURABLE ORDER BOOK: In-memory is fast but               |
|    volatile. Event sourcing provides durability via replay.             |
|    Trade-off: recovery time (replay all events) vs checkpointing        |
|    (periodic snapshots + replay from last snapshot).                    |
|                                                                         |
|  * SYNCHRONOUS vs ASYNC SETTLEMENT: Stock settlement is T+1             |
|    (async batch). Crypto is immediate. Async settlement decouples       |
|    matching speed from settlement complexity but introduces risk        |
|    (counterparty default between match and settlement).                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 14: INTERVIEW QUESTIONS

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
