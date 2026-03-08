# APACHE KAFKA
*Chapter 3: Producers and Consumers In Depth*

Mastering Kafka means understanding how producers and consumers work
internally -- batching, acknowledgments, offset management, and
rebalancing determine your system's delivery guarantees and performance.

## SECTION 3.1: PRODUCER INTERNALS

```
+--------------------------------------------------------------------------+
|                                                                          |
|  PRODUCER ARCHITECTURE                                                   |
|                                                                          |
|  Application Thread                                                      |
|       |                                                                  |
|       v                                                                  |
|  +----------+     +-----------+     +-----------+                        |
|  | Serialize | --> | Partition | --> | Record    |                       |
|  | Key+Value |     | (choose   |     | Accumul-  |                       |
|  |           |     |  target   |     | ator      |                       |
|  +----------+     |  partition)|     | (batching)|                       |
|                    +-----------+     +-----+-----+                       |
|                                            |                             |
|                                    +-------v-------+                     |
|                                    | Sender Thread |                     |
|                                    | (background)  |                     |
|                                    +-------+-------+                     |
|                                            |                             |
|                              +-------------+-------------+               |
|                              |             |             |               |
|                              v             v             v               |
|                          Broker 0      Broker 1      Broker 2            |
|                                                                          |
+--------------------------------------------------------------------------+
```

### WHAT HAPPENS WHEN YOU CALL send()

```
+--------------------------------------------------------------------------+
|                                                                          |
|  producer.send(new ProducerRecord("orders", "user-1", orderJson));       |
|                                                                          |
|  Step 1: SERIALIZE                                                       |
|  Key and value are serialized using configured serializers.              |
|  key.serializer = StringSerializer                                       |
|  value.serializer = JsonSerializer (or Avro, Protobuf)                   |
|  Output: raw bytes                                                       |
|                                                                          |
|  Step 2: PARTITION                                                       |
|  Decide which partition to send to:                                      |
|  * If key != null:  partition = hash(key) % num_partitions               |
|  * If key == null:  sticky partition (batch to one, rotate)              |
|  * If custom:       your Partitioner class decides                       |
|                                                                          |
|  Step 3: ACCUMULATE (Record Accumulator)                                 |
|  Message added to a batch for that partition.                            |
|  Batch is sent when: batch.size is full OR linger.ms expires.            |
|  If buffer.memory is full, send() BLOCKS (max.block.ms = 60s).           |
|                                                                          |
|  Step 4: SENDER THREAD (background, async)                               |
|  Picks ready batches, compresses them, sends to broker leader.           |
|  Waits for ack based on acks setting (0, 1, all).                        |
|                                                                          |
|  Step 5: CALLBACK                                                        |
|  On success: callback receives RecordMetadata (partition, offset, ts).   |
|  On failure: callback receives Exception. Message may be retried.        |
|                                                                          |
+--------------------------------------------------------------------------+
```

### PARTITIONING STRATEGIES

```
+----------------------------------------------------------------------------+
|                                                                            |
|  How the producer decides which partition gets a message:                  |
|                                                                            |
|  +---------------------------------------------------------------------+   |
|  | Strategy         | When                | Behavior                   |   |
|  |------------------|---------------------|----------------------------|   |
|  | Key-based hash   | key != null         | hash(key) % partitions     |   |
|  |                  |                     | Same key -> same partition |   |
|  |                  |                     | Guarantees ordering by key |   |
|  |------------------|---------------------|----------------------------|   |
|  | Sticky partition | key == null         | Batch to one partition,    |   |
|  | (Kafka 2.4+)    |                     | switch when batch is full   |   |
|  |                  |                     | Better batching than RR    |   |
|  |------------------|---------------------|----------------------------|   |
|  | Round-robin      | key == null         | Rotate across partitions   |   |
|  | (pre-2.4)       |                     | Even spread, poor batching  |   |
|  |------------------|---------------------|----------------------------|   |
|  | Custom           | Partitioner class   | Your logic decides         |   |
|  |                  | configured          | E.g., route by region      |   |
|  +---------------------------------------------------------------------+   |
|                                                                            |
|  EXAMPLE — Key-based routing:                                              |
|                                                                            |
|  send(key="user-A", value=order1)  -> hash("user-A") % 3 = P0              |
|  send(key="user-A", value=order2)  -> hash("user-A") % 3 = P0  (same!)     |
|  send(key="user-B", value=order3)  -> hash("user-B") % 3 = P1              |
|                                                                            |
|  All of user-A's orders go to P0. Ordering within P0 is guaranteed.        |
|  User-A's orders will always be processed in order.                        |
|                                                                            |
+----------------------------------------------------------------------------+
```

