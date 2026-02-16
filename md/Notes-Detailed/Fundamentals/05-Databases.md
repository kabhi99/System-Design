# CHAPTER 5: DATABASES
*Choosing and Designing Data Storage Systems*

Every system needs to store data. Understanding database fundamentals,
trade-offs between SQL and NoSQL, and when to use each is essential
for system design.

## SECTION 5.1: RELATIONAL DATABASES (SQL)

### WHAT ARE RELATIONAL DATABASES?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RELATIONAL DATABASE FUNDAMENTALS                                      |
|                                                                         |
|  Data is organized into TABLES (relations) with:                       |
|  * Rows (records/tuples)                                               |
|  * Columns (fields/attributes)                                        |
|  * Primary keys (unique identifier)                                   |
|  * Foreign keys (relationships between tables)                        |
|                                                                         |
|  EXAMPLE: E-Commerce Database                                          |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |  USERS TABLE                                                    |  |
|  |  +---------+-----------+-------------------------------------+ |  |
|  |  | user_id |   name    |            email                    | |  |
|  |  +---------+-----------+-------------------------------------+ |  |
|  |  |    1    |   Alice   |       alice@example.com             | |  |
|  |  |    2    |    Bob    |        bob@example.com              | |  |
|  |  +---------+-----------+-------------------------------------+ |  |
|  |       ^ Primary Key                                            |  |
|  +-----------------------------------------------------------------+  |
|                            |                                           |
|                            | Relationship (Foreign Key)                |
|                            v                                           |
|  +-----------------------------------------------------------------+  |
|  |  ORDERS TABLE                                                   |  |
|  |  +----------+---------+------------+---------------+           |  |
|  |  | order_id | user_id |   total    |  created_at   |           |  |
|  |  +----------+---------+------------+---------------+           |  |
|  |  |   101    |    1    |   $99.99   |  2024-01-15   |           |  |
|  |  |   102    |    1    |   $45.00   |  2024-01-16   |           |  |
|  |  |   103    |    2    |  $199.99   |  2024-01-16   |           |  |
|  |  +----------+---------+------------+---------------+           |  |
|  |                 ^ Foreign Key                                   |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  EXAMPLES: PostgreSQL, MySQL, Oracle, SQL Server, SQLite              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ACID PROPERTIES

