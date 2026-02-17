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