### RETRIES AND ORDERING GUARANTEES

```
+--------------------------------------------------------------------------+
|                                                                          |
|  RETRIES:                                                                |
|                                                                          |
|  retries = 2147483647 (default, effectively infinite since Kafka 2.1)    |
|  delivery.timeout.ms = 120000 (2 min total time to deliver)              |
|  retry.backoff.ms = 100 (wait between retries)                           |
|                                                                          |
|  Producer retries automatically on transient errors:                     |
|  * NOT_LEADER_FOR_PARTITION (leader moved)                               |
|  * NETWORK_EXCEPTION (broker unreachable)                                |
|  * REQUEST_TIMED_OUT (broker too slow)                                   |
|                                                                          |
|  NON-retriable errors (fail immediately):                                |
|  * INVALID_TOPIC (topic doesn't exist)                                   |
|  * MESSAGE_TOO_LARGE (exceeds max size)                                  |
|  * AUTHORIZATION_FAILED (no permission)                                  |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  ORDERING PROBLEM WITH RETRIES:                                          |
|                                                                          |
|  max.in.flight.requests.per.connection = 5 (default)                     |
|  This means 5 batches can be in-flight to a broker simultaneously.       |
|                                                                          |
|  Batch 1 [msg A, B] -> sent -> FAILS                                     |
|  Batch 2 [msg C, D] -> sent -> SUCCEEDS                                  |
|  Batch 1 retried     -> SUCCEEDS                                         |
|  Broker log: C, D, A, B  (OUT OF ORDER!)                                 |
|                                                                          |
|  FIX: enable.idempotence = true (default since Kafka 3.0)                |
|  Broker tracks sequence numbers per producer per partition.              |
|  Even with 5 in-flight requests, broker reorders correctly.              |
|                                                                          |
|  Without idempotence, set max.in.flight.requests = 1                     |
|  (slow, but guarantees order)                                            |
|                                                                          |
+--------------------------------------------------------------------------+
```

### PRODUCER JAVA EXAMPLE

```java
Properties props = new Properties();                                
props.put("bootstrap.servers", "broker1:9092,broker2:9092");        
props.put("key.serializer",                                         
    "org.apache.kafka.common.serialization.StringSerializer");      
props.put("value.serializer",                                       
    "org.apache.kafka.common.serialization.StringSerializer");      
props.put("acks", "all");                                           
props.put("enable.idempotence", "true");                            
props.put("linger.ms", "20");                                       
props.put("batch.size", "65536");                                   
props.put("compression.type", "lz4");                               

KafkaProducer<String, String> producer = new KafkaProducer<>(props);

ProducerRecord<String, String> record =                             
    new ProducerRecord<>("orders", "user-123", orderJson);          

// Async send with callback                                         
producer.send(record, (metadata, exception) -> {                    
    if (exception != null) {                                        
        log.error("Send failed for key=user-123", exception);       
    } else {                                                        
        log.info("Sent to partition={} offset={}",                  
            metadata.partition(), metadata.offset());               
    }                                                               
});                                                                 

// Flush all buffered messages before shutdown                      
producer.flush();                                                   
producer.close();                                                   
```

