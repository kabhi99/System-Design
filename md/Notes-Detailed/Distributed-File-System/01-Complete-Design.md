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

## SECTION 7: INTERVIEW QUESTIONS

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
+-------------------------------------------------------------------------+
```
