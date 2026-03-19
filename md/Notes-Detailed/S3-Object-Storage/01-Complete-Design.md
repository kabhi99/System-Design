# DESIGN S3 / OBJECT STORAGE

*Complete Design: Requirements, Architecture, and Interview Guide*

## SECTION 1: UNDERSTANDING THE PROBLEM

Object storage is a flat-namespace, HTTP-accessible storage system optimized
for immutable blobs (objects). It differs fundamentally from file systems and
block storage.

```
+-----------------------------------------------------------------------+
|              STORAGE PARADIGM COMPARISON                              |
+-----------------------------------------------------------------------+
|                                                                       |
|  +--------------------+--------------------+--------------------+     |
|  |   BLOCK STORAGE    |   FILE STORAGE     |  OBJECT STORAGE    |     |
|  +--------------------+--------------------+--------------------+     |
|  | Fixed-size blocks  | Hierarchical dirs  | Flat namespace     |     |
|  | (512B, 4KB)        | /home/user/file    | bucket/key         |     |
|  | No metadata        | POSIX semantics    | Rich metadata      |     |
|  | Random R/W         | Random R/W         | Whole-object R/W   |     |
|  | SAN / local disk   | NFS / CIFS         | HTTP REST API      |     |
|  | Low latency        | Medium latency     | Higher latency     |     |
|  | VM disks, DB       | Shared files,      | Backups, media,    |     |
|  |                    | home dirs          | data lakes, logs   |     |
|  +--------------------+--------------------+--------------------+     |
|                                                                       |
|  Object storage trades POSIX semantics and random writes for          |
|  extreme durability, scalability, and cost efficiency at exabyte      |
|  scale.                                                               |
|                                                                       |
|  Key abstraction:                                                     |
|    Object = Key + Data Blob + Metadata + Version ID                   |
|    Bucket = Logical namespace (globally unique name)                  |
+-----------------------------------------------------------------------+
```

### CORE API SURFACE

```
+-----------------------------------------------------------------------+
|                     OBJECT STORAGE API                                |
+-----------------------------------------------------------------------+
|                                                                       |
|  PUT    /bucket/key         Upload object (or part of multipart)      |
|  GET    /bucket/key         Download object (supports range reads)    |
|  DELETE /bucket/key         Delete object (or place delete marker)    |
|  HEAD   /bucket/key         Get metadata without downloading body     |
|  LIST   /bucket?prefix=p    List objects with prefix (paginated)      |
|                                                                       |
|  Multipart:                                                           |
|  POST   /bucket/key?uploads         Initiate multipart upload         |
|  PUT    /bucket/key?partNumber=N    Upload part                       |
|  POST   /bucket/key?uploadId=X      Complete multipart upload         |
|                                                                       |
+-----------------------------------------------------------------------+
```

## SECTION 2: REQUIREMENTS

### FUNCTIONAL REQUIREMENTS

```
+-----------------------------------------------------------------------+
|                      FUNCTIONAL REQUIREMENTS                          |
+-----------------------------------------------------------------------+
|                                                                       |
|  FR-1  PUT / GET / DELETE objects up to 5 TB in size                  |
|                                                                       |
|  FR-2  Buckets                                                        |
|        * Create / delete buckets (globally unique names)              |
|        * List objects within a bucket with prefix filtering           |
|                                                                       |
|  FR-3  Versioning                                                     |
|        * Optional per-bucket versioning                               |
|        * Access any historical version by version ID                  |
|        * Delete markers for soft delete                               |
|                                                                       |
|  FR-4  Multipart Upload                                               |
|        * Upload large objects in parallel parts (5 MB - 5 GB each)    |
|        * Resume interrupted uploads                                   |
|        * Complete / abort multipart sessions                          |
|                                                                       |
|  FR-5  Storage Classes                                                |
|        * Hot (standard), warm (infrequent access), cold (glacier),    |
|          archive (deep archive)                                       |
|        * Lifecycle policies for automatic tiering                     |
|                                                                       |
|  FR-6  Access Control                                                 |
|        * Bucket policies, IAM integration                             |
|        * Pre-signed URLs for time-limited access                      |
|        * Server-side encryption (SSE-S3, SSE-KMS, SSE-C)              |
|                                                                       |
+-----------------------------------------------------------------------+
```

### NON-FUNCTIONAL REQUIREMENTS

```
+-----------------------------------------------------------------------+
|                    NON-FUNCTIONAL REQUIREMENTS                        |
+-----------------------------------------------------------------------+
|                                                                       |
|  NFR-1  Durability         99.999999999% (11 nines) annual            |
|                            Probability of losing an object in a       |
|                            year: < 1 in 100 billion                   |
|                                                                       |
|  NFR-2  Availability       99.99% (< 53 min downtime / year)          |
|                                                                       |
|  NFR-3  Consistency        Strong read-after-write consistency        |
|                            After PUT returns 200, any subsequent      |
|                            GET returns the new data                   |
|                                                                       |
|  NFR-4  Scalability        Exabytes of storage, millions of RPS       |
|                                                                       |
|  NFR-5  Latency            First-byte < 100 ms for hot tier           |
|                            Minutes to hours for archive retrieval     |
|                                                                       |
|  NFR-6  Cost efficiency    Pennies per GB-month for cold storage      |
|                                                                       |
+-----------------------------------------------------------------------+
```

## SECTION 3: BACK-OF-ENVELOPE ESTIMATION