### BATCHING AND COMPRESSION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BATCHING (critical for throughput)                                     |
|                                                                         |
|  The producer accumulates messages into batches BEFORE sending.         |
|                                                                         |
|  KEY CONFIGS:                                                           |
|                                                                         |
|  batch.size = 16384 (16KB default)                                      |
|    Max bytes per batch. Batch is sent when this is full.                |
|                                                                         |
|  linger.ms = 0 (default)                                                |
|    How long to wait for more messages before sending a batch.           |
|    Set to 5-100ms for higher throughput (more batching).                |
|                                                                         |
|  buffer.memory = 33554432 (32MB default)                                |
|    Total memory for unsent messages. If full, send() blocks.            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  COMPRESSION (applied per batch):                                       |
|                                                                         |
|  compression.type = none | gzip | snappy | lz4 | zstd                   |
|                                                                         |
|  +----------+--------+--------+----------+                              |
|  | Type     | Ratio  | Speed  | CPU      |                              |
|  +----------+--------+--------+----------+                              |
|  | none     | 1x     | -      | none     |                              |
|  | gzip     | best   | slow   | high     |                              |
|  | snappy   | good   | fast   | low      |                              |
|  | lz4      | good   | fastest| lowest   |                              |
|  | zstd     | best   | fast   | medium   |                              |
|  +----------+--------+--------+----------+                              |
|                                                                         |
|  RECOMMENDATION: Use lz4 or zstd for most workloads.                    |
|  Compression saves network bandwidth AND disk space.                    |
|  Broker stores compressed batches as-is (no re-compression).            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MESSAGE SIZE LIMITS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KAFKA MESSAGE SIZE CONFIGURATION                                       |
|  =================================                                      |
|                                                                         |
|  DEFAULT MAX MESSAGE SIZE: 1 MB (1048576 bytes)                         |
|                                                                         |
|  All 3 configs must be aligned — mismatch causes silent failures:       |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Config                      | Where    | Default  | Purpose        | |
|  |-----------------------------|----------|----------|----------------| |
|  | max.request.size            | Producer | 1 MB     | Max size of a  | |
|  |                             |          |          | produce request| |
|  | message.max.bytes           | Broker   | 1 MB     | Max message    | |
|  |                             | (topic)  |          | broker accepts | |
|  | max.partition.fetch.bytes   | Consumer | 1 MB     | Max data per   | |
|  |                             |          |          | partition fetch| |
|  | replica.fetch.max.bytes     | Broker   | 1 MB     | Max replication| |
|  |                             |          |          | fetch size     | |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  TO INCREASE TO 10 MB (example):                                        |
|  Producer:  max.request.size = 10485760                                 |
|  Broker:    message.max.bytes = 10485760                                |
|  Consumer:  max.partition.fetch.bytes = 10485760                        |
|  Broker:    replica.fetch.max.bytes = 10485760                          |
|                                                                         |
|  WARNING: Increasing message size impacts:                              |
|  * Broker memory (each partition buffer holds max.message.bytes)        |
|  * Replication speed (large messages slow ISR sync)                     |
|  * Consumer lag (one large message blocks others in partition)          |
|  * GC pressure (large byte arrays in JVM heap)                          |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  LARGE MESSAGE STRATEGIES:                                              |
|                                                                         |
|  1. CLAIM CHECK PATTERN (recommended)                                   |
|     Store payload in S3/GCS, send reference in Kafka message.           |
|     { "order_id": "123", "payload_ref": "s3://bucket/data.json" }       |
|     Consumer fetches from S3 when processing.                           |
|     Keeps Kafka fast, scalable, and within limits.                      |
|                                                                         |
|  2. COMPRESSION (good first step)                                       |
|     compression.type = lz4 (fast) or zstd (best ratio)                  |
|     JSON compresses 5-10x. A 5 MB JSON -> ~500 KB after lz4.            |
|     Applied per batch at producer, stored compressed on broker.         |
|     Consumer decompresses automatically.                                |
|                                                                         |
|  3. CHUNKING (avoid if possible)                                        |
|     Split into ordered chunks with sequence numbers.                    |
|     Complex: must handle ordering, missing chunks, reassembly.          |
|     Kafka Headers can carry chunk metadata:                             |
|       chunk-id: uuid, chunk-seq: 3, chunk-total: 5                      |
|                                                                         |
|  4. SCHEMA OPTIMIZATION                                                 |
|     Switch from JSON to Avro/Protobuf — 3-10x smaller.                  |
|     Avro + Schema Registry = compact + schema evolution.                |
|     Protobuf = smallest binary format, strongly typed.                  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  DECISION GUIDE:                                                        |
|                                                                         |
|  Message < 1 MB   --> Use as-is (default config works)                  |
|  Message 1-10 MB  --> Try compression first                             |
|                       If still large --> Claim Check to S3              |
|  Message > 10 MB  --> Always use Claim Check                            |
|  Binary data      --> Always use Claim Check (images, video, files)     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ACKNOWLEDGMENTS (acks)

