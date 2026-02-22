# APACHE KAFKA
*Chapter 4: Advanced Patterns and Production Operations*

This chapter covers advanced architectural patterns built on Kafka,
production tuning, and the broader ecosystem tools.

## SECTION 4.1: EXACTLY-ONCE SEMANTICS (EOS)

```
+--------------------------------------------------------------------------+
|                                                                          |
|  THE THREE DELIVERY GUARANTEES:                                          |
|                                                                          |
|  AT-MOST-ONCE:  Fire and forget. Fast, may lose messages.                |
|  AT-LEAST-ONCE: Retry on failure. Safe, may duplicate.                   |
|  EXACTLY-ONCE:  Each message processed exactly once. Hardest.            |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  KAFKA EXACTLY-ONCE = Idempotent Producer + Transactions                 |
|                                                                          |
|  1. IDEMPOTENT PRODUCER (single partition)                               |
|     enable.idempotence=true                                              |
|     Guarantees no duplicates within a single partition.                  |
|                                                                          |
|  2. TRANSACTIONS (cross-partition, cross-topic)                          |
|     Atomic writes across multiple partitions/topics.                     |
|     Also atomically commits consumer offsets.                            |
|                                                                          |
+--------------------------------------------------------------------------+
```

### TRANSACTIONAL PRODUCER

```java
// Transactional Producer: read-process-write pattern                             
Properties props = new Properties();                                              
props.put("bootstrap.servers", "localhost:9092");                                 
props.put("transactional.id", "order-processor-1"); // unique per instance        
props.put("enable.idempotence", "true");                                          

KafkaProducer<String, String> producer = new KafkaProducer<>(props);              
producer.initTransactions();                                                      

try {                                                                             
    producer.beginTransaction();                                                  

    // Consume from input topic                                                   
    ConsumerRecords<String, String> records = consumer.poll(100);                 
    for (ConsumerRecord<String, String> record : records) {                       
        // Process and write to output topic                                      
        String result = process(record.value());                                  
        producer.send(new ProducerRecord<>("output-topic", record.key(), result));
    }                                                                             

    // Atomically commit consumer offsets + produced messages                     
    producer.sendOffsetsToTransaction(                                            
        currentOffsets, consumer.groupMetadata());                                
    producer.commitTransaction();                                                 

} catch (Exception e) {                                                           
    producer.abortTransaction();                                                  
}                                                                                 
```

```
+--------------------------------------------------------------------------+
|                                                                          |
|  TRANSACTION FLOW:                                                       |
|                                                                          |
|  1. producer.initTransactions()                                          |
|     Register transactional.id with coordinator                           |
|                                                                          |
|  2. producer.beginTransaction()                                          |
|     Start a new transaction                                              |
|                                                                          |
|  3. producer.send() (multiple calls)                                     |
|     Messages buffered, marked as "uncommitted"                           |
|     Consumers with isolation.level=read_committed won't see them         |
|                                                                          |
|  4. producer.sendOffsetsToTransaction()                                  |
|     Include consumer offset commits in the transaction                   |
|                                                                          |
|  5. producer.commitTransaction()                                         |
|     Atomic commit: all messages + offsets become visible                 |
|                                                                          |
|  6. On failure: producer.abortTransaction()                              |
|     All messages discarded, offsets not committed                        |
|                                                                          |
|  Consumer side: isolation.level=read_committed                           |
|  Only sees messages from committed transactions.                         |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 4.2: KAFKA STREAMS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KAFKA STREAMS = A Java library for stream processing                   |
|                                                                         |
|  * No separate cluster needed (runs inside your app)                    |
|  * Exactly-once processing built in                                     |
|  * Stateful operations (joins, aggregations, windowing)                 |
|  * Fault-tolerant state stores (backed by changelog topics)             |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  ARCHITECTURE:                                                          |
|                                                                         |
|  +-------------------+     +-------------------+                        |
|  | Your App          |     | Your App          |                        |
|  | (Kafka Streams)   |     | (Kafka Streams)   |                        |
|  |                   |     |                   |                        |
|  | Task 0: P0 -> P0' |     | Task 1: P1 -> P1' |                        |
|  | Task 2: P2 -> P2' |     | Task 3: P3 -> P3' |                        |
|  |                   |     |                   |                        |
|  | [RocksDB Store]   |     | [RocksDB Store]   |                        |
|  +-------------------+     +-------------------+                        |
|           |                         |                                   |
|           v                         v                                   |
|  +--------------------------------------------+                         |
|  |           Kafka Cluster                     |                        |
|  | Input Topics | Output Topics | Changelogs   |                        |
|  +--------------------------------------------+                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

```java
// Kafka Streams: Word count example                                         
StreamsBuilder builder = new StreamsBuilder();                               