Relational databases guarantee ACID properties for transactions:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ACID TRANSACTIONS                                                     |
|                                                                         |
|  A - ATOMICITY                                                         |
|  -------------                                                          |
|  A transaction is all-or-nothing. If any part fails, the entire       |
|  transaction is rolled back.                                           |
|                                                                         |
|  BEGIN TRANSACTION;                                                    |
|    UPDATE accounts SET balance = balance - 100 WHERE id = 1;          |
|    UPDATE accounts SET balance = balance + 100 WHERE id = 2;          |
|  COMMIT;                                                               |
|                                                                         |
|  If second UPDATE fails -> first UPDATE is also rolled back           |
|                                                                         |
|  IMPLEMENTATION: Write-Ahead Log (WAL)                                |
|  Changes logged before applying. On crash, replay or rollback log.   |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  C - CONSISTENCY                                                       |
|  ---------------                                                        |
|  Database moves from one valid state to another. Constraints           |
|  (foreign keys, unique, check) are always satisfied.                  |
|                                                                         |
|  INSERT INTO orders (user_id, total) VALUES (999, 100);               |
|  -> FAILS if user_id 999 doesn't exist (foreign key constraint)       |
|                                                                         |
|  TYPES OF CONSTRAINTS:                                                 |
|  * PRIMARY KEY: Unique, non-null identifier                          |
|  * FOREIGN KEY: References another table's primary key               |
|  * UNIQUE: No duplicate values                                       |
|  * CHECK: Custom validation (e.g., age >= 0)                        |
|  * NOT NULL: Must have a value                                       |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  I - ISOLATION                                                         |
|  -------------                                                          |
|  Concurrent transactions don't interfere with each other.             |
|  Each transaction sees a consistent snapshot.                          |
|                                                                         |
|  Transaction A: Reading user balance                                  |
|  Transaction B: Updating user balance                                 |
|  -> A sees consistent balance (before or after B, not partial)        |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  D - DURABILITY                                                        |
|  -------------                                                          |
|  Once committed, data survives crashes. Written to disk.              |
|                                                                         |
|  COMMIT succeeds -> Data is on disk -> Survives power failure          |
|                                                                         |
|  IMPLEMENTATION: fsync() after WAL writes, checkpointing             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.2: ISOLATION LEVELS (DEEP DIVE)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ISOLATION LEVELS AND ANOMALIES                                       |
|                                                                         |
|  ANOMALIES (Problems without proper isolation)                        |
|  -----------------------------------------------                        |
|                                                                         |
|  1. DIRTY READ                                                         |
|     Reading uncommitted changes from another transaction              |
|                                                                         |
|     Txn A: UPDATE balance = 100 (not committed)                       |
|     Txn B: SELECT balance -> sees 100                                  |
|     Txn A: ROLLBACK                                                    |
|     -> B read data that never existed!                                 |
|                                                                         |
|  2. NON-REPEATABLE READ                                                |
|     Same query returns different values within transaction            |
|                                                                         |
|     Txn A: SELECT balance -> 100                                       |
|     Txn B: UPDATE balance = 200, COMMIT                               |
|     Txn A: SELECT balance -> 200 (different!)                          |
|                                                                         |
|  3. PHANTOM READ                                                       |
|     New rows appear in repeated query                                 |
|                                                                         |
|     Txn A: SELECT * WHERE age > 18 -> 100 rows                        |
|     Txn B: INSERT row with age = 25, COMMIT                          |
|     Txn A: SELECT * WHERE age > 18 -> 101 rows (phantom!)             |
|                                                                         |
|  4. LOST UPDATE                                                        |
|     Two transactions overwrite each other                             |
|                                                                         |
|     Txn A: Read balance = 100                                         |
|     Txn B: Read balance = 100                                         |
|     Txn A: Write balance = 150 (+50)                                  |
|     Txn B: Write balance = 130 (+30)                                  |
|     -> A's update is lost! Final = 130, should be 180                 |
|                                                                         |
|  5. WRITE SKEW                                                         |
|     Two transactions read same data, make decisions, write different |
|                                                                         |
|     Rule: At least 1 doctor must be on-call                          |
|     Txn A: 2 doctors on-call, remove self (1 left) -> OK              |
|     Txn B: 2 doctors on-call, remove self (1 left) -> OK              |
|     -> Both commit: 0 doctors on-call! (constraint violated)          |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  ISOLATION LEVELS (SQL Standard)                                      |
|  ---------------------------------                                      |
|                                                                         |
|  +-----------------+---------+----------------+---------+-----------+|
|  | Level           | Dirty   | Non-Repeatable | Phantom | Lost      ||
|  |                 | Read    | Read           | Read    | Update    ||
|  +-----------------+---------+----------------+---------+-----------+|
|  | Read Uncommitted| Possible| Possible       | Possible| Possible  ||
|  | Read Committed  | Prevented| Possible      | Possible| Possible  ||
|  | Repeatable Read | Prevented| Prevented     | Possible| Prevented ||
|  | Serializable    | Prevented| Prevented     |Prevented| Prevented ||
|  +-----------------+---------+----------------+---------+-----------+|
|                                                                         |
|  READ UNCOMMITTED                                                      |
|  --------------------                                                   |
|  * See uncommitted changes                                            |
|  * Almost never used (data corruption)                                |
|  * Use case: None in production                                       |
|                                                                         |
|  READ COMMITTED (Default in PostgreSQL, Oracle)                       |
|  -------------------------------------------------                      |
|  * See only committed changes                                         |
|  * Most common in production                                          |
|  * Good balance of consistency and performance                       |
|                                                                         |
|  REPEATABLE READ (Default in MySQL)                                   |
|  -------------------------------------                                  |
|  * Transaction sees snapshot at start                                 |
|  * Same query returns same results                                   |
|  * Still allows phantom reads (new rows)                             |
|                                                                         |
|  SERIALIZABLE                                                          |
|  --------------                                                         |
|  * Transactions execute as if sequential                             |
|  * No anomalies possible                                              |
|  * Highest overhead, lowest throughput                               |
|  * Use for: Financial transactions, critical operations             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.3: LOCKING AND CONCURRENCY CONTROL

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONCURRENCY CONTROL STRATEGIES                                       |
|                                                                         |
|  1. PESSIMISTIC LOCKING                                               |
|  ========================                                               |
|  Lock data before reading/writing. Assume conflicts are common.       |
|                                                                         |
|  SELECT * FROM inventory WHERE id = 1 FOR UPDATE;                    |
|  -- Row is locked, other transactions wait                           |
|  UPDATE inventory SET quantity = quantity - 1 WHERE id = 1;          |
|  COMMIT;                                                               |
|  -- Lock released                                                     |
|                                                                         |
|  LOCK TYPES:                                                           |
|  +---------------------------------------------------------------+   |
|  | Shared Lock (S)      | Multiple readers allowed              |   |
|  | Exclusive Lock (X)   | Only one writer, no readers           |   |
|  | Intent Shared (IS)   | Intend to get S lock on child        |   |
|  | Intent Exclusive (IX)| Intend to get X lock on child        |   |
|  +---------------------------------------------------------------+   |
|                                                                         |
|  LOCK GRANULARITY:                                                     |
|  * Row-level: Highest concurrency, most overhead                     |
|  * Page-level: Medium concurrency                                    |
|  * Table-level: Lowest concurrency, least overhead                   |
|                                                                         |
|  PROS: Prevents conflicts                                             |
|  CONS: Deadlocks possible, reduces throughput                        |
|                                                                         |
|  DEADLOCK:                                                             |
|  Txn A: Lock row 1, waiting for row 2                                |
|  Txn B: Lock row 2, waiting for row 1                                |
|  -> Both waiting forever!                                              |
|                                                                         |
|  SOLUTION: Database detects and kills one transaction               |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. OPTIMISTIC LOCKING (Optimistic Concurrency Control)              |
|  =======================================================               |
|  Don't lock upfront. Check for conflicts at commit time.             |
|                                                                         |
|  APPROACH 1: VERSION NUMBER                                           |
|                                                                         |
|  CREATE TABLE inventory (                                              |
|    id INT PRIMARY KEY,                                                |
|    quantity INT,                                                       |
|    version INT DEFAULT 0                                              |
|  );                                                                     |
|                                                                         |
|  -- Read (remember version)                                           |
|  SELECT quantity, version FROM inventory WHERE id = 1;               |
|  -- Returns: quantity=10, version=5                                  |
|                                                                         |
|  -- Update (check version)                                            |
|  UPDATE inventory                                                      |
|  SET quantity = 9, version = version + 1                             |
|  WHERE id = 1 AND version = 5;                                       |
|                                                                         |
|  -- If 0 rows affected -> someone else modified!                      |
|  -- Retry the operation                                               |
|                                                                         |
|  APPROACH 2: TIMESTAMP                                                 |
|  Same concept, use updated_at timestamp instead of version           |
|                                                                         |
|  PROS: High concurrency, no deadlocks                                |
|  CONS: Retries on conflicts, wasted work                             |
|                                                                         |
|  USE WHEN: Conflicts are rare (most reads, few writes)              |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. MVCC (Multi-Version Concurrency Control)                         |
|  ============================================                           |
|  Keep multiple versions of each row. Readers see consistent snapshot.|
|                                                                         |
|  HOW IT WORKS:                                                         |
|  +---------------------------------------------------------------+   |
|  | Each row has:                                                  |   |
|  | * xmin: Transaction ID that created this version              |   |
|  | * xmax: Transaction ID that deleted/updated (created new)     |   |
|  |                                                                 |   |
|  | Row versions:                                                   |   |
|  | +---------------------------------------------------------+   |   |
|  | | Version 1 | data="Alice" | xmin=100 | xmax=150        |   |   |
|  | | Version 2 | data="Alicia" | xmin=150 | xmax=∞         |   |   |
|  | +---------------------------------------------------------+   |   |
|  |                                                                 |   |
|  | Transaction 120 sees Version 1 (120 > 100, 120 < 150)        |   |
|  | Transaction 200 sees Version 2 (200 > 150)                    |   |
|  +---------------------------------------------------------------+   |
|                                                                         |
|  BENEFITS:                                                             |
|  * Readers never block writers                                       |
|  * Writers never block readers                                       |
|  * Consistent snapshots without locks                                |
|                                                                         |
|  COST:                                                                 |
|  * Storage overhead (multiple versions)                              |
|  * Need VACUUM/garbage collection for old versions                   |
|                                                                         |
|  USED BY: PostgreSQL, MySQL InnoDB, Oracle                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.4: NOSQL DATABASES

