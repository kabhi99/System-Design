# CHAPTER 16: DISASTER RECOVERY AND CHANGE DATA CAPTURE
*Business Continuity and Real-Time Data Synchronization*

## SECTION 16.1: DISASTER RECOVERY (DR)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS DISASTER RECOVERY?                                            |
|                                                                         |
|  The ability to restore systems and data after a catastrophic         |
|  failure: natural disaster, cyberattack, hardware failure, or         |
|  human error.                                                          |
|                                                                         |
|  GOAL: Minimize downtime and data loss                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### KEY METRICS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RTO (Recovery Time Objective)                                         |
|  ==============================                                         |
|                                                                         |
|  Maximum acceptable time to restore service after disaster             |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Disaster                                Restored               |  |
|  |     |                                       |                   |  |
|  |     v                                       v                   |  |
|  |  ---●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━●---                  |  |
|  |     |<------------- RTO ----------------->|                   |  |
|  |                    (4 hours)                                    |  |
|  |                                                                 |  |
|  |  "We must be back online within 4 hours"                       |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  RPO (Recovery Point Objective)                                        |
|  ==============================                                         |
|                                                                         |
|  Maximum acceptable data loss measured in time                         |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Last Backup                    Disaster                        |  |
|  |      |                             |                            |  |
|  |      v                             v                            |  |
|  |  ---●━━━━━━━━━━━━━━━━━━━━━━━━━━━━●----                         |  |
|  |     |<--------- RPO ------------>|                             |  |
|  |               (1 hour)                                          |  |
|  |                                                                 |  |
|  |  "We can afford to lose up to 1 hour of data"                  |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  TYPICAL VALUES BY BUSINESS CRITICALITY:                               |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  System Type           RTO            RPO         Cost        |   |
|  |  ------------------------------------------------------------ |   |
|  |                                                                |   |
|  |  Critical (banking)    Minutes        Zero        $$$$       |   |
|  |  High (e-commerce)     < 1 hour       < 1 hour    $$$        |   |
|  |  Medium (internal)     4-8 hours      4 hours     $$         |   |
|  |  Low (dev/test)        24-48 hours    24 hours    $          |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DISASTER RECOVERY STRATEGIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STRATEGY 1: BACKUP AND RESTORE                                        |
|  ===============================                                        |
|                                                                         |
|  Simplest: Periodic backups, restore when needed                       |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Primary Region              Backup Storage                    |  |
|  |  +---------------+          +---------------+                 |  |
|  |  |   Database    |--backup-->|     S3       |                 |  |
|  |  |               | (nightly) |   (cold)     |                 |  |
|  |  +---------------+          +---------------+                 |  |
|  |                                                                 |  |
|  |  On disaster:                                                  |  |
|  |  1. Provision new infrastructure                              |  |
|  |  2. Restore from backup                                       |  |
|  |  3. Start services                                            |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  RTO: Hours to days                                                    |
|  RPO: Last backup (hours to 24 hours)                                 |
|  COST: $ (lowest)                                                      |
|  USE: Non-critical systems, dev/test                                  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  STRATEGY 2: PILOT LIGHT                                               |
|  ========================                                               |
|                                                                         |
|  Minimal version of environment always running in DR site             |
|  Core services (DB) replicated, others started on demand              |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Primary Region              DR Region                         |  |
|  |  +---------------+          +---------------+                 |  |
|  |  | App Servers   |          |    (OFF)      |  <- Start on    |  |
|  |  | (running)     |          |               |    demand      |  |
|  |  +---------------+          +---------------+                 |  |
|  |  +---------------+          +---------------+                 |  |
|  |  |   Database    |--sync--->|   Database    |  <- Always      |  |
|  |  |   (primary)   |          |   (standby)   |    synced      |  |
|  |  +---------------+          +---------------+                 |  |
|  |                                                                 |  |
|  |  On disaster:                                                  |  |
|  |  1. Scale up DR database                                      |  |
|  |  2. Start app servers                                         |  |
|  |  3. Update DNS                                                |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  RTO: 10 minutes to hours                                              |
|  RPO: Minutes (last sync)                                              |
|  COST: $$ (always-on DB)                                               |
|  USE: Important systems with moderate RTO                             |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  STRATEGY 3: WARM STANDBY                                              |
|  =========================                                              |
|                                                                         |
|  Scaled-down but fully functional version in DR site                   |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Primary Region              DR Region                         |  |
|  |  +---------------+          +---------------+                 |  |
|  |  | 10 App        |          | 2 App         |  <- Running     |  |
|  |  | Servers       |          | Servers       |    (scaled down)|  |
|  |  +---------------+          +---------------+                 |  |
|  |  +---------------+          +---------------+                 |  |
|  |  |   Database    |--sync--->|   Database    |  <- Synced      |  |
|  |  |   (primary)   |          |   (replica)   |                 |  |
|  |  +---------------+          +---------------+                 |  |
|  |                                                                 |  |
|  |  On disaster:                                                  |  |
|  |  1. Scale up DR environment                                   |  |
|  |  2. Promote DB replica                                        |  |
|  |  3. Update DNS                                                |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  RTO: Minutes                                                          |
|  RPO: Seconds to minutes                                               |
|  COST: $$$ (always running, smaller)                                   |
|  USE: Business-critical systems                                        |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  STRATEGY 4: HOT STANDBY / ACTIVE-ACTIVE                               |
|  ========================================                               |
|                                                                         |
|  Full capacity in both sites, traffic split                            |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |              +------------------------+                        |  |
|  |              |    Global Load Balancer |                       |  |
|  |              |         (GSLB)          |                       |  |
|  |              +-----------+------------+                        |  |
|  |                   50%    |    50%                              |  |
|  |              +-----------+-----------+                         |  |
|  |              v                       v                         |  |
|  |  +-------------------+  +-------------------+                 |  |
|  |  |   Region A        |  |   Region B        |                 |  |
|  |  |   (full scale)    |  |   (full scale)    |                 |  |
|  |  |   +-----------+   |  |   +-----------+   |                 |  |
|  |  |   | App (10)  |   |  |   | App (10)  |   |                 |  |
|  |  |   +-----------+   |  |   +-----------+   |                 |  |
|  |  |   +-----------+   |  |   +-----------+   |                 |  |
|  |  |   | Database  |<-sync-->| Database  |   |                 |  |
|  |  |   +-----------+   |  |   +-----------+   |                 |  |
|  |  +-------------------+  +-------------------+                 |  |
|  |                                                                 |  |
|  |  On disaster:                                                  |  |
|  |  1. GSLB routes 100% to healthy region                        |  |
|  |  2. Automatic failover                                        |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  RTO: Seconds (automatic)                                              |
|  RPO: Zero (synchronous replication) or seconds (async)               |
|  COST: $$$$ (2x infrastructure)                                        |
|  USE: Mission-critical, zero-downtime requirements                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DR STRATEGIES COMPARISON

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  Strategy         RTO          RPO        Cost     Complexity |   |
|  |  ------------------------------------------------------------ |   |
|  |                                                                |   |
|  |  Backup/Restore   Hours-Days   Hours      $        Low        |   |
|  |                                                                |   |
|  |  Pilot Light      10min-Hours  Minutes    $$       Medium     |   |
|  |                                                                |   |
|  |  Warm Standby     Minutes      Seconds    $$$      Medium     |   |
|  |                                                                |   |
|  |  Hot/Active       Seconds      Zero       $$$$     High       |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
|                                                                         |
|              RTO/RPO                                                    |
|                 ^                                                       |
|        Best     |    +--------------+                                  |
|                 |    | Hot Standby  |                                  |
|                 |    +--------------+                                  |
|                 |         +--------------+                             |
|                 |         |Warm Standby  |                             |
|                 |         +--------------+                             |
|                 |              +--------------+                        |
|                 |              | Pilot Light  |                        |
|                 |              +--------------+                        |
|                 |                   +--------------+                   |
|        Worst    |                   |Backup/Restore|                  |
|                 +------------------------------------------->          |
|                 Low                               High   COST          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DR BEST PRACTICES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. REGULAR TESTING                                                    |
|     * Run DR drills quarterly                                         |
|     * Chaos engineering (simulate failures)                           |
|     * Document and improve runbooks                                   |
|                                                                         |
|  2. AUTOMATE EVERYTHING                                                |
|     * Infrastructure as Code (Terraform)                              |
|     * Automated failover scripts                                      |
|     * Automated backup verification                                   |
|                                                                         |
|  3. GEOGRAPHIC SEPARATION                                              |
|     * DR site in different region                                     |
|     * Consider different cloud provider                               |
|     * Avoid shared dependencies                                       |
|                                                                         |
|  4. DATA PROTECTION                                                    |
|     * 3-2-1 Rule: 3 copies, 2 media types, 1 offsite                 |
|     * Encrypt backups                                                 |
|     * Test restore regularly                                          |
|                                                                         |
|  5. DOCUMENTATION                                                      |
|     * Runbooks for all scenarios                                      |
|     * Contact lists                                                   |
|     * Decision trees                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 16.2: CHANGE DATA CAPTURE (CDC)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS CDC?                                                          |
|                                                                         |
|  A technique to capture and propagate data changes from a database    |
|  to other systems in real-time.                                       |
|                                                                         |
|  Instead of: Polling database every N minutes                         |
|  CDC does: Stream every INSERT, UPDATE, DELETE as it happens          |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  TRADITIONAL APPROACH (Polling/Batch):                         |  |
|  |                                                                 |  |
|  |  Database ---- Query every 5 min ----> ETL ----> Data Warehouse|  |
|  |                (scan entire table)                              |  |
|  |                                                                 |  |
|  |  Problems:                                                      |  |
|  |  * High latency (5+ minutes)                                   |  |
|  |  * Expensive queries                                           |  |
|  |  * Misses intermediate changes                                 |  |
|  |  * Can't capture deletes easily                                |  |
|  |                                                                 |  |
|  |  ------------------------------------------------------------  |  |
|  |                                                                 |  |
|  |  CDC APPROACH:                                                  |  |
|  |                                                                 |  |
|  |  Database ---- Stream changes ----> Kafka ----> Consumers      |  |
|  |           (from transaction log)                                |  |
|  |                                                                 |  |
|  |  Benefits:                                                      |  |
|  |  * Real-time (milliseconds)                                    |  |
|  |  * Low overhead                                                 |  |
|  |  * Captures all changes                                        |  |
|  |  * Preserves order                                             |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CDC METHODS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  METHOD 1: TIMESTAMP-BASED (Polling)                                   |
|  ===================================                                    |
|                                                                         |
|  Query rows where updated_at > last_sync_time                          |
|                                                                         |
|  SELECT * FROM orders WHERE updated_at > '2024-01-15 10:00:00'        |
|                                                                         |
|  PROS: Simple, works with any database                                |
|  CONS: Misses deletes, requires timestamp column, polling overhead   |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  METHOD 2: TRIGGER-BASED                                               |
|  =======================                                                |
|                                                                         |
|  Database triggers write changes to a changelog table                  |
|                                                                         |
|  CREATE TRIGGER order_changes AFTER INSERT OR UPDATE OR DELETE        |
|  ON orders FOR EACH ROW                                                |
|  INSERT INTO order_changelog (operation, data, timestamp) VALUES ...  |
|                                                                         |
|  PROS: Captures all operations including deletes                      |
|  CONS: Performance impact, trigger maintenance                        |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  METHOD 3: LOG-BASED (Recommended)                                     |
|  ==================================                                     |
|                                                                         |
|  Read database transaction log (WAL/binlog/redo log)                  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  +---------------+                                             |  |
|  |  |   Database    |                                             |  |
|  |  |               |                                             |  |
|  |  |  +---------+  |     +-------------+     +-------------+    |  |
|  |  |  | WAL/    |------>|  Debezium/  |---->|   Kafka     |    |  |
|  |  |  | Binlog  |  |    |  CDC Tool   |     |             |    |  |
|  |  |  +---------+  |     +-------------+     +-------------+    |  |
|  |  +---------------+                               |             |  |
|  |                                                  |             |  |
|  |                    +----------------------------++             |  |
|  |                    v              v             v              |  |
|  |               +--------+    +--------+    +--------+          |  |
|  |               |Search  |    |Cache   |    |Data    |          |  |
|  |               |(Elastic|    |(Redis) |    |Warehouse|         |  |
|  |               +--------+    +--------+    +--------+          |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  PROS: No application changes, low overhead, complete & ordered      |
|  CONS: Database-specific, complex setup                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### POPULAR CDC TOOLS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DEBEZIUM (Most Popular)                                               |
|  =======================                                                |
|                                                                         |
|  Open-source, distributed CDC platform                                 |
|  Runs on Kafka Connect                                                 |
|                                                                         |
|  Supports:                                                              |
|  * MySQL (binlog)                                                      |
|  * PostgreSQL (logical replication)                                    |
|  * MongoDB (oplog)                                                     |
|  * SQL Server                                                          |
|  * Oracle                                                              |
|  * Cassandra                                                           |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Debezium Event Format:                                        |  |
|  |                                                                 |  |
|  |  {                                                              |  |
|  |    "before": { "id": 1, "name": "Old Name" },                 |  |
|  |    "after": { "id": 1, "name": "New Name" },                  |  |
|  |    "source": {                                                 |  |
|  |      "version": "1.9.0",                                      |  |
|  |      "connector": "mysql",                                    |  |
|  |      "name": "mydb",                                          |  |
|  |      "ts_ms": 1705000000000,                                  |  |
|  |      "db": "inventory",                                       |  |
|  |      "table": "customers"                                     |  |
|  |    },                                                          |  |
|  |    "op": "u",  // c=create, u=update, d=delete, r=read       |  |
|  |    "ts_ms": 1705000000123                                     |  |
|  |  }                                                             |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  OTHER CDC TOOLS                                                       |
|  ================                                                       |
|                                                                         |
|  * AWS DMS: Managed database migration with CDC                       |
|  * Maxwell: MySQL binlog -> Kafka (simpler than Debezium)             |
|  * GoldenGate: Oracle's enterprise CDC solution                       |
|  * Airbyte: Data integration with CDC connectors                      |
|  * Fivetran: Managed ELT with CDC                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CDC USE CASES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. CACHE INVALIDATION                                                 |
|  =====================                                                  |
|                                                                         |
|  Database --CDC--> Kafka --> Cache Service --> Invalidate Redis       |
|                                                                         |
|  When product price changes in DB, automatically update cache         |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. SEARCH INDEX SYNC                                                  |
|  ====================                                                   |
|                                                                         |
|  Database --CDC--> Kafka --> Elasticsearch Indexer                    |
|                                                                         |
|  Keep search index in sync with database in real-time                 |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. DATA WAREHOUSE / ANALYTICS                                         |
|  ============================                                           |
|                                                                         |
|  Database --CDC--> Kafka --> Snowflake/BigQuery                       |
|                                                                         |
|  Real-time analytics instead of nightly batch ETL                     |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. MICROSERVICES DATA SYNC                                            |
|  ===========================                                            |
|                                                                         |
|  Service A DB --CDC--> Kafka --> Service B                            |
|                                                                         |
|  Sync data between services without tight coupling                    |
|  Implement Outbox Pattern reliably                                     |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  5. AUDIT LOGGING                                                      |
|  ================                                                       |
|                                                                         |
|  Database --CDC--> Audit Log Storage                                  |
|                                                                         |
|  Complete history of all data changes for compliance                  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  6. DATABASE REPLICATION                                               |
|  =======================                                                |
|                                                                         |
|  Source DB --CDC--> Target DB (different vendor)                      |
|                                                                         |
|  Migrate from MySQL to PostgreSQL with zero downtime                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CDC ARCHITECTURE PATTERN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TYPICAL CDC ARCHITECTURE                                              |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  +---------------+                                             |  |
|  |  |  Application  |                                             |  |
|  |  |    Server     |                                             |  |
|  |  +-------+-------+                                             |  |
|  |          | writes                                               |  |
|  |          v                                                      |  |
|  |  +---------------+     +---------------+     +-------------+  |  |
|  |  |   Database    |---->|   Debezium    |---->|    Kafka    |  |  |
|  |  |   (MySQL)     | WAL |  Connector    |     |             |  |  |
|  |  +---------------+     +---------------+     +------+------+  |  |
|  |                                                      |         |  |
|  |                                               +------+------+  |  |
|  |                                               |             |  |  |
|  |  +--------------------------------------------+-------------+--+  |
|  |  |                                            |             |     |
|  |  v                    v                       v             v     |
|  |  +-----------+  +-----------+  +-----------+  +-----------+     |
|  |  |Elastic    |  |Redis      |  |Snowflake  |  |Audit      |     |
|  |  |Search     |  |Cache      |  |Warehouse  |  |Service    |     |
|  |  +-----------+  +-----------+  +-----------+  +-----------+     |
|  |                                                                 |  |
|  |  Each consumer processes changes independently                 |  |
|  |  Kafka provides durability and replay capability              |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CDC CHALLENGES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHALLENGE 1: SCHEMA EVOLUTION                                         |
|  * New columns added, columns renamed/dropped                         |
|  * Solution: Schema registry (Avro with Confluent Schema Registry)   |
|                                                                         |
|  CHALLENGE 2: ORDERING                                                 |
|  * Changes must be applied in order                                   |
|  * Solution: Kafka partitioning by key                               |
|                                                                         |
|  CHALLENGE 3: INITIAL SNAPSHOT                                         |
|  * How to sync existing data before CDC starts?                       |
|  * Solution: Debezium snapshot mode                                   |
|                                                                         |
|  CHALLENGE 4: EXACTLY-ONCE DELIVERY                                    |
|  * Consumer might crash mid-processing                                |
|  * Solution: Idempotent consumers, transactional outbox              |
|                                                                         |
|  CHALLENGE 5: LAG MONITORING                                           |
|  * CDC falling behind database changes                                |
|  * Solution: Monitor consumer lag, alert on threshold                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## QUICK REFERENCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DISASTER RECOVERY                                                      |
|  ================                                                       |
|                                                                         |
|  RTO = Max time to restore service                                    |
|  RPO = Max acceptable data loss                                       |
|                                                                         |
|  Strategies (cost ^, RTO/RPO v):                                      |
|  Backup -> Pilot Light -> Warm Standby -> Hot/Active-Active             |
|                                                                         |
|  CDC (Change Data Capture)                                             |
|  =========================                                              |
|                                                                         |
|  Captures database changes in real-time                               |
|  Methods: Timestamp, Triggers, Log-based (best)                       |
|  Tool: Debezium + Kafka (industry standard)                           |
|                                                                         |
|  Use cases: Cache sync, search indexing, analytics, audit            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 16