KStream<String, String> textLines =                                          
    builder.stream("text-input");                                            

KTable<String, Long> wordCounts = textLines                                  
    .flatMapValues(value -> Arrays.asList(value.toLowerCase().split("\\W+")))
    .groupBy((key, word) -> word)                                            
    .count(Materialized.as("word-count-store"));                             

wordCounts.toStream().to("word-count-output",                                
    Produced.with(Serdes.String(), Serdes.Long()));                          

KafkaStreams streams = new KafkaStreams(builder.build(), config);            
streams.start();                                                             
```

## SECTION 4.2.1: KAFKA STREAMS — CORE OPERATIONS

### Stateless Operations (filter, map, flatMap)

```
+---------------------------------------------------------------------------+
|                                                                           |
|  EVERY Kafka Streams pipeline uses these. Know them cold.                 |
|                                                                           |
|  +---------------------------------------------------------------------+  |
|  | Operation    | What It Does              | Output         | Use     |  |
|  |------------- |---------------------------|----------------|---------|  |
|  | filter       | Keep events matching cond | Same type      | Always  |  |
|  | map          | Transform key AND value   | New key+value  | Often   |  |
|  | mapValues    | Transform value only      | New value      | Most    |  |
|  | flatMapValues| One input -> many outputs | Multiple msgs  | Often   |  |
|  | selectKey    | Change the key            | New key        | Rekeying|  |
|  | peek         | Side effect (logging)     | Same (passthru)| Debug   |  |
|  | branch       | Split stream by condition | Multiple streams| Routes |  |
|  +---------------------------------------------------------------------+  |
|                                                                           |
+---------------------------------------------------------------------------+
```

```java
// FILTER — Remove events you don't care about                               
// "Only process orders above $100"                                          
KStream<String, Order> highValueOrders = orders                              
    .filter((key, order) -> order.getAmount() > 100);                        

// Skip null values (very common in production)                              
KStream<String, String> nonNull = stream                                     
    .filter((key, value) -> value != null);                                  

// MAPVALUES — Transform the value (most common operation)                   
// "Convert Order to OrderSummary for downstream"                            
KStream<String, OrderSummary> summaries = orders                             
    .mapValues(order -> new OrderSummary(                                    
        order.getId(),                                                       
        order.getAmount(),                                                   
        order.getStatus()                                                    
    ));                                                                      

// MAP — Transform both key and value (triggers repartition!)                
// "Rekey by customer_id instead of order_id"                                
KStream<String, Order> rekeyed = orders                                      
    .map((orderId, order) -> KeyValue.pair(order.getCustomerId(), order));   
// WARNING: map() that changes the key causes a repartition (network shuffle)
// Use mapValues() when you only need to change the value — no repartition   

// BRANCH — Split one stream into multiple based on conditions               
// "Route orders to different processing pipelines"                          
KStream<String, Order>[] branches = orders.branch(                           
    (key, order) -> order.getAmount() > 1000,   // [0] high value            
    (key, order) -> order.getAmount() > 100,     // [1] medium value         
    (key, order) -> true                          // [2] everything else     
);                                                                           
KStream<String, Order> highValue  = branches[0];                             
KStream<String, Order> medValue   = branches[1];                             
KStream<String, Order> lowValue   = branches[2];                             
```

### Stateful Operations (aggregate, reduce, joins)

```
+--------------------------------------------------------------------------+
|                                                                          |
|  STATEFUL = Operations that need to remember past events                 |
|  State is stored in RocksDB locally, backed by Kafka changelog topic     |
|                                                                          |
|  +--------------------------------------------------------------------+  |
|  | Operation    | What It Does                    | State Required    |  |
|  |------------- |---------------------------------|-------------------|  |
|  | count        | Count events per key            | key -> count      |  |
|  | aggregate    | Custom accumulation per key     | key -> agg value  |  |
|  | reduce       | Combine values (associative op) | key -> reduced    |  |
|  | join         | Combine two streams/tables      | both sides        |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
+--------------------------------------------------------------------------+
```

```java
// AGGREGATE — Custom accumulation per key                                
// "Track running total of order amounts per customer"                    
KTable<String, Double> customerTotals = orders                            
    .groupBy((orderId, order) -> order.getCustomerId())                   
    .aggregate(                                                           
        () -> 0.0,                                     // initializer     
        (customerId, order, runningTotal) ->            // adder          
            runningTotal + order.getAmount(),                             
        Materialized.as("customer-totals-store")       // state store name
    );                                                                    