NoSQL databases sacrifice some SQL features for scale and flexibility.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NOSQL DATABASE TYPES                                                  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  1. KEY-VALUE STORES                                           |  |
|  |  ---------------------                                          |  |
|  |  Simple key -> value mapping. O(1) lookups.                     |  |
|  |                                                                 |  |
|  |  Examples: Redis, DynamoDB, Riak, Memcached                   |  |
|  |                                                                 |  |
|  |  "user:123" -> { "name": "Alice", "email": "alice@ex.com" }    |  |
|  |  "session:abc" -> { "userId": 123, "expires": "..." }          |  |
|  |                                                                 |  |
|  |  OPERATIONS: GET, SET, DELETE, EXISTS                         |  |
|  |  DATA MODEL: Opaque blobs (value not inspected)               |  |
|  |                                                                 |  |
|  |  USE FOR:                                                      |  |
|  |  * Caching (sessions, page fragments)                         |  |
|  |  * Simple lookups by ID                                       |  |
|  |  * Rate limiting (counter per IP)                             |  |
|  |  * Feature flags                                               |  |
|  |                                                                 |  |
|  |  NOT FOR:                                                      |  |
|  |  * Complex queries                                             |  |
|  |  * Relationships between entities                             |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  2. DOCUMENT STORES                                            |  |
|  |  ----------------------                                         |  |
|  |  Store semi-structured documents (JSON/BSON)                   |  |
|  |  Can query by any field, index nested fields                  |  |
|  |                                                                 |  |
|  |  Examples: MongoDB, CouchDB, Firestore, Elasticsearch         |  |
|  |                                                                 |  |
|  |  {                                                              |  |
|  |    "_id": "order_123",                                         |  |
|  |    "user": { "id": 1, "name": "Alice" },                      |  |
|  |    "items": [                                                   |  |
|  |      { "product": "Widget", "qty": 2, "price": 10.00 },       |  |
|  |      { "product": "Gadget", "qty": 1, "price": 25.00 }        |  |
|  |    ],                                                           |  |
|  |    "total": 45.00,                                              |  |
|  |    "shipping": {                                                |  |
|  |      "address": "123 Main St",                                 |  |
|  |      "city": "NYC"                                             |  |
|  |    }                                                            |  |
|  |  }                                                              |  |
|  |                                                                 |  |
|  |  QUERIES:                                                       |  |
|  |  db.orders.find({ "user.id": 1 })                             |  |
|  |  db.orders.find({ "items.product": "Widget" })                |  |
|  |  db.orders.find({ "total": { "$gt": 100 } })                  |  |
|  |                                                                 |  |
|  |  USE FOR:                                                      |  |
|  |  * Content management (blogs, articles)                       |  |
|  |  * Product catalogs (varying attributes)                      |  |
|  |  * User profiles                                               |  |
|  |  * Event logging                                               |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  3. WIDE-COLUMN STORES                                         |  |
|  |  -------------------------                                      |  |
|  |  Tables with dynamic columns, column families                 |  |
|  |  Optimized for queries on large datasets                      |  |
|  |                                                                 |  |
|  |  Examples: Cassandra, HBase, BigTable, ScyllaDB               |  |
|  |                                                                 |  |
|  |  DATA MODEL:                                                    |  |
|  |  Row Key    | Column Families                                  |  |
|  |  ------------------------------------------                    |  |
|  |  user:123   | profile:name="Alice" | profile:email="..."      |  |
|  |             | orders:1="..." | orders:2="..."                 |  |
|  |                                                                 |  |
|  |  FEATURES:                                                      |  |
|  |  * Each row can have different columns                        |  |
|  |  * Columns sorted within row (fast range scans)               |  |
|  |  * Write optimized (LSM trees)                                |  |
|  |                                                                 |  |
|  |  USE FOR:                                                      |  |
|  |  * Time-series data (metrics, IoT sensors)                    |  |
|  |  * Event logging at scale                                     |  |
|  |  * Analytical workloads                                       |  |
|  |  * Write-heavy applications                                   |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  4. GRAPH DATABASES                                            |  |
|  |  ----------------------                                         |  |
|  |  Store nodes and relationships                                 |  |
|  |  Optimized for traversing connections                         |  |
|  |                                                                 |  |
|  |  Examples: Neo4j, Amazon Neptune, JanusGraph, TigerGraph      |  |
|  |                                                                 |  |
|  |  DATA MODEL:                                                    |  |
|  |       +-------+                                                |  |
|  |       | Alice | --- FRIENDS_WITH --> +-------+                |  |
|  |       +-------+                       |  Bob  |                |  |
|  |           |                           +---+---+                |  |
|  |      WORKS_AT                         WORKS_AT                 |  |
|  |           |                               |                    |  |
|  |           v                               v                    |  |
|  |    +--------------+               +--------------+            |  |
|  |    |   Google     |               |   Amazon     |            |  |
|  |    +--------------+               +--------------+            |  |
|  |                                                                 |  |
|  |  QUERY (Cypher - Neo4j):                                       |  |
|  |  MATCH (a:Person)-[:FRIENDS_WITH*1..3]-(b:Person)             |  |
|  |  WHERE a.name = 'Alice'                                       |  |
|  |  RETURN b.name                                                 |  |
|  |  -- Find friends within 3 hops of Alice                       |  |
|  |                                                                 |  |
|  |  USE FOR:                                                      |  |
|  |  * Social networks (friends, followers)                       |  |
|  |  * Recommendation engines                                     |  |
|  |  * Fraud detection (connection patterns)                      |  |
|  |  * Knowledge graphs                                            |  |
|  |  * Network/infrastructure management                          |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  5. TIME-SERIES DATABASES                                      |  |
|  |  -----------------------------                                  |  |
|  |  Optimized for timestamped data                                |  |
|  |                                                                 |  |
|  |  Examples: InfluxDB, TimescaleDB, Prometheus, QuestDB         |  |
|  |                                                                 |  |
|  |  FEATURES:                                                      |  |
|  |  * Automatic time-based partitioning                          |  |
|  |  * Compression optimized for time-series                      |  |
|  |  * Built-in downsampling and retention policies              |  |
|  |  * Time-based aggregation functions                           |  |
|  |                                                                 |  |
|  |  USE FOR:                                                      |  |
|  |  * Infrastructure monitoring (CPU, memory, disk)              |  |
|  |  * Application metrics                                        |  |
|  |  * IoT sensor data                                            |  |
|  |  * Financial tick data                                        |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.5: DATABASE INTERNALS - HOW NOSQL DATABASES WORK

Understanding internal data structures helps you make better design decisions.