```
+--------------------------------------------------------------------------+
|                                                                          |
|  acks SETTING = How many replicas must confirm before success            |
|                                                                          |
|  acks=0 (FIRE AND FORGET)                                                |
|  ========================                                                |
|  Producer does not wait for any acknowledgment.                          |
|  Fastest. Risk: messages may be lost.                                    |
|                                                                          |
|  Producer --> Broker (no response waited)                                |
|                                                                          |
|  Use case: metrics, logs where some loss is acceptable.                  |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  acks=1 (LEADER ONLY)                                                    |
|  =====================                                                   |
|  Leader writes to its local log and responds.                            |
|  Followers may not have the data yet.                                    |
|  Risk: data loss if leader dies before followers replicate.              |
|                                                                          |
|  Producer --> Leader (ack) --> Followers (async)                         |
|                                                                          |
|  Use case: default for most applications. Good balance.                  |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  acks=all (or acks=-1) (FULL REPLICATION)                                |
|  ==========================================                              |
|  Leader waits for ALL in-sync replicas (ISR) to acknowledge.             |
|  Slowest but safest. No data loss as long as >= 1 ISR alive.             |
|                                                                          |
|  Producer --> Leader --> All ISR Followers --> (ack)                     |
|                                                                          |
|  Use case: financial transactions, critical events.                      |
|  MUST combine with min.insync.replicas >= 2.                             |
|                                                                          |
+--------------------------------------------------------------------------+
```

### IDEMPOTENT PRODUCER