// REDUCE — Simpler than aggregate (same input/output type)               
// "Find the max order amount per customer"                               
KTable<String, Order> maxOrders = orders                                  
    .groupBy((orderId, order) -> order.getCustomerId())                   
    .reduce((order1, order2) ->                                           
        order1.getAmount() > order2.getAmount() ? order1 : order2         
    );                                                                    
```

## SECTION 4.2.2: KSTREAM-KTABLE JOINS (Very Common in Production)

```
+--------------------------------------------------------------------------+
|                                                                          |
|  JOIN = Enrich events with reference/lookup data                         |
|                                                                          |
|  This is one of the MOST USED patterns in real Kafka applications.       |
|  Example: Enrich every order event with customer profile data.           |
|                                                                          |
|  Three join types:                                                       |
|                                                                          |
|  +--------------------------------------------------------------------+  |
|  | Join Type        | Left (Stream) | Right (Table/Stream) | Output   |  |
|  |------------------|---------------|----------------------|----------|  |
|  | Inner Join       | Must match    | Must match           | Matched  |  |
|  | Left Join        | Always output | NULL if no match     | All left |  |
|  | Outer Join       | Always output | Always output        | All      |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  KStream-KTable Join:                                                    |
|  * Stream event arrives → look up latest value in table → emit joined    |
|  * Table is always up-to-date (compacted topic)                          |
|  * NOT windowed — table always has "current" state                       |
|                                                                          |
|  KStream-KStream Join:                                                   |
|  * MUST specify a time window (events matched within time window)        |
|  * Example: match order event with payment event within 30 minutes       |
|                                                                          |
+--------------------------------------------------------------------------+
```

```java
// KStream-KTable Join (most common)                                                        
// "Enrich every order with customer profile"                                               
KStream<String, Order> orders = builder.stream("orders");            // keyed by customer_id
KTable<String, Customer> customers = builder.table("customers");     // keyed by customer_id

KStream<String, EnrichedOrder> enriched = orders.join(                                      
    customers,                                                                              
    (order, customer) -> new EnrichedOrder(                                                 
        order.getId(),                                                                      
        order.getAmount(),                                                                  
        customer.getName(),      // enriched from table                                     
        customer.getTier()       // enriched from table                                     
    )                                                                                       
);                                                                                          
enriched.to("enriched-orders");                                                             

// KStream-KStream Join (windowed — match events within time)                               
// "Match orders with payments within 30 minutes"                                           
KStream<String, Order> orders = builder.stream("orders");                                   
KStream<String, Payment> payments = builder.stream("payments");                             

