# DISTRIBUTED FILE SYSTEM
*Complete System Design (GFS / HDFS)*

A distributed file system stores files across multiple machines, providing
fault tolerance, high throughput, and scalability for petabyte-scale data.
Google File System (GFS) and Hadoop Distributed File System (HDFS) are
the most influential designs.

## SECTION 1: REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS:                                               |
|  * Store and retrieve very large files (GB to TB each)                  |
|  * Support append-heavy workloads (logs, data pipelines)                |
|  * Provide high-throughput sequential reads                             |
|  * Handle metadata operations (list, rename, delete)                    |
|  * Fault tolerance (automatic recovery from node failures)              |
|                                                                         |
|  NON-FUNCTIONAL:                                                        |
|  * Scale: petabytes of data, millions of files                          |
|  * Throughput: 100+ GB/sec aggregate read bandwidth                     |
|  * Availability: 99.9%+ (tolerate multiple node failures)               |
|  * Consistency: strong for metadata, eventual OK for data replication   |
|                                                                         |
|  KEY ASSUMPTIONS (GFS/HDFS design choices):                             |
|  * Files are large (typically 100MB-10GB, not millions of tiny files)   |
|  * Workload is append-only or sequential read (not random write)        |
|  * Hardware failures are the norm, not the exception                    |
|  * Throughput matters more than latency                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  GFS / HDFS ARCHITECTURE                                                |
|                                                                         |
|  +-------------------+                                                  |
|  |   MASTER NODE     |  (NameNode in HDFS, GFS Master)                  |
|  |                   |                                                  |
|  | * File namespace  |  (directory tree, file -> chunk mapping)         |
|  | * Chunk locations |  (which chunk on which server)                   |
|  | * Chunk leases    |  (which server is primary for writes)            |
|  | * Replication mgmt|  (ensure 3 copies exist)                         |
|  +--------+----------+                                                  |
|           |                                                             |
|     +-----+-----+------+                                                |
|     |           |      |                                                |
|     v           v      v                                                |
|  +------+  +------+  +------+  +------+  +------+                       |
|  |Chunk |  |Chunk |  |Chunk |  |Chunk |  |Chunk |                       |
|  |Server|  |Server|  |Server|  |Server|  |Server|                       |
|  |  1   |  |  2   |  |  3   |  |  4   |  |  5   |                       |
|  |      |  |      |  |      |  |      |  |      |                       |
|  |[C1]  |  |[C1]  |  |[C2]  |  |[C3]  |  |[C2]  |                       |
|  |[C3]  |  |[C2]  |  |[C3]  |  |[C1]  |  |[C4]  |                       |
|  |[C5]  |  |[C4]  |  |[C5]  |  |[C6]  |  |[C6]  |                       |
|  +------+  +------+  +------+  +------+  +------+                       |
|                                                                         |
|  C1-C6 = Chunks (64MB each in GFS, 128MB in HDFS)                       |
|  Each chunk replicated 3x on different servers                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CHUNK DESIGN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHUNK = Fixed-size block of a file                                     |
|                                                                         |
|  * GFS: 64 MB per chunk                                                 |
|  * HDFS: 128 MB per chunk (default)                                     |
|                                                                         |
|  WHY LARGE CHUNKS?                                                      |
|  * Fewer chunks = less metadata on master (scales better)               |
|  * Amortize network overhead (one connection, many MB)                  |
|  * Client likely reads sequentially (large chunk = fewer seeks)         |
|  * Reduce master interactions (fewer chunk lookups)                     |
|                                                                         |
|  FILE-TO-CHUNK MAPPING:                                                 |
|  File: /data/logs/2024-01-15.log (500 MB)                               |
|  -> Chunk 0: bytes 0-127MB     (on servers 1, 3, 5)                     |
|  -> Chunk 1: bytes 128-255MB   (on servers 2, 4, 6)                     |
|  -> Chunk 2: bytes 256-383MB   (on servers 1, 4, 5)                     |
|  -> Chunk 3: bytes 384-500MB   (on servers 2, 3, 6)                     |
|                                                                         |
|  REPLICATION:                                                           |
|  * Default: 3 replicas per chunk                                        |
|  * Rack-aware: replicas on different racks for fault tolerance          |
|  * Master monitors and re-replicates if a server dies                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3: READ AND WRITE FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  READ FLOW:                                                             |
|                                                                         |
|  1. Client asks Master: "Where are chunks for /data/file.log?"          |
|  2. Master returns: chunk IDs + server locations                        |
|  3. Client contacts nearest chunk server directly                       |
|  4. Chunk server reads from local disk, returns data                    |
|  5. Client caches chunk locations (avoids repeated master queries)      |
|                                                                         |
|  Client ----(1) file, offset----> Master                                |
|  Client <---(2) chunk id, servers- Master                               |
|  Client ----(3) chunk id, offset-> ChunkServer                          |
|  Client <---(4) data-------------- ChunkServer                          |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  WRITE FLOW (GFS pipeline):                                             |
|                                                                         |
|  1. Client asks Master for chunk locations + primary                    |
|  2. Master grants lease to one chunk server (PRIMARY)                   |
|  3. Client pushes data to ALL replicas (pipelined, nearest first)       |
|  4. Client sends write request to PRIMARY                               |
|  5. Primary assigns order, forwards to secondaries                      |
|  6. Secondaries apply write, ack to primary                             |
|  7. Primary acks to client                                              |
|                                                                         |
|  Data flow:  Client -> Nearest -> Next -> Furthest (pipeline)           |
|  Control:    Client -> Primary -> Secondaries -> Primary -> Client      |
|                                                                         |
|  WHY SEPARATE DATA AND CONTROL?                                         |
|  * Data flows linearly (pipeline), maximizes network throughput         |
|  * Control ensures consistency (primary serializes writes)              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: MASTER NODE DESIGN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MASTER STORES (all in memory for speed):                               |
|                                                                         |
|  1. File namespace (directory tree)           -- persisted to disk      |
|  2. File -> [chunk IDs] mapping               -- persisted to disk      |
|  3. Chunk -> [server locations] mapping       -- NOT persisted          |
|     (rebuilt from chunk server heartbeats on startup)                   |
|                                                                         |
|  PERSISTENCE:                                                           |
|  * Operation log (like WAL) for all metadata mutations                  |
|  * Periodic checkpoints (compact snapshot of metadata)                  |
|  * On restart: load checkpoint + replay operation log                   |
|                                                                         |
|  MASTER HIGH AVAILABILITY:                                              |
|  * Shadow masters (replicate operation log)                             |
|  * Automatic failover to shadow master                                  |
|  * HDFS: Active NameNode + Standby NameNode (shared edit log via QJM)   |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  MASTER BOTTLENECK MITIGATION:                                          |
|  * Large chunks (fewer metadata entries)                                |
|  * Client caches chunk locations (fewer master queries)                 |
|  * Master only handles metadata, never data (data goes direct)          |
|  * HDFS Federation: multiple NameNodes, each owns a namespace portion   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5: FAULT TOLERANCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHUNK SERVER FAILURE:                                                  |
|  * Master detects via missed heartbeat (30s timeout)                    |
|  * Chunks on dead server are under-replicated                           |
|  * Master instructs other servers to re-replicate those chunks          |
|  * Priority: chunks with fewer replicas re-replicated first             |
|                                                                         |
|  DATA CORRUPTION:                                                       |
|  * Each chunk has a checksum (CRC32 per 64KB block)                     |
|  * Chunk servers verify checksum on every read                          |
|  * If mismatch: report to master, read from another replica             |
|  * Master schedules re-replication of corrupted chunk                   |
|                                                                         |
|  MASTER FAILURE:                                                        |
|  * Operation log replicated to remote machines                          |
|  * Shadow master takes over (may be briefly stale)                      |
|  * HDFS: automatic failover via ZooKeeper + shared edit log             |
|                                                                         |
|  NETWORK PARTITION:                                                     |
|  * Chunk leases have expiry (prevents split-brain writes)               |
|  * Master stops issuing leases if it can't reach chunk servers          |
|  * Clients retry with backoff                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6: GFS vs HDFS vs MODERN ALTERNATIVES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------+----------------+-----------------+------------------+  |
|  | Feature     | GFS            | HDFS            | Cloud (S3/GCS)   |  |
|  +-------------+----------------+-----------------+------------------+  |
|  | Chunk size  | 64 MB          | 128 MB          | 5MB-5GB parts    |  |
|  | Master      | Single + shadow| Active/Standby  | Managed          |  |
|  | Replication | 3x (custom)    | 3x (rack-aware) | 11-9s durability |  |
|  | Write model | Append + random| Append-only     | PUT (overwrite)  |  |
|  | Consistency | Relaxed        | Strong (1 writer)| Read-after-write|  |
|  | Scaling     | ~petabytes     | ~petabytes      | Exabytes+        |  |
|  | Operations  | Self-managed   | Self-managed    | Zero ops         |  |
|  +-------------+----------------+-----------------+------------------+  |
|                                                                         |
|  MODERN TREND: Object storage (S3/GCS/MinIO) has largely replaced       |
|  self-managed HDFS for most use cases. HDFS still used in Hadoop/Spark  |
|  ecosystems where data locality matters for compute performance.        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7: SCALE ESTIMATION