```
+--------------------------------------------------------------------------+
|                                                                          |
|  PROBLEM: Duplicate messages on retry                                    |
|                                                                          |
|  Producer sends msg --> network timeout --> producer retries             |
|  But the broker DID receive the first one --> DUPLICATE!                 |
|                                                                          |
|  SOLUTION: enable.idempotence = true (default since Kafka 3.0)           |
|                                                                          |
|  How it works:                                                           |
|  * Each producer gets a unique Producer ID (PID)                         |
|  * Each message gets a sequence number (per partition)                   |
|  * Broker rejects duplicates with same PID + sequence number             |
|                                                                          |
|  Producer (PID=7):                                                       |
|    send(seq=0) --> Broker accepts                                        |
|    send(seq=1) --> network timeout, retry                                |
|    send(seq=1) --> Broker sees duplicate, returns success (no dup)       |
|    send(seq=2) --> Broker accepts                                        |
|                                                                          |
|  REQUIREMENTS:                                                           |
|  * acks=all (set automatically)                                          |
|  * retries > 0 (set automatically)                                       |
|  * max.in.flight.requests.per.connection <= 5                            |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 3.2: CONSUMER INTERNALS

### CONSUMER LIFECYCLE

```
+---------------------------------------------------------------------------+
|                                                                           |
|  CONSUMER LIFECYCLE:                                                      |
|                                                                           |
|  1. CREATE   KafkaConsumer with config (group.id, deserializers, etc.)    |
|  2. SUBSCRIBE to topic(s): consumer.subscribe(List.of("orders"))          |
|  3. POLL     in a loop: consumer.poll() fetches + processes               |
|  4. COMMIT   offsets (auto or manual)                                     |
|  5. CLOSE    consumer.close() on shutdown (triggers rebalance)            |
|                                                                           |
|  -------------------------------------------------------------------      |
|                                                                           |
|  WHAT HAPPENS ON FIRST poll() FOR A NEW CONSUMER GROUP?                   |
|                                                                           |
|  1. Consumer finds the GROUP COORDINATOR (a specific broker)              |
|     Group coordinator = broker hosting the partition of                   |
|     __consumer_offsets for this group.                                    |
|                                                                           |
|  2. Sends JoinGroup request -> coordinator starts a rebalance             |
|                                                                           |
|  3. One consumer is elected as GROUP LEADER (not the coordinator!)        |
|     Leader runs the assignment strategy and tells coordinator             |
|     "Consumer A gets P0,P1 — Consumer B gets P2,P3"                       |
|                                                                           |
|  4. Coordinator sends assignments to all consumers                        |
|                                                                           |
|  5. Each consumer starts fetching from assigned partitions                |
|                                                                           |
+---------------------------------------------------------------------------+
```

### KEY CONSUMER CONFIGURATIONS

```
+---------------------------------------------------------------------------+
|                                                                           |
|  ESSENTIAL CONFIGS:                                                       |
|                                                                           |
|  +--------------------------------------------------------------------+   |
|  | Config                 | Default    | What It Does                 |   |
|  |------------------------|------------|------------------------------|   |
|  | group.id               | (required) | Consumer group name. All     |   |
|  |                        |            | consumers with same group.id |   |
|  |                        |            | share partitions.            |   |
|  |------------------------|------------|------------------------------|   |
|  | auto.offset.reset      | latest     | What to do when no committed |   |
|  |                        |            | offset exists (see below)    |   |
|  |------------------------|------------|------------------------------|   |
|  | enable.auto.commit     | true       | Auto-commit offsets every    |   |
|  |                        |            | auto.commit.interval.ms      |   |
|  |------------------------|------------|------------------------------|   |
|  | max.poll.records       | 500        | Max records per poll() call  |   |
|  |------------------------|------------|------------------------------|   |
|  | max.poll.interval.ms   | 300000     | Max gap between poll() calls |   |
|  |                        | (5 min)    | before consumer is kicked    |   |
|  |------------------------|------------|------------------------------|   |
|  | session.timeout.ms     | 45000      | Heartbeat timeout. Consumer  |   |
|  |                        | (45s)      | considered dead if no beat   |   |
|  |------------------------|------------|------------------------------|   |
|  | heartbeat.interval.ms  | 3000       | How often to send heartbeats |   |
|  |                        | (3s)       | Should be < 1/3 of session   |   |
|  |------------------------|------------|------------------------------|   |
|  | fetch.min.bytes        | 1          | Min data to return. Higher   |   |
|  |                        |            | = fewer requests, more batch |   |
|  |------------------------|------------|------------------------------|   |
|  | fetch.max.wait.ms      | 500        | Max broker wait for min.bytes|   |
|  +--------------------------------------------------------------------+   |
|                                                                           |
+---------------------------------------------------------------------------+
```

### auto.offset.reset EXPLAINED

```
+---------------------------------------------------------------------------+
|                                                                           |
|  When a consumer group reads a partition for the FIRST TIME               |
|  (no committed offset exists), what should it do?                         |
|                                                                           |
|  Topic "orders" has messages at offsets 0 through 999:                    |
|                                                                           |
|  [0] [1] [2] ... [500] ... [998] [999]                                    |
|                                                                           |
|  +--------------------------------------------------------------------+   |
|  | Setting  | Starts Reading From | Use Case                          |   |
|  |----------|---------------------|-----------------------------------|   |
|  | earliest | Offset 0            | Need ALL historical data.         |   |
|  |          | (beginning of topic) | Data pipelines, replay, backfill |   |
|  |----------|---------------------|-----------------------------------|   |
|  | latest   | Offset 999           | Only care about NEW messages.    |   |
|  | (default)| (end of topic)       | Real-time alerting, live feeds   |   |
|  |----------|---------------------|-----------------------------------|   |
|  | none     | THROW EXCEPTION      | Fail loudly if no offset saved.  |   |
|  |          |                      | Safety net for critical systems  |   |
|  +--------------------------------------------------------------------+   |
|                                                                           |
|  IMPORTANT: This ONLY applies when no committed offset exists.            |
|  If the consumer has committed before, it resumes from that offset        |
|  regardless of this setting.                                              |
|                                                                           |
|  COMMON MISTAKE:                                                          |
|  Setting auto.offset.reset=earliest expecting to re-read everything.      |
|  It won't — because the group already has a committed offset.             |
|  To truly re-read: reset offsets manually or use a NEW group.id.          |
|                                                                           |
+---------------------------------------------------------------------------+
```

### POLL LOOP

```
+--------------------------------------------------------------------------+
|                                                                          |
|  THE CONSUMER POLL LOOP                                                  |
|                                                                          |
|  Every Kafka consumer runs a poll loop:                                  |
|                                                                          |
|  while (true) {                                                          |
|      records = consumer.poll(Duration.ofMillis(100));                    |
|      for (record : records) {                                            |
|          process(record);                                                |
|      }                                                                   |
|  }                                                                       |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  WHAT poll() DOES INTERNALLY:                                            |
|                                                                          |
|  1. Sends heartbeat to group coordinator (I'm alive!)                    |
|  2. Fetches records from assigned partitions                             |
|  3. Auto-commits offsets (if enabled)                                    |
|  4. Handles rebalance callbacks                                          |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  CONSUMER THREAD MODEL:                                                  |
|                                                                          |
|  One consumer = one thread. You CANNOT share a KafkaConsumer across      |
|  threads. It is NOT thread-safe.                                         |
|                                                                          |
|  For parallel processing within one consumer:                            |
|                                                                          |
|  while (true) {                                                          |
|      records = consumer.poll(100ms);                                     |
|      // Submit to a thread pool for parallel processing                  |
|      for (record : records) {                                            |
|          executor.submit(() -> process(record));                         |
|      }                                                                   |
|      // Wait for all tasks to finish before committing                   |
|      executor.awaitCompletion();                                         |
|      consumer.commitSync();                                              |
|  }                                                                       |
|                                                                          |
|  WARNING: This breaks per-partition ordering.                            |
|  If ordering matters, process partitions sequentially.                   |
|                                                                          |
+--------------------------------------------------------------------------+
```

### DESERIALIZATION

```
+---------------------------------------------------------------------------+
|                                                                           |
|  Consumer must deserialize bytes back into objects:                       |
|                                                                           |
|  key.deserializer = StringDeserializer                                    |
|  value.deserializer = depends on what producer used                       |
|                                                                           |
|  +--------------------------------------------------------------------+   |
|  | Format     | Deserializer                    | Needs Schema Reg?   |   |
|  |------------|---------------------------------|---------------------|   |
|  | String     | StringDeserializer              | No                  |   |
|  | JSON       | JsonDeserializer                | No                  |   |
|  | Avro       | KafkaAvroDeserializer           | Yes                 |   |
|  | Protobuf   | KafkaProtobufDeserializer       | Yes                 |   |
|  | Raw bytes  | ByteArrayDeserializer           | No                  |   |
|  +--------------------------------------------------------------------+   |
|                                                                           |
|  POISON PILL: A message that cannot be deserialized.                      |
|  Consumer throws SerializationException and gets stuck in a loop.         |
|  Fix: wrap in try-catch, skip bad messages, send to DLQ.                  |
|                                                                           |
+---------------------------------------------------------------------------+
```

### CONSUMER JAVA EXAMPLE

```java
Properties props = new Properties();                                
props.put("bootstrap.servers", "broker1:9092,broker2:9092");        
props.put("group.id", "payment-service");                           
props.put("key.deserializer",                                       
    "org.apache.kafka.common.serialization.StringDeserializer");    
props.put("value.deserializer",                                     
    "org.apache.kafka.common.serialization.StringDeserializer");    
props.put("auto.offset.reset", "earliest");                         
props.put("enable.auto.commit", "false");                           
props.put("max.poll.records", "100");                               

KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props);
consumer.subscribe(List.of("orders"));                              