KStream<String, OrderWithPayment> matched = orders.join(                                    
    payments,                                                                               
    (order, payment) -> new OrderWithPayment(order, payment),                               
    JoinWindows.ofTimeDifferenceWithNoGrace(Duration.ofMinutes(30))                         
);                                                                                          
// If payment doesn't arrive within 30 min → no output (inner join)                         
// Use leftJoin() to still emit order with null payment (for timeout detection)             
```

## SECTION 4.2.3: WINDOWING (Real-Time Analytics)

```
+--------------------------------------------------------------------------+
|                                                                          |
|  WINDOWS = Group events by time ranges for aggregation                   |
|                                                                          |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  TUMBLING (Fixed, non-overlapping)                                 |  |
|  |  [0----5min][5----10min][10----15min]                              |  |
|  |  Use: Hourly/daily counts, batch reporting                         |  |
|  |  "Count orders per hour"                                           |  |
|  |                                                                    |  |
|  |  HOPPING (Fixed, overlapping)                                      |  |
|  |  [0----5min]                                                       |  |
|  |    [2.5--7.5min]                                                   |  |
|  |      [5----10min]                                                  |  |
|  |  Use: Moving averages, smoother trends                             |  |
|  |  "5-min average, updated every 2.5 min"                            |  |
|  |                                                                    |  |
|  |  SESSION (Dynamic, gap-based)                                      |  |
|  |  [--click-click-click--]  gap  [--click-click--]  gap  [--click]   |  |
|  |  Use: User activity sessions, engagement tracking                  |  |
|  |  "Group user clicks with 30-min inactivity gap"                    |  |
|  |                                                                    |  |
|  |  SLIDING (Continuous, event-triggered)                             |  |
|  |  Evaluated on every new event, looks back N time                   |  |
|  |  Use: Fraud detection, real-time rate limiting                     |  |
|  |  "More than 10 transactions in last 5 minutes = fraud alert"       |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|  |                                                                    |  |
|  |  DECISION GUIDE:                                                   |  |
|  |  * Fixed reporting intervals → Tumbling                            |  |
|  |  * Smooth trends / moving average → Hopping                        |  |
|  |  * User behavior / activity → Session                              |  |
|  |  * Real-time alerting / fraud → Sliding                            |  |
|  |                                                                    |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
+--------------------------------------------------------------------------+
```

```java
// TUMBLING WINDOW — "Count orders per customer per hour"                         
KTable<Windowed<String>, Long> hourlyCounts = orders                              
    .groupBy((orderId, order) -> order.getCustomerId())                           
    .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofHours(1)))               
    .count(Materialized.as("hourly-order-counts"));                               

// SESSION WINDOW — "Group user clicks into sessions (30-min gap)"                
KTable<Windowed<String>, Long> sessionClicks = clickStream                        
    .groupByKey()                                                                 
    .windowedBy(SessionWindows.ofInactivityGapWithNoGrace(Duration.ofMinutes(30)))
    .count(Materialized.as("session-click-counts"));                              

// HOPPING WINDOW — "5-min average, updated every 1 min"                          
KTable<Windowed<String>, Double> movingAvg = metrics                              
    .groupByKey()                                                                 
    .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(5))              
                           .advanceBy(Duration.ofMinutes(1)))                     
    .aggregate(                                                                   
        () -> new AvgAccumulator(0.0, 0),                                         
        (key, value, agg) -> agg.add(value),                                      
        Materialized.as("moving-avg-store")                                       
    )                                                                             
    .mapValues(agg -> agg.getAverage());                                          
```

```
+---------------------------------------------------------------------------+
|                                                                           |
|  EVENT TIME vs PROCESSING TIME                                            |
|                                                                           |
|  * Event time: When the event actually happened (embedded in message)     |
|  * Processing time: When Kafka Streams processes it                       |
|                                                                           |
|  Problem: Events can arrive LATE (network delay, batch uploads)           |
|                                                                           |
|  +----Timeline----->                                                      |
|  Window: [12:00 - 12:05]                                                  |
|  Event at 12:03 arrives at 12:07 → Out of window!                         |
|                                                                           |
|  Solutions:                                                               |
|  1. Grace period: Allow late events up to N minutes                       |
|     TimeWindows.ofSizeWithNoGrace(5min) → strict, no late events          |
|     TimeWindows.ofSizeAndGrace(5min, 2min) → accept up to 2 min late      |
|                                                                           |
|  2. Use event time extractor:                                             |
|     config: default.timestamp.extractor = MyEventTimeExtractor            |
|     Extract timestamp from message payload, not Kafka metadata            |
|                                                                           |
|  INTERVIEW TIP: Always mention event time vs processing time              |
|  when discussing windowed operations. Shows production awareness.         |
|                                                                           |
+---------------------------------------------------------------------------+
```

## SECTION 4.2.4: ERROR HANDLING & DEAD LETTER QUEUE (DLQ)

```
+--------------------------------------------------------------------------+
|                                                                          |
|  WHAT HAPPENS WHEN A MESSAGE CAN'T BE PROCESSED?                         |
|                                                                          |
|  Three strategies:                                                       |
|                                                                          |
|  1. FAIL (default): Stop the entire stream application                   |
|     - Safe but causes total downtime                                     |
|     - One bad message blocks ALL processing                              |
|                                                                          |
|  2. SKIP (log and continue): Drop the bad message                        |
|     - Loses data silently                                                |
|     - Only acceptable for non-critical data (analytics, logs)            |
|                                                                          |
|  3. DEAD LETTER QUEUE (recommended): Route bad messages to DLQ topic     |
|     - Processing continues for good messages                             |
|     - Bad messages preserved for investigation and replay                |
|     - Monitor DLQ size — spike = something is wrong                      |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  KAFKA STREAMS DLQ PATTERN:                                              |
|                                                                          |
|  Input Topic ──► Process ──┬──► Output Topic (success)                   |
|                            │                                             |
|                            └──► DLQ Topic (failures)                     |
|                                                                          |
+--------------------------------------------------------------------------+
```

```java
// DLQ pattern in Kafka Streams                                                 
KStream<String, String>[] processed = inputStream                               
    .mapValues(value -> {                                                       
        try {                                                                   
            return processMessage(value);     // business logic                 
        } catch (Exception e) {                                                 
            return "POISON:" + value;         // mark as failed                 
        }                                                                       
    })                                                                          
    .branch(                                                                    
        (key, value) -> !value.startsWith("POISON:"),  // [0] success           
        (key, value) -> true                            // [1] failures         
    );                                                                          

