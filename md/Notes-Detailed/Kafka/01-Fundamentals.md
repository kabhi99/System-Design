# APACHE KAFKA
*Chapter 1: Fundamentals*

Apache Kafka is a distributed event streaming platform capable of handling
trillions of events per day. Originally developed at LinkedIn, it is now
the backbone of real-time data pipelines at thousands of companies.

## SECTION 1.1: WHAT IS KAFKA?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KAFKA IN ONE SENTENCE                                                  |
|                                                                         |
|  A distributed, fault-tolerant, high-throughput commit log that         |
|  lets you publish, subscribe to, store, and process streams of          |
|  records (events) in real time.                                         |
|                                                                         |
|  -------------------------------------------------------------------   |
|                                                                         |
|  KEY TRAITS:                                                            |
|  * Distributed   -- runs as a cluster across many servers               |
|  * Durable       -- persists all data to disk, replicated               |
|  * Scalable      -- handles millions of messages/sec                    |
|  * Fast          -- low-latency (single-digit ms end-to-end)            |
|  * Ordered       -- strict ordering within a partition                  |
|  * Replayable    -- consumers can re-read old messages                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY WAS KAFKA CREATED?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM AT LINKEDIN (2010)                                         |
|                                                                         |
|  BEFORE KAFKA:                                                          |
|                                                                         |
|    Service A -----> Database                                            |
|    Service B -----> Database                                            |
|    Service C -----> Hadoop                                              |
|    Service D -----> Monitoring                                          |
|    Service E -----> Search Index                                        |
|                                                                         |
|    Every service had point-to-point connections.                        |
|    N services = N x N integrations.                                     |
|    Adding one new system meant touching every producer.                 |
|                                                                         |
|  -------------------------------------------------------------------   |
|                                                                         |
|  AFTER KAFKA:                                                           |
|                                                                         |
|    Service A --+                        +--> Database                   |
|    Service B --+--> [ KAFKA CLUSTER ] --+--> Hadoop                    |
|    Service C --+                        +--> Monitoring                 |
|    Service D --+                        +--> Search Index              |
|                                                                         |
|    Single integration point for all services.                           |
|    Producers and consumers are fully decoupled.                         |
|    Add any new system without changing existing ones.                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.2: CORE CONCEPTS