try {                                                               
    while (true) {                                                  
        ConsumerRecords<String, String> records =                   
            consumer.poll(Duration.ofMillis(100));                  

        for (ConsumerRecord<String, String> record : records) {     
            String userId = record.key();                           
            String orderJson = record.value();                      

            log.info("partition={} offset={} key={}",               
                record.partition(), record.offset(), userId);       

            processOrder(userId, orderJson);                        
        }                                                           

        consumer.commitSync();                                      
    }                                                               
} finally {                                                         
    consumer.close();    // triggers rebalance, releases partitions 
}                                                                   
```

### OFFSET MANAGEMENT

```
+--------------------------------------------------------------------------+
|                                                                          |
|  OFFSET COMMIT STRATEGIES                                                |
|                                                                          |
|  1. AUTO-COMMIT (default)                                                |
|     ==========================                                           |
|     enable.auto.commit = true                                            |
|     auto.commit.interval.ms = 5000                                       |
|                                                                          |
|     Every 5 seconds, the consumer automatically commits                  |
|     the latest offset it has poll()'d.                                   |
|                                                                          |
|     Risk: AT-LEAST-ONCE delivery                                         |
|     * If consumer crashes AFTER poll() but BEFORE commit                 |
|       --> messages re-delivered on restart (duplicates)                  |
|     * If consumer crashes AFTER commit but BEFORE processing             |
|       --> messages LOST (already committed)                              |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  2. MANUAL COMMIT (recommended for critical systems)                     |
|     =================================================                    |
|     enable.auto.commit = false                                           |
|                                                                          |
|     a) commitSync() -- blocks until offset is committed                  |
|        Safest, but slower.                                               |
|                                                                          |
|     b) commitAsync() -- fire and forget, with callback                   |
|        Faster, but no guarantee of commit success.                       |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  DELIVERY SEMANTICS:                                                     |
|                                                                          |
|  +-------------------+--------------------------+----------------------+ |
|  | Semantic          | How                      | Risk                 | |
|  +-------------------+--------------------------+----------------------+ |
|  | At-most-once      | Commit BEFORE processing | Lost messages        | |
|  | At-least-once     | Commit AFTER processing  | Duplicate messages   | |
|  | Exactly-once      | Kafka transactions       | Complexity + cost    | |
|  +-------------------+--------------------------+----------------------+ |
|                                                                          |
+--------------------------------------------------------------------------+
```

#### HOW OFFSETS WORK (Step-by-Step Example)

```
+---------------------------------------------------------------------------+
|                                                                           |
|  WHAT IS AN OFFSET?                                                       |
|  A monotonically increasing integer per message in a partition.           |
|  Think of it as a line number in a file.                                  |
|                                                                           |
|  Topic "orders", Partition 0:                                             |
|                                                                           |
|  +-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+            |
|  |  0  |  1  |  2  |  3  |  4  |  5  |  6  |  7  |  8  |  9  |            |
|  +-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+            |
|                          ^                    ^              ^            |
|                          |                    |              |            |
|                   committed offset     current position   latest msg      |
|                    (saved: 3)          (processing: 6)    (offset: 9)     |
|                                                                           |
|  WHERE ARE OFFSETS STORED?                                                |
|  Internal topic: __consumer_offsets (50 partitions by default)            |
|  Key: {consumer_group, topic, partition}                                  |
|  Value: committed offset number                                           |
|                                                                           |
+---------------------------------------------------------------------------+
```

#### REAL-WORLD EXAMPLE: Order Processing

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Consumer Group "payment-service" reading from "orders" Partition 0      |
|                                                                          |
|  Messages in partition:                                                  |
|  [0: order-100] [1: order-101] [2: order-102] [3: order-103]             |
|                                                                          |
|  ================================================================        |
|  SCENARIO 1: AT-LEAST-ONCE (commit AFTER processing)                     |
|  ================================================================        |
|                                                                          |
|  Step 1: poll()     -> gets [order-100, order-101, order-102]            |
|  Step 2: process    -> charge $50 for order-100  (success)               |
|  Step 3: process    -> charge $30 for order-101  (success)               |
|  Step 4: process    -> charge $80 for order-102  (success)               |
|  Step 5: commitSync(offset=3)   -> saved!                                |
|                                                                          |
|  CRASH SCENARIO:                                                         |
|  Step 1: poll()     -> gets [order-100, order-101, order-102]            |
|  Step 2: process    -> charge $50 for order-100  (success)               |
|  Step 3: process    -> charge $30 for order-101  (success)               |
|  Step 4: ** CRASH ** (before commit)                                     |
|                                                                          |
|  On restart: last committed offset = 0                                   |
|  poll() returns [order-100, order-101, order-102] AGAIN                  |
|  -> order-100 and order-101 get charged TWICE!                           |
|  -> Fix: make processing IDEMPOTENT (check if already charged)           |
|                                                                          |
|  ================================================================        |
|  SCENARIO 2: AT-MOST-ONCE (commit BEFORE processing)                     |
|  ================================================================        |
|                                                                          |
|  Step 1: poll()     -> gets [order-100, order-101, order-102]            |
|  Step 2: commitSync(offset=3)   -> saved!                                |
|  Step 3: process    -> charge $50 for order-100  (success)               |
|  Step 4: ** CRASH **                                                     |
|                                                                          |
|  On restart: last committed offset = 3                                   |
|  poll() returns [order-103, ...]                                         |
|  -> order-101 and order-102 were NEVER processed, NEVER retried          |
|  -> Money NOT collected. DATA LOSS.                                      |
|                                                                          |
+--------------------------------------------------------------------------+
```