processed[0].to("output-topic");                       // good messages         
processed[1]                                                                    
    .mapValues(v -> v.substring(7))                     // remove POISON: prefix
    .to("dlq-topic");                                   // bad messages → DLQ   
```

```
+--------------------------------------------------------------------------+
|                                                                          |
|  KAFKA CONNECT ERROR HANDLING (built-in DLQ support):                    |
|                                                                          |
|  // In connector config:                                                 |
|  {                                                                       |
|    "errors.tolerance": "all",                                            |
|    "errors.deadletterqueue.topic.name": "my-connector-dlq",              |
|    "errors.deadletterqueue.topic.replication.factor": 3,                 |
|    "errors.deadletterqueue.context.headers.enable": true                 |
|  }                                                                       |
|                                                                          |
|  * errors.tolerance=none (default): Fail on first error                  |
|  * errors.tolerance=all: Skip bad records, send to DLQ                   |
|  * Context headers include: error message, exception, timestamp          |
|                                                                          |
|  DLQ MONITORING:                                                         |
|  * Alert when DLQ topic has > 0 messages (something is wrong)            |
|  * Track DLQ rate: messages/min → sudden spike = new bug or bad data     |
|  * Replay workflow: fix root cause → replay DLQ messages → verify        |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 4.3: EVENT SOURCING WITH KAFKA