```
+--------------------------------------------------------------------------+
||                                                                         |
||  ASSUMPTIONS:                                                           |
||  * 10 PB total storage                                                  |
||  * 100K files, average file size 100 MB                                 |
||  * 128 MB chunk size (HDFS default)                                     |
||                                                                         |
||  ====================================================================   |
||                                                                         |
||  CHUNK COUNT:                                                           |
||  * 10 PB / 128 MB = ~80 million chunks                                  |
||  * x3 replicas = 240 million chunk replicas                             |
||                                                                         |
||  -------------------------------------------------------------------    |
||                                                                         |
||  MASTER METADATA:                                                       |
||  * 80M chunks x 100 bytes per entry = 8 GB                              |
||  * Fits comfortably in memory on a single machine                       |
||                                                                         |
||  -------------------------------------------------------------------    |
||                                                                         |
||  THROUGHPUT:                                                            |
||  * Write throughput: 1 GB/sec aggregate                                 |
||    (limited by network and disk I/O)                                    |
||  * Read throughput: 100 GB/sec aggregate across cluster                 |
||                                                                         |
||  -------------------------------------------------------------------    |
||                                                                         |
||  MACHINES:                                                              |
||  * 100 chunk servers, each 100 TB storage, 10 Gbps network              |
||  * Master memory: 8 GB metadata + overhead = fits in 64 GB RAM          |
||                                                                         |
+--------------------------------------------------------------------------+
```

