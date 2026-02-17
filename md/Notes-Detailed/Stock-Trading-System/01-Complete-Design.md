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

## SECTION 7: INTERVIEW QUESTIONS

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
+--------------------------------------------------------------------------+
```