```
+--------------------------------------------------------------------------+
|                                                                          |
|  EVENT SOURCING = Store state as a sequence of events                    |
|                                                                          |
|  Traditional: Store current state                                        |
|    Account balance = $500                                                |
|                                                                          |
|  Event sourcing: Store all events                                        |
|    1. AccountCreated(id=1, balance=0)                                    |
|    2. MoneyDeposited(id=1, amount=1000)                                  |
|    3. MoneyWithdrawn(id=1, amount=300)                                   |
|    4. MoneyWithdrawn(id=1, amount=200)                                   |
|    Current state = replay events = $500                                  |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  WHY KAFKA IS PERFECT FOR EVENT SOURCING:                                |
|                                                                          |
|  * Append-only log = natural event store                                 |
|  * Durable, replicated, ordered per partition                            |
|  * Log compaction keeps latest state per key                             |
|  * Multiple consumers can build different views (CQRS)                   |
|  * Event replay for debugging or rebuilding state                        |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  PATTERN:                                                                |
|                                                                          |
|  Command --> Validate --> Produce Event --> Kafka Topic                  |
|                                               |                          |
|                          +--------------------+----+                     |
|                          |                    |    |                     |
|                          v                    v    v                     |
|                     Read Model          Analytics  Audit                 |
|                     (Postgres)          (Druid)    (S3)                  |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 4.4: CQRS WITH KAFKA

```
+--------------------------------------------------------------------------+
|                                                                          |
|  CQRS = Command Query Responsibility Segregation                         |
|                                                                          |
|  Separate the WRITE model from the READ model.                           |
|  Kafka sits between them as the event backbone.                          |
|                                                                          |
|  +--------+    +-------+    +---------+    +--------+    +-----------+   |
|  | Client  | -> | Write | -> | Kafka   | -> | Read   | -> | Client   |   |
|  | (write) |    | Model |    | Topic   |    | Model  |    | (query)  |   |
|  +--------+    +-------+    +---------+    +--------+    +-----------+   |
|                                                                          |
|  Write Model:                                                            |
|  * Validates commands                                                    |
|  * Produces events to Kafka                                              |
|  * Optimized for writes (normalized DB)                                  |
|                                                                          |
|  Read Model:                                                             |
|  * Consumes events from Kafka                                            |
|  * Builds denormalized views                                             |
|  * Optimized for queries (materialized views, caches)                    |
|  * Can have MULTIPLE read models for different query patterns            |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 4.5: SAGA PATTERN (CHOREOGRAPHY)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SAGA = Distributed transaction using event choreography                |
|                                                                         |
|  E-commerce order flow:                                                 |
|                                                                         |
|  Order      Kafka       Payment     Kafka      Inventory    Kafka       |
|  Service    Topic       Service     Topic      Service      Topic       |
|    |                      |                      |                      |
|    |--OrderCreated------->|                      |                      |
|    |                      |--PaymentProcessed--->|                      |
|    |                      |                      |--StockReserved------>|
|    |<---------------------------------------------OrderConfirmed--------|
|    |                      |                      |                      |
|                                                                         |
|  COMPENSATION (on failure):                                             |
|    |                      |                      |                      |
|    |                      |                      |--StockFailed-------->|
|    |                      |<--RefundInitiated----|                      |
|    |<--OrderCancelled-----|                      |                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Each service:                                                          |
|  * Consumes events from upstream                                        |
|  * Does its local work                                                  |
|  * Produces events for downstream                                       |
|  * Produces COMPENSATION events on failure                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.6: DEAD LETTER QUEUE (DLQ)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DLQ = Topic for messages that failed processing                        |
|                                                                         |
|  Input Topic                                                            |
|      |                                                                  |
|      v                                                                  |
|  +----------+     Success     +---------------+                         |
|  | Consumer | --------------> | Output Topic  |                         |
|  |          |                 +---------------+                         |
|  |          |     Failure                                               |
|  |          | --- (after N retries) ---> +-----------+                  |
|  +----------+                            | DLQ Topic |                  |
|                                          +-----------+                  |
|                                               |                         |
|                                          Monitor / Alert                |
|                                          Manual review                  |
|                                          Retry later                    |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  IMPLEMENTATION:                                                        |
|  * Retry N times with exponential backoff                               |
|  * If still failing, produce to DLQ topic with error metadata           |
|  * DLQ topic: same key + original headers + error reason                |
|  * Alert ops team, manual investigation                                 |
|  * Optionally: automated re-drive from DLQ back to input                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.7: SCHEMA REGISTRY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCHEMA REGISTRY = Central store for message schemas                    |
|                                                                         |
|  Producer                  Schema Registry              Consumer        |
|     |                           |                          |            |
|     |-- Register schema ------->|                          |            |
|     |<-- Schema ID (42) --------|                          |            |
|     |                           |                          |            |
|     |== Send msg (ID=42 + data) =========================>|             |
|     |                           |                          |            |
|     |                           |<-- Fetch schema by ID ---|            |
|     |                           |--- Schema definition --->|            |
|     |                           |                          |            |
|     |                           |            Deserialize using schema   |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  SUPPORTED FORMATS:                                                     |
|  * Avro       (most popular, compact binary, schema evolution)          |
|  * Protobuf   (Google's format, strong typing)                          |
|  * JSON Schema (human-readable, larger size)                            |
|                                                                         |
|  SCHEMA EVOLUTION RULES:                                                |
|  * BACKWARD  -- new schema can read old data (add optional fields)      |
|  * FORWARD   -- old schema can read new data (remove optional fields)   |
|  * FULL      -- both backward and forward compatible                    |
|  * NONE      -- no compatibility check                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.8: KAFKA CONNECT

```
+--------------------------------------------------------------------------+
|                                                                          |
|  KAFKA CONNECT = Framework for moving data in/out of Kafka               |
|                                                                          |
|  +----------+    +-------------------+    +-----------+                  |
|  | External | -> | SOURCE CONNECTOR  | -> | Kafka     |                  |
|  | System   |    | (reads from ext)  |    | Topic     |                  |
|  +----------+    +-------------------+    +-----------+                  |
|                                                                          |
|  +-----------+    +-------------------+    +----------+                  |
|  | Kafka     | -> | SINK CONNECTOR    | -> | External |                  |
|  | Topic     |    | (writes to ext)   |    | System   |                  |
|  +-----------+    +-------------------+    +----------+                  |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  POPULAR CONNECTORS:                                                     |
|                                                                          |
|  SOURCE:                                                                 |
|  * Debezium (CDC from MySQL, Postgres, MongoDB)                          |
|  * JDBC Source (poll-based DB reads)                                     |
|  * FileStream Source (files -> Kafka)                                    |
|  * S3 Source                                                             |
|                                                                          |
|  SINK:                                                                   |
|  * Elasticsearch Sink (search indexing)                                  |
|  * S3 Sink (data lake archival)                                          |
|  * JDBC Sink (write to any RDBMS)                                        |
|  * BigQuery / Snowflake Sink (analytics)                                 |
|  * Redis Sink (cache population)                                         |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 4.9: MULTI-DATACENTER REPLICATION

```
+--------------------------------------------------------------------------+
|                                                                          |
|  MIRRORMAKER 2 (MM2) = Cross-cluster replication                         |
|                                                                          |
|  +-------------------+          +-------------------+                    |
|  | DC-EAST Cluster   |          | DC-WEST Cluster   |                    |
|  |                   |  MM2     |                   |                    |
|  | orders            | -------> | dc-east.orders    |                    |
|  | payments          | -------> | dc-east.payments  |                    |
|  | inventory         | -------> | dc-east.inventory |                    |
|  +-------------------+          +-------------------+                    |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  USE CASES:                                                              |
|  * Disaster recovery (active-passive)                                    |
|  * Geo-replication (active-active)                                       |
|  * Data aggregation (multiple clusters -> central)                       |
|  * Cloud migration (on-prem -> cloud)                                    |
|                                                                          |
|  CHALLENGES:                                                             |
|  * Offset translation (offsets differ across clusters)                   |
|  * Eventual consistency (replication lag)                                |
|  * Avoiding infinite loops in active-active                              |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 4.10: PERFORMANCE TUNING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THROUGHPUT vs LATENCY TUNING                                           |
|                                                                         |
|  +-------------------+------------------------+----------------------+  |
|  | Setting           | High Throughput        | Low Latency          |  |
|  +-------------------+------------------------+----------------------+  |
|  | batch.size        | 64KB - 256KB           | 0 - 16KB             |  |
|  | linger.ms         | 10 - 100ms             | 0                    |  |
|  | compression.type  | lz4 or zstd            | none or lz4          |  |
|  | acks              | 1                      | 1                    |  |
|  | buffer.memory     | 64MB+                  | 32MB                 |  |
|  | fetch.min.bytes   | 1MB+                   | 1                    |  |
|  | fetch.max.wait.ms | 500ms                  | 10ms                 |  |
|  +-------------------+------------------------+----------------------+  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  BROKER-SIDE TUNING:                                                    |
|                                                                         |
|  num.io.threads = 8            (disk I/O threads)                       |
|  num.network.threads = 3       (network request threads)                |
|  socket.send.buffer.bytes      (TCP send buffer, -1 = OS default)       |
|  socket.receive.buffer.bytes   (TCP receive buffer)                     |
|  log.flush.interval.messages   (fsync frequency, usually leave to OS)   |
|                                                                         |
|  PARTITION COUNT:                                                       |
|  * More partitions = more throughput (more parallel consumers)          |
|  * More partitions = more memory, file handles, leader elections        |
|  * Sweet spot: 10-50 partitions per topic for most workloads            |
|  * Rule: partitions >= expected peak consumer count                     |
|                                                                         |
|  JVM TUNING:                                                            |
|  * Heap: 4-6 GB (NOT more, let OS use RAM for page cache)               |
|  * GC: G1GC with -XX:MaxGCPauseMillis=20                                |
|  * Leave majority of RAM for OS page cache (Kafka's real cache)         |
|                                                                         |
+-------------------------------------------------------------------------+
```