## SECTION 8: DESIGN ALTERNATIVES AND TRADE-OFFS

```
+--------------------------------------------------------------------------+
||                                                                         |
||  ALTERNATIVE 1: Single Master vs Multi-Master vs Masterless             |
||                                                                         |
||  * Single master (GFS/HDFS): simple, consistent, but SPOF.              |
||    Mitigated with standby.                                              |
||  * Multi-master (HDFS Federation): each master owns namespace           |
||    portion. More scale but routing complexity.                          |
||  * Masterless (Ceph): CRUSH algorithm computes placement,               |
||    no master bottleneck. More complex, harder to debug.                 |
||  * Trade-off: single master works for most scales (up to ~100M          |
||    files). Multi-master at extreme scale.                               |
||                                                                         |
||  ====================================================================   |
||                                                                         |
||  ALTERNATIVE 2: Large Chunks (64-128 MB) vs Small Chunks (4-16 MB)      |
||                                                                         |
||  * Large chunks: fewer metadata entries, better sequential              |
||    throughput, amortize network overhead                                |
||  * Small chunks: better for small files, less internal                  |
||    fragmentation, faster replication                                    |
||  * GFS chose 64 MB (batch workloads). Modern object stores              |
||    have variable part sizes.                                            |
||  * Small file problem: millions of 1 KB files = millions of             |
||    metadata entries, master overloaded                                  |
||                                                                         |
||  ====================================================================   |
||                                                                         |
||  ALTERNATIVE 3: Replication vs Erasure Coding                           |
||                                                                         |
||  * Replication (3x): simple, fast reads (any replica),                  |
||    3x storage overhead                                                  |
||  * Erasure coding (RS 6+3): 1.5x storage overhead, tolerates            |
||    same failures, but slow reads (reconstruction)                       |
||  * Trade-off: replication for hot data (fast reads), erasure            |
||    coding for warm/cold (saves storage)                                 |
||  * HDFS 3.0+ supports erasure coding. Google Colossus uses              |
||    erasure coding.                                                      |
||                                                                         |
||  ====================================================================   |
||                                                                         |
||  ALTERNATIVE 4: Append-Only vs Random Write                             |
||                                                                         |
||  * Append-only (GFS/HDFS): simpler consistency, perfect for             |
||    logs/data pipelines, write once read many                            |
||  * Random write: needed for databases, much harder                      |
||    (locking, conflict resolution)                                       |
||  * GFS supported random write but discouraged it (relaxed               |
||    consistency). HDFS is strictly append-only.                          |
||                                                                         |
||  ====================================================================   |
||                                                                         |
||  ALTERNATIVE 5: Self-Managed (HDFS) vs Cloud Object Store (S3/GCS)      |
||                                                                         |
||  * Self-managed: data locality for compute (Spark), full control,       |
||    but high ops burden                                                  |
||  * Cloud: zero ops, 11-9s durability, exabyte scale, but no             |
||    data locality, pay per request                                       |
||                                                                         |
||  +------------+---------------+------------------+                      |
||  | Aspect     | HDFS          | Cloud (S3/GCS)   |                      |
||  +------------+---------------+------------------+                      |
||  | Cost       | CapEx + ops   | Pay per use      |                      |
||  | Ops        | High          | Zero             |                      |
||  | Durability | 3x replicas   | 11 nines         |                      |
||  | Latency    | Low (local)   | Higher (network) |                      |
||  | Locality   | Yes           | No               |                      |
||  | Lock-in    | None          | Vendor           |                      |
||  +------------+---------------+------------------+                      |
||                                                                         |
||  * Trend: even Hadoop shops moving to S3 + Spark. Data locality         |
||    matters less with fast networks.                                     |
||                                                                         |
+--------------------------------------------------------------------------+
```