### LSM TREE (Log-Structured Merge Tree)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LSM TREE - Used by DynamoDB, Cassandra, RocksDB, LevelDB, HBase     |
|                                                                         |
|  Optimized for WRITE-HEAVY workloads (100x faster writes than B-tree)|
|                                                                         |
|  KEY INSIGHT:                                                          |
|  * Sequential writes are 100x faster than random writes              |
|  * So buffer writes in memory, flush sequentially to disk            |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  LSM TREE ARCHITECTURE                                                |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |     MEMORY                                                      |  |
|  |  +---------------------------------------------------------+   |  |
|  |  |              MEMTABLE (Sorted in memory)                |   |  |
|  |  |                                                         |   |  |
|  |  |   Writes go here first (Red-Black Tree or Skip List)   |   |  |
|  |  |   +---+---+---+---+---+---+---+---+                   |   |  |
|  |  |   | A | B | D | F | G | K | M | Z |  (sorted)        |   |  |
|  |  |   +---+---+---+---+---+---+---+---+                   |   |  |
|  |  |                                                         |   |  |
|  |  |   When full (e.g., 64MB) -> flush to disk as SSTable    |   |  |
|  |  +---------------------------------------------------------+   |  |
|  |                          |                                      |  |
|  |                          | Flush (sequential write)            |  |
|  |                          v                                      |  |
|  |     DISK (SSTables - Sorted String Tables)                     |  |
|  |  +---------------------------------------------------------+   |  |
|  |  |  Level 0:  [SSTable1] [SSTable2] [SSTable3]            |   |  |
|  |  |            (may overlap)                                |   |  |
|  |  |                     |                                   |   |  |
|  |  |                     | Compaction                        |   |  |
|  |  |                     v                                   |   |  |
|  |  |  Level 1:  [    SSTable - larger, sorted, no overlap  ]|   |  |
|  |  |                     |                                   |   |  |
|  |  |                     v                                   |   |  |
|  |  |  Level 2:  [        Even larger SSTables              ]|   |  |
|  |  |                                                         |   |  |
|  |  |  Each level is 10x larger than previous                |   |  |
|  |  +---------------------------------------------------------+   |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  WRITE PATH                                                            |
|                                                                         |
|  1. Write to WAL (Write-Ahead Log) - durability                      |
|  2. Write to Memtable (in-memory sorted structure)                   |
|  3. ACK to client (write complete!)                                  |
|  4. When Memtable full -> flush to SSTable on disk                   |
|                                                                         |
|  WHY SO FAST:                                                          |
|  * Memory write = microseconds                                       |
|  * Sequential disk write (SSTable) = fast                           |
|  * No random I/O during writes!                                      |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  READ PATH                                                             |
|                                                                         |
|  1. Check Memtable (most recent data)                                |
|  2. Check each SSTable from newest to oldest                        |
|  3. Return first match found                                         |
|                                                                         |
|  OPTIMIZATION - BLOOM FILTERS:                                        |
|  Each SSTable has a Bloom filter                                     |
|  "Is key possibly in this SSTable?"                                  |
|  If NO -> skip reading this file entirely                             |
|  Reduces disk reads dramatically!                                    |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  COMPACTION                                                            |
|                                                                         |
|  Merge SSTables to:                                                   |
|  * Remove deleted/overwritten data                                   |
|  * Reduce number of files to search                                 |
|  * Reclaim space                                                      |
|                                                                         |
|  COMPACTION STRATEGIES:                                               |
|                                                                         |
|  SIZE-TIERED (Cassandra default):                                    |
|  Merge SSTables of similar size                                      |
|  Good for write-heavy workloads                                      |
|                                                                         |
|  LEVELED (RocksDB, LevelDB):                                         |
|  Fixed size SSTables, merge level-by-level                          |
|  Better read performance, more write amplification                  |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  LSM vs B-TREE COMPARISON                                             |
|                                                                         |
|  +----------------+------------------+------------------------------+|
|  |                | LSM Tree         | B-Tree (PostgreSQL, MySQL)  ||
|  +----------------+------------------+------------------------------+|
|  | Write speed    | Very fast        | Moderate (random I/O)       ||
|  | Read speed     | Moderate         | Fast (single lookup)        ||
|  | Space          | May use more     | More compact                ||
|  | Write pattern  | Sequential       | Random                      ||
|  | Use case       | Write-heavy      | Read-heavy                  ||
|  | Used by        | Cassandra, Rocks | PostgreSQL, MySQL           ||
|  +----------------+------------------+------------------------------+|
|                                                                         |
+-------------------------------------------------------------------------+
```

### SSTABLE (Sorted String Table)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SSTABLE STRUCTURE                                                     |
|                                                                         |
|  Immutable file with sorted key-value pairs + index                  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                         SSTable File                           |  |
|  |                                                                 |  |
|  |  +-----------------------------------------------------------+|  |
|  |  |                    DATA BLOCKS                            ||  |
|  |  |  +-----------------------------------------------------+ ||  |
|  |  |  | Block 1: A=1, B=2, C=3, D=4, E=5                    | ||  |
|  |  |  +-----------------------------------------------------+ ||  |
|  |  |  | Block 2: F=6, G=7, H=8, I=9, J=10                   | ||  |
|  |  |  +-----------------------------------------------------+ ||  |
|  |  |  | Block 3: K=11, L=12, M=13, N=14, O=15               | ||  |
|  |  |  +-----------------------------------------------------+ ||  |
|  |  +-----------------------------------------------------------+|  |
|  |                                                                 |  |
|  |  +-----------------------------------------------------------+|  |
|  |  |                    INDEX BLOCK                            ||  |
|  |  |  A -> Block 1 offset                                      ||  |
|  |  |  F -> Block 2 offset                                      ||  |
|  |  |  K -> Block 3 offset                                      ||  |
|  |  |  (Sparse index - first key of each block)                ||  |
|  |  +-----------------------------------------------------------+|  |
|  |                                                                 |  |
|  |  +-----------------------------------------------------------+|  |
|  |  |                    BLOOM FILTER                           ||  |
|  |  |  Quick "is key possibly here?" check                     ||  |
|  |  +-----------------------------------------------------------+|  |
|  |                                                                 |  |
|  |  +-----------------------------------------------------------+|  |
|  |  |                    FOOTER                                 ||  |
|  |  |  Index offset, Bloom filter offset, metadata             ||  |
|  |  +-----------------------------------------------------------+|  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  FINDING A KEY:                                                        |
|  1. Check Bloom filter: "Is key G possibly here?"                    |
|  2. Binary search index: G is between F and K -> Block 2             |
|  3. Read Block 2, scan for G                                         |
|  4. Return value (7)                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DYNAMODB ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HOW DYNAMODB WORKS                                                    |
|                                                                         |
|  Built on principles from Amazon's Dynamo paper (2007)               |
|  + Modern improvements                                                |
|                                                                         |
|  KEY COMPONENTS:                                                       |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |                      REQUEST ROUTER                            |  |
|  |  +-----------------------------------------------------------+|  |
|  |  |  * Routes requests to correct partition                   ||  |
|  |  |  * Handles authentication/authorization                   ||  |
|  |  |  * Request throttling                                     ||  |
|  |  +-----------------------------------------------------------+|  |
|  |                          |                                      |  |
|  |                          v                                      |  |
|  |              CONSISTENT HASHING RING                           |  |
|  |  +-----------------------------------------------------------+|  |
|  |  |                                                           ||  |
|  |  |     Partition Key -> Hash -> Position on Ring              ||  |
|  |  |                                                           ||  |
|  |  |              ●-------●-------●                            ||  |
|  |  |            /                   \                          ||  |
|  |  |          ●       Hash Ring      ●                        ||  |
|  |  |            \                   /                          ||  |
|  |  |              ●-------●-------●                            ||  |
|  |  |                                                           ||  |
|  |  |  Each position owned by a storage node                   ||  |
|  |  +-----------------------------------------------------------+|  |
|  |                          |                                      |  |
|  |                          v                                      |  |
|  |                  STORAGE NODES                                 |  |
|  |  +-----------------------------------------------------------+|  |
|  |  |                                                           ||  |
|  |  |  Each partition stored on 3 nodes (replication factor=3) ||  |
|  |  |                                                           ||  |
|  |  |  +-------------+ +-------------+ +-------------+        ||  |
|  |  |  |   Node A    | |   Node B    | |   Node C    |        ||  |
|  |  |  |  (Leader)   | |  (Replica)  | |  (Replica)  |        ||  |
|  |  |  |             | |             | |             |        ||  |
|  |  |  | +---------+ | | +---------+ | | +---------+ |        ||  |
|  |  |  | |B+ Tree  | | | |B+ Tree  | | | |B+ Tree  | |        ||  |
|  |  |  | |(Storage)| | | |(Storage)| | | |(Storage)| |        ||  |
|  |  |  | +---------+ | | +---------+ | | +---------+ |        ||  |
|  |  |  +-------------+ +-------------+ +-------------+        ||  |
|  |  |                                                           ||  |
|  |  +-----------------------------------------------------------+|  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  DYNAMODB DATA MODEL                                                   |
|                                                                         |
|  TABLE STRUCTURE:                                                      |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  PARTITION KEY (Hash Key)                                      |  |
|  |  * Determines which partition stores the item                 |  |
|  |  * Example: user_id                                           |  |
|  |                                                                 |  |
|  |  SORT KEY (Range Key) - Optional                              |  |
|  |  * Orders items within a partition                            |  |
|  |  * Enables range queries                                      |  |
|  |  * Example: timestamp, order_id                               |  |
|  |                                                                 |  |
|  |  EXAMPLE TABLE:                                                |  |
|  |  +----------------+----------------+-----------------------+  |  |
|  |  | user_id (PK)   | order_id (SK)  | attributes...         |  |  |
|  |  +----------------+----------------+-----------------------+  |  |
|  |  | user_123       | order_001      | { total: 99.99 }      |  |  |
|  |  | user_123       | order_002      | { total: 45.00 }      |  |  |
|  |  | user_123       | order_003      | { total: 150.00 }     |  |  |
|  |  | user_456       | order_001      | { total: 25.00 }      |  |  |
|  |  +----------------+----------------+-----------------------+  |  |
|  |                                                                 |  |
|  |  Query: Get all orders for user_123                           |  |
|  |  -> Hits single partition, scans by sort key                   |  |
|  |  -> Very efficient!                                            |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  WRITE PATH IN DYNAMODB                                               |
|                                                                         |
|  1. Request arrives at Request Router                                |
|  2. Router hashes partition key -> finds partition                   |
|  3. Route to leader node for that partition                         |
|  4. Leader writes to local storage                                   |
|  5. Leader replicates to 2 replicas                                 |
|  6. Wait for quorum (2 of 3) -> ACK to client                       |
|                                                                         |
|  WRITE OPTIONS:                                                        |
|  * Eventually consistent: ACK after leader write (fastest)          |
|  * Strongly consistent: Wait for all replicas (slower)              |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  READ PATH IN DYNAMODB                                                |
|                                                                         |
|  EVENTUALLY CONSISTENT READ (default):                               |
|  * Read from any replica                                             |
|  * Might get stale data (milliseconds old)                          |
|  * Cheaper, faster                                                    |
|                                                                         |
|  STRONGLY CONSISTENT READ:                                            |
|  * Read from leader                                                  |
|  * Guaranteed latest data                                            |
|  * 2x the cost, slightly slower                                     |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  GLOBAL SECONDARY INDEX (GSI)                                         |
|                                                                         |
|  Query by non-primary key attributes                                 |
|                                                                         |
|  Main table: PK = user_id                                            |
|  GSI: PK = email (query users by email)                             |
|                                                                         |
|  HOW IT WORKS:                                                         |
|  * Separate table with different partition key                      |
|  * DynamoDB keeps it in sync automatically                          |
|  * Eventually consistent with main table                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CASSANDRA ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CASSANDRA - Peer-to-peer, no single point of failure                |
|                                                                         |
|  KEY DIFFERENCES FROM DYNAMODB:                                       |
|  * Open source                                                        |
|  * Peer-to-peer (no leader, all nodes equal)                        |
|  * Tunable consistency (you choose W and R)                         |
|  * Uses LSM Trees (not B-Trees like DynamoDB)                       |
|                                                                         |
|  ARCHITECTURE:                                                         |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |                    CASSANDRA RING                              |  |
|  |                                                                 |  |
|  |              Node A ●---------● Node B                         |  |
|  |                    /           \                                |  |
|  |                   /             \                               |  |
|  |           Node F ●               ● Node C                      |  |
|  |                   \             /                               |  |
|  |                    \           /                                |  |
|  |              Node E ●---------● Node D                         |  |
|  |                                                                 |  |
|  |  * Each node owns a token range                                |  |
|  |  * Data replicated to N consecutive nodes                     |  |
|  |  * Any node can handle any request (coordinator)              |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  WRITE PATH (with Replication Factor = 3):                           |
|                                                                         |
|  1. Client writes to any node (becomes coordinator)                  |
|  2. Coordinator hashes partition key -> finds owning nodes           |
|  3. Coordinator sends write to all 3 replica nodes                  |
|  4. Each node: Write to CommitLog -> Memtable -> ACK                  |
|  5. Coordinator waits for W acks (configurable)                     |
|  6. Return success to client                                         |
|                                                                         |
|  CONSISTENCY LEVELS:                                                   |
|  +--------------+------------------------------------------------+  |
|  | Level        | Meaning                                         |  |
|  +--------------+------------------------------------------------+  |
|  | ONE          | Wait for 1 replica (fastest, least safe)       |  |
|  | QUORUM       | Wait for majority (N/2 + 1)                    |  |
|  | ALL          | Wait for all replicas (slowest, safest)        |  |
|  | LOCAL_QUORUM | Quorum in local datacenter only                |  |
|  +--------------+------------------------------------------------+  |
|                                                                         |
|  STRONG CONSISTENCY:                                                   |
|  W + R > N (write consistency + read consistency > replication)     |
|  Example: W=QUORUM, R=QUORUM with N=3 -> 2+2 > 3 [x]                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DATA STRUCTURES SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATABASE DATA STRUCTURES                                             |
|                                                                         |
|  +----------------+------------------------------------------------+ |
|  | Data Structure | Used By / Purpose                              | |
|  +----------------+------------------------------------------------+ |
|  | B+ Tree        | PostgreSQL, MySQL, DynamoDB storage           | |
|  |                | Good for reads, range queries                 | |
|  +----------------+------------------------------------------------+ |
|  | LSM Tree       | Cassandra, RocksDB, LevelDB, HBase           | |
|  |                | Good for writes, append-only workloads       | |
|  +----------------+------------------------------------------------+ |
|  | SSTable        | LSM tree's disk format                        | |
|  |                | Immutable sorted files                        | |
|  +----------------+------------------------------------------------+ |
|  | Memtable       | LSM tree's in-memory buffer                   | |
|  |                | Red-Black tree or Skip List                  | |
|  +----------------+------------------------------------------------+ |
|  | Skip List      | Redis sorted sets, Memtable                   | |
|  |                | O(log n) insert/search, simpler than trees   | |
|  +----------------+------------------------------------------------+ |
|  | Hash Table     | Redis hash, DynamoDB partition routing       | |
|  |                | O(1) lookup by key                           | |
|  +----------------+------------------------------------------------+ |
|  | Bloom Filter   | SSTable lookup optimization                   | |
|  |                | "Is key possibly in this file?"              | |
|  +----------------+------------------------------------------------+ |
|  | Consistent Hash| DynamoDB, Cassandra partition placement      | |
|  |                | Distribute data, minimize reshuffling        | |
|  +----------------+------------------------------------------------+ |
|                                                                         |
|  INTERVIEW TIP:                                                        |
|  When asked "How does DynamoDB work?", mention:                      |
|  1. Consistent hashing for partitioning                              |
|  2. Replication across 3 AZs                                        |
|  3. Partition key + optional sort key                               |
|  4. Eventually vs strongly consistent reads                         |
|  5. GSIs for alternate access patterns                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.6: SQL vs NOSQL DECISION FRAMEWORK

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DECISION MATRIX                                                       |
|                                                                         |
|  FACTOR                    | SQL                 | NoSQL               |
|  --------------------------------------------------------------------- |
|  Schema                    | Fixed, predefined   | Flexible, dynamic   |
|  Relationships             | Strong (JOINs)      | Denormalized        |
|  Scaling                   | Vertical (primary)  | Horizontal          |
|  Consistency               | Strong (ACID)       | Eventual (usually)  |
|  Query flexibility         | Very flexible       | Access pattern      |
|  Write throughput          | Moderate            | Very high           |
|  Transactions              | Multi-row/table     | Usually single-doc  |
|  Maturity                  | Very mature         | Newer               |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  CHOOSE SQL WHEN:                                                      |
|  -----------------                                                     |
|  [x] Data has clear relationships                                       |
|  [x] You need complex queries (JOINs, aggregations)                    |
|  [x] ACID transactions are required                                     |
|  [x] Data integrity is critical                                         |
|  [x] Schema is well-defined and stable                                 |
|                                                                         |
|  Examples:                                                             |
|  * Banking and financial systems                                      |
|  * E-commerce orders and payments                                     |
|  * Inventory management                                               |
|  * User accounts with complex permissions                             |
|  * ERP systems                                                        |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  CHOOSE NOSQL WHEN:                                                    |
|  ------------------                                                    |
|  [x] You need massive horizontal scale                                  |
|  [x] Schema is evolving or unknown                                      |
|  [x] Access patterns are simple and well-defined                        |
|  [x] Eventual consistency is acceptable                                 |
|  [x] High write throughput is needed                                    |
|                                                                         |
|  Examples:                                                             |
|  * Session storage (key-value: Redis)                                |
|  * Content management (document: MongoDB)                            |
|  * IoT sensor data (wide-column: Cassandra)                          |
|  * Social connections (graph: Neo4j)                                 |
|  * Real-time analytics (time-series: InfluxDB)                       |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  POLYGLOT PERSISTENCE                                                  |
|  ---------------------                                                  |
|  Use different databases for different purposes!                      |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                     E-Commerce System                          |  |
|  |                                                                 |  |
|  |  Orders, Users --> PostgreSQL (ACID transactions)             |  |
|  |  Product Catalog --> MongoDB (flexible schema)                 |  |
|  |  Sessions, Cache --> Redis (fast key-value)                   |  |
|  |  Search --> Elasticsearch (full-text search)                  |  |
|  |  Recommendations --> Neo4j (graph relationships)              |  |
|  |  Analytics --> ClickHouse (OLAP)                              |  |
|  |  Metrics --> InfluxDB (time-series)                           |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.6: INDEXING DEEP DIVE

Indexes make queries fast. Understanding them is crucial.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HOW INDEXES WORK                                                      |
|                                                                         |
|  WITHOUT INDEX:                                                        |
|  -----------------                                                      |
|  Query: SELECT * FROM users WHERE email = 'alice@example.com'         |
|  Database: Scan EVERY row to find matching email                      |
|  Time complexity: O(n) - linear scan                                  |
|  1 million rows = 1 million comparisons!                              |
|                                                                         |
|  WITH INDEX ON email:                                                  |
|  ---------------------                                                  |
|  Database: Use B-tree to jump directly to matching row                |
|  Time complexity: O(log n) - binary search                            |
|  1 million rows = ~20 comparisons!                                    |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  B-TREE INDEX STRUCTURE                                        |  |
|  |                                                                 |  |
|  |                    +-----------------+                         |  |
|  |                    |  D   |   M      |  Root node              |  |
|  |                    +--+--------+-----+                         |  |
|  |               +------+        +-------+                        |  |
|  |               v                       v                        |  |
|  |        +----------+            +----------+                   |  |
|  |        | A  |  C  |            | F | H | K |                  |  |
|  |        +-+----+---+            +-+---+---+-+                   |  |
|  |          |    |                  |   |   |                     |  |
|  |          v    v                  v   v   v                     |  |
|  |        [A,B] [C]              [D,E][F,G][H-K]  Leaf nodes      |  |
|  |                                      (pointers to rows)       |  |
|  |                                                                 |  |
|  |  Looking for "G":                                              |  |
|  |  1. Root: G > D, G < M -> go right                             |  |
|  |  2. Internal: F < G < H -> middle branch                       |  |
|  |  3. Leaf: Find G, get row pointer                             |  |
|  |  -> 3 node accesses instead of scanning all rows!              |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  B+ TREE vs B-TREE:                                                    |
|  * B+ Tree: Data only in leaf nodes, leaves linked                   |
|  * Better for range queries (scan linked leaves)                     |
|  * Most databases use B+ Trees                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### INDEX TYPES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INDEX TYPES                                                           |
|                                                                         |
|  1. B-TREE INDEX (Default, most common)                               |
|  ----------------------------------------                               |
|  Good for: Equality, range queries, sorting, prefix matching         |
|                                                                         |
|  CREATE INDEX idx_email ON users(email);                              |
|                                                                         |
|  Supports:                                                             |
|  * email = 'alice@example.com'      [x] equality                       |
|  * email LIKE 'alice%'              [x] prefix                         |
|  * email > 'a' AND email < 'b'      [x] range                         |
|  * ORDER BY email                    [x] sorting                       |
|  * email LIKE '%alice%'             [ ] suffix (full scan)            |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. HASH INDEX                                                         |
|  -----------------                                                      |
|  Good for: Exact equality only (O(1) lookup)                          |
|                                                                         |
|  CREATE INDEX idx_id ON users USING HASH(id);                         |
|                                                                         |
|  Supports:                                                             |
|  * id = 123                          [x]                                |
|  * id > 100                          [ ] (no range)                    |
|  * ORDER BY id                       [ ] (no ordering)                 |
|                                                                         |
|  USE WHEN: Only need exact matches                                    |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. COMPOSITE INDEX (Multiple columns)                                |
|  ---------------------------------------                                |
|  CREATE INDEX idx_user_date ON orders(user_id, created_at);          |
|                                                                         |
|  LEFTMOST PREFIX RULE:                                                 |
|  Index can be used for queries starting with leftmost columns        |
|                                                                         |
|  Index on (a, b, c) supports:                                         |
|  * WHERE a = 1                               [x]                        |
|  * WHERE a = 1 AND b = 2                     [x]                        |
|  * WHERE a = 1 AND b = 2 AND c = 3           [x]                        |
|  * WHERE b = 2                               [ ] (a missing)           |
|  * WHERE a = 1 AND c = 3                     partial (a only)        |
|                                                                         |
|  COLUMN ORDER MATTERS:                                                 |
|  Put most selective column first (highest cardinality)               |
|  Put columns used for equality before range                          |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. COVERING INDEX (Index-Only Scan)                                  |
|  --------------------------------------                                 |
|  Index contains all columns needed by query                          |
|                                                                         |
|  CREATE INDEX idx_covering ON users(email) INCLUDE (name, created_at);|
|                                                                         |
|  Query: SELECT name, email FROM users WHERE email = '...'            |
|  -> Answered entirely from index, no table lookup!                    |
|                                                                         |
|  HUGE performance boost for frequently run queries                   |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  5. PARTIAL INDEX (Filtered Index)                                    |
|  ------------------------------------                                   |
|  Index only some rows                                                 |
|                                                                         |
|  CREATE INDEX idx_active ON users(email) WHERE status = 'active';    |
|                                                                         |
|  Smaller index, faster updates for inactive users                    |
|  Only helps queries that match the WHERE condition                   |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  6. FULL-TEXT INDEX                                                    |
|  -------------------                                                    |
|  For text search                                                       |
|                                                                         |
|  CREATE FULLTEXT INDEX idx_content ON articles(title, content);      |
|                                                                         |
|  Query: WHERE MATCH(title, content) AGAINST('database design')       |
|                                                                         |
|  For advanced search: Use Elasticsearch!                             |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  7. SPATIAL INDEX (R-Tree, GiST)                                      |
|  ---------------------------------                                      |
|  For geographic/geometric data                                        |
|                                                                         |
|  CREATE INDEX idx_location ON places USING GIST(location);           |
|                                                                         |
|  Query: WHERE ST_DWithin(location, point, 1000)                      |
|  -> Find all places within 1km of point                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.7: QUERY OPTIMIZATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUERY OPTIMIZATION TECHNIQUES                                        |
|                                                                         |
|  1. USE EXPLAIN ANALYZE                                               |
|  =======================                                                |
|                                                                         |
|  EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'alice@ex.com';   |
|                                                                         |
|  OUTPUT:                                                               |
|  +------------------------------------------------------------------+ |
|  | Index Scan using idx_email on users  (cost=0.29..8.31 rows=1)   | |
|  |   Index Cond: (email = 'alice@ex.com')                          | |
|  |   Actual time: 0.021..0.022 ms                                  | |
|  |   Rows: 1                                                        | |
|  +------------------------------------------------------------------+ |
|                                                                         |
|  WHAT TO LOOK FOR:                                                     |
|  * Seq Scan (Sequential Scan) - BAD for large tables                |
|  * Index Scan - GOOD                                                  |
|  * Index Only Scan - BEST (covering index)                          |
|  * Nested Loop - Can be slow with large datasets                    |
|  * Hash Join / Merge Join - Better for large datasets               |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. COMMON QUERY PROBLEMS                                             |
|  =========================                                              |
|                                                                         |
|  PROBLEM: Function on indexed column                                  |
|  [ ] WHERE YEAR(created_at) = 2024                                     |
|    -> Can't use index on created_at                                   |
|  [x] WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01'   |
|    -> Uses index                                                       |
|                                                                         |
|  PROBLEM: Type mismatch                                               |
|  [ ] WHERE user_id = '123'  (user_id is INTEGER)                      |
|    -> Implicit cast, may not use index                                |
|  [x] WHERE user_id = 123                                               |
|                                                                         |
|  PROBLEM: LIKE with leading wildcard                                  |
|  [ ] WHERE name LIKE '%smith'                                          |
|    -> Full table scan                                                 |
|  [x] WHERE name LIKE 'smith%'                                          |
|    -> Uses index (prefix match)                                       |
|  [x] Use full-text search for arbitrary substring                     |
|                                                                         |
|  PROBLEM: OR conditions                                               |
|  [ ] WHERE status = 'active' OR status = 'pending'                    |
|    -> May not use index efficiently                                   |
|  [x] WHERE status IN ('active', 'pending')                            |
|                                                                         |
|  PROBLEM: SELECT *                                                    |
|  [ ] SELECT * FROM users WHERE id = 1                                 |
|    -> Fetches all columns, prevents index-only scan                  |
|  [x] SELECT id, name, email FROM users WHERE id = 1                   |
|    -> Only fetch needed columns                                       |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. JOIN OPTIMIZATION                                                  |
|  ======================                                                 |
|                                                                         |
|  JOIN ORDER MATTERS:                                                   |
|  Start with smallest result set, filter early                        |
|                                                                         |
|  [ ] SELECT * FROM orders o                                            |
|    JOIN users u ON o.user_id = u.id                                  |
|    WHERE u.status = 'active'                                         |
|    -> Joins all orders, then filters                                  |
|                                                                         |
|  [x] SELECT * FROM users u                                             |
|    JOIN orders o ON o.user_id = u.id                                 |
|    WHERE u.status = 'active'                                         |
|    -> Filters users first, then joins                                 |
|                                                                         |
|  INDEX JOIN COLUMNS:                                                   |
|  CREATE INDEX idx_orders_user ON orders(user_id);                    |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. PAGINATION OPTIMIZATION                                           |
|  ============================                                           |
|                                                                         |
|  PROBLEM: OFFSET is slow for large values                            |
|  [ ] SELECT * FROM posts ORDER BY id LIMIT 20 OFFSET 10000;           |
|    -> DB must scan 10,000 rows to skip them                          |
|                                                                         |
|  SOLUTION: Keyset pagination (cursor-based)                          |
|  [x] SELECT * FROM posts WHERE id > 10000 ORDER BY id LIMIT 20;       |
|    -> Uses index, skips nothing                                       |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  5. N+1 QUERY PROBLEM                                                  |
|  =======================                                                |
|                                                                         |
|  PROBLEM: 1 query + N additional queries                              |
|                                                                         |
|  # Python/ORM example                                                  |
|  users = User.all()                     # 1 query                     |
|  for user in users:                                                    |
|      print(user.orders)                 # N queries!                   |
|                                                                         |
|  SOLUTIONS:                                                            |
|  1. Eager loading: User.includes(:orders).all()                      |
|     -> 2 queries total (users + all orders)                           |
|                                                                         |
|  2. JOIN:                                                              |
|     SELECT u.*, o.* FROM users u                                     |
|     LEFT JOIN orders o ON o.user_id = u.id                           |
|                                                                         |
|  3. Batch loading (DataLoader pattern for GraphQL)                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.8: NEWSQL AND HTAP DATABASES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NEWSQL DATABASES                                                      |
|                                                                         |
|  Combine SQL guarantees (ACID) with NoSQL scalability.               |
|                                                                         |
|  Examples: CockroachDB, TiDB, Google Spanner, YugabyteDB             |
|                                                                         |
|  FEATURES:                                                             |
|  [x] SQL interface and ACID transactions                               |
|  [x] Horizontal scalability (like NoSQL)                               |
|  [x] Distributed architecture                                          |
|  [x] Strong consistency across regions                                 |
|                                                                         |
|  HOW THEY WORK:                                                        |
|  * Distributed consensus (Raft/Paxos) for consistency               |
|  * Automatic sharding and rebalancing                                |
|  * Multi-region replication                                          |
|                                                                         |
|  GOOGLE SPANNER:                                                       |
|  -----------------                                                      |
|  * First globally distributed database with external consistency    |
|  * Uses TrueTime (atomic clocks + GPS) for global ordering          |
|  * Can handle transactions across continents                        |
|                                                                         |
|  USE WHEN:                                                             |
|  * Need SQL but must scale horizontally                              |
|  * Global distribution with strong consistency                      |
|  * Can't sacrifice ACID for scale                                   |
|                                                                         |
|  TRADE-OFFS:                                                           |
|  * Higher latency than single-node SQL (consensus overhead)         |
|  * More complex operations                                           |
|  * Higher cost                                                       |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  HTAP (Hybrid Transactional/Analytical Processing)                   |
|                                                                         |
|  Single database for both OLTP and OLAP workloads.                   |
|                                                                         |
|  TRADITIONAL APPROACH:                                                 |
|  +------------------------------------------------------------------+ |
|  | OLTP Database --> ETL --> Data Warehouse --> Analytics         | |
|  | (transactions)           (hours delay)       (reports)          | |
|  +------------------------------------------------------------------+ |
|                                                                         |
|  HTAP APPROACH:                                                        |
|  +------------------------------------------------------------------+ |
|  | HTAP Database                                                    | |
|  | +-----------------+    +-----------------+                     | |
|  | | Row Store       |<-->| Column Store    |                     | |
|  | | (transactions)  |    | (analytics)     |                     | |
|  | +-----------------+    +-----------------+                     | |
|  |        Real-time sync                                           | |
|  +------------------------------------------------------------------+ |
|                                                                         |
|  Examples: TiDB, SingleStore, SAP HANA, AlloyDB                      |
|                                                                         |
|  BENEFITS:                                                             |
|  * Real-time analytics on live data                                  |
|  * No ETL pipeline complexity                                        |
|  * Reduced infrastructure                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.9: DATABASE SCALING PATTERNS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATABASE SCALING TECHNIQUES                                           |
|                                                                         |
|  1. VERTICAL SCALING (Scale Up)                                       |
|  ===============================                                        |
|  Add more resources to single machine                                 |
|                                                                         |
|  Before: 16 CPU, 64GB RAM, 1TB SSD                                   |
|  After:  64 CPU, 512GB RAM, 10TB NVMe                                |
|                                                                         |
|  PROS: Simple, no code changes                                        |
|  CONS: Hardware limits, single point of failure, expensive           |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. READ REPLICAS                                                      |
|  =================                                                      |
|  One primary for writes, multiple replicas for reads                  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |    Writes --> Primary DB                                       |  |
|  |                   |                                             |  |
|  |                   | Replication                                 |  |
|  |              +----+----+------------+                          |  |
|  |              v         v            v                          |  |
|  |          Replica 1  Replica 2  Replica 3                       |  |
|  |              ^         ^            ^                          |  |
|  |              +----+----+------------+                          |  |
|  |                   |                                             |  |
|  |    Reads ---------+                                            |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  CONSIDERATIONS:                                                       |
|  * Replication lag: Replicas may be behind                          |
|  * Read-after-write: May need to read from primary after write     |
|  * Use for: Read-heavy workloads (80-90% reads)                    |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. SHARDING (Horizontal Partitioning)                                |
|  =======================================                                |
|  Split data across multiple databases                                 |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  All Users                                                      |  |
|  |     |                                                           |  |
|  |     |  Shard by user_id % 4                                    |  |
|  |     |                                                           |  |
|  |     +----> Shard 0: user_id % 4 = 0                           |  |
|  |     +----> Shard 1: user_id % 4 = 1                           |  |
|  |     +----> Shard 2: user_id % 4 = 2                           |  |
|  |     +----> Shard 3: user_id % 4 = 3                           |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  See Chapter 6 for detailed sharding strategies                      |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. CONNECTION POOLING                                                |
|  =====================                                                  |
|  Reuse database connections instead of creating new ones             |
|                                                                         |
|  Without pooling: Open connection -> Query -> Close (expensive!)       |
|  With pooling: Get from pool -> Query -> Return to pool               |
|                                                                         |
|  +------------------------------------------------------------------+ |
|  | Application                                                      | |
|  |    v^                                                            | |
|  | Connection Pool (e.g., PgBouncer)                               | |
|  |    v^                                                            | |
|  | Database                                                         | |
|  +------------------------------------------------------------------+ |
|                                                                         |
|  POOLING MODES (PgBouncer):                                           |
|  * Session: Connection per session (safest)                         |
|  * Transaction: Connection per transaction (more sharing)          |
|  * Statement: Connection per statement (most aggressive)           |
|                                                                         |
|  Tools: PgBouncer, HikariCP, ProxySQL                               |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  5. CACHING LAYER                                                      |
|  ===================                                                    |
|  Reduce database load with cache                                      |
|                                                                         |
|  +------------------------------------------------------------------+ |
|  | Application --> Redis Cache --> Database                        | |
|  |                    |                                             | |
|  |             Cache hit: Return                                   | |
|  |             Cache miss: Query DB, cache result                  | |
|  +------------------------------------------------------------------+ |
|                                                                         |
|  See Chapter 4 for caching strategies                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATABASES - KEY TAKEAWAYS                                             |
|                                                                         |
|  SQL (RELATIONAL)                                                      |
|  -----------------                                                     |
|  * Structured data with relationships                                |
|  * ACID transactions for data integrity                              |
|  * Flexible queries with SQL                                         |
|  * Isolation levels: Read Committed most common                     |
|                                                                         |
|  NOSQL                                                                 |
|  -----                                                                 |
|  * Key-Value: Simple lookups, caching                                |
|  * Document: Flexible schema, semi-structured                        |
|  * Wide-Column: Time-series, high-volume writes                      |
|  * Graph: Relationship-heavy data                                    |
|  * Time-Series: Timestamped metrics                                  |
|                                                                         |
|  CONCURRENCY CONTROL                                                   |
|  --------------------                                                  |
|  * Pessimistic: Lock early, prevent conflicts                       |
|  * Optimistic: No locks, detect conflicts at commit                 |
|  * MVCC: Multiple versions, readers don't block writers             |
|                                                                         |
|  INDEXING                                                              |
|  --------                                                              |
|  * B-tree: Default, good for range and equality                      |
|  * Composite: Multiple columns, leftmost prefix rule                 |
|  * Covering: Include all columns, avoid table lookup                |
|  * Trade-off: Faster reads vs slower writes                          |
|                                                                         |
|  QUERY OPTIMIZATION                                                    |
|  -----------------                                                     |
|  * Use EXPLAIN ANALYZE                                               |
|  * Avoid functions on indexed columns                                |
|  * Use keyset pagination (not OFFSET)                               |
|  * Solve N+1 with eager loading                                     |
|                                                                         |
|  SCALING                                                               |
|  -------                                                               |
|  * Read replicas: Scale reads                                        |
|  * Sharding: Scale writes and storage                                |
|  * Connection pooling: Reduce overhead                               |
|  * NewSQL: SQL + horizontal scale                                   |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  INTERVIEW TIP                                                         |
|  -------------                                                         |
|  Don't default to one database type. Ask about:                      |
|  * Access patterns (reads vs writes ratio)                          |
|  * Consistency requirements (ACID vs eventual)                      |
|  * Scale requirements (data size, QPS)                              |
|  * Query complexity (JOINs, aggregations)                           |
|  * Team expertise                                                    |
|                                                                         |
|  Common interview questions:                                          |
|  * When would you use SQL vs NoSQL?                                 |
|  * How would you optimize a slow query?                             |
|  * What isolation level and why?                                    |
|  * How to handle concurrent updates?                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 5

