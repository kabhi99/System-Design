# CHAPTER 20: DATABASE INTERNALS DEEP DIVE
*How Databases Really Work Under the Hood*

This chapter covers advanced database internals essential for system design
interviews: storage engines, B+Trees, query planning, and concurrency control.

## SECTION 20.1: HOW DATA IS STORED ON DISK

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATABASE STORAGE HIERARCHY                                             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  DATABASE                                                         |  |
|  |      |                                                            |  |
|  |      +--> TABLESPACE (logical grouping of files)                  |  |
|  |              |                                                    |  |
|  |              +--> DATA FILE (physical file on disk)               |  |
|  |                      |                                            |  |
|  |                      +--> PAGES/BLOCKS (fixed-size units)         |  |
|  |                              |                                    |  |
|  |                              +--> ROWS/TUPLES (actual data)       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DATABASE PAGES (THE FUNDAMENTAL UNIT)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS A PAGE?                                                        |
|                                                                         |
|  The smallest unit of I/O between disk and memory.                      |
|  Database reads/writes entire pages, not individual rows.               |
|                                                                         |
|  PAGE SIZES:                                                            |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Database        Default Page Size                                |  |
|  |  -----------------------------------------------------------------|  |
|  |  PostgreSQL      8 KB                                             |  |
|  |  MySQL InnoDB    16 KB                                            |  |
|  |  SQL Server      8 KB                                             |  |
|  |  Oracle          8 KB (configurable 2-32 KB)                      |  |
|  |  SQLite          4 KB                                             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  WHY PAGES MATTER:                                                      |
|  * Reading 1 byte = reading entire page (8 KB)                          |
|  * Random I/O is expensive (seek time)                                  |
|  * Sequential reads are 100x+ faster                                    |
|  * Page size affects B-tree fan-out                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### PAGE STRUCTURE (PostgreSQL Example)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANATOMY OF A DATABASE PAGE (8 KB)                                      |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  +--------------------------------------------------------------+ |  |
|  |  | PAGE HEADER (24 bytes)                                       | |  |
|  |  | * Page LSN (log sequence number)                             | |  |
|  |  | * Checksum                                                   | |  |
|  |  | * Flags, version info                                        | |  |
|  |  | * Free space pointers                                        | |  |
|  |  +--------------------------------------------------------------+ |  |
|  |  +--------------------------------------------------------------+ |  |
|  |  | LINE POINTERS (Item IDs)                                     | |  |
|  |  | * Array of 4-byte pointers to tuples                         | |  |
|  |  | * [offset, length, flags] for each row                       | |  |
|  |  +--------------------------------------------------------------+ |  |
|  |                                                                   |  |
|  |             v Free Space (grows toward each other) ^              |  |
|  |                                                                   |  |
|  |  +--------------------------------------------------------------+ |  |
|  |  | TUPLES (Row Data)                                            | |  |
|  |  | * Actual row data stored here                                | |  |
|  |  | * New rows added from bottom                                 | |  |
|  |  | * Each tuple has header (23 bytes) + data                    | |  |
|  |  +--------------------------------------------------------------+ |  |
|  |  +--------------------------------------------------------------+ |  |
|  |  | SPECIAL SPACE (optional)                                     | |  |
|  |  | * Index-specific data                                        | |  |
|  |  +--------------------------------------------------------------+ |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  WHEN PAGE IS FULL:                                                     |
|  * New page allocated                                                   |
|  * Or vacuum reclaims dead tuples                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HEAP vs INDEX STORAGE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TWO STORAGE APPROACHES                                                 |
|                                                                         |
|  1. HEAP TABLE (PostgreSQL default, MySQL secondary indexes)            |
|  ============================================================           |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Table data stored in heap (unordered):                           |  |
|  |                                                                   |  |
|  |  Page 1: [Row 5][Row 12][Row 3]                                   |  |
|  |  Page 2: [Row 8][Row 1][Row 15]                                   |  |
|  |  Page 3: [Row 7][Row 9][Row 2]                                    |  |
|  |                                                                   |  |
|  |  Index stores: key > (page_id, row_offset)                        |  |
|  |                                                                   |  |
|  |  PROS: Fast inserts (append anywhere)                             |  |
|  |  CONS: Index lookup + heap lookup (two I/O operations)            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  2. CLUSTERED INDEX / INDEX-ORGANIZED TABLE (MySQL InnoDB)              |
|  ==========================================================             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Data stored in primary key order (in the B+Tree itself):         |  |
|  |                                                                   |  |
|  |                    [Root: keys 50, 100]                           |  |
|  |                    /        |        \                            |  |
|  |           [1-49]       [50-99]      [100-150]                     |  |
|  |              v            v             v                         |  |
|  |          [Full Row]  [Full Row]   [Full Row]  < Data in leaves    |  |
|  |                                                                   |  |
|  |  Primary key lookup: Single B+Tree traversal                      |  |
|  |  Secondary index: key > primary_key > data (double lookup)        |  |
|  |                                                                   |  |
|  |  PROS: Primary key lookups very fast                              |  |
|  |  CONS: Sequential inserts ideal, random inserts cause splits      |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 20.2: ROW-BASED vs COLUMN-BASED DATABASES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TWO FUNDAMENTALLY DIFFERENT APPROACHES                                 |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  ROW-BASED (Row-Oriented) Storage                                 |  |
|  |  =================================                                |  |
|  |                                                                   |  |
|  |  Table: users                                                     |  |
|  |  +----+------+-----+--------+                                     |  |
|  |  | id | name | age | city   |                                     |  |
|  |  +----+------+-----+--------+                                     |  |
|  |  | 1  | Alice| 30  | NYC    |                                     |  |
|  |  | 2  | Bob  | 25  | LA     |                                     |  |
|  |  | 3  | Carol| 35  | Chicago|                                     |  |
|  |  +----+------+-----+--------+                                     |  |
|  |                                                                   |  |
|  |  Stored on disk as:                                               |  |
|  |  [1|Alice|30|NYC][2|Bob|25|LA][3|Carol|35|Chicago]                |  |
|  |  +---- Row 1 ----++-- Row 2 --++------ Row 3 -------+             |  |
|  |                                                                   |  |
|  |  Each row stored together contiguously                            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  COLUMN-BASED (Column-Oriented) Storage                           |  |
|  |  =======================================                          |  |
|  |                                                                   |  |
|  |  Same table stored as:                                            |  |
|  |                                                                   |  |
|  |  id column:   [1][2][3]                                           |  |
|  |  name column: [Alice][Bob][Carol]                                 |  |
|  |  age column:  [30][25][35]                                        |  |
|  |  city column: [NYC][LA][Chicago]                                  |  |
|  |                                                                   |  |
|  |  Each column stored together contiguously                         |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY STORAGE FORMAT MATTERS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUERY: SELECT AVG(age) FROM users WHERE city = 'NYC'                   |
|                                                                         |
|  ROW-BASED:                                                             |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Must read: [1|Alice|30|NYC][2|Bob|25|LA][3|Carol|35|Chicago]     |  |
|  |                    ^                ^              ^              |  |
|  |              Read full row    Read full row  Read full row        |  |
|  |                                                                   |  |
|  |  > Reads ALL columns even though we only need age & city          |  |
|  |  > If row is 1KB, reads 1KB x N rows                              |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  COLUMN-BASED:                                                          |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Only reads:                                                      |  |
|  |  age column:  [30][25][35]                                        |  |
|  |  city column: [NYC][LA][Chicago]                                  |  |
|  |                                                                   |  |
|  |  > Only 2 columns, not all columns                                |  |
|  |  > Sequential reads (very fast)                                   |  |
|  |  > Better compression (similar values together)                   |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  QUERY: SELECT * FROM users WHERE id = 1                                |
|                                                                         |
|  ROW-BASED: Fast! Read one row block                                    |
|  COLUMN-BASED: Slow! Must read from every column file                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ROW vs COLUMN COMPARISON

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMPARISON TABLE                                                       |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  Aspect              Row-Based         Column-Based              |   |
|  |  ------------------------------------------------------------    |   |
|  |                                                                  |   |
|  |  Best for            OLTP              OLAP                      |   |
|  |                      (transactions)    (analytics)               |   |
|  |                                                                  |   |
|  |  Single row ops      Fast              Slow                      |   |
|  |  (SELECT * WHERE                                                 |   |
|  |   id = X)                                                        |   |
|  |                                                                  |   |
|  |  Aggregations        Slow              Very Fast                 |   |
|  |  (SUM, AVG, COUNT)                                               |   |
|  |                                                                  |   |
|  |  INSERT/UPDATE       Fast              Slow                      |   |
|  |                                                                  |   |
|  |  Compression         Moderate          Excellent                 |   |
|  |                      (mixed types)     (same type per column)    |   |
|  |                                                                  |   |
|  |  Wide tables         Inefficient       Efficient                 |   |
|  |  (100+ columns)      (reads all)       (reads needed only)       |   |
|  |                                                                  |   |
|  |  Ad-hoc queries      Moderate          Excellent                 |   |
|  |  (unknown columns)                                               |   |
|  |                                                                  |   |
|  |  Examples            PostgreSQL        ClickHouse                |   |
|  |                      MySQL             BigQuery                  |   |
|  |                      Oracle            Redshift                  |   |
|  |                      SQL Server        Snowflake                 |   |
|  |                                        Apache Parquet            |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COLUMN-STORE COMPRESSION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY COLUMNAR COMPRESSES BETTER                                         |
|                                                                         |
|  status column with 1 million rows:                                     |
|  [active][active][inactive][active][active][inactive]...                |
|                                                                         |
|  COMPRESSION TECHNIQUES:                                                |
|                                                                         |
|  1. RUN-LENGTH ENCODING (RLE)                                           |
|  ----------------------------                                           |
|  [active, 500000][inactive, 500000]                                     |
|  Instead of storing value 1M times, store value + count                 |
|                                                                         |
|  2. DICTIONARY ENCODING                                                 |
|  -----------------------                                                |
|  Dictionary: {0: "active", 1: "inactive"}                               |
|  Data: [0][0][1][0][0][1]... (1 byte instead of string)                 |
|                                                                         |
|  3. BIT-PACKING                                                         |
|  ------------                                                           |
|  If column has only 4 distinct values, use 2 bits per value             |
|  Instead of 4 bytes per integer                                         |
|                                                                         |
|  RESULT: 10x-100x compression ratios common                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 20.3: B+TREE DEEP DIVE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  B-TREE vs B+TREE                                                       |
|                                                                         |
|  ORIGINAL B-TREE:                                                       |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |                    +--------------+                               |  |
|  |                    | [30] [50]    |   < Keys + Data at ALL        |  |
|  |                    |  v     v     |     levels                    |  |
|  |                    | data  data   |                               |  |
|  |                    +--------------+                               |  |
|  |               /          |          \                             |  |
|  |         [10,20]       [35,45]      [60,70]                        |  |
|  |          v  v          v  v         v  v                          |  |
|  |         data data     data data    data data                      |  |
|  |                                                                   |  |
|  |  LIMITATION: Data scattered across all levels                     |  |
|  |  > Range queries must traverse up and down                        |  |
|  |  > Less keys per node (data takes space)                          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  B+TREE (What databases use):                                           |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |                    +--------------+                               |  |
|  |                    | [30] [50]    |  < Internal: Keys ONLY        |  |
|  |                    | (no data)    |                               |  |
|  |                    +--------------+                               |  |
|  |               /          |          \                             |  |
|  |         [10,20,30]   [35,45,50]   [60,70,80]  < Leaf: Keys+Data   |  |
|  |              |           |             |         (or pointers)    |  |
|  |         <----+-----------+-------------+---->  Linked list!       |  |
|  |                                                                   |  |
|  |  ADVANTAGES:                                                      |  |
|  |  * Internal nodes fit more keys (no data = higher fan-out)        |  |
|  |  * All data at leaf level (predictable I/O)                       |  |
|  |  * Leaves linked > Range scans are sequential!                    |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### B+TREE OPERATIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SEARCH: O(log n)                                                       |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Find key 45:                                                     |  |
|  |                                                                   |  |
|  |  1. Start at root [30, 60]                                        |  |
|  |  2. 45 > 30 and 45 < 60 > middle child                            |  |
|  |  3. Child node [35, 45, 55]                                       |  |
|  |  4. Follow to leaf, find 45                                       |  |
|  |                                                                   |  |
|  |  Disk reads: ~3-4 for millions of rows                            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  INSERT: O(log n), may cause splits                                     |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Insert 42:                                                       |  |
|  |                                                                   |  |
|  |  1. Find leaf where 42 belongs                                    |  |
|  |  2. Insert in sorted order                                        |  |
|  |  3. If leaf full > SPLIT:                                         |  |
|  |     * Split leaf into two                                         |  |
|  |     * Promote middle key to parent                                |  |
|  |     * If parent full > split propagates up                        |  |
|  |                                                                   |  |
|  |  PAGE SPLITS: Expensive! Require multiple writes                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  RANGE SCAN: O(log n + k) where k = matching rows                       |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  SELECT * WHERE age BETWEEN 20 AND 40:                            |  |
|  |                                                                   |  |
|  |  1. Find leaf with 20 (log n)                                     |  |
|  |  2. Scan right through linked leaves until > 40                   |  |
|  |  3. Sequential read - very efficient!                             |  |
|  |                                                                   |  |
|  |  [..18,19,20]-->[21,25,30]-->[35,38,40]-->[45,50..]               |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### B+TREE STORAGE: MYSQL vs POSTGRESQL

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MYSQL INNODB (Clustered Index)                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  PRIMARY KEY INDEX:                                               |  |
|  |  * Leaf nodes contain FULL ROW DATA                               |  |
|  |  * Data physically ordered by primary key                         |  |
|  |  * PK lookup = one index traversal                                |  |
|  |                                                                   |  |
|  |  SECONDARY INDEX:                                                 |  |
|  |  * Leaf nodes contain PRIMARY KEY (not row pointer)               |  |
|  |  * Secondary lookup = index traversal + PK index traversal        |  |
|  |  * WHY? Row locations change (page splits, VACUUM)                |  |
|  |         PK value doesn't change                                   |  |
|  |                                                                   |  |
|  |  COST: Secondary index lookup = 2x B+Tree traversals              |  |
|  |  BENEFIT: No index maintenance when rows move                     |  |
|  |                                                                   |  |
|  |  Random UUID PK = DISASTER                                        |  |
|  |  > Inserts cause random page splits                               |  |
|  |  > Index size balloons                                            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  POSTGRESQL (Heap + Separate Indexes)                                   |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  TABLE (Heap):                                                    |  |
|  |  * Rows stored in insertion order (unordered)                     |  |
|  |  * No clustered index by default                                  |  |
|  |                                                                   |  |
|  |  INDEX (any, including PK):                                       |  |
|  |  * Leaf nodes contain (page_id, row_offset) = ctid                |  |
|  |  * All indexes are "secondary"                                    |  |
|  |                                                                   |  |
|  |  ANY LOOKUP: Index traversal + heap fetch                         |  |
|  |                                                                   |  |
|  |  COST: Even PK lookup needs heap fetch                            |  |
|  |  BENEFIT: All indexes equal, simpler model                        |  |
|  |           Random inserts OK (no clustered order)                  |  |
|  |                                                                   |  |
|  |  MVCC OVERHEAD: Dead tuples in heap until VACUUM                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### UUID VS AUTO-INCREMENT PRIMARY KEYS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE UUID PROBLEM IN B+TREES                                            |
|                                                                         |
|  AUTO-INCREMENT ID: 1, 2, 3, 4, 5, 6...                                 |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Inserts always go to rightmost leaf:                             |  |
|  |                                                                   |  |
|  |  [1,2,3] > [4,5,6] > [7,8,9] > [10,11,12] < NEW                   |  |
|  |                                                                   |  |
|  |  Y Sequential writes (one page at a time)                         |  |
|  |  Y Pages fill up completely (no waste)                            |  |
|  |  Y Pages cached in memory (recently written)                      |  |
|  |  Y Minimal page splits                                            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  RANDOM UUID: 550e8400-e29b-41d4-a716-446655440000                      |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Inserts scattered randomly:                                      |  |
|  |                                                                   |  |
|  |  Insert UUID starting with "1..." > page 3                        |  |
|  |  Insert UUID starting with "a..." > page 47                       |  |
|  |  Insert UUID starting with "5..." > page 21                       |  |
|  |  Insert UUID starting with "f..." > page 89                       |  |
|  |                                                                   |  |
|  |  X Random writes (different page each time)                       |  |
|  |  X Every insert needs different page loaded                       |  |
|  |  X More page splits (inserting into full pages)                   |  |
|  |  X Index fragmentation (50% page fill typical)                    |  |
|  |  X Terrible cache hit rate                                        |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  BENCHMARK IMPACT (MySQL InnoDB):                                       |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Metric              Auto-Inc       Random UUID                   |  |
|  |  -----------------------------------------------------------------|  |
|  |  Insert rate         50,000/s       5,000/s                       |  |
|  |  Index size          1 GB           2 GB (fragmented)             |  |
|  |  Page reads/query    3-4            10+ (scattered)               |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  SOLUTIONS:                                                             |
|  * Use UUIDv7 (timestamp-prefixed, sortable)                            |
|  * Use ULID (Universally Unique Lexicographically Sortable ID)          |
|  * Use Snowflake IDs (time-ordered)                                     |
|  * Keep UUID but use auto-increment as clustered key                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 20.4: QUERY PLANNER AND EXPLAIN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  QUERY EXECUTION PIPELINE                                               |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  SQL Query                                                        |  |
|  |      |                                                            |  |
|  |      v                                                            |  |
|  |  +-------------+                                                  |  |
|  |  |   PARSER    |  Syntax check, build parse tree                  |  |
|  |  +------+------+                                                  |  |
|  |         |                                                         |  |
|  |         v                                                         |  |
|  |  +-------------+                                                  |  |
|  |  |  ANALYZER   |  Resolve names, check permissions                |  |
|  |  +------+------+                                                  |  |
|  |         |                                                         |  |
|  |         v                                                         |  |
|  |  +-------------+                                                  |  |
|  |  |  REWRITER   |  Apply views, rules                              |  |
|  |  +------+------+                                                  |  |
|  |         |                                                         |  |
|  |         v                                                         |  |
|  |  +-------------+                                                  |  |
|  |  |  PLANNER/   |  Generate execution plans                        |  |
|  |  |  OPTIMIZER  |  Estimate costs, pick best plan                  |  |
|  |  +------+------+                                                  |  |
|  |         |                                                         |  |
|  |         v                                                         |  |
|  |  +-------------+                                                  |  |
|  |  |  EXECUTOR   |  Execute the chosen plan                         |  |
|  |  +-------------+                                                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SCAN TYPES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THREE MAIN SCAN TYPES                                                  |
|                                                                         |
|  1. SEQUENTIAL SCAN (Table Scan / Full Table Scan)                      |
|  ==================================================                     |
|  Read every row in the table                                            |
|                                                                         |
|  EXPLAIN: Seq Scan on users                                             |
|                                                                         |
|  WHEN USED:                                                             |
|  * No suitable index                                                    |
|  * Query returns large % of table                                       |
|  * Small tables (index overhead not worth it)                           |
|                                                                         |
|  COST: O(n) - reads all pages                                           |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. INDEX SCAN                                                          |
|  =================                                                      |
|  Use index to find matching rows, then fetch from heap                  |
|                                                                         |
|  EXPLAIN: Index Scan using idx_email on users                           |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. Traverse B+Tree index                                         |  |
|  |  2. For each matching key, get row pointer                        |  |
|  |  3. Fetch row from heap page                                      |  |
|  |                                                                   |  |
|  |  Index: [alice@...] --> (page 5, row 3)                           |  |
|  |                              |                                    |  |
|  |                              v                                    |  |
|  |  Heap:  Page 5 [...][row 3][...]                                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  COST: O(log n) for index + O(k) heap fetches                           |
|  PROBLEM: Random I/O if many matches scattered across pages             |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. INDEX ONLY SCAN                                                     |
|  =======================                                                |
|  All columns needed are IN the index - no heap access!                  |
|                                                                         |
|  EXPLAIN: Index Only Scan using idx_email_name on users                 |
|                                                                         |
|  Covering index: CREATE INDEX idx ON users(email) INCLUDE (name);       |
|  Query: SELECT email, name FROM users WHERE email = '...'               |
|                                                                         |
|  > Answered entirely from index pages                                   |
|  > FASTEST option when applicable                                       |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  4. BITMAP INDEX SCAN                                                   |
|  =========================                                              |
|  Build bitmap of matching rows, then fetch in page order                |
|                                                                         |
|  EXPLAIN:                                                               |
|    Bitmap Heap Scan on users                                            |
|      -> Bitmap Index Scan on idx_status                                 |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. Scan index, build bitmap of matching pages                    |  |
|  |     Page bitmap: [0,1,0,1,1,0,0,1,0,1]                            |  |
|  |                    ^   ^ ^     ^   ^                              |  |
|  |                    |   +-+-----+---+                              |  |
|  |                    |     |     |                                  |  |
|  |  2. Fetch pages in order: 1, 3, 4, 7, 9                           |  |
|  |     (Sequential-ish I/O instead of random)                        |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  WHEN USED:                                                             |
|  * Moderate selectivity (too many rows for index scan)                  |
|  * Combining multiple indexes (AND/OR conditions)                       |
|  * WHERE status = 'active' AND age > 25                                 |
|                                                                         |
|  BITMAP AND/OR: Can combine multiple indexes                            |
|  > Bitmap on idx_status AND bitmap on idx_age                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### EXPLAIN ANALYZE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  READING EXPLAIN OUTPUT                                                 |
|                                                                         |
|  EXPLAIN ANALYZE                                                        |
|  SELECT * FROM users WHERE email = 'alice@example.com';                 |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Index Scan using idx_email on users                              |  |
|  |    (cost=0.42..8.44 rows=1 width=72)                              |  |
|  |    (actual time=0.025..0.026 rows=1 loops=1)                      |  |
|  |    Index Cond: (email = 'alice@example.com')                      |  |
|  |  Planning Time: 0.085 ms                                          |  |
|  |  Execution Time: 0.042 ms                                         |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  READING THE OUTPUT:                                                    |
|                                                                         |
|  cost=0.42..8.44                                                        |
|       +--+--++-+-+                                                      |
|     startup   total                                                     |
|     cost      cost                                                      |
|                                                                         |
|  * Startup cost: Time before first row returned                         |
|  * Total cost: Time to return all rows                                  |
|  * Cost in arbitrary units (not seconds)                                |
|                                                                         |
|  rows=1: Estimated rows returned                                        |
|  width=72: Average row size in bytes                                    |
|                                                                         |
|  actual time=0.025..0.026: Real execution time (ms)                     |
|  rows=1: Actual rows returned                                           |
|  loops=1: Times this node was executed                                  |
|                                                                         |
|  RED FLAGS IN EXPLAIN:                                                  |
|  * Seq Scan on large table                                              |
|  * Rows estimate wildly off from actual                                 |
|  * Nested Loop with large outer table                                   |
|  * Sort on large dataset (disk sort)                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### OPTIMIZER DECISIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHEN DOES OPTIMIZER CHOOSE EACH SCAN?                                  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Selectivity (% of table)    Likely Scan Type                     |  |
|  |  -----------------------------------------------------------------|  |
|  |  < 1%                        Index Scan                           |  |
|  |  1-10%                       Bitmap Index Scan                    |  |
|  |  > 10-20%                    Sequential Scan                      |  |
|  |                                                                   |  |
|  |  (Thresholds vary by data distribution, row size, etc.)           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  WHY NOT ALWAYS USE INDEX?                                              |
|                                                                         |
|  If query returns 50% of table:                                         |
|  * Index scan: 50% x N random page reads (slow!)                        |
|  * Seq scan: N sequential page reads (faster!)                          |
|                                                                         |
|  Random I/O: ~10ms per page (HDD), ~0.1ms (SSD)                         |
|  Sequential I/O: ~0.1ms per page (HDD), ~0.01ms (SSD)                   |
|                                                                         |
|  STATISTICS: Optimizer uses table statistics                            |
|  * pg_stats in PostgreSQL                                               |
|  * ANALYZE command updates statistics                                   |
|  * Stale stats = bad query plans!                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 20.5: LOCKING DEEP DIVE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SHARED vs EXCLUSIVE LOCKS                                              |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  SHARED LOCK (S-Lock / Read Lock)                                 |  |
|  |  ====================================                             |  |
|  |                                                                   |  |
|  |  * Multiple transactions can hold S-lock simultaneously           |  |
|  |  * Prevents writes while reading                                  |  |
|  |  * Other readers allowed                                          |  |
|  |                                                                   |  |
|  |  Example: SELECT ... FOR SHARE;                                   |  |
|  |                                                                   |  |
|  |  Txn A: S-Lock on row 1 Y                                         |  |
|  |  Txn B: S-Lock on row 1 Y (allowed, both reading)                 |  |
|  |  Txn C: X-Lock on row 1 X (blocked, waiting)                      |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  EXCLUSIVE LOCK (X-Lock / Write Lock)                             |  |
|  |  ========================================                         |  |
|  |                                                                   |  |
|  |  * Only ONE transaction can hold X-lock                           |  |
|  |  * Blocks all other readers AND writers                           |  |
|  |                                                                   |  |
|  |  Example: SELECT ... FOR UPDATE;                                  |  |
|  |           UPDATE / DELETE statements                              |  |
|  |                                                                   |  |
|  |  Txn A: X-Lock on row 1 Y                                         |  |
|  |  Txn B: S-Lock on row 1 X (blocked)                               |  |
|  |  Txn C: X-Lock on row 1 X (blocked)                               |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  LOCK COMPATIBILITY MATRIX:                                             |
|  +------------------------------------------------------------------+   |
|  |                  Requested Lock                                  |   |
|  |              +-------------+-------------+                       |   |
|  |              |   Shared    |  Exclusive  |                       |   |
|  |  +-----------+-------------+-------------+                       |   |
|  |  |  Shared   |   Y Grant   |   X Wait   |                        |   |
|  |  |  Held     |             |             |                       |   |
|  |  +-----------+-------------+-------------+                       |   |
|  |  | Exclusive |   X Wait   |   X Wait   |                         |   |
|  |  |  Held     |             |             |                       |   |
|  |  +-----------+-------------+-------------+                       |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

