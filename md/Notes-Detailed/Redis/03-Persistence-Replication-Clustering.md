# REDIS
*Chapter 3: Persistence, Replication, and Clustering*

Redis is not just a cache -- it can be a durable database. This chapter
covers how Redis persists data, replicates for high availability, and
scales horizontally with clustering.

## SECTION 3.1: PERSISTENCE

### RDB (REDIS DATABASE SNAPSHOTS)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RDB = Point-in-time snapshot of entire dataset saved to disk.          |
|                                                                         |
|  HOW IT WORKS:                                                          |
|  1. Redis forks a child process (copy-on-write)                         |
|  2. Child writes all data to a temp .rdb file                           |
|  3. When done, replaces old dump.rdb atomically                         |
|  4. Parent continues serving requests uninterrupted                     |
|                                                                         |
|  CONFIG:                                                                |
|  save 900 1        -- snapshot if >= 1 key changed in 900 seconds       |
|  save 300 10       -- snapshot if >= 10 keys changed in 300 seconds     |
|  save 60 10000     -- snapshot if >= 10000 keys changed in 60 seconds   |
|                                                                         |
|  MANUAL TRIGGER:                                                        |
|  BGSAVE             -- background save (non-blocking)                   |
|  SAVE               -- foreground save (BLOCKS everything, avoid!)      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  PROS:                                                                  |
|  * Compact single file (easy backup, transfer, restore)                 |
|  * Fast restart (load binary file into memory)                          |
|  * fork() means parent is barely affected                               |
|                                                                         |
|  CONS:                                                                  |
|  * Data loss between snapshots (last 1-5 minutes typically)             |
|  * fork() can be slow with large datasets (10+ GB)                      |
|  * fork() doubles memory briefly (copy-on-write, but peak can spike)    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### AOF (APPEND-ONLY FILE)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  AOF = Log every write command to disk.                                 |
|                                                                         |
|  HOW IT WORKS:                                                          |
|  * Every write command (SET, INCR, LPUSH, etc.) is appended to file     |
|  * On restart, Redis replays the AOF to rebuild state                   |
|                                                                         |
|  FSYNC POLICIES:                                                        |
|                                                                         |
|  +------------------+---------------+-------------------+               |
|  | Policy           | Data Safety   | Performance       |               |
|  +------------------+---------------+-------------------+               |
|  | appendfsync always | Best (zero  | Slowest           |               |
|  |                    | data loss)  | (fsync per write) |               |
|  +------------------+---------------+-------------------+               |
|  | appendfsync everysec | Good (lose| Good (DEFAULT,    |               |
|  |                    | <= 1 second)| fsync per second) |               |
|  +------------------+---------------+-------------------+               |
|  | appendfsync no     | Worst (OS   | Fastest           |               |
|  |                    | decides)    | (no forced fsync) |               |
|  +------------------+---------------+-------------------+               |
|                                                                         |
|  AOF REWRITE:                                                           |
|  * AOF file grows over time (redundant commands)                        |
|  * Rewrite compacts it: 100 INCRs on "counter" -> SET counter 100       |
|  * Triggered automatically (auto-aof-rewrite-percentage 100)            |
|  * BGREWRITEAOF command triggers manually                               |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  REDIS 7.0+ MULTI-PART AOF:                                             |
|  * AOF split into base file + incremental files                         |
|  * Rewrite only modifies base file                                      |
|  * Safer and faster rewrites                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### RDB vs AOF

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +------------------+---------------------------+--------------------+  |
|  | Feature          | RDB                       | AOF                |  |
|  +------------------+---------------------------+--------------------+  |
|  | Format           | Binary snapshot            | Text log of cmds  |  |
|  | Data safety      | Lose minutes of data      | Lose <= 1 second   |  |
|  | File size        | Compact                   | Larger             |  |
|  | Restart speed    | Fast (load binary)        | Slower (replay)    |  |
|  | Write perf       | No impact (background)    | Slight (fsync)     |  |
|  | Backup           | Easy (single file)        | Harder             |  |
|  +------------------+---------------------------+--------------------+  |
|                                                                         |
|  RECOMMENDATION:                                                        |
|  * Cache only: No persistence (or RDB for warm restarts)                |
|  * Data store: AOF with everysec fsync + periodic RDB backups           |
|  * Maximum safety: Both RDB + AOF enabled                               |
|    (Redis uses AOF for recovery since it's more complete)               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.2: REPLICATION

```
+--------------------------------------------------------------------------+
|                                                                          |
|  REDIS REPLICATION = Master-Replica (formerly master-slave)              |
|                                                                          |
|  +----------+     +----------+     +----------+                          |
|  |  MASTER  | --> | REPLICA 1| --> | REPLICA 3|  (chained)               |
|  | (read +  |     | (read    |     | (read    |                          |
|  |  write)  | --> | only)    |     | only)    |                          |
|  +----------+     +----------+     +----------+                          |
|                   | REPLICA 2|                                           |
|                   | (read    |                                           |
|                   | only)    |                                           |
|                   +----------+                                           |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  HOW IT WORKS:                                                           |
|                                                                          |
|  1. FULL SYNC (initial or after long disconnect):                        |
|     * Master runs BGSAVE, creates RDB snapshot                           |
|     * Sends RDB to replica                                               |
|     * Replica loads RDB, then receives buffered writes                   |
|                                                                          |
|  2. PARTIAL SYNC (short disconnect):                                     |
|     * Master has a replication backlog (in-memory buffer)                |
|     * Replica sends its replication offset                               |
|     * Master sends only the missed commands (no full sync!)              |
|                                                                          |
|  3. CONTINUOUS:                                                          |
|     * Master sends every write command to all replicas                   |
|     * Replication is ASYNCHRONOUS by default                             |
|     * WAIT command for synchronous replication (blocks)                  |
|                                                                          |
|  -------------------------------------------------------------------     |
|                                                                          |
|  CONFIG:                                                                 |
|  replicaof 192.168.1.100 6379   -- make this instance a replica          |
|  replica-read-only yes           -- replicas reject writes (default)     |
|  repl-backlog-size 1mb           -- backlog for partial sync             |
|  min-replicas-to-write 1         -- require N replicas for writes        |
|  min-replicas-max-lag 10         -- max lag (seconds) for above          |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 3.3: REDIS SENTINEL (HIGH AVAILABILITY)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SENTINEL = Automatic failover for Redis master-replica setups.         |
|                                                                         |
|  +----------+    +----------+    +----------+                           |
|  |Sentinel 1|    |Sentinel 2|    |Sentinel 3|  (monitoring)             |
|  +----+-----+    +----+-----+    +----+-----+                           |
|       |               |               |                                 |
|       v               v               v                                 |
|  +----------+    +----------+    +----------+                           |
|  |  MASTER  |    | REPLICA 1|    | REPLICA 2|                           |
|  +----------+    +----------+    +----------+                           |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  SENTINEL RESPONSIBILITIES:                                             |
|                                                                         |
|  1. MONITORING:  Checks if master and replicas are alive                |
|  2. NOTIFICATION: Alerts admins when something goes wrong               |
|  3. FAILOVER:    If master fails:                                       |
|     a. Sentinels vote to confirm master is down (quorum)                |
|     b. One sentinel is elected leader                                   |
|     c. Leader promotes a replica to new master                          |
|     d. Other replicas reconfigure to follow new master                  |
|     e. Clients are notified of new master address                       |
|  4. CONFIG PROVIDER: Clients ask sentinel for current master            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  FAILOVER TIMELINE:                                                     |
|  * Master goes down                                                     |
|  * after down-after-milliseconds (default 30s) -> marked as SDOWN       |
|  * When quorum sentinels agree -> marked as ODOWN                       |
|  * Sentinel leader elected -> promotes replica                          |
|  * Total failover time: 30-60 seconds typically                         |
|                                                                         |
|  MINIMUM SETUP: 3 sentinel instances (for quorum of 2)                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.4: REDIS CLUSTER (HORIZONTAL SCALING)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REDIS CLUSTER = Automatic data sharding across multiple masters.       |
|                                                                         |
|  +-------------------+  +-------------------+  +-------------------+    |
|  | Master 1          |  | Master 2          |  | Master 3          |    |
|  | Slots 0-5460      |  | Slots 5461-10922  |  | Slots 10923-16383 |    |
|  |   |               |  |   |               |  |   |               |    |
|  |   v               |  |   v               |  |   v               |    |
|  | Replica 1A        |  | Replica 2A        |  | Replica 3A        |    |
|  +-------------------+  +-------------------+  +-------------------+    |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  HASH SLOTS:                                                            |
|  * 16384 total hash slots distributed across masters                    |
|  * Key assignment: CRC16(key) % 16384 = slot number                     |
|  * Each master owns a range of slots                                    |
|  * Hash tags: {user:123}.profile -> hash on "user:123" only             |
|    (ensures related keys go to same slot)                               |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  CLUSTER TOPOLOGY:                                                      |
|  * Minimum: 3 masters + 3 replicas = 6 nodes                            |
|  * Each master has 1+ replicas for failover                             |
|  * Nodes communicate via cluster bus (gossip protocol, port+10000)      |
|  * Clients can connect to ANY node, get redirected if needed            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  REDIRECTIONS:                                                          |
|                                                                         |
|  Client -> Node 1: GET user:500                                         |
|  Node 1 -> Client: -MOVED 7365 192.168.1.102:6379                       |
|  Client -> Node 2: GET user:500                                         |
|  Node 2 -> Client: "John"                                               |
|                                                                         |
|  * MOVED: slot permanently belongs to another node                      |
|  * ASK: slot is being migrated, try other node once                     |
|  * Smart clients cache slot-to-node mapping (avoid redirects)           |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  LIMITATIONS:                                                           |
|  * Multi-key commands only work if ALL keys are in same slot            |
|  * No multi-database support (only DB 0)                                |
|  * Larger cluster = more gossip overhead                                |
|  * Max recommended: ~1000 nodes                                         |
|  * Transactions/Lua scripts: only keys on the same node                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CLUSTER vs SENTINEL

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +------------------+----------------------------+-------------------+  |
|  | Feature          | Sentinel                   | Cluster           |  |
|  +------------------+----------------------------+-------------------+  |
|  | Sharding         | No (single master)         | Yes (multi-master)|  |
|  | HA               | Yes (automatic failover)   | Yes (per-shard)   |  |
|  | Data size        | Limited by one server RAM  | Aggregate RAM     |  |
|  | Write scaling    | No (single write point)    | Yes (multi-write) |  |
|  | Read scaling     | Yes (read from replicas)   | Yes               |  |
|  | Complexity       | Lower                      | Higher            |  |
|  | Multi-key ops    | All keys available         | Same slot only    |  |
|  +------------------+----------------------------+-------------------+  |
|                                                                         |
|  USE SENTINEL: Dataset fits in one server's RAM (< 100 GB).             |
|  USE CLUSTER: Dataset too large for one server, need write scaling.     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.5: MEMORY OPTIMIZATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MEMORY ANALYSIS:                                                       |
|                                                                         |
|  INFO memory                     -- overall memory stats                |
|  MEMORY USAGE key                -- bytes used by a specific key        |
|  MEMORY DOCTOR                   -- memory health report                |
|  redis-cli --bigkeys             -- find largest keys                   |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  MEMORY SAVING TECHNIQUES:                                              |
|                                                                         |
|  1. Use compact encodings                                               |
|     * Small hashes -> listpack (much less overhead than hashtable)      |
|     * Tune: hash-max-listpack-entries 128                               |
|     * Tune: hash-max-listpack-value 64                                  |
|                                                                         |
|  2. Short key names                                                     |
|     * "user:123:session" vs "u:123:s" (saves bytes per key)             |
|     * Matters when millions of keys                                     |
|                                                                         |
|  3. Use hashes to group small values                                    |
|     * Instead of: SET user:1:name "John", SET user:1:age "30"           |
|     * Use: HSET user:1 name "John" age "30"                             |
|     * 1 key overhead instead of 2                                       |
|                                                                         |
|  4. Use integers where possible                                         |
|     * Redis shares integer objects 0-9999 (no allocation)               |
|                                                                         |
|  5. Set maxmemory + eviction policy                                     |
|     * maxmemory 4gb                                                     |
|     * maxmemory-policy allkeys-lru                                      |
|                                                                         |
|  6. Compress values client-side                                         |
|     * gzip/lz4 large JSON before storing                                |
|     * Trade CPU for memory                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```