```java
// AT-LEAST-ONCE — Production standard for payment/order systems                   
// Process first, commit after. Downstream MUST be idempotent.                     

while (true) {                                                                     
    ConsumerRecords<String, Order> records = consumer.poll(Duration.ofMillis(100));

    for (ConsumerRecord<String, Order> record : records) {                         
        Order order = record.value();                                              

        if (alreadyProcessed(order.getId())) {                                     
            continue;                            // idempotency check              
        }                                                                          

        chargePayment(order);                    // business logic                 
        markProcessed(order.getId());            // save to DB                     
    }                                                                              

    consumer.commitSync();                       // commit AFTER all processed     
}                                                                                  
```

```java
// FINE-GRAINED: Commit offset per partition (more control)        
// Useful when processing takes a long time per batch              

for (TopicPartition partition : records.partitions()) {            
    List<ConsumerRecord<String, Order>> partitionRecords =         
        records.records(partition);                                

    for (ConsumerRecord<String, Order> record : partitionRecords) {
        processOrder(record.value());                              
    }                                                              

    long lastOffset = partitionRecords                             
        .get(partitionRecords.size() - 1).offset();                

    consumer.commitSync(                                           
        Map.of(partition, new OffsetAndMetadata(lastOffset + 1))   
    );                                                             
}                                                                  
```