DEADLOCKS
---------

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DEADLOCK: Circular wait between transactions                           |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Time    Transaction A              Transaction B                 |  |
|  |  ----    -------------              -------------                 |  |
|  |  T1      BEGIN                      BEGIN                         |  |
|  |  T2      UPDATE row 1 (X-Lock) Y    UPDATE row 2 (X-Lock) Y       |  |
|  |  T3      UPDATE row 2 ... WAIT      UPDATE row 1 ... WAIT         |  |
|  |          ^ waiting for B            ^ waiting for A               |  |
|  |                                                                   |  |
|  |          +---------------------------------------------+          |  |
|  |          |         A ---waits for---> B                |          |  |
|  |          |         ^                   |                |         |  |
|  |          |         +---waits for-------+                |         |  |
|  |          |              DEADLOCK!                       |         |  |
|  |          +---------------------------------------------+          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  DEADLOCK DETECTION:                                                    |
|  * Database periodically checks for cycles in wait graph                |
|  * When detected: one transaction is aborted (victim)                   |
|  * Victim selection: usually youngest/least work done                   |
|                                                                         |
|  PREVENTION STRATEGIES:                                                 |
|  * Lock resources in consistent order (always row 1 before row 2)       |
|  * Use shorter transactions                                             |
|  * Use lock timeouts                                                    |
|  * Use optimistic locking instead                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TWO-PHASE LOCKING (2PL)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TWO-PHASE LOCKING PROTOCOL                                             |
|                                                                         |
|  Guarantees SERIALIZABILITY (correct concurrent execution)              |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Number of                                                        |  |
|  |  Locks Held                                                       |  |
|  |       ^                                                           |  |
|  |       |          /\                                               |  |
|  |       |         /  \                                              |  |
|  |       |        /    \                                             |  |
|  |       |       /      \                                            |  |
|  |       |      /        \                                           |  |
|  |       |     /          \                                          |  |
|  |       |----+            +---------------------                    |  |
|  |       +------------------------------------------> Time           |  |
|  |            |           |              |                           |  |
|  |         Growing     Lock Point     Shrinking                      |  |
|  |         Phase       (commit)       Phase                          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  PHASE 1 - GROWING PHASE:                                               |
|  * Transaction acquires locks as needed                                 |
|  * Cannot release any locks yet                                         |
|                                                                         |
|  PHASE 2 - SHRINKING PHASE:                                             |
|  * Transaction releases locks                                           |
|  * Cannot acquire any new locks                                         |
|                                                                         |
|  VARIANTS:                                                              |
|                                                                         |
|  Basic 2PL:                                                             |
|  * Release locks during shrinking phase                                 |
|  * Problem: Cascading aborts possible                                   |
|                                                                         |
|  Strict 2PL (S2PL):                                                     |
|  * Hold X-locks until commit/abort                                      |
|  * Prevents cascading aborts                                            |
|  * Most databases use this                                              |
|                                                                         |
|  Rigorous 2PL (Strong S2PL):                                            |
|  * Hold ALL locks until commit/abort                                    |
|  * Even S-locks held until end                                          |
|  * Simplest to implement                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 20.6: DATABASE CONNECTION POOLING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM                                                            |
|                                                                         |
|  Creating database connection is EXPENSIVE:                             |
|                                                                         |
|  1. TCP 3-way handshake                                                 |
|  2. TLS handshake (if SSL)                                              |
|  3. Authentication                                                      |
|  4. Session initialization                                              |
|  5. Memory allocation on server                                         |
|                                                                         |
|  TIME: 50-100ms per connection                                          |
|                                                                         |
|  WITHOUT POOLING:                                                       |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Request 1: [Connect 100ms][Query 10ms][Close]                    |  |
|  |  Request 2: [Connect 100ms][Query 10ms][Close]                    |  |
|  |  Request 3: [Connect 100ms][Query 10ms][Close]                    |  |
|  |                                                                   |  |
|  |  Total: 330ms for 30ms of actual work!                            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CONNECTION POOL ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONNECTION POOLING                                                     |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Application                  Connection Pool      Database       |  |
|  |  -----------                  -----------------    ---------      |  |
|  |                                                                   |  |
|  |  Thread 1 ---> getConnection() --> [Conn 1] ----> DB Server       |  |
|  |                     |              [Conn 2] ---->                 |  |
|  |  Thread 2 --------->|              [Conn 3] ---->                 |  |
|  |                     |              [Conn 4] ---->                 |  |
|  |  Thread 3 --------->|                                             |  |
|  |                     |                                             |  |
|  |  Thread 4 --> Wait... (pool exhausted)                            |  |
|  |                                                                   |  |
|  |  Thread 1: releaseConnection()                                    |  |
|  |  Thread 4: gets Conn 1 ------------------------->                 |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  WITH POOLING:                                                          |
|  Request 1: [Get conn 0.1ms][Query 10ms][Return conn]                   |
|  Request 2: [Get conn 0.1ms][Query 10ms][Return conn]                   |
|  Request 3: [Get conn 0.1ms][Query 10ms][Return conn]                   |
|                                                                         |
|  Total: 30.3ms vs 330ms!                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### POOL SIZING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HOW MANY CONNECTIONS?                                                  |
|                                                                         |
|  TOO FEW: Requests wait, throughput limited                             |
|  TOO MANY: Database overwhelmed, context switching                      |
|                                                                         |
|  FORMULA (starting point):                                              |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  connections = (core_count * 2) + effective_spindle_count         |  |
|  |                                                                   |  |
|  |  For SSD (effective spindle = 0):                                 |  |
|  |  connections ~ core_count * 2                                     |  |
|  |                                                                   |  |
|  |  Example: 4 core server > ~8-10 connections optimal               |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  COUNTERINTUITIVE: More connections ! more throughput                   |
|                                                                         |
|  WHY?                                                                   |
|  * CPU context switching overhead                                       |
|  * Lock contention increases                                            |
|  * Memory per connection (~10MB in PostgreSQL)                          |
|  * Disk I/O doesn't parallelize infinitely                              |
|                                                                         |
|  POOL CONFIGURATION:                                                    |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Parameter         Typical Value    Notes                         |  |
|  |  -----------------------------------------------------------------|  |
|  |  min_pool_size     5               Keep warm connections          |  |
|  |  max_pool_size     10-20           Based on DB capacity           |  |
|  |  connection_timeout 30s            Wait before giving up          |  |
|  |  idle_timeout      10min           Close idle connections         |  |
|  |  max_lifetime      30min           Recycle connections            |  |
|  |  validation_query  SELECT 1       Check connection valid          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CONNECTION POOLERS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  EXTERNAL CONNECTION POOLERS                                            |
|                                                                         |
|  For PostgreSQL:                                                        |
|                                                                         |
|  PgBouncer:                                                             |
|  * Lightweight (low memory)                                             |
|  * Session, transaction, or statement pooling modes                     |
|  * Single-threaded (run multiple instances)                             |
|                                                                         |
|  Pgpool-II:                                                             |
|  * Load balancing                                                       |
|  * Replication                                                          |
|  * Connection pooling                                                   |
|  * Heavier weight                                                       |
|                                                                         |
|  For MySQL:                                                             |
|                                                                         |
|  ProxySQL:                                                              |
|  * Query routing                                                        |
|  * Read/write splitting                                                 |
|  * Connection pooling                                                   |
|                                                                         |
|  Application-Level Poolers:                                             |
|  * HikariCP (Java - fastest)                                            |
|  * SQLAlchemy pool (Python)                                             |
|  * pgx pool (Go)                                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 20.7: CREATE INDEX CONCURRENTLY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM: Regular CREATE INDEX blocks writes                        |
|                                                                         |
|  CREATE INDEX idx_email ON users(email);                                |
|                                                                         |
|  During index creation:                                                 |
|  * Reads: OK                                                            |
|  * Writes: BLOCKED!                                                     |
|                                                                         |
|  For large tables: Index creation can take minutes/hours                |
|  Production impact: Application writes fail                             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  CONCURRENT INDEX CREATION (PostgreSQL)                           |  |
|  |                                                                   |  |
|  |  CREATE INDEX CONCURRENTLY idx_email ON users(email);             |  |
|  |                                                                   |  |
|  |  How it works:                                                    |  |
|  |  1. First pass: Build index from current snapshot                 |  |
|  |  2. Wait for concurrent transactions to complete                  |  |
|  |  3. Second pass: Add rows changed during first pass               |  |
|  |  4. Mark index as valid                                           |  |
|  |                                                                   |  |
|  |  During creation:                                                 |  |
|  |  * Reads: OK                                                      |  |
|  |  * Writes: OK (not blocked!)                                      |  |
|  |                                                                   |  |
|  |  TRADE-OFFS:                                                      |  |
|  |  Y No write blocking                                              |  |
|  |  X Takes 2-3x longer                                              |  |
|  |  X More I/O                                                       |  |
|  |  X Cannot run in transaction                                      |  |
|  |  X If fails, leaves invalid index (must drop manually)            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  MYSQL (Online DDL):                                                    |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  ALTER TABLE users ADD INDEX idx_email(email),                    |  |
|  |  ALGORITHM=INPLACE, LOCK=NONE;                                    |  |
|  |                                                                   |  |
|  |  ALGORITHM options:                                               |  |
|  |  * INPLACE: Modify table in place (no copy)                       |  |
|  |  * COPY: Create new table, copy data                              |  |
|  |  * INSTANT: Metadata change only (MySQL 8.0+)                     |  |
|  |                                                                   |  |
|  |  LOCK options:                                                    |  |
|  |  * NONE: Allow reads and writes                                   |  |
|  |  * SHARED: Allow reads, block writes                              |  |
|  |  * EXCLUSIVE: Block all                                           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 20