## SECTION 9: COMMON ISSUES AND FAILURE SCENARIOS

```
+--------------------------------------------------------------------------+
||                                                                         |
||  ISSUE 1: Master Single Point of Failure                                |
||                                                                         |
||  * Problem: master goes down, all metadata ops stop, new file           |
||    creates fail                                                         |
||  * Solution: standby master with shared edit log (HDFS QJM),            |
||    automatic failover via ZooKeeper, clients cache chunk                |
||    locations so reads continue                                          |
||                                                                         |
||  ====================================================================   |
||                                                                         |
||  ISSUE 2: Hot Chunk Servers                                             |
||                                                                         |
||  * Problem: one file is very popular, all reads hit same 3              |
||    chunk servers                                                        |
||  * Solution: increase replication factor for hot files (3 -> 10),       |
||    CDN/cache layer in front, read from any replica (load balance)       |
||                                                                         |
||  ====================================================================   |
||                                                                         |
||  ISSUE 3: Small File Problem                                            |
||                                                                         |
||  * Problem: millions of tiny files, each consuming a metadata           |
||    entry. Master memory exhausted at ~500M files.                       |
||  * Solution: HAR (Hadoop Archives) merge small files, use               |
||    different storage (HBase, S3) for small objects,                     |
||    CombineFileInputFormat for MapReduce                                 |
||                                                                         |
||  ====================================================================   |
||                                                                         |
||  ISSUE 4: Network Partition Between Master and Chunk Servers            |
||                                                                         |
||  * Problem: master can't reach chunk server, thinks it's dead,          |
||    triggers re-replication. But server is fine, now has extra           |
||    copies.                                                              |
||  * Solution: lease-based approach (chunk server leases expire,          |
||    it stops serving), heartbeat grace period, don't re-replicate        |
||    immediately (wait 10 min)                                            |
||                                                                         |
||  ====================================================================   |
||                                                                         |
||  ISSUE 5: Stale Reads After Write                                       |
||                                                                         |
||  * Problem: client writes to file, another client reads from            |
||    different replica that hasn't received the write yet                 |
||  * Solution: read from primary replica (lease holder), or client        |
||    reads from same chunk server it wrote to, or use generation          |
||    numbers                                                              |
||                                                                         |
||  ====================================================================   |
||                                                                         |
||  ISSUE 6: Rebalancing Storm                                             |
||                                                                         |
||  * Problem: adding/removing machines triggers massive data              |
||    movement, saturates network, degrades normal operations              |
||  * Solution: throttle rebalancing bandwidth (HDFS balancer has          |
||    bandwidth limit), schedule during off-peak, prioritize               |
||    under-replicated chunks                                              |
||                                                                         |
+--------------------------------------------------------------------------+
```