```
+--------------------------------------------------------------------------+
|                                                                          |
|  WHY lastOffset + 1 ?                                                    |
|                                                                          |
|  Committed offset = "next message to read", NOT "last message read"      |
|                                                                          |
|  If you processed offset 5, commit offset 6.                             |
|  On restart, consumer starts reading FROM offset 6.                      |
|                                                                          |
|  Common bug: committing offset 5 instead of 6                            |
|  -> message at offset 5 gets re-processed every restart.                 |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  SUMMARY:                                                                |
|                                                                          |
|  * Auto-commit: Simple, risk of duplicates or loss. OK for logs.         |
|  * Manual commitSync: Safest. Use for payments, orders, critical data.   |
|  * Manual commitAsync: Faster, use with commitSync on shutdown.          |
|  * Per-partition commit: Most control, use for slow processing.          |
|  * Always make consumers idempotent in at-least-once systems.            |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 3.3: CONSUMER REBALANCING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS A REBALANCE?                                                   |
|                                                                         |
|  Reassignment of partitions to consumers within a group.                |
|                                                                         |
|  Triggered when:                                                        |
|  * A consumer joins the group                                           |
|  * A consumer leaves the group (crash or shutdown)                      |
|  * A consumer is kicked out (missed poll() deadline)                    |
|  * Partitions are added to a subscribed topic                           |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  EAGER REBALANCE (default before 2.4)                                   |
|  =====================================                                  |
|  1. ALL consumers stop reading                                          |
|  2. ALL consumers give up their partitions                              |
|  3. Coordinator reassigns all partitions                                |
|  4. All consumers get new assignments                                   |
|                                                                         |
|  Problem: "stop the world" -- ALL consumers pause briefly               |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  COOPERATIVE (INCREMENTAL) REBALANCE (2.4+)                             |
|  =============================================                          |
|  1. Only AFFECTED partitions are revoked                                |
|  2. Other consumers continue reading unaffected partitions              |
|  3. Revoked partitions are reassigned                                   |
|                                                                         |
|  Much less disruption. Set via:                                         |
|  partition.assignment.strategy =                                        |
|    org.apache.kafka.clients.consumer.CooperativeStickyAssignor          |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  STATIC GROUP MEMBERSHIP (minimize rebalances)                          |
|  ===============================================                        |
|  group.instance.id = "consumer-1"                                       |
|                                                                         |
|  * Consumer gets a fixed identity                                       |
|  * On restart, gets same partitions back (no rebalance)                 |
|  * Only triggers rebalance if gone > session.timeout.ms                 |
|  * Best for: stateful consumers, K8s rolling restarts                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.4: CONSUMER LAG MONITORING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONSUMER LAG = latest offset - consumer's committed offset             |
|                                                                         |
|  Partition 0:                                                           |
|  [0] [1] [2] [3] [4] [5] [6] [7] [8] [9] [10] [11] [12]                 |
|                          ^                          ^                   |
|                          |                          |                   |
|                   consumer offset=5           latest offset=12          |
|                                                                         |
|                   LAG = 12 - 5 = 7 messages behind                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  MONITORING TOOLS:                                                      |
|  * kafka-consumer-groups.sh --describe --group my-group                 |
|  * Burrow (LinkedIn's lag monitoring tool)                              |
|  * Kafka JMX metrics (records-lag-max)                                  |
|  * Prometheus + Grafana dashboards                                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  WHEN LAG IS HIGH:                                                      |
|  * Consumer is too slow -> optimize processing or add consumers         |
|  * Consumer is stuck -> check for blocking I/O or deadlocks             |
|  * Spike in producer traffic -> auto-scale consumers                    |
|  * Consumer rebalancing too often -> use static membership              |
|                                                                         |
+-------------------------------------------------------------------------+
```

```bash
# Check consumer lag from CLI                                               
bin/kafka-consumer-groups.sh \                                              
    --bootstrap-server localhost:9092 \                                     
    --describe \                                                            
    --group order-service                                                   

# Output:                                                                   
# GROUP          TOPIC        PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
# order-service  orders       0          1000            1050            50 
# order-service  orders       1          2000            2005            5  
# order-service  orders       2          1500            1500            0  
```
