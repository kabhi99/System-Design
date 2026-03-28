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
+------------------------------------------------------------------------+
|                                                                        |
|  REDIS REPLICATION = Master-Replica (formerly master-slave)            |
|                                                                        |
|  +----------+     +----------+     +----------+                        |
|  |  MASTER  | --> | REPLICA 1| --> | REPLICA 3|  (chained)             |
|  | (read +  |     | (read    |     | (read    |                        |
|  |  write)  | --> | only)    |     | only)    |                        |
|  +----------+     +----------+     +----------+                        |
|                   | REPLICA 2|                                         |
|                   | (read    |                                         |
|                   | only)    |                                         |
|                   +----------+                                         |
|                                                                        |
|  * Master handles ALL writes                                           |
|  * Replicas are READ-ONLY copies                                       |
|  * Replication is ASYNCHRONOUS by default                              |
|                                                                        |
|  ================================================================      |
|  IS IT SYNCHRONOUS? NO — ASYNC BY DEFAULT                              |
|  ================================================================      |
|                                                                        |
|  What happens when a client writes to master:                          |
|                                                                        |
|  Client          Master                 Replica                        |
|    |                |                      |                           |
|    |-- SET k v ---->|                      |                           |
|    |                |-- (write to memory)   |                          |
|    |<-- OK ---------|                      |                           |
|    |                |                      |                           |
|    |  (client is    |-- SET k v ---------->|  (async, in background)   |
|    |   already done)|                      |-- (apply to memory)       |
|    |                |                      |                           |
|                                                                        |
|  KEY POINT: The master responds OK to the client BEFORE the            |
|  replica receives the write. The client does NOT wait for              |
|  replication to complete.                                              |
|                                                                        |
|  This means:                                                           |
|  * Writes are FAST (no waiting for replica ack)                        |
|  * Replica may LAG behind master (eventual consistency)                |
|  * If master crashes, unsynced writes are LOST                         |
|                                                                        |
|  -------------------------------------------------------------------   |
|  DATA LOSS SCENARIO (why async replication is risky)                   |
|  -------------------------------------------------------------------   |
|                                                                        |
|  t=0  Client writes SET order:789 "paid" to Master   -> OK             |
|  t=1  Master queues command to send to Replica                         |
|  t=2  MASTER CRASHES (before sending to Replica)                       |
|  t=3  Sentinel promotes Replica to new Master                          |
|  t=4  New Master does NOT have order:789 = "paid"                      |
|                                                                        |
|  Result: Client thinks order is paid. Database says it's not.          |
|  This is the fundamental trade-off of async replication.               |
|                                                                        |
|  -------------------------------------------------------------------   |
|  SEMI-SYNCHRONOUS REPLICATION (WAIT command)                           |
|  -------------------------------------------------------------------   |
|                                                                        |
|  Redis is NOT fully synchronous, but WAIT gives you a middle ground:   |
|                                                                        |
|  SET order:789 "paid"                                                  |
|  WAIT 1 5000                                                           |
|    |    |                                                              |
|    |    +-- timeout: 5000ms (give up after 5 seconds)                  |
|    +------- wait for at least 1 replica to acknowledge                 |
|                                                                        |
|  Client          Master                 Replica                        |
|    |                |                      |                           |
|    |-- SET k v ---->|                      |                           |
|    |                |-- (write to memory)   |                          |
|    |                |-- SET k v ---------->|                           |
|    |                |                      |-- (apply to memory)       |
|    |                |<-- ACK --------------|                           |
|    |<-- 1 ----------|  (1 replica acked)   |                           |
|    |                |                      |                           |
|    | (NOW client    |                      |                           |
|    |  can proceed)  |                      |                           |
|                                                                        |
|  WAIT returns the NUMBER of replicas that acknowledged.                |
|  If it returns 0, no replica got the write before timeout.             |
|                                                                        |
|  IMPORTANT: WAIT does NOT make the write more durable on master.       |
|  It only tells you whether replicas received it. If master crashes     |
|  after WAIT returns but before replica is promoted, the write          |
|  survives on the replica.                                              |
|                                                                        |
|  -------------------------------------------------------------------   |
|  CONFIG FOR WRITE SAFETY                                               |
|  -------------------------------------------------------------------   |
|                                                                        |
|  min-replicas-to-write 1                                               |
|    Master REJECTS writes if fewer than 1 replica is connected          |
|    and healthy. Prevents writing to a master that lost all replicas.   |
|                                                                        |
|  min-replicas-max-lag 10                                               |
|    A replica is considered "healthy" only if its lag is < 10 seconds.  |
|    Combined with above: "reject writes if no replica is within 10s."   |
|                                                                        |
|  These two settings TOGETHER prevent the split-brain data loss         |
|  scenario where an isolated master keeps accepting writes.             |
|                                                                        |
|  ================================================================      |
|  REPLICATION PROCESS — STEP BY STEP                                    |
|  ================================================================      |
|                                                                        |
|  -------------------------------------------------------------------   |
|  PHASE 1: FULL SYNC (initial connect or long disconnect)               |
|  -------------------------------------------------------------------   |
|                                                                        |
|  Replica                        Master                                 |
|    |                              |                                    |
|    |-- PSYNC ? -1 -------------->|  ("I'm new, full sync please")      |
|    |                              |                                    |
|    |                              |-- fork() child process             |
|    |                              |-- BGSAVE (create RDB snapshot)     |
|    |                              |   (master keeps serving clients)   |
|    |                              |                                    |
|    |                              |-- buffer new writes that arrive    |
|    |                              |   during BGSAVE                    |
|    |                              |                                    |
|    |<-- RDB file (bulk transfer) -|  (send snapshot to replica)        |
|    |                              |                                    |
|    |-- (flush old data)           |                                    |
|    |-- (load RDB into memory)     |                                    |
|    |                              |                                    |
|    |<-- buffered writes ---------|  (catch up on writes during RDB)    |
|    |                              |                                    |
|    |  (now in sync)               |                                    |
|                                                                        |
|  COST OF FULL SYNC:                                                    |
|  * Master: CPU for fork() + disk I/O for RDB                           |
|  * Network: transfer entire dataset (could be GBs)                     |
|  * Replica: flush + reload (brief unavailability)                      |
|  * Memory: fork() briefly doubles memory (copy-on-write)               |
|                                                                        |
|  -------------------------------------------------------------------   |
|  PHASE 2: PARTIAL SYNC (short disconnect and reconnect)                |
|  -------------------------------------------------------------------   |
|                                                                        |
|  Master maintains a REPLICATION BACKLOG — a fixed-size circular        |
|  buffer (default 1MB) of recent write commands.                        |
|                                                                        |
|  +----------------------------------------------------------+          |
|  | Replication Backlog (circular buffer, 1MB default)        |         |
|  |                                                          |          |
|  | [SET a 1] [INCR b] [DEL c] [SET d 4] [ZADD e 1 x] ...  |            |
|  |                             ^                            |          |
|  |                             |                            |          |
|  |                     replica's last offset                |          |
|  +----------------------------------------------------------+          |
|                                                                        |
|  When replica reconnects after a brief disconnect:                     |
|                                                                        |
|  Replica                        Master                                 |
|    |                              |                                    |
|    |-- PSYNC {repl-id} {offset} ->|  ("I was at offset 12345")         |
|    |                              |                                    |
|    |                              |-- check: is offset in backlog?     |
|    |                              |                                    |
|    |   IF YES (offset still in backlog):                               |
|    |<-- +CONTINUE + missed cmds --|  (send only what was missed)       |
|    |                              |                                    |
|    |   IF NO (offset fell off backlog — too far behind):               |
|    |<-- +FULLRESYNC -------------|  (need full sync again)             |
|                                                                        |
|  WHY THIS MATTERS:                                                     |
|  * Short network blip (1-5 seconds): partial sync, ~instant recovery   |
|  * Long outage (minutes+): backlog overwritten, full sync required     |
|  * Increase repl-backlog-size if you expect longer disconnects         |
|                                                                        |
|  -------------------------------------------------------------------   |
|  PHASE 3: CONTINUOUS REPLICATION (steady state)                        |
|  -------------------------------------------------------------------   |
|                                                                        |
|  After sync, master streams every write command to replicas:           |
|                                                                        |
|  Client A --> SET user:1 "Alice" --> Master                            |
|                                        |                               |
|                                        +--> Replica 1: SET user:1 ...  |
|                                        +--> Replica 2: SET user:1 ...  |
|                                                                        |
|  * Replication happens at the COMMAND level, not data level            |
|  * Non-deterministic commands (RANDOMKEY, TIME, SPOP) are converted    |
|    to deterministic equivalents before replicating                     |
|  * Replicas send ACKs to master with their current offset              |
|    (master tracks how far behind each replica is)                      |
|                                                                        |
|  -------------------------------------------------------------------   |
|  REPLICATION MODES COMPARISON                                          |
|  -------------------------------------------------------------------   |
|                                                                        |
|  +----------------+-----------+------------+----------+                |
|  | Mode           | Data Safe | Latency    | Config   |                |
|  +----------------+-----------+------------+----------+                |
|  | Async (default)| Risk of   | Fastest    | Default  |                |
|  |                | data loss | (no wait)  |          |                |
|  +----------------+-----------+------------+----------+                |
|  | WAIT N timeout | Better    | Slower     | Per-cmd  |                |
|  |                | (N acks)  | (wait ack) | WAIT 1 T |                |
|  +----------------+-----------+------------+----------+                |
|  | min-replicas   | Prevents  | Same as    | Config   |                |
|  |                | orphan    | async      | setting  |                |
|  |                | writes    |            |          |                |
|  +----------------+-----------+------------+----------+                |
|                                                                        |
|  NONE of these give fully synchronous replication like ZooKeeper.      |
|  Redis prioritizes SPEED over perfect consistency.                     |
|                                                                        |
|  -------------------------------------------------------------------   |
|  CONFIG                                                                |
|  -------------------------------------------------------------------   |
|                                                                        |
|  replicaof 192.168.1.100 6379   -- make this instance a replica        |
|  replica-read-only yes           -- replicas reject writes (default)   |
|  repl-backlog-size 1mb           -- backlog for partial sync           |
|  min-replicas-to-write 1         -- require N replicas for writes      |
|  min-replicas-max-lag 10         -- max lag (seconds) for above        |
|                                                                        |
|  -------------------------------------------------------------------   |
|  INTERVIEW SUMMARY                                                     |
|  -------------------------------------------------------------------   |
|                                                                        |
|  Q: "Is Redis replication synchronous?"                                |
|                                                                        |
|  A: "No, it's asynchronous by default. The master responds to the      |
|  client BEFORE the replica receives the write. This means writes       |
|  are fast but can be lost if the master crashes before replicating.    |
|  You can use the WAIT command for semi-synchronous behavior, where     |
|  the client blocks until N replicas acknowledge. And you can use       |
|  min-replicas-to-write to reject writes if no healthy replica is       |
|  connected. But Redis never offers fully synchronous replication —     |
|  for that you'd use ZooKeeper or etcd."                                |
|                                                                        |
+------------------------------------------------------------------------+
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