## SECTION 10: INTERVIEW QUESTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: Why are chunks 64-128 MB instead of 4 KB like OS file systems?      |
|  A: Fewer chunks = less master metadata, fewer network round trips,     |
|     amortize TCP overhead, workload is sequential not random.           |
|                                                                         |
|  Q: How does GFS handle concurrent appends?                             |
|  A: Record append: client sends data, primary picks offset, ensures     |
|     all replicas write at same offset. Duplicates/padding possible      |
|     (at-least-once). Application must handle dedup.                     |
|                                                                         |
|  Q: What happens if the master goes down?                               |
|  A: Shadow master takes over from replicated operation log. Brief       |
|     unavailability for metadata ops. Reads from chunk servers with      |
|     cached locations can continue.                                      |
|                                                                         |
|  Q: How is HDFS different from a regular distributed DB?                |
|  A: Optimized for throughput not latency, append-only writes,           |
|     large sequential reads, batch processing (MapReduce/Spark).         |
|     Not suitable for random reads/writes or low-latency queries.        |
|                                                                         |
|  Q: How would you design this for small files (millions of 1 KB)?       |
|  A: Large chunks waste space for small files. Solutions: merge small    |
|     files into archives (HAR in HDFS), use a key-value store instead,   |
|     or use object storage (S3) with metadata in a DB.                   |
|                                                                         |
|  Q: When would you choose HDFS over S3?                                 |
|  A: When data locality matters for compute (co-located Spark/           |
|     MapReduce), when you need append-only streaming writes, when        |
|     you need to avoid egress costs, or in on-premise environments.      |
|                                                                         |
|  Q: How does erasure coding save storage vs replication?                |
|  A: 3x replication: 1 PB data = 3 PB storage. RS(6,3) erasure           |
|     coding: 1 PB data = 1.5 PB storage. Same fault tolerance            |
|     (tolerate 3 failures) but half the storage. Trade-off: reads        |
|     are slower (must reconstruct from multiple fragments).              |
|                                                                         |
+-------------------------------------------------------------------------+
```