```
+-----------------------------------------------------------------------+
|                    CAPACITY ESTIMATION                                |
+-----------------------------------------------------------------------+
|                                                                       |
|  Total objects stored:          ~100 trillion                         |
|  Total data stored:             ~100 exabytes                         |
|  Average object size:           ~1 MB (highly skewed: many small,     |
|                                  few very large)                      |
|                                                                       |
|  --- Request Rates ---                                                |
|  PUT requests / sec:            ~500K                                 |
|  GET requests / sec:            ~5M                                   |
|  LIST requests / sec:           ~200K                                 |
|  DELETE requests / sec:         ~100K                                 |
|                                                                       |
|  --- Storage Growth ---                                               |
|  New data / day:                ~500 PB                               |
|  Net growth (after deletes):    ~200 PB / day                         |
|                                                                       |
|  --- Durability Math ---                                              |
|  11 nines over 100 trillion objects:                                  |
|  Expected object losses / year = 100T x 10^-11 = 1 object / year      |
|                                                                       |
|  --- Erasure Coding (example: RS 8+4) ---                             |
|  Object chunk: 1 MB object > 8 data chunks + 4 parity chunks          |
|  Each chunk: 128 KB                                                   |
|  Storage overhead: 12/8 = 1.5x (vs 3x for triple replication)         |
|  Can tolerate: 4 simultaneous chunk losses (any 4 of 12)              |
|                                                                       |
|  --- Metadata ---                                                     |
|  Per-object metadata record: ~500 bytes                               |
|  Total metadata: 100T x 500B = 50 PB                                  |
|  (Sharded across thousands of metadata DB nodes)                      |
|                                                                       |
+-----------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

```
+-----------------------------------------------------------------------+
|                     HIGH-LEVEL ARCHITECTURE                           |
+-----------------------------------------------------------------------+
|                                                                       |
|    +-----------+                                                      |
|    |  Client   |  (SDK, CLI, console)                                 |
|    +-----+-----+                                                      |
|          |  HTTPS (REST API)                                          |
|          v                                                            |
|    +-----+---------+                                                  |
|    |  API Gateway   |  Auth, rate limiting, request routing           |
|    +-----+---------+                                                  |
|          |                                                            |
|    +-----+--+-----+-----+                                             |
|    |        |     |      |                                            |
|    v        v     v      v                                            |
|  +-+------+ +-+------+ +-+------+ +-+----------+                      |
|  |Metadata| | Data   | |Placement| | Identity  |                      |
|  |Service | | Service| | Service | | & Access  |                      |
|  +---+----+ +---+----+ +---+-----+ | Control   |                      |
|      |          |           |       +-----------+                     |
|      v          v           v                                         |
|  +---+----+ +---+----+ +---+-----+                                    |
|  |Metadata| | Data   | | Cluster |                                    |
|  |  DB    | | Nodes  | |  Map    |                                    |
|  |(sharded| |(HDDs/  | |(node   |                                     |
|  | KV/SQL)| | SSDs)  | | health,|                                     |
|  +--------+ +--------+ | caps)  |                                     |
|                         +--------+                                    |
+-----------------------------------------------------------------------+
```

### SERVICE RESPONSIBILITIES

```
+---------------------+-------------------------------------------------+
|      Service        |              Responsibility                     |
+---------------------+-------------------------------------------------+
| API Gateway         | TLS termination, authentication, request        |
|                     | parsing, rate limiting, routing to services     |
+---------------------+-------------------------------------------------+
| Metadata Service    | Maps (bucket, key, version) > data location.    |
|                     | Handles LIST, HEAD, consistency guarantees.     |
+---------------------+-------------------------------------------------+
| Data Service        | Manages physical storage on data nodes.         |
|                     | Handles chunking, erasure coding, I/O.          |
+---------------------+-------------------------------------------------+
| Placement Service   | Decides WHERE to store new data. Rack/AZ-aware  |
|                     | placement. Manages cluster topology.            |
+---------------------+-------------------------------------------------+
| Identity & Access   | IAM policies, bucket policies, pre-signed URLs, |
| Control             | encryption key management.                      |
+---------------------+-------------------------------------------------+
```

## SECTION 5: DATA STORAGE

### CHUNKING & LAYOUT

```
+-----------------------------------------------------------------------+
|                     DATA CHUNKING                                     |
+-----------------------------------------------------------------------+
|                                                                       |
|  Object: "photos/vacation.jpg" (24 MB)                                |
|                                                                       |
|  Step 1: Split into fixed-size data chunks                            |
|                                                                       |
|  +--------+--------+--------+--------+--------+--------+              |
|  |Chunk 0 |Chunk 1 |Chunk 2 |Chunk 3 |Chunk 4 |Chunk 5 |              |
|  | 4 MB   | 4 MB   | 4 MB   | 4 MB   | 4 MB   | 4 MB   |              |
|  +--------+--------+--------+--------+--------+--------+              |
|  (k=6 data chunks)                                                    |
|                                                                       |
|  Step 2: Erasure code > generate parity chunks                        |
|                                                                       |
|  +--------+--------+--------+--------+--------+--------+              |
|  |Parity 0|Parity 1|Parity 2|Parity 3|                                |
|  | 4 MB   | 4 MB   | 4 MB   | 4 MB   |                                |
|  +--------+--------+--------+--------+                                |
|  (m=4 parity chunks)                                                  |
|                                                                       |
|  Total: 10 chunks x 4 MB = 40 MB stored (1.67x overhead)              |
|  Can lose any 4 of 10 chunks and still reconstruct the object.        |
|                                                                       |
+-----------------------------------------------------------------------+
```

### ERASURE CODING VS REPLICATION

```
+-----------------------------------------------------------------------+
|            ERASURE CODING vs REPLICATION                              |
+-----------------------------------------------------------------------+
|                                                                       |
|  +----------------------------+----------------------------+          |
|  |    TRIPLE REPLICATION      |    ERASURE CODING (6+4)   |           |
|  +----------------------------+----------------------------+          |
|  | 3 full copies of object    | 6 data + 4 parity chunks  |           |
|  | Storage overhead: 3x       | Storage overhead: 1.67x   |           |
|  | Can lose 2 replicas        | Can lose 4 of 10 chunks   |           |
|  | Simple read (any copy)     | Read: need any 6 of 10    |           |
|  | Simple write (3 copies)    | Write: compute parity     |           |
|  | Fast repair (just copy)    | Repair: reconstruct chunk |           |
|  | Higher storage cost        | Lower storage cost        |           |
|  | Better for hot/small obj   | Better for warm/large obj |           |
|  +----------------------------+----------------------------+          |
|                                                                       |
|  Reed-Solomon coding:                                                 |
|    Given k data chunks, produce m parity chunks such that any         |
|    k of (k+m) chunks suffice to reconstruct the original data.        |
|    Uses Galois field arithmetic (GF(2^8) commonly).                   |
|                                                                       |
|  Typical configurations:                                              |
|    Hot tier:    RS(4,2)  - 1.5x overhead, tolerate 2 failures         |
|    Standard:    RS(6,3)  - 1.5x overhead, tolerate 3 failures         |
|    Durable:     RS(8,4)  - 1.5x overhead, tolerate 4 failures         |
|    Cold:        RS(12,4) - 1.33x overhead, tolerate 4 failures        |
+-----------------------------------------------------------------------+
```

### DATA NODE & VOLUME ARCHITECTURE

```
+-----------------------------------------------------------------------+
|                   DATA NODE ARCHITECTURE                              |
+-----------------------------------------------------------------------+
|                                                                       |
|  +---------------------------+                                        |
|  |       Data Node           |                                        |
|  +---------------------------+                                        |
|  |  +--------+ +--------+   |                                         |
|  |  |Volume 0| |Volume 1|   |  Volumes = large pre-allocated files    |
|  |  | (100GB)| | (100GB)|   |  on local disk. Chunks appended         |
|  |  +--------+ +--------+   |  sequentially inside volumes.           |
|  |  +--------+ +--------+   |                                         |
|  |  |Volume 2| |Volume 3|   |  Benefits:                              |
|  |  | (100GB)| | (100GB)|   |  - Sequential writes (high throughput)  |
|  |  +--------+ +--------+   |  - Avoids millions of small files       |
|  |                           |  - Efficient space management          |
|  |  Index: chunk_id > (vol, offset, length)                           |
|  |  Heartbeat: report health + capacity to Placement Service          |
|  +---------------------------+                                        |
|                                                                       |
|  A data center has thousands of data nodes.                           |
|  Each node: 12-36 HDDs, 100-400 TB raw capacity.                      |
|  Total cluster: exabytes of raw storage.                              |
+-----------------------------------------------------------------------+
```

## SECTION 6: METADATA

### KEY-TO-LOCATION MAPPING

```
+-----------------------------------------------------------------------+
|                    METADATA SCHEMA                                    |
+-----------------------------------------------------------------------+
|                                                                       |
|  Primary key: (bucket_name, object_key, version_id)                   |
|                                                                       |
|  +-------------------+-------------------------------------------+    |
|  | Field             | Example                                   |    |
|  +-------------------+-------------------------------------------+    |
|  | bucket            | "my-photos"                               |    |
|  | key               | "vacation/beach.jpg"                      |    |
|  | version_id        | "v3nX8kL2..."                             |    |
|  | size              | 24000000  (24 MB)                         |    |
|  | content_type      | "image/jpeg"                              |    |
|  | etag              | "a1b2c3d4..."  (MD5 or multipart hash)    |    |
|  | created_at        | 2026-01-15T10:30:00Z                      |    |
|  | storage_class     | "STANDARD"                                |    |
|  | encryption        | "AES-256 / SSE-S3"                        |    |
|  | is_delete_marker  | false                                     |    |
|  | chunk_locations   | [                                         |    |
|  |                   |   { chunk: 0, node: DN-42, vol: 7,        |    |
|  |                   |     offset: 83886080, len: 4194304 },     |    |
|  |                   |   { chunk: 1, node: DN-17, vol: 3,        |    |
|  |                   |     offset: 12582912, len: 4194304 },     |    |
|  |                   |   ... (6 data + 4 parity locations)       |    |
|  |                   | ]                                         |    |
|  +-------------------+-------------------------------------------+    |
|                                                                       |
+-----------------------------------------------------------------------+
```

### METADATA DATABASE SHARDING

```
+------------------------------------------------------------------------+
|                 METADATA SHARDING                                      |
+------------------------------------------------------------------------+
|                                                                        |
|  Strategy: shard by hash(bucket + key)                                 |
|                                                                        |
|  +----------+  +----------+  +----------+  +----------+                |
|  | Shard 0  |  | Shard 1  |  | Shard 2  |  | Shard 3  |                |
|  | hash     |  | hash     |  | hash     |  | hash     |                |
|  | [0, 25%) |  | [25, 50%)|  | [50, 75%)|  | [75,100%)|                |
|  +----+-----+  +----+-----+  +----+-----+  +----+-----+                |
|       |              |              |              |                   |
|       v              v              v              v                   |
|  +----+-----+  +----+-----+  +----+-----+  +----+-----+                |
|  | Primary  |  | Primary  |  | Primary  |  | Primary  |                |
|  | Replica  |  | Replica  |  | Replica  |  | Replica  |                |
|  | Replica  |  | Replica  |  | Replica  |  | Replica  |                |
|  +----------+  +----------+  +----------+  +----------+                |
|                                                                        |
|  Each shard: Raft/Paxos consensus for strong consistency.              |
|  Write: quorum write to primary + replicas before ack.                 |
|  Read: read from primary (or any replica after sync).                  |
|                                                                        |
|  LIST operation challenge:                                             |
|    LIST by prefix needs to scan across shards (hash sharding           |
|    scatters keys with the same prefix).                                |
|    Solution: maintain a separate prefix-ordered secondary index        |
|    or use range-based sharding for LIST-heavy workloads.               |
+------------------------------------------------------------------------+
```

### CONSISTENCY MODEL

```
+------------------------------------------------------------------------+
|                   STRONG READ-AFTER-WRITE                              |
+------------------------------------------------------------------------+
|                                                                        |
|  Timeline:                                                             |
|                                                                        |
|  Client A:  PUT /bucket/key ---------> 200 OK                          |
|                                           |                            |
|  Client B:                                +-- GET /bucket/key          |
|                                                  |                     |
|                                                  v                     |
|                                           MUST return new data         |
|                                                                        |
|  Implementation:                                                       |
|  1. PUT writes data to data nodes                                      |
|  2. PUT commits metadata to sharded DB (Raft quorum)                   |
|  3. PUT returns 200 only AFTER metadata is committed                   |
|  4. Any subsequent GET hits the metadata DB, which reflects            |
|     the committed state                                                |
|                                                                        |
|  For LIST consistency (harder):                                        |
|  * S3 achieved strong LIST consistency in 2020 by synchronously        |
|    updating the listing index before returning PUT success             |
|  * Uses a "witness" mechanism to detect in-flight writes               |
+------------------------------------------------------------------------+
```

## SECTION 7: WRITE PATH

### STANDARD PUT FLOW

```
+-----------------------------------------------------------------------+
|                      WRITE PATH (PUT)                                 |
+-----------------------------------------------------------------------+
|                                                                       |
|  Client                                                               |
|    |                                                                  |
|    |  PUT /bucket/key  (body: 24 MB)                                  |
|    v                                                                  |
|  +----------+                                                         |
|  |API Gateway|  1. Authenticate, authorize, validate                  |
|  +----+-----+                                                         |
|       |                                                               |
|       v                                                               |
|  +----+-----+                                                         |
|  | Placement |  2. Select target data nodes                           |
|  | Service   |     - Rack-aware: spread chunks across racks/AZs       |
|  +----+-----+     - Prefer nodes with available capacity              |
|       |            - Return placement plan: chunk>node mapping        |
|       v                                                               |
|  +----+---------+                                                     |
|  | Data Service  |  3. Stream data from client                        |
|  |               |     a. Split into k data chunks                    |
|  |               |     b. Compute m parity chunks (Reed-Solomon)      |
|  |               |     c. Stream each chunk to assigned data node     |
|  |               |     d. Each data node appends to local volume      |
|  |               |     e. Data node returns checksum + ack            |
|  +----+---------+                                                     |
|       |                                                               |
|       | All (k+m) chunks confirmed                                    |
|       v                                                               |
|  +----+---------+                                                     |
|  | Metadata     |  4. Write metadata record                           |
|  | Service      |     - (bucket, key, version) > chunk locations      |
|  |              |     - Raft quorum commit                            |
|  +----+---------+                                                     |
|       |                                                               |
|       | Metadata committed                                            |
|       v                                                               |
|  Return 200 OK + ETag to client                                       |
+-----------------------------------------------------------------------+
```

### MULTIPART UPLOAD

```
+-----------------------------------------------------------------------+
|                   MULTIPART UPLOAD FLOW                               |
+-----------------------------------------------------------------------+
|                                                                       |
|  Use case: uploading objects > 100 MB. Allows parallel upload         |
|  of parts and resumption after failure.                               |
|                                                                       |
|  Step 1: Initiate                                                     |
|  +----------+    POST /bucket/key?uploads    +----------+             |
|  |  Client  +----------------------------------> API GW  |            |
|  +----------+    <-- 200 { uploadId: "abc" } +----------+             |
|                                                                       |
|  Step 2: Upload Parts (in parallel)                                   |
|  +----------+    PUT /bucket/key?partNum=1&uploadId=abc               |
|  |  Client  +----+  (body: 100 MB part)                               |
|  |  (thread |    |                                                    |
|  |   pool)  |    +  PUT /bucket/key?partNum=2&uploadId=abc            |
|  |          |    |  (body: 100 MB part)                               |
|  |          |    |                                                    |
|  |          |    +  PUT /bucket/key?partNum=3&uploadId=abc            |
|  +----------+       (body: 50 MB part)                                |
|                                                                       |
|  Each part is independently chunked, erasure-coded, and stored.       |
|  Server returns ETag per part.                                        |
|                                                                       |
|  Step 3: Complete                                                     |
|  +----------+    POST /bucket/key?uploadId=abc                        |
|  |  Client  +----> { parts: [{partNum:1, etag:...}, ...] }            |
|  +----------+                                                         |
|                                                                       |
|  Server: validates all parts present, assembles metadata record       |
|  linking all part chunk locations. Returns final 200 OK + ETag.       |
|                                                                       |
|  Abort: POST /bucket/key?uploadId=abc&abort                           |
|  > Server marks upload as aborted, GC reclaims orphaned chunks.       |
|                                                                       |
+-----------------------------------------------------------------------+
```

## SECTION 8: READ PATH

### STANDARD GET FLOW

```
+-----------------------------------------------------------------------+
|                       READ PATH (GET)                                 |
+-----------------------------------------------------------------------+
|                                                                       |
|  Client                                                               |
|    |                                                                  |
|    |  GET /bucket/key                                                 |
|    v                                                                  |
|  +----------+                                                         |
|  |API Gateway|  1. Authenticate, authorize                            |
|  +----+-----+                                                         |
|       |                                                               |
|       v                                                               |
|  +----+---------+                                                     |
|  | Metadata     |  2. Lookup (bucket, key) > chunk locations          |
|  | Service      |     Returns: list of (node, vol, offset, len)       |
|  +----+---------+     for each of (k+m) chunks                        |
|       |                                                               |
|       v                                                               |
|  +----+---------+                                                     |
|  | Data Service  |  3. Read k chunks from data nodes                  |
|  |               |     - Read from k nearest / fastest nodes          |
|  |               |     - Verify checksum per chunk                    |
|  |               |     - If a chunk is corrupt / unavailable:         |
|  |               |       read a parity chunk instead and              |
|  |               |       reconstruct via erasure decoding             |
|  +----+---------+                                                     |
|       |                                                               |
|       v                                                               |
|  +----+---------+                                                     |
|  | Reassemble   |  4. Concatenate data chunks in order                |
|  | & Stream     |     Stream back to client as HTTP response          |
|  +----+---------+                                                     |
|       |                                                               |
|       v                                                               |
|  Client receives object bytes                                         |
+-----------------------------------------------------------------------+
```

### RANGE READS

```
+------------------------------------------------------------------------+
|                       RANGE READS                                      |
+------------------------------------------------------------------------+
|                                                                        |
|  Request: GET /bucket/key  Range: bytes=1000000-1999999                |
|  (Read 1 MB starting at offset 1,000,000)                              |
|                                                                        |
|  +--object data (24 MB)--------------------------------------+         |
|  |                                                            |        |
|  | chunk 0 (4MB) | chunk 1 (4MB) | chunk 2 (4MB) | ...      |          |
|  |               |               |               |          |          |
|  +------+--------+----+----------+---------------+-----------+         |
|         ^             ^                                                |
|         |             |                                                |
|    offset 1MB    offset 2MB                                            |
|    falls in      end boundary                                          |
|    chunk 0                                                             |
|                                                                        |
|  The data service:                                                     |
|  1. Determines which chunks contain the requested byte range           |
|  2. Reads only those chunks (here: just chunk 0)                       |
|  3. Extracts the requested byte range from the decoded chunk           |
|  4. Streams only those bytes to the client                             |
|                                                                        |
|  Benefit: avoid downloading the entire 24 MB object for a 1 MB read    |
+------------------------------------------------------------------------+
```

### READ CACHING

```
+-----------------------------------------------------------------------+
|                      READ CACHING                                     |
+-----------------------------------------------------------------------+
|                                                                       |
|  +--------+     +---------+     +----------+     +----------+         |
|  | Client +--->| CDN     +--->| Read     +--->| Data     |            |
|  |        |    | (edge   |    | Cache    |    | Nodes    |            |
|  |        |    |  cache) |    | (cluster)|    | (disk)   |            |
|  +--------+    +---------+    +----------+    +----------+            |
|                                                                       |
|  Layer 1 - CDN (for public or pre-signed objects):                    |
|    Cache at edge PoPs. Short TTL. Offloads hot objects.               |
|                                                                       |
|  Layer 2 - Read cache (in front of data nodes):                       |
|    In-memory or SSD cache of frequently accessed chunks.              |
|    Reduces disk I/O on data nodes.                                    |
|    Keyed by (chunk_id). LRU/LFU eviction.                             |
|                                                                       |
|  Layer 3 - Client-side caching:                                       |
|    HTTP ETag / If-None-Match for conditional GETs.                    |
|    304 Not Modified saves bandwidth.                                  |
+-----------------------------------------------------------------------+
```

## SECTION 9: DURABILITY & AVAILABILITY

### ERASURE CODING DURABILITY MATH

```
+------------------------------------------------------------------------+
|              DURABILITY CALCULATION                                    |
+------------------------------------------------------------------------+
|                                                                        |
|  Configuration: RS(6,3) - 6 data + 3 parity = 9 chunks total           |
|  Can tolerate: 3 simultaneous chunk failures                           |
|                                                                        |
|  Assumptions:                                                          |
|    * Annual disk failure rate (AFR): 2%                                |
|    * Repair time: 6 hours                                              |
|    * Chunks spread across 9 different nodes/racks                      |
|                                                                        |
|  P(single chunk unavailable) = AFR x repair_fraction                   |
|                               = 0.02 x (6/8760) ~ 1.37 x 10^-5         |
|                                                                        |
|  Object is lost only if > 4 chunks fail simultaneously:                |
|  P(loss) = C(9,4) x p^4 x (1-p)^5                                      |
|          = 126 x (1.37e-5)^4 x (~1)^5                                  |
|          ~ 4.4 x 10^-16                                                |
|                                                                        |
|  That's ~15 nines of durability per object per repair cycle.           |
|  With 100T objects: expected losses ~ 0.00004 / year                   |
|  (well within 11 nines target)                                         |
|                                                                        |
|  Key insight: spreading chunks across failure domains (racks, AZs)     |
|  makes correlated failures (e.g., rack power loss) survivable.         |
+------------------------------------------------------------------------+
```

### REPAIR SCANNER

```
+------------------------------------------------------------------------+
|                    REPAIR SCANNER                                      |
+------------------------------------------------------------------------+
|                                                                        |
|  Background process that continuously ensures durability:              |
|                                                                        |
|  +------------------+                                                  |
|  | Repair Scanner   |                                                  |
|  +--------+---------+                                                  |
|           |                                                            |
|           | 1. Scan all chunks on a data node                          |
|           |    (full sweep every ~2 weeks)                             |
|           v                                                            |
|  +--------+---------+                                                  |
|  | Checksum Verify  |  2. Read chunk, verify CRC-32C                   |
|  +--------+---------+     If corrupt > mark degraded                   |
|           |                                                            |
|           v                                                            |
|  +--------+---------+                                                  |
|  | Chunk Census     |  3. Count live replicas/chunks per object        |
|  +--------+---------+     If below threshold > schedule repair         |
|           |                                                            |
|           v                                                            |
|  +--------+---------+                                                  |
|  | Repair Worker    |  4. Read k healthy chunks                        |
|  |                  |     Reconstruct missing chunks via EC decode     |
|  |                  |     Write to new healthy data node               |
|  |                  |     Update metadata with new location            |
|  +------------------+                                                  |
|                                                                        |
|  Triggered repairs:                                                    |
|  * Node death > all chunks on that node need repair                    |
|  * Disk failure > chunks on that disk need repair                      |
|  * Bit rot detected > single chunk repair                              |
+------------------------------------------------------------------------+
```

### RACK/AZ-AWARE PLACEMENT

```
+-----------------------------------------------------------------------+
|                  PLACEMENT STRATEGY                                   |
+-----------------------------------------------------------------------+
|                                                                       |
|  Goal: spread chunks across failure domains so that a single          |
|  rack/AZ outage cannot lose more than m chunks.                       |
|                                                                       |
|  Example: RS(6,3), 3 Availability Zones                               |
|                                                                       |
|  +------ AZ-1 ------+  +------ AZ-2 ------+  +------ AZ-3 ---------+  |
|  |                   |  |                   |  |                   |  |
|  | +-----+ +-----+  |  | +-----+ +-----+  |  | +-----+ +--------+  |  |
|  | |Data | |Data |  |  | |Data | |Parity|  |  | |Parity| |Parity | |  |
|  | |  0  | |  1  |  |  | |  2  | |  0   |  |  | |  1   | |  2    | |  |
|  | +-----+ +-----+  |  | +-----+ +-----+  |  | +-----+ +--------+  |  |
|  | |Data | |Data |  |  |                   |  | |Data  |           |  |
|  | |  3  | |  4  |  |  |                   |  | |  5   |           |  |
|  | +-----+ +-----+  |  |                   |  | +-----+            |  |
|  +-------------------+  +-------------------+  +-------------------+  |
|                                                                       |
|  If AZ-1 goes down entirely: lose chunks D0, D1, D3, D4 (4 chunks)    |
|  Remaining: D2, D5, P0, P1, P2 = 5 chunks                             |
|  Need 6 to reconstruct > NOT enough (this layout is bad)              |
|                                                                       |
|  Better layout: max 3 chunks per AZ:                                  |
|                                                                       |
|  +------ AZ-1 ------+  +------ AZ-2 ------+  +------ AZ-3 ---------+  |
|  | D0, D1, D2       |  | D3, D4, D5       |  | P0, P1, P2          |  |
|  | (3 chunks)       |  | (3 chunks)       |  | (3 chunks)          |  |
|  +-------------------+  +-------------------+  +-------------------+  |
|                                                                       |
|  Any single AZ down: lose 3 chunks, retain 6 > can reconstruct.       |
|  This is the placement constraint the placement service enforces.     |
+-----------------------------------------------------------------------+
```

## SECTION 10: VERSIONING & LIFECYCLE

### OBJECT VERSIONING

```
+-----------------------------------------------------------------------+
|                    OBJECT VERSIONING                                  |
+-----------------------------------------------------------------------+
|                                                                       |
|  Bucket: "my-docs" (versioning enabled)                               |
|  Key: "report.pdf"                                                    |
|                                                                       |
|  +----------+----------+----------+-----------+--------+              |
|  | Version  |   Date   |  Size    |  Status   | Marker |              |
|  +----------+----------+----------+-----------+--------+              |
|  | v001     | Jan 10   | 2 MB     | archived  |   no   |              |
|  | v002     | Feb 14   | 2.5 MB   | current   |   no   |              |
|  | v003     | Mar 01   | --       | deleted   |  yes   |  < delete    |
|  +----------+----------+----------+-----------+--------+     marker   |
|                                                                       |
|  GET /my-docs/report.pdf                                              |
|    > Returns 404 (latest version is a delete marker)                  |
|                                                                       |
|  GET /my-docs/report.pdf?versionId=v002                               |
|    > Returns the 2.5 MB version (still accessible)                    |
|                                                                       |
|  DELETE /my-docs/report.pdf?versionId=v003                            |
|    > Removes the delete marker; GET now returns v002                  |
|                                                                       |
|  Versioning protects against accidental overwrites and deletes.       |
|  Storage cost: all versions count toward storage billing.             |
+-----------------------------------------------------------------------+
```

### STORAGE CLASSES & LIFECYCLE

```
+-----------------------------------------------------------------------+
|                  STORAGE CLASSES                                      |
+-----------------------------------------------------------------------+
|                                                                       |
|  +-------------+--------+-----------+----------+-------------------+  |
|  |   Class     | $/GB   | First-Byte| Min Dur. | Use Case          |  |
|  |             | /month | Latency   |          |                   |  |
|  +-------------+--------+-----------+----------+-------------------+  |
|  | Standard    | $0.023 | < 100 ms  | none     | Frequently        |  |
|  | (Hot)       |        |           |          | accessed data     |  |
|  +-------------+--------+-----------+----------+-------------------+  |
|  | Infrequent  | $0.0125| < 100 ms  | 30 days  | Monthly access    |  |
|  | Access (IA) |        |           |          | patterns          |  |
|  +-------------+--------+-----------+----------+-------------------+  |
|  | Glacier     | $0.004 | 1-5 min   | 90 days  | Quarterly         |  |
|  | (Cold)      |        | (expedited)|         | access, backups   |  |
|  +-------------+--------+-----------+----------+-------------------+  |
|  | Deep Archive| $0.001 | 12-48 hrs | 180 days | Compliance,       |  |
|  |             |        |           |          | 7-year retention  |  |
|  +-------------+--------+-----------+----------+-------------------+  |
|                                                                       |
|  Lifecycle Policy Example:                                            |
|  +-------------------------------------------------------------+      |
|  |  Rule: "archive-old-logs"                                    |     |
|  |  Prefix: "logs/"                                             |     |
|  |  Transitions:                                                |     |
|  |    Day 0   > Standard                                       |      |
|  |    Day 30  > Infrequent Access                              |      |
|  |    Day 90  > Glacier                                        |      |
|  |    Day 365 > Deep Archive                                   |      |
|  |  Expiration:                                                 |     |
|  |    Day 2555 (7 years) > Delete permanently                  |      |
|  +-------------------------------------------------------------+      |
|                                                                       |
|  Transition mechanics:                                                |
|  * Background job scans metadata for objects matching rules           |
|  * Rewrite data with denser erasure coding (cold tiers)               |
|  * Move to cheaper storage media (tape for deep archive)              |
|  * Update metadata storage_class field                                |
+-----------------------------------------------------------------------+
```

## SECTION 11: ACCESS CONTROL

### AUTHORIZATION MODEL

```
+-----------------------------------------------------------------------+
|                   ACCESS CONTROL LAYERS                               |
+-----------------------------------------------------------------------+
|                                                                       |
|  Request arrives:                                                     |
|       |                                                               |
|       v                                                               |
|  +----+----------+                                                    |
|  | 1. Identity    |  WHO is making the request?                       |
|  |    Resolution  |  - IAM user/role (access key + secret key)        |
|  |                |  - Pre-signed URL (embedded credentials)          |
|  |                |  - Anonymous (public bucket)                      |
|  +----+----------+                                                    |
|       |                                                               |
|       v                                                               |
|  +----+----------+                                                    |
|  | 2. IAM Policy  |  Does the IAM policy ALLOW this action?           |
|  |    Check       |  Evaluate: Effect, Action, Resource, Condition    |
|  +----+----------+                                                    |
|       |                                                               |
|       v                                                               |
|  +----+----------+                                                    |
|  | 3. Bucket      |  Does the bucket policy ALLOW / DENY?             |
|  |    Policy      |  (Resource-based policy attached to bucket)       |
|  +----+----------+                                                    |
|       |                                                               |
|       v                                                               |
|  +----+----------+                                                    |
|  | 4. ACL Check   |  Legacy per-object ACLs (if enabled)              |
|  +----+----------+                                                    |
|       |                                                               |
|       v                                                               |
|  ALLOW or DENY (explicit deny wins at any layer)                      |
+-----------------------------------------------------------------------+
```

### PRE-SIGNED URLS

```
+-----------------------------------------------------------------------+
|                   PRE-SIGNED URLs                                     |
+-----------------------------------------------------------------------+
|                                                                       |
|  Purpose: grant temporary access to a private object without          |
|  sharing credentials.                                                 |
|                                                                       |
|  Generation (server-side):                                            |
|  +----------------------------------------------------------+         |
|  | URL = https://bucket.s3.amazonaws.com/key                 |        |
|  |       ?X-Amz-Algorithm=AWS4-HMAC-SHA256                  |         |
|  |       &X-Amz-Credential=AKID/date/region/s3/aws4_request |         |
|  |       &X-Amz-Date=20260314T120000Z                       |         |
|  |       &X-Amz-Expires=3600       (valid 1 hour)           |         |
|  |       &X-Amz-Signature=abc123...  (HMAC of request)      |         |
|  +----------------------------------------------------------+         |
|                                                                       |
|  Workflow:                                                            |
|  +--------+   "generate upload URL"   +-----------+                   |
|  | App    +-------------------------->| App       |                   |
|  | Client |   <-- pre-signed PUT URL  | Server    |                   |
|  +---+----+                           +-----------+                   |
|      |                                                                |
|      |  PUT (directly to object storage, no app server proxy)         |
|      v                                                                |
|  +---+-----------+                                                    |
|  | Object Storage |  Validates signature, expiry, and permissions     |
|  +---------------+                                                    |
|                                                                       |
|  Benefits: app server never touches the data > saves bandwidth        |
+-----------------------------------------------------------------------+
```

### ENCRYPTION

```
+-----------------------------------------------------------------------+
|                   ENCRYPTION OPTIONS                                  |
+-----------------------------------------------------------------------+
|                                                                       |
|  +-------------------+--------------------------------------------+   |
|  |   Mode            |   How It Works                             |   |
|  +-------------------+--------------------------------------------+   |
|  | SSE-S3            | Service manages keys entirely.             |   |
|  |                   | Each object encrypted with a unique data   |   |
|  |                   | key, which is encrypted by a master key    |   |
|  |                   | rotated automatically.                     |   |
|  +-------------------+--------------------------------------------+   |
|  | SSE-KMS           | Keys managed in a KMS (e.g., AWS KMS).     |   |
|  |                   | Customer controls key policy, rotation,    |   |
|  |                   | and audit trail. Envelope encryption:      |   |
|  |                   | data key encrypted by KMS master key.      |   |
|  +-------------------+--------------------------------------------+   |
|  | SSE-C             | Customer provides encryption key in each   |   |
|  |                   | request header. Service encrypts/decrypts  |   |
|  |                   | but does NOT store the key.                |   |
|  +-------------------+--------------------------------------------+   |
|  | Client-Side       | Customer encrypts before upload.           |   |
|  |                   | Service stores opaque ciphertext.          |   |
|  |                   | Full customer control, no trust in server. |   |
|  +-------------------+--------------------------------------------+   |
|                                                                       |
|  Envelope Encryption (SSE-KMS detail):                                |
|                                                                       |
|  +----------+    Generate DEK    +----------+                         |
|  |   KMS    +<-------------------+  Object  |                         |
|  | Service  +---> (DEK, EncDEK)  |  Storage |                         |
|  +----------+                    +----+-----+                         |
|                                       |                               |
|                         Encrypt object data with DEK                  |
|                         Store EncDEK alongside ciphertext             |
|                         Discard plaintext DEK from memory             |
+-----------------------------------------------------------------------+
```

## SECTION 12: SCALING

### METADATA SCALING

```
+------------------------------------------------------------------------+
|                  METADATA DB SCALING                                   |
+------------------------------------------------------------------------+
|                                                                        |
|  Challenge: 100+ trillion metadata records, millions of QPS            |
|                                                                        |
|  +-------------------+                                                 |
|  | Consistent Hash   |  Route (bucket, key) to shard                   |
|  | Ring / Range Map  |                                                 |
|  +--------+----------+                                                 |
|           |                                                            |
|     +-----+-----+-----+-----+-----+                                    |
|     |     |     |     |     |     |                                    |
|     v     v     v     v     v     v                                    |
|  +--+--+--+--+--+--+--+--+--+--+--+--+                                 |
|  | S0  | S1  | S2  | S3  | S4  | S5  |   ... thousands of shards       |
|  +--+--+--+--+--+--+--+--+--+--+--+--+                                 |
|     |     |     |     |     |     |                                    |
|   Raft  Raft  Raft  Raft  Raft  Raft   (3-5 replicas each)             |
|                                                                        |
|  Shard splitting:                                                      |
|  When a shard grows too large (by record count or QPS), split it:      |
|  * Choose a split point in the key range                               |
|  * Clone data to new shard group                                       |
|  * Update routing table atomically                                     |
|  * Drain old shard                                                     |
|                                                                        |
|  Hot-shard mitigation:                                                 |
|  * Monitor per-shard QPS                                               |
|  * Add read replicas for read-heavy shards                             |
|  * Sub-shard hot prefixes                                              |
+------------------------------------------------------------------------+
```

### DATA NODE SCALING

```
+-----------------------------------------------------------------------+
|                 DATA NODE SCALING                                     |
+-----------------------------------------------------------------------+
|                                                                       |
|  Adding capacity:                                                     |
|  1. Rack new data nodes in the cluster                                |
|  2. Nodes register with Placement Service (capacity, rack, AZ)        |
|  3. Placement Service begins directing new writes to new nodes        |
|  4. Background rebalancer migrates some chunks from full nodes        |
|                                                                       |
|  Decommissioning a node:                                              |
|  1. Mark node as "draining" in Placement Service                      |
|  2. No new writes directed to this node                               |
|  3. Repair scanner treats all chunks on this node as "missing"        |
|  4. Reconstructs and places them on healthy nodes                     |
|  5. Once fully drained, node removed from cluster map                 |
|                                                                       |
|  Node failure:                                                        |
|  1. Heartbeat timeout > node marked down                              |
|  2. Immediate: reads fall back to other chunks (EC tolerates it)      |
|  3. Background: repair scanner reconstructs lost chunks               |
|  4. Time to full repair: depends on cluster bandwidth                 |
|     (e.g., 100 TB node x 1 Gbps repair bandwidth ~ ~9 hours)          |
+-----------------------------------------------------------------------+
```

### GARBAGE COLLECTION

```
+------------------------------------------------------------------------+
|                   GARBAGE COLLECTION                                   |
+------------------------------------------------------------------------+
|                                                                        |
|  Sources of garbage:                                                   |
|  * Deleted objects / old versions past lifecycle expiration            |
|  * Aborted multipart uploads (orphaned parts)                          |
|  * Overwritten objects (old version chunks, no versioning)             |
|                                                                        |
|  GC Process:                                                           |
|  +-------------------+                                                 |
|  | 1. Mark Phase     |  Scan metadata DB for:                          |
|  |                   |  - Deleted objects past grace period            |
|  |                   |  - Expired lifecycle objects                    |
|  |                   |  - Aborted multipart uploads > 7 days old       |
|  +--------+----------+  Collect chunk IDs to delete                    |
|           |                                                            |
|           v                                                            |
|  +--------+----------+                                                 |
|  | 2. Reference Check|  Verify no other metadata record points to      |
|  |                   |  these chunks (deduplication safety)            |
|  +--------+----------+                                                 |
|           |                                                            |
|           v                                                            |
|  +--------+----------+                                                 |
|  | 3. Sweep Phase    |  Issue delete commands to data nodes            |
|  |                   |  Data nodes free space in volumes               |
|  |                   |  Compact volumes when fragmentation > 30%       |
|  +-------------------+                                                 |
|                                                                        |
|  GC runs continuously as a low-priority background job.                |
|  Grace period (e.g., 24 hours) prevents deleting during in-flight      |
|  reads that may still reference old chunks.                            |
+------------------------------------------------------------------------+
```

### CROSS-REGION REPLICATION

```
+-----------------------------------------------------------------------+
|               CROSS-REGION REPLICATION (CRR)                          |
+-----------------------------------------------------------------------+
|                                                                       |
|  Purpose: disaster recovery, compliance, low-latency reads globally   |
|                                                                       |
|  +-----------+          Async           +-----------+                 |
|  | Region A  +------------------------->| Region B  |                 |
|  | (primary) |     replication stream   | (replica) |                 |
|  +-----------+                          +-----------+                 |
|                                                                       |
|  Flow:                                                                |
|  1. Object written to Region A (primary)                              |
|  2. Change event published to replication queue                       |
|  3. Replication worker reads object from Region A                     |
|  4. Writes object to Region B (full PUT with data + metadata)         |
|  5. Replication lag: typically seconds to minutes                     |
|                                                                       |
|  Conflict resolution (bidirectional CRR):                             |
|  * Last-writer-wins based on timestamp                                |
|  * Or: version vector for conflict detection, manual resolution       |
|                                                                       |
|  Consistency note:                                                    |
|  * CRR is async > Region B may be slightly behind                     |
|  * Read-after-write consistency is per-region, not cross-region       |
|  * For strong cross-region: route all writes through one region       |
+-----------------------------------------------------------------------+
```

## SECTION 13: INTERVIEW Q&A

```
+-----------------------------------------------------------------------+
|  Q1: How do you achieve 11 nines of durability?                       |
+-----------------------------------------------------------------------+
|                                                                       |
|  Erasure coding (e.g., RS 6+3) spreads data across independent        |
|  failure domains (racks, AZs). The probability of losing enough       |
|  chunks simultaneously to make an object unrecoverable is             |
|  astronomically low (~10^-15 per repair cycle). A background repair   |
|  scanner continuously detects and reconstructs degraded chunks        |
|  before additional failures occur. Checksums detect bit rot.          |
|  AZ-aware placement ensures a single zone failure cannot exceed       |
|  the erasure coding tolerance.                                        |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|  Q2: Why erasure coding over triple replication?                      |
+-----------------------------------------------------------------------+
|                                                                       |
|  At exabyte scale, storage cost dominates. Triple replication uses    |
|  3x storage; RS(6,3) uses only 1.5x while tolerating 3 failures.      |
|  The trade-off is higher CPU for encoding/decoding and more complex   |
|  repair. For hot small objects where latency matters, replication     |
|  (simpler reads) may still be preferred. Most large-scale systems     |
|  use a hybrid: replication for metadata DBs, erasure coding for       |
|  bulk data.                                                           |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|  Q3: How does strong read-after-write consistency work?               |
+-----------------------------------------------------------------------+
|                                                                       |
|  The write path commits metadata to a Raft-based (or Paxos-based)     |
|  sharded database. The PUT request only returns 200 after the         |
|  metadata is committed (quorum ack). Any subsequent GET reads from    |
|  the metadata leader (or a synchronized follower), which guarantees   |
|  it sees the latest committed write. This is per-shard consistency    |
|  - no global ordering across shards, but each key's history is        |
|  linearizable.                                                        |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|  Q4: How do you handle a 5 TB file upload?                            |
+-----------------------------------------------------------------------+
|                                                                       |
|  Multipart upload. The client splits the file into parts (e.g.,       |
|  100 MB each = 50,000 parts). Parts are uploaded in parallel,         |
|  each independently erasure-coded and stored. If a part fails,        |
|  retry just that part. On completion, the server assembles a          |
|  metadata record linking all part chunk locations into one logical    |
|  object. This gives parallelism, fault tolerance, and resumability.   |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|  Q5: How does the LIST operation work at scale?                       |
+-----------------------------------------------------------------------+
|                                                                       |
|  LIST needs prefix-ordered results, but metadata is hash-sharded      |
|  (scattering prefixes). Two approaches:                               |
|  1. Secondary prefix index: a separate ordered index partitioned by   |
|     (bucket, key prefix). Updated synchronously on writes.            |
|  2. Range-based sharding: shard metadata by (bucket, key) range       |
|     instead of hash. LIST becomes a range scan on one or few shards.  |
|  AWS S3 uses approach (1) to keep hash-based sharding for point       |
|  lookups while supporting consistent LIST.                            |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|  Q6: What happens when a data node dies?                              |
+-----------------------------------------------------------------------+
|                                                                       |
|  Immediate impact: the chunks on that node are unavailable. However,  |
|  with RS(6,3), each object has 9 chunks across different nodes.       |
|  Reads simply use the remaining healthy chunks (need any 6 of 9).     |
|  No read disruption as long as < 3 nodes per object are down.         |
|  In the background, the repair scanner identifies under-replicated    |
|  chunks and reconstructs them on healthy nodes. The placement         |
|  service ensures new chunks land on different failure domains.        |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|  Q7: How do storage classes (hot/warm/cold) differ physically?        |
+-----------------------------------------------------------------------+
|                                                                       |
|  Hot: data on SSDs or fast HDDs, denser erasure coding (e.g., RS      |
|  4+2), more read replicas, indexed for fast access.                   |
|  Warm: slower HDDs, same erasure coding, fewer replicas.              |
|  Cold (Glacier): data packed into large sequential archives on        |
|  high-density HDDs. Retrieval requires "thawing" - reading from       |
|  archive and staging to a hot tier before serving.                    |
|  Deep Archive: data potentially on tape libraries. Retrieval takes    |
|  hours. Extremely cheap per GB because tape media cost is low.        |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|  Q8: How do pre-signed URLs work securely?                            |
+-----------------------------------------------------------------------+
|                                                                       |
|  The server signs the URL with HMAC using the requester's secret      |
|  key. The signature covers the HTTP method, bucket, key, expiry       |
|  time, and optional conditions (content type, max size). When the     |
|  URL is used, the storage service recomputes the signature and        |
|  verifies it matches. The URL is time-limited (e.g., 1 hour).         |
|  The signer's IAM permissions are checked at request time, not at     |
|  signing time - so revoking the IAM user's access also invalidates    |
|  outstanding pre-signed URLs.                                         |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|  Q9: How would you implement cross-region replication?                |
+-----------------------------------------------------------------------+
|                                                                       |
|  Attach a change-data-capture stream to the metadata DB. When an      |
|  object is written, a replication event is published to a durable     |
|  queue (e.g., Kafka). A replication worker in the destination         |
|  region reads the object from the source region and performs a full   |
|  PUT in the destination. Replication is asynchronous - a few          |
|  seconds of lag. For bidirectional replication, use conflict          |
|  resolution (last-writer-wins or version vectors). Replication        |
|  status is tracked per-object for monitoring and SLA compliance.      |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|  Q10: How do you prevent data loss from software bugs?                |
+-----------------------------------------------------------------------+
|                                                                       |
|  Defense in depth:                                                    |
|  1. Immutability: objects are write-once. Overwrites create new       |
|     versions (with versioning) or new chunk sets.                     |
|  2. Checksums at every layer: client>API, API>data node, on-disk.     |
|     Any mismatch triggers re-read or repair.                          |
|  3. Versioning + MFA Delete: critical buckets require MFA to delete   |
|     versions, preventing accidental mass deletion.                    |
|  4. Object Lock (WORM): compliance mode prevents any deletion for     |
|     a retention period, even by the root account.                     |
|  5. Canary reads: background jobs continuously read random objects    |
|     and verify integrity, catching silent corruption.                 |
|  6. Staged rollouts: code changes to the data path are deployed       |
|     gradually with automated rollback on error rate spikes.           |
+-----------------------------------------------------------------------+
```

*End of S3 / Object Storage System Design Notes*