### TOPICS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TOPIC = A named category/feed of messages                              |
|                                                                         |
|  Think of it like a database table or a folder in a filesystem.         |
|                                                                         |
|  Examples:                                                              |
|  * "user-signups"     -- every new user registration                    |
|  * "order-events"     -- order created, paid, shipped, delivered        |
|  * "page-views"       -- every web page view for analytics             |
|  * "inventory-updates"-- stock level changes                            |
|                                                                         |
|  Properties:                                                            |
|  * A topic can have zero, one, or many producers                        |
|  * A topic can have zero, one, or many consumers                        |
|  * Topics are split into PARTITIONS for parallelism                     |
|  * Data is retained for a configurable period (default 7 days)          |
|  * Data is immutable -- once written, cannot be changed                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### PARTITIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PARTITION = An ordered, immutable sequence of messages                  |
|                                                                         |
|  Topic "order-events" with 3 partitions:                                |
|                                                                         |
|  Partition 0:  [msg0] [msg1] [msg2] [msg3] [msg4] [msg5] -->           |
|  Partition 1:  [msg0] [msg1] [msg2] [msg3] -->                         |
|  Partition 2:  [msg0] [msg1] [msg2] [msg3] [msg4] -->                  |
|                                                                         |
|  -------------------------------------------------------------------   |
|                                                                         |
|  WHY PARTITIONS?                                                        |
|                                                                         |
|  1. PARALLELISM                                                         |
|     Each partition can be consumed by a different consumer               |
|     3 partitions = up to 3 consumers reading in parallel                |
|                                                                         |
|  2. SCALABILITY                                                         |
|     Partitions can live on different brokers (servers)                   |
|     More partitions = more throughput                                   |
|                                                                         |
|  3. ORDERING                                                            |
|     Messages within a partition are strictly ordered                     |
|     Messages ACROSS partitions have NO ordering guarantee               |
|                                                                         |
|  -------------------------------------------------------------------   |
|                                                                         |
|  HOW MESSAGES ARE ASSIGNED TO PARTITIONS:                               |
|                                                                         |
|  * No key   -> Round-robin across partitions                            |
|  * With key -> hash(key) % num_partitions                               |
|                                                                         |
|  Example: key = "user-123"                                              |
|  hash("user-123") % 3 = 1  --> always goes to Partition 1              |
|  All events for user-123 are ordered in the same partition              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### OFFSETS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OFFSET = A unique ID for each message within a partition               |
|                                                                         |
|  Partition 0:                                                           |
|  +-----+-----+-----+-----+-----+-----+-----+-----+                    |
|  | 0   | 1   | 2   | 3   | 4   | 5   | 6   | 7   |  --> new writes    |
|  +-----+-----+-----+-----+-----+-----+-----+-----+                    |
|    ^                         ^              ^                           |
|    |                         |              |                           |
|  oldest                  consumer        latest                        |
|  message                 position        message                       |
|                                                                         |
|  -------------------------------------------------------------------   |
|                                                                         |
|  KEY PROPERTIES:                                                        |
|  * Offsets are auto-incrementing integers (0, 1, 2, 3...)               |
|  * Offsets are unique WITHIN a partition (not across partitions)         |
|  * Consumers track their own offset (where they've read up to)          |
|  * Kafka stores consumer offsets in __consumer_offsets topic             |
|  * Consumers can RESET their offset to re-read old data                 |
|  * Offsets are never reused even after messages expire                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### BROKERS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BROKER = A single Kafka server                                         |
|                                                                         |
|  A Kafka CLUSTER is made of multiple brokers.                           |
|                                                                         |
|  +------------------+  +------------------+  +------------------+       |
|  |    Broker 1      |  |    Broker 2      |  |    Broker 3      |       |
|  |                  |  |                  |  |                  |       |
|  | Topic-A Part-0   |  | Topic-A Part-1   |  | Topic-A Part-2   |       |
|  | Topic-B Part-1   |  | Topic-B Part-2   |  | Topic-B Part-0   |       |
|  | Topic-C Part-2   |  | Topic-C Part-0   |  | Topic-C Part-1   |       |
|  |                  |  |                  |  |                  |       |
|  +------------------+  +------------------+  +------------------+       |
|                                                                         |
|  * Each broker is identified by an integer ID (0, 1, 2...)              |
|  * Each broker holds some topic partitions (not all)                    |
|  * Connecting to ANY broker connects you to the entire cluster          |
|    (every broker knows about every other broker = "bootstrap")          |
|  * A typical production cluster has 3-12+ brokers                       |
|  * One broker is elected as the CONTROLLER (manages partitions)         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.3: PRODUCERS AND CONSUMERS

### PRODUCERS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PRODUCER = An application that writes data to Kafka topics             |
|                                                                         |
|  +----------+                                                           |
|  | Producer |                                                           |
|  +----+-----+                                                           |
|       |                                                                 |
|       |  send("order-events", key="order-42", value={...})              |
|       |                                                                 |
|       v                                                                 |
|  +----+-----+-----+-----+                                              |
|  | Partition 0 | Part 1 | Part 2 |   Topic: order-events               |
|  +-------------+---------+--------+                                     |
|                                                                         |
|  -------------------------------------------------------------------   |
|                                                                         |
|  PRODUCER DECIDES:                                                      |
|  * Which topic to write to                                              |
|  * Optionally which partition (via key or custom partitioner)           |
|  * Acknowledgment level (acks=0, acks=1, acks=all)                     |
|  * Compression (none, gzip, snappy, lz4, zstd)                         |
|  * Batching behavior (batch.size, linger.ms)                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CONSUMERS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONSUMER = An application that reads data from Kafka topics            |
|                                                                         |
|  +----------+                                                           |
|  | Consumer | <-- poll() loop                                           |
|  +----+-----+                                                           |
|       |                                                                 |
|       |  Reads from partition, tracks its own offset                     |
|       |                                                                 |
|  Partition 0:                                                           |
|  [0] [1] [2] [3] [4] [5] [6] [7]                                       |
|                    ^                                                    |
|                    |                                                    |
|               consumer offset = 4                                       |
|               (has read 0-3, will read 4 next)                          |
|                                                                         |
|  -------------------------------------------------------------------   |
|                                                                         |
|  KEY BEHAVIOR:                                                          |
|  * Consumer PULLS data (Kafka does not push)                            |
|  * Consumer controls the pace of reading                                |
|  * Consumer can re-read data by resetting its offset                    |
|  * Multiple consumers can read the same topic independently             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CONSUMER GROUPS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONSUMER GROUP = A set of consumers that cooperate to consume          |
|  a topic.  Each partition is read by exactly ONE consumer in            |
|  the group.                                                             |
|                                                                         |
|  Topic "orders" with 4 partitions, Consumer Group "order-service":      |
|                                                                         |
|  Partition 0 -----> Consumer A                                          |
|  Partition 1 -----> Consumer A                                          |
|  Partition 2 -----> Consumer B                                          |
|  Partition 3 -----> Consumer C                                          |
|                                                                         |
|  Consumer D is IDLE (more consumers than partitions)                    |
|                                                                         |
|  -------------------------------------------------------------------   |
|                                                                         |
|  RULES:                                                                 |
|  * 1 partition can be assigned to only 1 consumer in a group            |
|  * 1 consumer can handle multiple partitions                            |
|  * If consumers > partitions, extra consumers sit idle                  |
|  * If a consumer dies, its partitions are reassigned (rebalance)        |
|                                                                         |
|  -------------------------------------------------------------------   |
|                                                                         |
|  MULTIPLE GROUPS CAN READ THE SAME TOPIC:                               |
|                                                                         |
|  Topic "orders"                                                         |
|       |                                                                 |
|       +--> Group "order-service"   (processes orders)                   |
|       +--> Group "analytics"       (builds dashboards)                  |
|       +--> Group "audit-log"       (compliance logging)                 |
|                                                                         |
|  Each group gets ALL messages. Within a group, messages are             |
|  split across consumers. This is pub-sub + load balancing.              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.4: KAFKA vs TRADITIONAL MESSAGE QUEUES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMPARISON TABLE                                                       |
|                                                                         |
|  +---------------+----------------+----------------+----------------+   |
|  | Feature       | Kafka          | RabbitMQ       | AWS SQS        |   |
|  +---------------+----------------+----------------+----------------+   |
|  | Model         | Commit log     | Message broker | Queue service  |   |
|  | Ordering      | Per-partition  | Per-queue      | Best-effort    |   |
|  | Retention     | Time/size      | Until consumed | 14 days max    |   |
|  | Replay        | Yes (offsets)  | No             | No             |   |
|  | Throughput    | Millions/sec   | Thousands/sec  | Thousands/sec  |   |
|  | Latency       | ~5ms           | ~1ms           | ~10-50ms       |   |
|  | Consumer      | Pull           | Push           | Pull           |   |
|  | Scaling       | Add partitions | Add queues     | Automatic      |   |
|  | Delivery      | At-least-once  | At-most-once   | At-least-once  |   |
|  |               | Exactly-once   | At-least-once  |                |   |
|  | Persistence   | Always (disk)  | Optional       | Always         |   |
|  | Managed       | Confluent/MSK  | CloudAMQP      | Native AWS     |   |
|  +---------------+----------------+----------------+----------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHEN TO USE KAFKA

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USE KAFKA WHEN:                                                        |
|                                                                         |
|  Y High throughput needed (100K+ messages/sec)                          |
|  Y Event replay is required (reprocess old events)                      |
|  Y Strict ordering within a key is needed                               |
|  Y Multiple consumers need the same data (pub-sub)                      |
|  Y Event sourcing / CQRS architecture                                   |
|  Y Real-time stream processing (Kafka Streams, Flink)                   |
|  Y Durable audit log / compliance requirement                           |
|  Y Decoupling microservices at scale                                    |
|                                                                         |
|  -------------------------------------------------------------------   |
|                                                                         |
|  DO NOT USE KAFKA WHEN:                                                 |
|                                                                         |
|  X Simple task queue (use RabbitMQ or SQS instead)                      |
|  X Very low latency pub-sub needed (use Redis Pub/Sub)                  |
|  X Small scale with < 1000 messages/sec (overkill)                      |
|  X Need complex routing (RabbitMQ has better exchange logic)            |
|  X Need message-level acknowledgment per consumer                       |
|  X Serverless / minimal ops wanted (SQS/SNS is simpler)                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.5: KAFKA ECOSYSTEM OVERVIEW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KAFKA ECOSYSTEM                                                        |
|                                                                         |
|  +---------------------------------------------------------------+     |
|  |                        KAFKA CORE                              |     |
|  |  Brokers / Topics / Partitions / Replication / Log Storage     |     |
|  +---------------------------------------------------------------+     |
|       |             |              |              |                     |
|       v             v              v              v                     |
|  +---------+  +-----------+  +-----------+  +------------+             |
|  | Kafka   |  | Kafka     |  | Schema    |  | Kafka      |             |
|  | Streams |  | Connect   |  | Registry  |  | REST Proxy |             |
|  |         |  |           |  |           |  |            |             |
|  | Stream  |  | Source:   |  | Avro /    |  | HTTP API   |             |
|  | process |  |  DB, File |  | Protobuf  |  | for non-   |             |
|  | library |  | Sink:     |  | JSON      |  | JVM apps   |             |
|  |         |  |  DB, S3,  |  | schema    |  |            |             |
|  |         |  |  Elastic  |  | evolution |  |            |             |
|  +---------+  +-----------+  +-----------+  +------------+             |
|                                                                         |
|  -------------------------------------------------------------------   |
|                                                                         |
|  MANAGED KAFKA OPTIONS:                                                 |
|  * Confluent Cloud     -- fully managed, from Kafka creators            |
|  * AWS MSK             -- Amazon Managed Streaming for Kafka            |
|  * Azure Event Hubs    -- Kafka-compatible protocol                     |
|  * Aiven for Kafka     -- multi-cloud managed                           |
|  * Redpanda            -- Kafka API compatible, no JVM                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.6: QUICK START EXAMPLE

```bash
# Download and start Kafka (using KRaft mode, no ZooKeeper)
# Download from https://kafka.apache.org/downloads

# Generate a cluster ID
KAFKA_CLUSTER_ID="$(bin/kafka-storage.sh random-uuid)"

# Format the storage
bin/kafka-storage.sh format -t $KAFKA_CLUSTER_ID \
    -c config/kraft/server.properties

# Start the broker
bin/kafka-server-start.sh config/kraft/server.properties
```

```bash
# Create a topic
bin/kafka-topics.sh --create \
    --topic my-first-topic \
    --bootstrap-server localhost:9092 \
    --partitions 3 \
    --replication-factor 1

# List topics
bin/kafka-topics.sh --list --bootstrap-server localhost:9092

# Describe a topic
bin/kafka-topics.sh --describe \
    --topic my-first-topic \
    --bootstrap-server localhost:9092
```

```bash
# Produce messages (interactive)
bin/kafka-console-producer.sh \
    --topic my-first-topic \
    --bootstrap-server localhost:9092
> Hello Kafka!
> This is my second message
> ^C

# Consume messages (from beginning)
bin/kafka-console-consumer.sh \
    --topic my-first-topic \
    --from-beginning \
    --bootstrap-server localhost:9092
```

```java
// Java Producer Example
Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("key.serializer",
    "org.apache.kafka.common.serialization.StringSerializer");
props.put("value.serializer",
    "org.apache.kafka.common.serialization.StringSerializer");

Producer<String, String> producer = new KafkaProducer<>(props);

producer.send(new ProducerRecord<>(
    "order-events",        // topic
    "order-123",           // key
    "{\"status\":\"created\"}" // value
));

producer.close();
```

```java
// Java Consumer Example
Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("group.id", "order-service");
props.put("key.deserializer",
    "org.apache.kafka.common.serialization.StringDeserializer");
props.put("value.deserializer",
    "org.apache.kafka.common.serialization.StringDeserializer");

Consumer<String, String> consumer = new KafkaConsumer<>(props);
consumer.subscribe(Arrays.asList("order-events"));

while (true) {
    ConsumerRecords<String, String> records =
        consumer.poll(Duration.ofMillis(100));
    for (ConsumerRecord<String, String> record : records) {
        System.out.printf("offset=%d, key=%s, value=%s%n",
            record.offset(), record.key(), record.value());
    }
}
```
