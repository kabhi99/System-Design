# FILE STORAGE SYSTEM DESIGN (GOOGLE DRIVE / DROPBOX)

A COMPLETE CONCEPTUAL GUIDE
SECTION 1: UNDERSTANDING THE PROBLEM
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHAT IS A CLOUD FILE STORAGE SYSTEM?                                 |*
*|                                                                         |*
*|  A service that allows users to:                                       |*
*|  * Store files in the cloud                                           |*
*|  * Access files from any device                                       |*
*|  * Sync files across devices automatically                            |*
*|  * Share files with others                                            |*
*|  * Collaborate in real-time                                           |*
*|                                                                         |*
*|  Examples: Google Drive, Dropbox, OneDrive, Box, iCloud Drive         |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  KEY CHALLENGES                                                        |*
*|                                                                         |*
*|  1. MASSIVE SCALE                                                      |*
*|     * Billions of files                                               |*
*|     * Petabytes of storage                                            |*
*|     * Millions of concurrent users                                    |*
*|                                                                         |*
*|  2. FILE SYNCHRONIZATION                                               |*
*|     * Keep files consistent across devices                            |*
*|     * Handle offline edits                                            |*
*|     * Resolve conflicts                                               |*
*|                                                                         |*
*|  3. RELIABILITY                                                        |*
*|     * Never lose user data                                            |*
*|     * Handle hardware failures                                        |*
*|     * Disaster recovery                                               |*
*|                                                                         |*
*|  4. PERFORMANCE                                                        |*
*|     * Fast uploads/downloads                                          |*
*|     * Quick sync                                                       |*
*|     * Low latency for metadata operations                            |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2: REQUIREMENTS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  FUNCTIONAL REQUIREMENTS                                               |*
*|                                                                         |*
*|  1. FILE OPERATIONS                                                    |*
*|     * Upload files (any type, up to several GB)                      |*
*|     * Download files                                                   |*
*|     * Delete files                                                     |*
*|     * Move/rename files                                               |*
*|     * Create folders                                                   |*
*|                                                                         |*
*|  2. SYNCHRONIZATION                                                    |*
*|     * Sync files across multiple devices                             |*
*|     * Support offline access                                          |*
*|     * Auto-sync when back online                                     |*
*|     * Conflict detection and resolution                              |*
*|                                                                         |*
*|  3. SHARING                                                            |*
*|     * Share files/folders with specific users                        |*
*|     * Public links with optional password/expiry                     |*
*|     * Permission levels (view, edit, admin)                          |*
*|                                                                         |*
*|  4. VERSION HISTORY                                                    |*
*|     * Keep previous versions of files                                |*
*|     * Restore to previous versions                                   |*
*|     * View version history                                            |*
*|                                                                         |*
*|  5. SEARCH                                                             |*
*|     * Search by filename                                              |*
*|     * Full-text search within documents                              |*
*|     * Search by metadata (date, type, owner)                        |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  NON-FUNCTIONAL REQUIREMENTS                                           |*
*|                                                                         |*
*|  1. RELIABILITY                                                        |*
*|     * Data durability: 99.999999999% (11 nines)                      |*
*|     * No data loss ever                                               |*
*|                                                                         |*
*|  2. AVAILABILITY                                                       |*
*|     * 99.9% uptime                                                    |*
*|     * Graceful degradation                                            |*
*|                                                                         |*
*|  3. SCALABILITY                                                        |*
*|     * Support billions of files                                       |*
*|     * Handle traffic spikes                                           |*
*|                                                                         |*
*|  4. PERFORMANCE                                                        |*
*|     * Upload/download: maximize bandwidth utilization                |*
*|     * Sync: near-instant for small changes                          |*
*|     * Metadata operations: < 100ms                                   |*
*|                                                                         |*
*|  5. SECURITY                                                           |*
*|     * Encryption at rest and in transit                              |*
*|     * Access control                                                  |*
*|     * Audit logging                                                   |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3: SCALE ESTIMATION
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  ASSUMPTIONS                                                           |*
*|                                                                         |*
*|  * 500 million total users                                            |*
*|  * 100 million daily active users (DAU)                               |*
*|  * Average 200 files per user                                         |*
*|  * Average file size: 500 KB                                          |*
*|  * 15 GB free storage per user                                        |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  STORAGE ESTIMATION                                                    |*
*|                                                                         |*
*|  Total files:                                                          |*
*|  500M users × 200 files = 100 billion files                           |*
*|                                                                         |*
*|  Total storage (if all users max out):                                |*
*|  500M users × 15 GB = 7.5 Exabytes (EB)                              |*
*|                                                                         |*
*|  Realistic storage (average 5 GB per user):                           |*
*|  500M × 5 GB = 2.5 Exabytes (EB)                                     |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  TRAFFIC ESTIMATION                                                    |*
*|                                                                         |*
*|  Uploads per day:                                                      |*
*|  * Assume each DAU uploads 2 files/day                               |*
*|  * 100M × 2 = 200 million uploads/day                                |*
*|  * 200M / 86400 = ~2,300 uploads/second                              |*
*|                                                                         |*
*|  Downloads per day:                                                    |*
*|  * Assume each DAU downloads 5 files/day                             |*
*|  * 100M × 5 = 500 million downloads/day                              |*
*|  * 500M / 86400 = ~5,800 downloads/second                            |*
*|                                                                         |*
*|  Bandwidth:                                                            |*
*|  * Upload: 2300/s × 500 KB = 1.15 GB/s                              |*
*|  * Download: 5800/s × 500 KB = 2.9 GB/s                             |*
*|  * Peak (5x): ~15 GB/s total                                        |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  METADATA ESTIMATION                                                   |*
*|                                                                         |*
*|  Metadata per file:                                                    |*
*|  * File ID: 16 bytes                                                 |*
*|  * Filename: 100 bytes (avg)                                         |*
*|  * Owner ID: 8 bytes                                                  |*
*|  * Size: 8 bytes                                                      |*
*|  * Created/Modified timestamps: 16 bytes                             |*
*|  * Checksum: 32 bytes                                                 |*
*|  * Permissions: 100 bytes                                            |*
*|  * Path/folder info: 200 bytes                                       |*
*|  * Total: ~500 bytes per file                                        |*
*|                                                                         |*
*|  Total metadata:                                                       |*
*|  100 billion files × 500 bytes = 50 TB                               |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4: HIGH-LEVEL ARCHITECTURE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SYSTEM COMPONENTS OVERVIEW                                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |              CLIENTS (Web, Desktop, Mobile)                    |  |*
*|  |                          |                                      |  |*
*|  |                          v                                      |  |*
*|  |            +-----------------------------+                     |  |*
*|  |            |       LOAD BALANCER         |                     |  |*
*|  |            +-------------+---------------+                     |  |*
*|  |                          |                                      |  |*
*|  |         +----------------+----------------+                    |  |*
*|  |         |                |                |                    |  |*
*|  |         v                v                v                    |  |*
*|  |    +---------+     +---------+     +---------+               |  |*
*|  |    |   API   |     |   API   |     |   API   |               |  |*
*|  |    | Gateway |     | Gateway |     | Gateway |               |  |*
*|  |    +----+----+     +----+----+     +----+----+               |  |*
*|  |         |                |                |                    |  |*
*|  |         +----------------+----------------+                    |  |*
*|  |                          |                                      |  |*
*|  |    +---------------------+---------------------+              |  |*
*|  |    |                     |                     |              |  |*
*|  |    v                     v                     v              |  |*
*|  |  +----------+     +----------+     +--------------+          |  |*
*|  |  | Metadata |     |   Sync   |     |    Block     |          |  |*
*|  |  | Service  |     | Service  |     |   Service    |          |  |*
*|  |  +----+-----+     +----+-----+     +------+-------+          |  |*
*|  |       |                |                  |                   |  |*
*|  |       v                v                  v                   |  |*
*|  |  +----------+   +-----------+    +-----------------+        |  |*
*|  |  | Metadata |   |   Sync    |    |  Block Storage  |        |  |*
*|  |  |    DB    |   |   Queue   |    |  (Blob Store)   |        |  |*
*|  |  +----------+   +-----------+    +-----------------+        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  KEY DESIGN PRINCIPLE: SEPARATE METADATA FROM FILE DATA              |*
*|                                                                         |*
*|  WHY?                                                                  |*
*|  * Metadata operations are frequent, small, need low latency         |*
*|  * File data is large, needs high throughput                         |*
*|  * Different storage requirements, different scaling                 |*
*|  * Metadata in database, files in blob storage                       |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 5: CORE COMPONENTS DEEP DIVE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  1. BLOCK SERVICE (File Chunking)                                     |*
*|  ================================                                      |*
*|                                                                         |*
*|  KEY INSIGHT: Don't store files as single blobs!                      |*
*|  Instead, split files into fixed-size BLOCKS (chunks)                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Original file (10 MB):                                        |  |*
*|  |  +----------------------------------------------------------+ |  |*
*|  |  |                    document.pdf                           | |  |*
*|  |  +----------------------------------------------------------+ |  |*
*|  |                          |                                     |  |*
*|  |                          | Split into 4 MB blocks             |  |*
*|  |                          v                                     |  |*
*|  |  +----------------+ +----------------+ +----------------+    |  |*
*|  |  |   Block 1      | |   Block 2      | |   Block 3      |    |  |*
*|  |  |   4 MB         | |   4 MB         | |   2 MB         |    |  |*
*|  |  |   hash: abc123 | |   hash: def456 | |   hash: ghi789 |    |  |*
*|  |  +----------------+ +----------------+ +----------------+    |  |*
*|  |                                                                 |  |*
*|  |  Each block stored separately with content-hash as ID         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  WHY CHUNKING?                                                         |*
*|                                                                         |*
*|  BENEFIT 1: EFFICIENT SYNC                                            |*
*|  * If only 1 block changes, upload only that block                  |*
*|  * Not the entire file!                                              |*
*|                                                                         |*
*|  BENEFIT 2: DEDUPLICATION                                             |*
*|  * Same block content = same hash                                    |*
*|  * Store identical blocks only once                                  |*
*|  * User A and User B upload same file -> stored once                 |*
*|                                                                         |*
*|  BENEFIT 3: RESUMABLE UPLOADS                                         |*
*|  * Upload interrupted? Resume from last successful block            |*
*|  * Don't restart entire file                                        |*
*|                                                                         |*
*|  BENEFIT 4: PARALLEL TRANSFERS                                        |*
*|  * Upload/download multiple blocks simultaneously                   |*
*|  * Maximize bandwidth utilization                                    |*
*|                                                                         |*
*|  BLOCK SIZE DECISION:                                                  |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TOO SMALL (e.g., 64 KB):                                     |  |*
*|  |  [ ] Too many blocks per file (metadata overhead)              |  |*
*|  |  [ ] Too many network round trips                               |  |*
*|  |                                                                 |  |*
*|  |  TOO LARGE (e.g., 64 MB):                                     |  |*
*|  |  [ ] Small change = upload entire large block                  |  |*
*|  |  [ ] Less deduplication opportunity                            |  |*
*|  |                                                                 |  |*
*|  |  SWEET SPOT: 4 MB (Dropbox uses 4 MB)                        |  |*
*|  |  [x] Good balance of overhead vs efficiency                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  2. METADATA SERVICE                                                   |*
*|  ===================                                                   |*
*|                                                                         |*
*|  Stores information ABOUT files (not the files themselves)           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  FILE METADATA:                                                |  |*
*|  |                                                                 |  |*
*|  |  {                                                              |  |*
*|  |    "file_id": "f123456",                                      |  |*
*|  |    "name": "document.pdf",                                    |  |*
*|  |    "size": 10485760,             // 10 MB                     |  |*
*|  |    "mime_type": "application/pdf",                            |  |*
*|  |    "owner_id": "u789",                                        |  |*
*|  |    "parent_folder_id": "folder123",                          |  |*
*|  |    "created_at": "2024-01-15T10:30:00Z",                     |  |*
*|  |    "modified_at": "2024-01-15T14:20:00Z",                    |  |*
*|  |    "version": 3,                                              |  |*
*|  |    "checksum": "sha256:abc123...",                           |  |*
*|  |    "blocks": [                                                 |  |*
*|  |      {"hash": "abc123", "order": 0, "size": 4194304},       |  |*
*|  |      {"hash": "def456", "order": 1, "size": 4194304},       |  |*
*|  |      {"hash": "ghi789", "order": 2, "size": 2097152}        |  |*
*|  |    ]                                                           |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  DATABASE SCHEMA:                                                      |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: users                                                  |  |*
*|  |  * user_id (PK)                                               |  |*
*|  |  * email                                                       |  |*
*|  |  * storage_quota                                               |  |*
*|  |  * storage_used                                                |  |*
*|  |                                                                 |  |*
*|  |  TABLE: files                                                  |  |*
*|  |  * file_id (PK)                                               |  |*
*|  |  * name                                                        |  |*
*|  |  * owner_id (FK -> users)                                      |  |*
*|  |  * parent_folder_id (FK -> files, nullable)                   |  |*
*|  |  * is_folder (boolean)                                        |  |*
*|  |  * size                                                        |  |*
*|  |  * checksum                                                    |  |*
*|  |  * latest_version                                              |  |*
*|  |  * created_at, modified_at                                    |  |*
*|  |                                                                 |  |*
*|  |  TABLE: file_versions                                         |  |*
*|  |  * version_id (PK)                                            |  |*
*|  |  * file_id (FK -> files)                                       |  |*
*|  |  * version_number                                              |  |*
*|  |  * size                                                        |  |*
*|  |  * checksum                                                    |  |*
*|  |  * created_at                                                  |  |*
*|  |                                                                 |  |*
*|  |  TABLE: blocks                                                 |  |*
*|  |  * block_hash (PK) - content-addressed                       |  |*
*|  |  * size                                                        |  |*
*|  |  * storage_location                                           |  |*
*|  |  * reference_count (for garbage collection)                  |  |*
*|  |                                                                 |  |*
*|  |  TABLE: file_blocks (mapping)                                 |  |*
*|  |  * file_version_id (FK)                                       |  |*
*|  |  * block_hash (FK)                                            |  |*
*|  |  * block_order                                                 |  |*
*|  |                                                                 |  |*
*|  |  TABLE: sharing                                                |  |*
*|  |  * file_id (FK)                                               |  |*
*|  |  * shared_with_user_id (FK)                                   |  |*
*|  |  * permission (view/edit/admin)                               |  |*
*|  |  * created_at                                                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  3. BLOCK STORAGE (Blob Store)                                        |*
*|  =============================                                         |*
*|                                                                         |*
*|  Where the actual file blocks are stored                              |*
*|                                                                         |*
*|  OPTIONS:                                                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  OPTION A: Cloud Object Storage (Recommended)                 |  |*
*|  |  * Amazon S3, Google Cloud Storage, Azure Blob               |  |*
*|  |  * 11 nines durability built-in                              |  |*
*|  |  * Auto-replication across regions                           |  |*
*|  |  * Pay per use, infinite scale                               |  |*
*|  |                                                                 |  |*
*|  |  OPTION B: Build Your Own (HDFS-like)                        |  |*
*|  |  * Hadoop Distributed File System                            |  |*
*|  |  * Full control                                               |  |*
*|  |  * More operational complexity                                |  |*
*|  |  * Used by: Facebook (Haystack), early Dropbox               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  KEY CONCEPT: CONTENT-ADDRESSABLE STORAGE                             |*
*|                                                                         |*
*|  Block ID = Hash of block content                                      |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Block content: "Hello World..."                              |  |*
*|  |              |                                                  |  |*
*|  |              v                                                  |  |*
*|  |  SHA256 hash: "a591a6d40bf420404a011733cfb7b190..."          |  |*
*|  |              |                                                  |  |*
*|  |              v                                                  |  |*
*|  |  Stored at: s3://blocks/a591a6d40bf420404a...                |  |*
*|  |                                                                 |  |*
*|  |  Benefits:                                                     |  |*
*|  |  * Automatic deduplication (same content = same hash)        |  |*
*|  |  * Integrity verification (hash mismatch = corruption)       |  |*
*|  |  * Immutable (content can't change without changing hash)    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  4. SYNC SERVICE                                                       |*
*|  ===============                                                       |*
*|                                                                         |*
*|  The brain of the system - keeps devices in sync                      |*
*|                                                                         |*
*|  HOW SYNC WORKS:                                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  DEVICE A (Laptop)          CLOUD           DEVICE B (Phone)  |  |*
*|  |        |                      |                      |         |  |*
*|  |        | 1. File modified     |                      |         |  |*
*|  |        |    locally           |                      |         |  |*
*|  |        |                      |                      |         |  |*
*|  |        | 2. Compute changed   |                      |         |  |*
*|  |        |    blocks            |                      |         |  |*
*|  |        |                      |                      |         |  |*
*|  |        | 3. Upload changed    |                      |         |  |*
*|  |        +--------------------->|                      |         |  |*
*|  |        |    blocks only       |                      |         |  |*
*|  |        |                      |                      |         |  |*
*|  |        |                      | 4. Notify Device B   |         |  |*
*|  |        |                      |    "file changed"    |         |  |*
*|  |        |                      +--------------------->|         |  |*
*|  |        |                      |                      |         |  |*
*|  |        |                      | 5. Request changes   |         |  |*
*|  |        |                      |<---------------------+         |  |*
*|  |        |                      |                      |         |  |*
*|  |        |                      | 6. Send changed      |         |  |*
*|  |        |                      |    blocks            |         |  |*
*|  |        |                      +--------------------->|         |  |*
*|  |        |                      |                      |         |  |*
*|  |        |                      |                      | 7. Apply|  |*
*|  |        |                      |                      |   changes|  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  NOTIFICATION MECHANISM:                                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  OPTION 1: Long Polling                                       |  |*
*|  |  * Client keeps HTTP connection open                         |  |*
*|  |  * Server responds when change occurs                        |  |*
*|  |  * Fallback if WebSocket not available                       |  |*
*|  |                                                                 |  |*
*|  |  OPTION 2: WebSocket (Preferred)                              |  |*
*|  |  * Persistent bidirectional connection                       |  |*
*|  |  * Real-time push notifications                              |  |*
*|  |  * Low latency                                                |  |*
*|  |                                                                 |  |*
*|  |  OPTION 3: Push Notifications (Mobile)                        |  |*
*|  |  * FCM (Android), APNs (iOS)                                 |  |*
*|  |  * For when app is in background                             |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 6: FILE UPLOAD/DOWNLOAD FLOWS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  UPLOAD FLOW (Detailed)                                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Step 1: CLIENT PREPARES UPLOAD                                |  |*
*|  |  ---------------------------------                              |  |*
*|  |  * Split file into 4 MB blocks                                |  |*
*|  |  * Calculate SHA256 hash of each block                        |  |*
*|  |  * Calculate overall file checksum                            |  |*
*|  |                                                                 |  |*
*|  |  Step 2: CLIENT REQUESTS UPLOAD                                |  |*
*|  |  --------------------------------                               |  |*
*|  |  POST /api/files/upload                                       |  |*
*|  |  {                                                              |  |*
*|  |    "filename": "document.pdf",                                |  |*
*|  |    "size": 10485760,                                          |  |*
*|  |    "checksum": "sha256:...",                                  |  |*
*|  |    "blocks": [                                                 |  |*
*|  |      {"hash": "abc123", "size": 4194304},                    |  |*
*|  |      {"hash": "def456", "size": 4194304},                    |  |*
*|  |      {"hash": "ghi789", "size": 2097152}                     |  |*
*|  |    ]                                                           |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  Step 3: SERVER CHECKS FOR EXISTING BLOCKS (Deduplication)    |  |*
*|  |  ---------------------------------------------------------     |  |*
*|  |  Server responds:                                              |  |*
*|  |  {                                                              |  |*
*|  |    "file_id": "f123456",                                      |  |*
*|  |    "blocks_needed": ["abc123", "ghi789"],  // def456 exists! |  |*
*|  |    "upload_urls": {                                           |  |*
*|  |      "abc123": "https://s3.../presigned-url-1",              |  |*
*|  |      "ghi789": "https://s3.../presigned-url-2"               |  |*
*|  |    }                                                           |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  Step 4: CLIENT UPLOADS BLOCKS                                 |  |*
*|  |  ---------------------------------                              |  |*
*|  |  * Upload directly to blob storage (presigned URLs)          |  |*
*|  |  * Parallel uploads for speed                                 |  |*
*|  |  * Skip blocks that already exist                            |  |*
*|  |                                                                 |  |*
*|  |  Step 5: CLIENT CONFIRMS COMPLETION                           |  |*
*|  |  ---------------------------------                              |  |*
*|  |  POST /api/files/upload/complete                              |  |*
*|  |  {                                                              |  |*
*|  |    "file_id": "f123456",                                      |  |*
*|  |    "blocks_uploaded": ["abc123", "ghi789"]                   |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  Step 6: SERVER UPDATES METADATA                              |  |*
*|  |  ---------------------------------                              |  |*
*|  |  * Create file record in database                             |  |*
*|  |  * Link file to blocks                                        |  |*
*|  |  * Increment block reference counts                          |  |*
*|  |  * Update user's storage usage                                |  |*
*|  |  * Notify other devices for sync                             |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DOWNLOAD FLOW                                                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. Client requests file:                                     |  |*
*|  |     GET /api/files/{file_id}                                  |  |*
*|  |                                                                 |  |*
*|  |  2. Server returns metadata + download URLs:                  |  |*
*|  |     {                                                          |  |*
*|  |       "filename": "document.pdf",                             |  |*
*|  |       "size": 10485760,                                       |  |*
*|  |       "blocks": [                                              |  |*
*|  |         {"hash": "abc123", "url": "https://cdn.../abc123"},  |  |*
*|  |         {"hash": "def456", "url": "https://cdn.../def456"},  |  |*
*|  |         {"hash": "ghi789", "url": "https://cdn.../ghi789"}   |  |*
*|  |       ]                                                        |  |*
*|  |     }                                                          |  |*
*|  |                                                                 |  |*
*|  |  3. Client downloads blocks in parallel                       |  |*
*|  |     (from CDN for better performance)                         |  |*
*|  |                                                                 |  |*
*|  |  4. Client reassembles file from blocks                       |  |*
*|  |                                                                 |  |*
*|  |  5. Client verifies checksum                                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 7: CONFLICT RESOLUTION
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  THE CONFLICT PROBLEM                                                  |*
*|                                                                         |*
*|  What if two users edit the same file simultaneously?                 |*
*|  Or same user edits on two offline devices?                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  SCENARIO: Offline Conflict                                    |  |*
*|  |                                                                 |  |*
*|  |  Time    Device A (Offline)    Server    Device B (Offline)   |  |*
*|  |  ----    -----------------     ------    -----------------    |  |*
*|  |  T0      File v1               File v1   File v1              |  |*
*|  |          |                               |                     |  |*
*|  |  T1      Edit -> v2 (local)               Edit -> v3 (local)    |  |*
*|  |          |                               |                     |  |*
*|  |  T2      Goes online ------------------------------------->   |  |*
*|  |          Uploads v2            v2        |                     |  |*
*|  |          |                               |                     |  |*
*|  |  T3      |                               Goes online          |  |*
*|  |          |                               Tries to upload v3   |  |*
*|  |          |                               CONFLICT!            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  CONFLICT RESOLUTION STRATEGIES                                       |*
*|                                                                         |*
*|  STRATEGY 1: Last Write Wins (Simple but lossy)                       |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  * Compare timestamps                                          |  |*
*|  |  * Latest edit wins                                            |  |*
*|  |  * Earlier edit is discarded                                   |  |*
*|  |                                                                 |  |*
*|  |  PROS: Simple                                                  |  |*
*|  |  CONS: Data loss! User's edits disappear                      |  |*
*|  |                                                                 |  |*
*|  |  USED BY: Some simple sync systems                            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  STRATEGY 2: Create Conflicting Copies (Dropbox approach) ⭐         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  * Detect conflict                                             |  |*
*|  |  * Keep BOTH versions                                         |  |*
*|  |  * Rename one as "conflicted copy"                            |  |*
*|  |                                                                 |  |*
*|  |  Result:                                                       |  |*
*|  |  * document.pdf (latest)                                      |  |*
*|  |  * document (John's conflicted copy 2024-01-15).pdf          |  |*
*|  |                                                                 |  |*
*|  |  PROS: No data loss                                           |  |*
*|  |  CONS: User must manually merge                               |  |*
*|  |                                                                 |  |*
*|  |  USED BY: Dropbox, most file sync services                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  STRATEGY 3: Operational Transform / CRDTs (Real-time collab)        |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  * Track individual operations (not whole file)               |  |*
*|  |  * Automatically merge non-conflicting changes                |  |*
*|  |  * Resolve conflicts at character level                       |  |*
*|  |                                                                 |  |*
*|  |  PROS: Seamless real-time collaboration                       |  |*
*|  |  CONS: Complex, only works for certain file types            |  |*
*|  |                                                                 |  |*
*|  |  USED BY: Google Docs, Notion, Figma                         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  RECOMMENDATION FOR FILE STORAGE:                                     |*
*|  * Strategy 2 (Conflicting copies) for files                        |*
*|  * Strategy 3 for documents that support real-time editing          |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 8: DEDUPLICATION
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHY DEDUPLICATION?                                                    |*
*|                                                                         |*
*|  * Same file uploaded by thousands of users                          |*
*|  * Popular documents, photos, videos                                  |*
*|  * Can save 50-70% storage!                                          |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DEDUPLICATION LEVELS                                                 |*
*|                                                                         |*
*|  LEVEL 1: File-Level Dedup                                            |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  * Hash entire file                                            |  |*
*|  |  * If hash exists, don't store again                          |  |*
*|  |  * Simple but limited (any change = new file)                 |  |*
*|  |                                                                 |  |*
*|  |  User A: photo.jpg (hash: abc123) -> STORED                    |  |*
*|  |  User B: photo.jpg (hash: abc123) -> LINK to existing         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  LEVEL 2: Block-Level Dedup ⭐ (Better)                              |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  * Hash each block separately                                  |  |*
*|  |  * Even partial overlap is deduplicated                       |  |*
*|  |                                                                 |  |*
*|  |  File A (100 MB):  [Block1] [Block2] [Block3] ... [Block25]   |  |*
*|  |  File B (100 MB):  [Block1] [Block2] [BlockX] ... [Block25]   |  |*
*|  |                                                                 |  |*
*|  |  Only BlockX needs storage, others already exist!             |  |*
*|  |  95%+ space saved                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DEDUPLICATION SCOPE                                                  |*
*|                                                                         |*
*|  User-Level: Dedup within single user's files                        |*
*|  * Simple, no privacy concerns                                        |*
*|  * Limited savings                                                     |*
*|                                                                         |*
*|  Global: Dedup across ALL users ⭐                                    |*
*|  * Maximum storage savings                                            |*
*|  * Privacy consideration: Can't tell users "you already have this"  |*
*|  * Security: Encrypted blocks can't be deduplicated                 |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  REFERENCE COUNTING FOR GARBAGE COLLECTION                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Block "abc123" used by:                                      |  |*
*|  |  * User A's file1.pdf (version 1)                            |  |*
*|  |  * User A's file1.pdf (version 2)                            |  |*
*|  |  * User B's document.pdf                                      |  |*
*|  |                                                                 |  |*
*|  |  Reference count: 3                                            |  |*
*|  |                                                                 |  |*
*|  |  When User A deletes file1.pdf:                               |  |*
*|  |  * Decrement ref count: 3 -> 1                                 |  |*
*|  |  * Block still needed (User B has it)                        |  |*
*|  |                                                                 |  |*
*|  |  When User B deletes document.pdf:                            |  |*
*|  |  * Decrement ref count: 1 -> 0                                 |  |*
*|  |  * NOW safe to delete block from storage                     |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 9: SECURITY
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  ENCRYPTION                                                            |*
*|                                                                         |*
*|  IN TRANSIT:                                                           |*
*|  * TLS/HTTPS for all API calls                                       |*
*|  * TLS for upload/download to blob storage                           |*
*|                                                                         |*
*|  AT REST:                                                              |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  OPTION 1: Server-Side Encryption (Standard)                  |  |*
*|  |  * Cloud provider encrypts blocks                             |  |*
*|  |  * Provider manages keys                                       |  |*
*|  |  * Simple, transparent to application                         |  |*
*|  |  * Provider can technically read data                         |  |*
*|  |                                                                 |  |*
*|  |  OPTION 2: Client-Side Encryption (Zero-Knowledge)            |  |*
*|  |  * Client encrypts before upload                              |  |*
*|  |  * Only user has key                                          |  |*
*|  |  * Server cannot read data                                    |  |*
*|  |  * Breaks: deduplication, search, preview                    |  |*
*|  |  * Used by: Tresorit, SpiderOak                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  ACCESS CONTROL (DETAILED)                                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  PERMISSION MODEL: Role-Based + Resource-Based Hybrid         |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  PERMISSION HIERARCHY:                                        |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |  OWNER (Full Control)                                     ||  |*
*|  |  |  * Delete file permanently                                ||  |*
*|  |  |  * Transfer ownership                                     ||  |*
*|  |  |  * Change sharing settings                                ||  |*
*|  |  |  * View all permissions                                   ||  |*
*|  |  |  * All Editor permissions                                 ||  |*
*|  |  |                                                           ||  |*
*|  |  |  EDITOR (Modify)                                          ||  |*
*|  |  |  * Upload new versions                                    ||  |*
*|  |  |  * Rename file                                            ||  |*
*|  |  |  * Move file (within shared scope)                       ||  |*
*|  |  |  * All Commenter permissions                              ||  |*
*|  |  |                                                           ||  |*
*|  |  |  COMMENTER (Collaborate)                                  ||  |*
*|  |  |  * Add comments                                           ||  |*
*|  |  |  * Suggest edits (for supported docs)                    ||  |*
*|  |  |  * All Viewer permissions                                 ||  |*
*|  |  |                                                           ||  |*
*|  |  |  VIEWER (Read-Only)                                       ||  |*
*|  |  |  * View/preview file                                      ||  |*
*|  |  |  * Download file (if allowed)                            ||  |*
*|  |  |  * View version history                                   ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  SHARING SCOPE:                                                |  |*
*|  |                                                                 |  |*
*|  |  1. PRIVATE (Default)                                         |  |*
*|  |     Only owner can access                                     |  |*
*|  |                                                                 |  |*
*|  |  2. SPECIFIC USERS                                            |  |*
*|  |     Share with individual email addresses                     |  |*
*|  |     Each user gets explicit permission level                 |  |*
*|  |                                                                 |  |*
*|  |  3. GROUPS                                                     |  |*
*|  |     Share with predefined groups (e.g., "Engineering Team")  |  |*
*|  |     Group membership managed separately                       |  |*
*|  |                                                                 |  |*
*|  |  4. ORGANIZATION (Domain)                                     |  |*
*|  |     Anyone with @company.com can access                      |  |*
*|  |     Common for internal documents                            |  |*
*|  |                                                                 |  |*
*|  |  5. ANYONE WITH LINK                                          |  |*
*|  |     No authentication required                                |  |*
*|  |     Link acts as secret key                                   |  |*
*|  |                                                                 |  |*
*|  |  6. PUBLIC                                                     |  |*
*|  |     Discoverable via search                                   |  |*
*|  |     Indexed by search engines                                |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  ACCESS CONTROL DATABASE SCHEMA:                              |  |*
*|  |                                                                 |  |*
*|  |  TABLE: permissions                                           |  |*
*|  |  +------------+-------------+------------+---------------+   |  |*
*|  |  | file_id    | grantee_type| grantee_id | permission    |   |  |*
*|  |  +------------+-------------+------------+---------------+   |  |*
*|  |  | f123       | USER        | u456       | EDITOR        |   |  |*
*|  |  | f123       | GROUP       | g789       | VIEWER        |   |  |*
*|  |  | f123       | DOMAIN      | company.com| VIEWER        |   |  |*
*|  |  | f123       | ANYONE      | NULL       | VIEWER        |   |  |*
*|  |  +------------+-------------+------------+---------------+   |  |*
*|  |                                                                 |  |*
*|  |  TABLE: share_links                                           |  |*
*|  |  +---------+---------+-----------+----------+------------+   |  |*
*|  |  | link_id | file_id | token     | password | expires_at |   |  |*
*|  |  |         |         | (random)  | (hashed) |            |   |  |*
*|  |  +---------+---------+-----------+----------+------------+   |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  PERMISSION CHECK FLOW:                                       |  |*
*|  |                                                                 |  |*
*|  |  1. User requests file access                                 |  |*
*|  |  2. Check: Is user the owner? -> Full access                  |  |*
*|  |  3. Check: Does user have explicit permission? -> Use it      |  |*
*|  |  4. Check: Is user in a group with permission? -> Use it     |  |*
*|  |  5. Check: Is user's domain allowed? -> Use it               |  |*
*|  |  6. Check: Is file public/link-shared? -> Use that level     |  |*
*|  |  7. Otherwise -> DENY                                          |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  FOLDER PERMISSION INHERITANCE:                               |  |*
*|  |                                                                 |  |*
*|  |  By default, files inherit parent folder permissions         |  |*
*|  |                                                                 |  |*
*|  |  Shared Folder/               <- Shared with Team (Editor)    |  |*
*|  |    +-- doc1.pdf               <- Inherits Editor access       |  |*
*|  |    +-- doc2.pdf               <- Inherits Editor access       |  |*
*|  |    +-- Subfolder/             <- Inherits Editor access       |  |*
*|  |        +-- secret.pdf         <- Can restrict further        |  |*
*|  |                                                                 |  |*
*|  |  Rules:                                                        |  |*
*|  |  * Child can RESTRICT parent permissions                     |  |*
*|  |  * Child CANNOT grant MORE than parent allows                |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  LINK OPTIONS:                                                 |  |*
*|  |                                                                 |  |*
*|  |  * Password protected                                         |  |*
*|  |  * Expiration date                                            |  |*
*|  |  * Download disabled (view only)                             |  |*
*|  |  * Access count limit (e.g., valid for 10 views)            |  |*
*|  |  * IP whitelist                                               |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  AUDIT LOGGING:                                                |  |*
*|  |                                                                 |  |*
*|  |  Track all access for compliance:                             |  |*
*|  |  * Who accessed what file                                     |  |*
*|  |  * When (timestamp)                                           |  |*
*|  |  * What action (view, download, edit, share)                 |  |*
*|  |  * From where (IP, device)                                   |  |*
*|  |  * Result (allowed, denied)                                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  PRESIGNED URLs FOR SECURE DIRECT ACCESS                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Instead of proxying all file data through API servers:       |  |*
*|  |                                                                 |  |*
*|  |  1. Client requests download                                  |  |*
*|  |  2. Server verifies permissions                               |  |*
*|  |  3. Server generates presigned URL (valid 15 min)            |  |*
*|  |  4. Client downloads directly from blob storage              |  |*
*|  |                                                                 |  |*
*|  |  Presigned URL example:                                       |  |*
*|  |  https://s3.amazonaws.com/bucket/block123                    |  |*
*|  |    ?X-Amz-Algorithm=AWS4-HMAC-SHA256                         |  |*
*|  |    &X-Amz-Expires=900                                        |  |*
*|  |    &X-Amz-Signature=abc123...                                |  |*
*|  |                                                                 |  |*
*|  |  Benefits:                                                     |  |*
*|  |  * Reduced load on API servers                               |  |*
*|  |  * Better download speeds (CDN/edge)                         |  |*
*|  |  * Still secure (temporary, signed)                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 10: SCALING AND RELIABILITY
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  METADATA DATABASE SCALING                                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  OPTION 1: Single Database with Read Replicas                 |  |*
*|  |  * PostgreSQL/MySQL                                            |  |*
*|  |  * Master for writes, replicas for reads                      |  |*
*|  |  * Good up to ~millions of users                              |  |*
*|  |                                                                 |  |*
*|  |  OPTION 2: Sharded Database                                   |  |*
*|  |  * Shard by user_id                                           |  |*
*|  |  * Each user's data on one shard                             |  |*
*|  |  * Complex: cross-shard queries for sharing                  |  |*
*|  |                                                                 |  |*
*|  |  OPTION 3: NoSQL (Cassandra/DynamoDB)                        |  |*
*|  |  * Built-in horizontal scaling                                |  |*
*|  |  * Partition by user_id + file_id                            |  |*
*|  |  * Limited query flexibility                                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  BLOB STORAGE SCALING                                                 |*
*|                                                                         |*
*|  Cloud object storage (S3, GCS) handles this automatically:          |*
*|  * Unlimited scale                                                    |*
*|  * 11 nines durability                                               |*
*|  * Automatic replication across zones/regions                        |*
*|  * Pay per use                                                        |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DATA REPLICATION                                                      |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  WITHIN REGION (High Availability):                           |  |*
*|  |  * 3 copies across availability zones                        |  |*
*|  |  * Survives: single server/rack/zone failure                 |  |*
*|  |                                                                 |  |*
*|  |  CROSS REGION (Disaster Recovery):                            |  |*
*|  |  * Async replication to secondary region                     |  |*
*|  |  * Survives: entire region outage                            |  |*
*|  |  * Trade-off: storage cost vs recovery point objective       |  |*
*|  |                                                                 |  |*
*|  |  +-----------------+        +-----------------+              |  |*
*|  |  |   US-EAST       |        |   US-WEST       |              |  |*
*|  |  |                 |  Async |                 |              |  |*
*|  |  |  +---+ +---+    |<------>| +---+ +---+     |              |  |*
*|  |  |  |AZ1| |AZ2|   |  Repl   | |AZ1| |AZ2|     |              |  |*
*|  |  |  +---+ +---+   |         | +---+ +---+     |              |  |*
*|  |  |     +---+      |         |    +---+        |              |  |*
*|  |  |     |AZ3|      |         |    |AZ3|        |              |  |*
*|  |  |     +---+      |         |    +---+        |              |  |*
*|  |  +-----------------+        +-----------------+              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  CDN FOR DOWNLOADS                                                     |*
*|                                                                         |*
*|  * Cache popular files at edge locations                             |*
*|  * Faster downloads for users worldwide                              |*
*|  * Reduced load on origin (blob storage)                            |*
*|  * CloudFront, Cloudflare, Fastly                                   |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 11: ADDITIONAL FEATURES
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  VERSION HISTORY (DETAILED)                                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  WHY VERSIONING?                                               |  |*
*|  |                                                                 |  |*
*|  |  * Recover from accidental changes                            |  |*
*|  |  * Undo unwanted edits                                        |  |*
*|  |  * Audit trail of changes                                     |  |*
*|  |  * Compare different versions                                  |  |*
*|  |  * Ransomware protection (restore pre-attack)                |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  VERSION STORAGE MODEL:                                        |  |*
*|  |                                                                 |  |*
*|  |  Each file edit creates a new version                         |  |*
*|  |  Versions share unchanged blocks (space efficient!)           |  |*
*|  |                                                                 |  |*
*|  |  document.pdf                                                  |  |*
*|  |  |                                                             |  |*
*|  |  +-- Version 3 (current) - Jan 15, 3:00 PM - John            |  |*
*|  |  |   Blocks: [abc, def, NEW_ghi]                             |  |*
*|  |  |   Size: 10 MB                                              |  |*
*|  |  |   Action: "Updated page 3"                                |  |*
*|  |  |                                                             |  |*
*|  |  +-- Version 2 - Jan 15, 10:00 AM - Mary                     |  |*
*|  |  |   Blocks: [abc, def, old_ghi]                             |  |*
*|  |  |   Size: 10 MB                                              |  |*
*|  |  |   Action: "Added signature"                               |  |*
*|  |  |                                                             |  |*
*|  |  +-- Version 1 - Jan 10, 9:00 AM - John                      |  |*
*|  |      Blocks: [abc, xyz]                                       |  |*
*|  |      Size: 8 MB                                               |  |*
*|  |      Action: "Initial upload"                                |  |*
*|  |                                                                 |  |*
*|  |  STORAGE EFFICIENCY:                                           |  |*
*|  |  * Only new/changed blocks stored                            |  |*
*|  |  * Blocks [abc, def] shared across versions                  |  |*
*|  |  * 3 versions of 10 MB file ≠ 30 MB storage                 |  |*
*|  |  * Actual storage might be only 15 MB (shared blocks)        |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  VERSION DATABASE SCHEMA:                                      |  |*
*|  |                                                                 |  |*
*|  |  TABLE: file_versions                                         |  |*
*|  |  +------------+----------+------------+-----------+--------+ |  |*
*|  |  | version_id | file_id  | version_num| created_by| size   | |  |*
*|  |  +------------+----------+------------+-----------+--------+ |  |*
*|  |  | v789       | f123     | 3          | u_john    | 10 MB  | |  |*
*|  |  | v456       | f123     | 2          | u_mary    | 10 MB  | |  |*
*|  |  | v123       | f123     | 1          | u_john    | 8 MB   | |  |*
*|  |  +------------+----------+------------+-----------+--------+ |  |*
*|  |                                                                 |  |*
*|  |  TABLE: version_blocks (mapping)                              |  |*
*|  |  +------------+------------+-------------+                   |  |*
*|  |  | version_id | block_hash | block_order |                   |  |*
*|  |  +------------+------------+-------------+                   |  |*
*|  |  | v789       | abc        | 0           |                   |  |*
*|  |  | v789       | def        | 1           |                   |  |*
*|  |  | v789       | NEW_ghi    | 2           |                   |  |*
*|  |  | v456       | abc        | 0           | <- Same block!    |  |*
*|  |  | v456       | def        | 1           | <- Same block!    |  |*
*|  |  | v456       | old_ghi    | 2           |                   |  |*
*|  |  +------------+------------+-------------+                   |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  VERSION OPERATIONS:                                           |  |*
*|  |                                                                 |  |*
*|  |  1. VIEW HISTORY                                              |  |*
*|  |     List all versions with metadata                          |  |*
*|  |     Show who made changes and when                           |  |*
*|  |                                                                 |  |*
*|  |  2. PREVIEW OLD VERSION                                       |  |*
*|  |     View/download any previous version                       |  |*
*|  |     Compare with current version                             |  |*
*|  |                                                                 |  |*
*|  |  3. RESTORE VERSION                                           |  |*
*|  |     Make old version the current version                     |  |*
*|  |     Creates new version (doesn't delete history)             |  |*
*|  |     v3 -> v4 (content of v1)                                  |  |*
*|  |                                                                 |  |*
*|  |  4. NAMED VERSIONS (Snapshots)                                |  |*
*|  |     Mark important versions: "Final Draft"                   |  |*
*|  |     Protected from auto-cleanup                              |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  VERSION CREATION TRIGGERS:                                   |  |*
*|  |                                                                 |  |*
*|  |  1. EXPLICIT SAVE                                             |  |*
*|  |     User clicks "Save" in editor                             |  |*
*|  |                                                                 |  |*
*|  |  2. FILE RE-UPLOAD                                            |  |*
*|  |     Desktop client detects file change -> sync               |  |*
*|  |                                                                 |  |*
*|  |  3. AUTO-SAVE (for documents)                                |  |*
*|  |     Every N minutes during editing                           |  |*
*|  |     Coalesce rapid changes (don't create 100 versions)      |  |*
*|  |                                                                 |  |*
*|  |  4. SIGNIFICANT CHANGE                                        |  |*
*|  |     More than X% of file changed                             |  |*
*|  |     Skip version for tiny typo fixes                        |  |*
*|  |                                                                 |  |*
*|  |  ============================================================ |  |*
*|  |                                                                 |  |*
*|  |  DELTA STORAGE (Advanced Optimization):                       |  |*
*|  |                                                                 |  |*
*|  |  For text files, store DELTA (diff) instead of full version |  |*
*|  |                                                                 |  |*
*|  |  v1: Full content (base)                                     |  |*
*|  |  v2: Delta from v1 (+10 lines, -2 lines)                    |  |*
*|  |  v3: Delta from v2 (+5 lines, modified 1 line)              |  |*
*|  |                                                                 |  |*
*|  |  Reconstruct: v1 + delta(v2) + delta(v3) = current          |  |*
*|  |                                                                 |  |*
*|  |  Trade-off:                                                    |  |*
*|  |  * Saves storage                                              |  |*
*|  |  * Slower to reconstruct old versions                        |  |*
*|  |  * Periodically store full "keyframes"                       |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  VERSION RETENTION POLICY:                                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TIER 1: Recent (0-30 days)                                   |  |*
*|  |  * Keep ALL versions                                          |  |*
*|  |  * Full resolution history                                    |  |*
*|  |                                                                 |  |*
*|  |  TIER 2: Medium (30-365 days)                                 |  |*
*|  |  * Keep daily snapshots (last version of each day)           |  |*
*|  |  * Delete intermediate versions                               |  |*
*|  |                                                                 |  |*
*|  |  TIER 3: Long-term (1+ years)                                 |  |*
*|  |  * Keep monthly snapshots                                     |  |*
*|  |  * Or user-named "important" versions                        |  |*
*|  |                                                                 |  |*
*|  |  NEVER DELETE:                                                 |  |*
*|  |  * Named/starred versions                                     |  |*
*|  |  * Versions with comments                                     |  |*
*|  |  * Legally required (compliance)                             |  |*
*|  |                                                                 |  |*
*|  |  Premium users: Extended retention (keep all for 1 year)     |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SEARCH                                                                |*
*|                                                                         |*
*|  Filename search:                                                      |*
*|  * Index filenames in Elasticsearch                                  |*
*|  * Fast prefix/substring matching                                    |*
*|                                                                         |*
*|  Full-text search (documents):                                        |*
*|  * Extract text from PDFs, docs, etc.                               |*
*|  * Index in Elasticsearch                                            |*
*|  * Async processing (not blocking upload)                           |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  TRASH / SOFT DELETE                                                  |*
*|                                                                         |*
*|  * Deleted files go to trash                                         |*
*|  * Recoverable for 30 days                                           |*
*|  * Then permanently deleted                                           |*
*|  * Doesn't count against quota while in trash                       |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  OFFLINE MODE                                                          |*
*|                                                                         |*
*|  Desktop/mobile clients:                                              |*
*|  * Mark files for offline access                                     |*
*|  * Download and cache locally                                        |*
*|  * Track local changes while offline                                |*
*|  * Sync when back online                                             |*
*|  * Handle conflicts (conflicting copies)                            |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 12: INTERVIEW QUICK REFERENCE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  KEY DESIGN DECISIONS                                                  |*
*|                                                                         |*
*|  1. CHUNKING (Most Important!)                                        |*
*|     * Split files into 4 MB blocks                                   |*
*|     * Enables: efficient sync, deduplication, resumable uploads     |*
*|     * Content-addressable: block ID = hash of content               |*
*|                                                                         |*
*|  2. SEPARATE METADATA FROM DATA                                       |*
*|     * Metadata: PostgreSQL/MySQL (fast queries, ACID)               |*
*|     * File data: S3/GCS (infinite scale, 11 nines durability)      |*
*|                                                                         |*
*|  3. DEDUPLICATION                                                      |*
*|     * Block-level dedup saves 50-70% storage                        |*
*|     * Reference counting for garbage collection                     |*
*|                                                                         |*
*|  4. SYNC MECHANISM                                                     |*
*|     * WebSocket for real-time notifications                         |*
*|     * Only sync changed blocks                                       |*
*|     * Conflict resolution: create conflicting copies                |*
*|                                                                         |*
*|  5. SECURITY                                                           |*
*|     * Presigned URLs for direct blob access                        |*
*|     * Server-side encryption at rest                                |*
*|     * TLS for transit                                                |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  COMMON INTERVIEW QUESTIONS                                           |*
*|                                                                         |*
*|  Q: How do you handle large file uploads?                            |*
*|  A: Chunking + parallel upload + resumable + presigned URLs         |*
*|                                                                         |*
*|  Q: How do you sync files across devices?                            |*
*|  A: Track changes, only sync changed blocks, WebSocket notif        |*
*|                                                                         |*
*|  Q: How do you handle conflicts?                                      |*
*|  A: Create conflicting copies (like Dropbox), user resolves         |*
*|                                                                         |*
*|  Q: How do you save storage?                                          |*
*|  A: Block-level deduplication using content hashing                 |*
*|                                                                         |*
*|  Q: How do you ensure durability?                                     |*
*|  A: Cloud storage (11 nines) + cross-region replication            |*
*|                                                                         |*
*|  Q: How do you scale metadata?                                        |*
*|  A: Shard by user_id, read replicas                                 |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  ARCHITECTURE SUMMARY                                                  |*
*|                                                                         |*
*|  Client -> LB -> API Gateway -> Services -> Storage                      |*
*|                                                                         |*
*|  Services:                                                             |*
*|  * Metadata Service -> PostgreSQL (files, folders, sharing)          |*
*|  * Block Service -> S3/GCS (actual file blocks)                      |*
*|  * Sync Service -> WebSocket + Message Queue                         |*
*|                                                                         |*
*|  Key Numbers:                                                          |*
*|  * Block size: 4 MB                                                  |*
*|  * Metadata per file: ~500 bytes                                    |*
*|  * Dedup savings: 50-70%                                            |*
*|  * Durability: 99.999999999% (11 nines)                            |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

ADVANCED TOPICS & REAL-WORLD PROBLEMS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  RANSOMWARE PROTECTION                                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Problem: User's computer infected -> all files encrypted      |  |*
*|  |           -> Synced to cloud -> All versions destroyed          |  |*
*|  |                                                                 |  |*
*|  |  Solutions:                                                    |  |*
*|  |                                                                 |  |*
*|  |  1. DELAYED PERMANENT DELETION                                |  |*
*|  |     * "Deleted" files kept in trash for 30 days              |  |*
*|  |     * Overwritten versions kept for 30 days                  |  |*
*|  |     * Can restore even after ransomware encrypts             |  |*
*|  |                                                                 |  |*
*|  |  2. ANOMALY DETECTION                                         |  |*
*|  |     * Detect mass file modifications (1000+ files/minute)   |  |*
*|  |     * Detect file extension changes (.docx -> .encrypted)    |  |*
*|  |     * Detect entropy increase (encrypted = high entropy)    |  |*
*|  |     * Auto-pause sync, alert user                           |  |*
*|  |                                                                 |  |*
*|  |  3. IMMUTABLE SNAPSHOTS                                       |  |*
*|  |     * Daily snapshots that cannot be modified                |  |*
*|  |     * WORM storage (Write Once Read Many)                    |  |*
*|  |     * Even admin can't delete for retention period          |  |*
*|  |                                                                 |  |*
*|  |  4. VERSION PINNING                                           |  |*
*|  |     * Enterprise: Pin to specific version                    |  |*
*|  |     * Ransomware changes don't propagate automatically      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DATA RESIDENCY & COMPLIANCE (GDPR, HIPAA)                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  PROBLEM: EU users' data must stay in EU                      |  |*
*|  |                                                                 |  |*
*|  |  Data Model:                                                   |  |*
*|  |  TABLE: data_residency_policies                               |  |*
*|  |  +--------------+------------+-----------------------------+ |  |*
*|  |  | org_id       | region     | allowed_storage_regions     | |  |*
*|  |  | acme_corp    | EU         | [eu-west-1, eu-central-1]   | |  |*
*|  |  | us_bank      | US         | [us-east-1, us-west-2]      | |  |*
*|  |  +--------------+------------+-----------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  Implementation:                                               |  |*
*|  |  * Route uploads to region-specific S3 buckets               |  |*
*|  |  * Metadata DB per region (or global with region column)     |  |*
*|  |  * Block cross-region sharing for restricted files          |  |*
*|  |  * Audit logs for compliance reporting                       |  |*
*|  |                                                                 |  |*
*|  |  GDPR Right to be Forgotten:                                  |  |*
*|  |  * Hard delete all user data on request                      |  |*
*|  |  * Include backups, logs, analytics                         |  |*
*|  |  * Crypto-shredding: Encrypt data with user key, delete key |  |*
*|  |                                                                 |  |*
*|  |  HIPAA (Healthcare):                                          |  |*
*|  |  * PHI data encrypted at rest AND in transit                |  |*
*|  |  * Access audit logs retained 6 years                       |  |*
*|  |  * BAA (Business Associate Agreement) with cloud provider   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DELTA SYNC (Bandwidth Optimization)                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Problem: User changes 1 byte in 100 MB file                 |  |*
*|  |           Naive: Upload entire 100 MB again                  |  |*
*|  |           Smart: Upload only the changed part                |  |*
*|  |                                                                 |  |*
*|  |  RSYNC ALGORITHM (Dropbox uses variant):                      |  |*
*|  |                                                                 |  |*
*|  |  1. Split file into blocks (4 KB each)                       |  |*
*|  |  2. Calculate weak hash (rolling hash) for each block        |  |*
*|  |  3. Calculate strong hash (SHA256) for matching blocks       |  |*
*|  |  4. Client sends only:                                       |  |*
*|  |     * New/changed blocks (actual data)                       |  |*
*|  |     * References to unchanged blocks (just hash)            |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  Original:  [Block A][Block B][Block C][Block D]         ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Modified:  [Block A][Block B'][Block C][Block D]        ||  |*
*|  |  |                         ^                                 ||  |*
*|  |  |                    Only this changed                      ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Upload:    Reference to A, B' data, Reference to C, D   ||  |*
*|  |  |             (Upload ~4 KB instead of entire file)        ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  Savings: 90%+ bandwidth reduction for typical edits          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  MALWARE SCANNING                                                      |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Problem: User uploads malware -> shares with team -> infects  |  |*
*|  |                                                                 |  |*
*|  |  Solution:                                                     |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  Upload                                                   ||  |*
*|  |  |    |                                                      ||  |*
*|  |  |    v                                                      ||  |*
*|  |  |  Quarantine Zone (temp storage)                          ||  |*
*|  |  |    |                                                      ||  |*
*|  |  |    v                                                      ||  |*
*|  |  |  Malware Scanner (ClamAV, VirusTotal API)                ||  |*
*|  |  |    |                                                      ||  |*
*|  |  |    +-- Clean -> Move to permanent storage                 ||  |*
*|  |  |    |                                                      ||  |*
*|  |  |    +-- Infected -> Block, notify user, quarantine        ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  Performance: Async scanning for large files                  |  |*
*|  |  Mark file as "scanning" until complete                      |  |*
*|  |                                                                 |  |*
*|  |  For enterprise: Additional DLP (Data Loss Prevention)       |  |*
*|  |  * Scan for SSN, credit card numbers, passwords in files    |  |*
*|  |  * Block/alert on sensitive data sharing                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  LARGE FILE HANDLING (Multi-GB Files)                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Challenge: 10 GB video file upload                           |  |*
*|  |                                                                 |  |*
*|  |  Solutions:                                                    |  |*
*|  |                                                                 |  |*
*|  |  1. CHUNKED/RESUMABLE UPLOAD                                  |  |*
*|  |     * Split into 4 MB chunks                                  |  |*
*|  |     * Upload chunks in parallel (5-10 concurrent)            |  |*
*|  |     * Each chunk has its own presigned URL                   |  |*
*|  |     * Resume from last successful chunk on failure           |  |*
*|  |                                                                 |  |*
*|  |  2. S3 MULTIPART UPLOAD                                       |  |*
*|  |     * Initiate multipart upload -> get upload_id              |  |*
*|  |     * Upload parts (can be parallel, out of order)           |  |*
*|  |     * Complete multipart -> S3 assembles the file             |  |*
*|  |     * Abort if not completed in 24 hours                     |  |*
*|  |                                                                 |  |*
*|  |  3. STREAMING UPLOAD                                          |  |*
*|  |     * Don't buffer entire file in memory                     |  |*
*|  |     * Stream chunks directly to S3                           |  |*
*|  |     * Use chunked transfer encoding                          |  |*
*|  |                                                                 |  |*
*|  |  Progress Tracking:                                            |  |*
*|  |  * Client tracks uploaded chunks                             |  |*
*|  |  * Server endpoint: GET /upload/{id}/progress                |  |*
*|  |  * WebSocket for real-time progress updates                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  LINK SHARING ABUSE                                                    |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Problem: Shared link goes viral -> bandwidth costs explode   |  |*
*|  |           Or: Pirated content shared via your platform       |  |*
*|  |                                                                 |  |*
*|  |  Solutions:                                                    |  |*
*|  |                                                                 |  |*
*|  |  1. RATE LIMITING ON SHARED LINKS                            |  |*
*|  |     * Max downloads per hour (e.g., 100)                     |  |*
*|  |     * Captcha after threshold                                |  |*
*|  |     * Disable link if abuse detected                        |  |*
*|  |                                                                 |  |*
*|  |  2. EXPIRING LINKS                                            |  |*
*|  |     * Default expiration: 7 days                             |  |*
*|  |     * User can set custom expiration                        |  |*
*|  |     * Max downloads limit (e.g., 100 downloads then disable)|  |*
*|  |                                                                 |  |*
*|  |  3. PASSWORD PROTECTION                                       |  |*
*|  |     * Require password to access shared link                 |  |*
*|  |     * Prevents casual sharing abuse                          |  |*
*|  |                                                                 |  |*
*|  |  4. DMCA/COPYRIGHT HANDLING                                   |  |*
*|  |     * Content ID matching for video/audio                    |  |*
*|  |     * Takedown request workflow                              |  |*
*|  |     * Repeat infringer policy -> account termination         |  |*
*|  |                                                                 |  |*
*|  |  5. ANALYTICS & MONITORING                                    |  |*
*|  |     * Track downloads per link                               |  |*
*|  |     * Alert on unusual patterns                              |  |*
*|  |     * Geographic distribution of downloads                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  COLD STORAGE TIERING                                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Problem: 80% of files never accessed after 90 days          |  |*
*|  |           Storing everything in hot storage is expensive     |  |*
*|  |                                                                 |  |*
*|  |  Solution: Automatic tiering                                  |  |*
*|  |                                                                 |  |*
*|  |  +----------------+-----------------+--------------------+   |  |*
*|  |  | Tier           | When            | Cost               |   |  |*
*|  |  +----------------+-----------------+--------------------+   |  |*
*|  |  | Hot (S3 Std)   | < 30 days       | $$$                |   |  |*
*|  |  | Warm (S3 IA)   | 30-90 days      | $$                 |   |  |*
*|  |  | Cold (Glacier) | 90-365 days     | $                  |   |  |*
*|  |  | Archive        | > 365 days      | ¢                  |   |  |*
*|  |  +----------------+-----------------+--------------------+   |  |*
*|  |                                                                 |  |*
*|  |  Implementation:                                               |  |*
*|  |  * Track last_accessed_at per file                           |  |*
*|  |  * Nightly job moves files to appropriate tier               |  |*
*|  |  * On access: Restore from cold (may take minutes/hours)    |  |*
*|  |  * Show user "File is being restored, available in 1 hour"  |  |*
*|  |                                                                 |  |*
*|  |  S3 Intelligent Tiering: AWS auto-tiers based on access     |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  CROSS-REGION DISASTER RECOVERY                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  PRIMARY REGION (US-EAST)      SECONDARY (US-WEST)       ||  |*
*|  |  |                                                           ||  |*
*|  |  |  +--------------+              +--------------+          ||  |*
*|  |  |  |  Metadata DB | --async----> |  Replica DB  |          ||  |*
*|  |  |  |   (Master)   |   repl       |  (Standby)   |          ||  |*
*|  |  |  +--------------+              +--------------+          ||  |*
*|  |  |                                                           ||  |*
*|  |  |  +--------------+              +--------------+          ||  |*
*|  |  |  |  S3 Bucket   | --CRR------> |  S3 Bucket   |          ||  |*
*|  |  |  |   Primary    |  (Cross      |   Replica    |          ||  |*
*|  |  |  +--------------+   Region     +--------------+          ||  |*
*|  |  |                     Repl)                                 ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  RPO (Recovery Point Objective): 1 hour                       |  |*
*|  |  RTO (Recovery Time Objective): 4 hours                       |  |*
*|  |                                                                 |  |*
*|  |  Failover: DNS switch to secondary region                     |  |*
*|  |  Failback: Reverse replication, switch back                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  QUOTA MANAGEMENT & BILLING                                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Free tier: 5 GB                                              |  |*
*|  |  Plus: 100 GB ($9.99/month)                                  |  |*
*|  |  Business: 2 TB ($19.99/month)                               |  |*
*|  |                                                                 |  |*
*|  |  Implementation:                                               |  |*
*|  |                                                                 |  |*
*|  |  TABLE: user_quotas                                           |  |*
*|  |  +-------------+---------------+---------------------------+ |  |*
*|  |  | user_id     | quota_bytes   | used_bytes                | |  |*
*|  |  | 123         | 5368709120    | 4500000000                | |  |*
*|  |  +-------------+---------------+---------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  On upload:                                                    |  |*
*|  |  1. Check if used_bytes + new_file_size <= quota_bytes       |  |*
*|  |  2. If over -> reject with "Upgrade your plan"               |  |*
*|  |  3. Atomic increment: UPDATE user_quotas SET used_bytes +=   |  |*
*|  |                                                                 |  |*
*|  |  On delete:                                                    |  |*
*|  |  * Decrement used_bytes                                       |  |*
*|  |  * Account for deduplication (shared blocks)                 |  |*
*|  |                                                                 |  |*
*|  |  Edge case: Same block shared by 2 users                     |  |*
*|  |  * Each user "owns" the logical size                        |  |*
*|  |  * Physical storage is deduplicated                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

ARCHITECTURE DIAGRAM
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|                    +------------------------------+                    |*
*|                    |     CLIENTS                   |                    |*
*|                    |  (Web, Desktop, Mobile)      |                    |*
*|                    +--------------+---------------+                    |*
*|                                   |                                    |*
*|                                   v                                    |*
*|                    +------------------------------+                    |*
*|                    |       LOAD BALANCER          |                    |*
*|                    +--------------+---------------+                    |*
*|                                   |                                    |*
*|            +----------------------+----------------------+            |*
*|            |                      |                      |            |*
*|            v                      v                      v            |*
*|     +------------+        +------------+        +------------+       |*
*|     |  Metadata  |        |   Sync     |        |   Block    |       |*
*|     |  Service   |        |  Service   |        |  Service   |       |*
*|     +-----+------+        +-----+------+        +-----+------+       |*
*|           |                     |                     |               |*
*|           v                     v                     v               |*
*|     +------------+        +------------+        +------------+       |*
*|     | PostgreSQL |        |   Redis    |        |  S3 / GCS  |       |*
*|     |  (Master)  |        |  Pub/Sub   |        |            |       |*
*|     +-----+------+        +------------+        |   BLOCKS   |       |*
*|           |                                      |  (4 MB ea) |       |*
*|           v                                      +------------+       |*
*|     +------------+                                    |               |*
*|     |  Replicas  |                                    |               |*
*|     +------------+                                    v               |*
*|                                                 +------------+       |*
*|                                                 |    CDN     |       |*
*|                                                 | (Downloads)|       |*
*|                                                 +------------+       |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF FILE STORAGE SYSTEM DESIGN
