# REAL-TIME MESSAGING SYSTEM - HIGH LEVEL DESIGN

CHAPTER 2: HIGH-LEVEL ARCHITECTURE
SECTION 0: COMPLETE HIGH-LEVEL DESIGN DIAGRAM
## +----------------------------------------------------------------------------------+
*|                                                                                  |*
*|                    REAL-TIME MESSAGING SYSTEM - FULL HLD                        |*
*|                                                                                  |*
*+----------------------------------------------------------------------------------+*
*+---------------------+*
*|    CLIENTS          |*
*|  (Mobile/Web/Desktop)|*
*+----------+----------+*
*|*
*+----------------------------+----------------------------+*
*|                            |                            |*
*v                            v                            v*
*+---------------+           +---------------+           +---------------+*
*|   User A      |           |   User B      |           |   User C      |*
*|   (Sender)    |           |  (Recipient)  |           |  (Offline)    |*
*+-------+-------+           +---------------+           +---------------+*
*|*
*| WebSocket*
*|*
*+-----------v----------------------------------------------------------------------+*
*|                                                                                  |*
*|                         EDGE / GATEWAY LAYER                                     |*
*|                                                                                  |*
*|  +----------------------------------------------------------------------------+ |*
*|  |                                                                            | |*
*|  |                    GLOBAL LOAD BALANCER (DNS / GeoDNS)                    | |*
*|  |                                                                            | |*
*|  |    Routes users to nearest region based on latency                        | |*
*|  |                                                                            | |*
*|  +---------------------------------+------------------------------------------+ |*
*|                                    |                                            |*
*|            +-----------------------+-----------------------+                   |*
*|            |                       |                       |                   |*
*|            v                       v                       v                   |*
*|    +---------------+       +---------------+       +---------------+          |*
*|    |  Region: US   |       | Region: EU    |       | Region: Asia  |          |*
*|    +-------+-------+       +---------------+       +---------------+          |*
*|            |                                                                   |*
*|            v                                                                   |*
*|    +----------------------------------------------------------------+         |*
*|    |                                                                |         |*
*|    |              L4 LOAD BALANCER (TCP/WebSocket)                 |         |*
*|    |                                                                |         |*
*|    |   * Sticky sessions based on user_id                          |         |*
*|    |   * Health checks on chat servers                             |         |*
*|    |   * Connection draining on server shutdown                    |         |*
*|    |                                                                |         |*
*|    +--------------------------+-------------------------------------+         |*
*|                               |                                               |*
*+-------------------------------+-----------------------------------------------+*
*|*
*+-------------------------------v-----------------------------------------------+*
*|                                                                               |*
*|                      REAL-TIME CONNECTION LAYER                              |*
*|                                                                               |*
*|   +-------------+    +-------------+    +-------------+    +-------------+  |*
*|   | Chat Server |    | Chat Server |    | Chat Server |    | Chat Server |  |*
*|   |      1      |    |      2      |    |      3      |    |     ...N    |  |*
*|   |             |    |             |    |             |    |             |  |*
*|   | ~50K conns  |    | ~50K conns  |    | ~50K conns  |    | ~50K conns  |  |*
*|   +------+------+    +------+------+    +------+------+    +------+------+  |*
*|          |                  |                  |                  |          |*
*|          | RESPONSIBILITIES:                                                 |*
*|          | * Maintain WebSocket connections                                  |*
*|          | * Authenticate users (JWT)                                        |*
*|          | * Handle typing indicators                                        |*
*|          | * Local connection map                                            |*
*|          |                                                                   |*
*|          +------------------+------------------+-----------------------------+*
*|                             |                                                |*
*|                             | Publish/Subscribe                              |*
*|                             v                                                |*
*|   +----------------------------------------------------------------------+  |*
*|   |                                                                      |  |*
*|   |                    REDIS CLUSTER (Pub/Sub)                          |  |*
*|   |                                                                      |  |*
*|   |   * Connection Registry: user_id > chat_server_id                   |  |*
*|   |   * Presence State: user_id > {online/offline, last_seen}          |  |*
*|   |   * Server-to-Server message routing via channels                   |  |*
*|   |   * Typing indicator pub/sub                                        |  |*
*|   |                                                                      |  |*
*|   +----------------------------------------------------------------------+  |*
*|                                                                               |*
*+-------------------------------+-----------------------------------------------+*
*|*
*| Produce messages*
*v*
*+-------------------------------------------------------------------------------+*
*|                                                                               |*
*|                        MESSAGE QUEUE LAYER (Kafka)                           |*
*|                                                                               |*
*|   +------------------------------------------------------------------------+ |*
*|   |                                                                        | |*
*|   |                         KAFKA CLUSTER                                  | |*
*|   |                                                                        | |*
*|   |   +--------------------------------------------------------------+    | |*
*|   |   |                                                              |    | |*
*|   |   |   TOPICS:                                                    |    | |*
*|   |   |                                                              |    | |*
*|   |   |   messages.outbound         > Delivery to online users      |    | |*
*|   |   |   (partitioned by user_id)                                   |    | |*
*|   |   |                                                              |    | |*
*|   |   |   messages.store            > Persist to database           |    | |*
*|   |   |   (partitioned by conversation_id)                           |    | |*
*|   |   |                                                              |    | |*
*|   |   |   messages.notifications    > Push for offline users        |    | |*
*|   |   |   (partitioned by user_id)                                   |    | |*
*|   |   |                                                              |    | |*
*|   |   |   messages.retry.{delay}    > Delayed retries               |    | |*
*|   |   |                                                              |    | |*
*|   |   |   messages.dlq              > Dead letter queue             |    | |*
*|   |   |                                                              |    | |*
*|   |   +--------------------------------------------------------------+    | |*
*|   |                                                                        | |*
*|   +------------------------------------------------------------------------+ |*
*|                                                                               |*
*|           |                        |                        |                |*
*|           |                        |                        |                |*
*|           v                        v                        v                |*
*|   +---------------+        +---------------+        +---------------+       |*
*|   |   Delivery    |        |   Storage     |        |     Push      |       |*
*|   |   Workers     |        |   Workers     |        |   Workers     |       |*
*|   |               |        |               |        |               |       |*
*|   | Consumer Group|        | Consumer Group|        | Consumer Group|       |*
*|   +-------+-------+        +-------+-------+        +-------+-------+       |*
*|           |                        |                        |                |*
*+-----------+------------------------+------------------------+----------------+*
*|                        |                        |*
*v                        v                        v*
*+-------------------------------------------------------------------------------+*
*|                                                                               |*
*|                          BACKEND SERVICES LAYER                              |*
*|                                                                               |*
*|   +-------------------------------------------------------------------------+|*
*|   |                                                                         ||*
*|   |   +---------------+   +---------------+   +---------------+            ||*
*|   |   |   Message     |   |   User        |   |   Group       |            ||*
*|   |   |   Service     |   |   Service     |   |   Service     |            ||*
*|   |   |               |   |               |   |               |            ||*
*|   |   | * Send/receive|   | * Auth        |   | * Create group|            ||*
*|   |   | * History     |   | * Profile     |   | * Manage      |            ||*
*|   |   | * Search      |   | * Settings    |   |   members     |            ||*
*|   |   | * Sync        |   | * Contacts    |   | * Permissions |            ||*
*|   |   +---------------+   +---------------+   +---------------+            ||*
*|   |                                                                         ||*
*|   |   +---------------+   +---------------+   +---------------+            ||*
*|   |   |   Presence    |   |   Media       |   |   Key         |            ||*
*|   |   |   Service     |   |   Service     |   |   Service     |            ||*
*|   |   |               |   |               |   |   (E2EE)      |            ||*
*|   |   | * Online/     |   | * Upload      |   |               |            ||*
*|   |   |   offline     |   | * Download    |   | * Key exchange|            ||*
*|   |   | * Last seen   |   | * Thumbnails  |   | * Pre-keys    |            ||*
*|   |   | * Typing      |   | * Compression |   | * Session mgmt|            ||*
*|   |   +---------------+   +---------------+   +---------------+            ||*
*|   |                                                                         ||*
*|   +-------------------------------------------------------------------------+|*
*|                                                                               |*
*+---------------------------+---------------------------------------------------+*
*|*
*v*
*+-------------------------------------------------------------------------------+*
*|                                                                               |*
*|                           DATA STORAGE LAYER                                 |*
*|                                                                               |*
*|   +-------------------------------------------------------------------------+|*
*|   |                                                                         ||*
*|   |   +-----------------------+        +-----------------------+           ||*
*|   |   |                       |        |                       |           ||*
*|   |   |  MESSAGE STORAGE      |        |  USER/METADATA        |           ||*
*|   |   |  (Cassandra)          |        |  (PostgreSQL)         |           ||*
*|   |   |                       |        |                       |           ||*
*|   |   |  * Messages           |        |  * Users              |           ||*
*|   |   |  * Conversations      |        |  * Groups             |           ||*
*|   |   |  * Partitioned by     |        |  * Contacts           |           ||*
*|   |   |    conversation_id    |        |  * Settings           |           ||*
*|   |   |  * TTL for expiry     |        |  * Encryption keys    |           ||*
*|   |   |                       |        |                       |           ||*
*|   |   +-----------------------+        +-----------------------+           ||*
*|   |                                                                         ||*
*|   |   +-----------------------+        +-----------------------+           ||*
*|   |   |                       |        |                       |           ||*
*|   |   |  MEDIA STORAGE        |        |  CACHE                |           ||*
*|   |   |  (S3 / GCS)           |        |  (Redis Cluster)      |           ||*
*|   |   |                       |        |                       |           ||*
*|   |   |  * Images             |        |  * Recent messages    |           ||*
*|   |   |  * Videos             |        |  * User sessions      |           ||*
*|   |   |  * Voice messages     |        |  * Connection state   |           ||*
*|   |   |  * Documents          |        |  * Presence           |           ||*
*|   |   |  * Encrypted at rest  |        |  * Rate limiting      |           ||*
*|   |   |                       |        |                       |           ||*
*|   |   +-----------------------+        +-----------------------+           ||*
*|   |                                                                         ||*
*|   +-------------------------------------------------------------------------+|*
*|                                                                               |*
*+-------------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------------+*
*|                                                                               |*
*|                      EXTERNAL SERVICES / INTEGRATIONS                        |*
*|                                                                               |*
*|   +-------------------------------------------------------------------------+|*
*|   |                                                                         ||*
*|   |   +-----------------------+        +-----------------------+           ||*
*|   |   |                       |        |                       |           ||*
*|   |   |  PUSH NOTIFICATIONS   |        |  CDN                  |           ||*
*|   |   |                       |        |  (CloudFront/Akamai)  |           ||*
*|   |   |  * APNs (iOS)         |        |                       |           ||*
*|   |   |  * FCM (Android)      |        |  * Media delivery     |           ||*
*|   |   |  * Web Push           |        |  * Thumbnails         |           ||*
*|   |   |                       |        |  * Static assets      |           ||*
*|   |   |                       |        |                       |           ||*
*|   |   +-----------------------+        +-----------------------+           ||*
*|   |                                                                         ||*
*|   +-------------------------------------------------------------------------+|*
*|                                                                               |*
*+-------------------------------------------------------------------------------+*

DATA FLOW DIAGRAMS

## +------------------------------------------------------------------------------+
*|                                                                              |*
*|  FLOW 1: SEND MESSAGE (User A > User B, Both Online)                        |*
*|                                                                              |*
*|  +-------------------------------------------------------------------------+|*
*|  |                                                                         ||*
*|  |   User A                                                                ||*
*|  |     |                                                                   ||*
*|  |     | 1. WebSocket: Send message                                       ||*
*|  |     v                                                                   ||*
*|  |   Chat Server 1                                                         ||*
*|  |     |                                                                   ||*
*|  |     | 2. Authenticate, validate                                        ||*
*|  |     |                                                                   ||*
*|  |     | 3. Lookup User B's server in Redis                              ||*
*|  |     |    Result: Chat Server 3                                         ||*
*|  |     |                                                                   ||*
*|  |     | 4. Produce to Kafka (messages.outbound)                          ||*
*|  |     |                                                                   ||*
*|  |     | 5. Return ACK to User A (message sent)                          ||*
*|  |     v                                                                   ||*
*|  |   Kafka                                                                 ||*
*|  |     |                                                                   ||*
*|  |     | 6. Delivery Worker consumes                                      ||*
*|  |     v                                                                   ||*
*|  |   Delivery Worker                                                       ||*
*|  |     |                                                                   ||*
*|  |     | 7. Route to Chat Server 3 (via gRPC or Redis pub/sub)           ||*
*|  |     v                                                                   ||*
*|  |   Chat Server 3                                                         ||*
*|  |     |                                                                   ||*
*|  |     | 8. Find User B's WebSocket connection locally                   ||*
*|  |     |                                                                   ||*
*|  |     | 9. Push message via WebSocket                                   ||*
*|  |     v                                                                   ||*
*|  |   User B                                                                ||*
*|  |     |                                                                   ||*
*|  |     | 10. Receive message, display                                     ||*
*|  |     |                                                                   ||*
*|  |     | 11. Send delivery receipt back                                   ||*
*|  |     v                                                                   ||*
*|  |   User A receives "Delivered YY"                                       ||*
*|  |                                                                         ||*
*|  +-------------------------------------------------------------------------+|*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  FLOW 2: SEND MESSAGE (User B is OFFLINE)                                   |*
*|                                                                              |*
*|  +-------------------------------------------------------------------------+|*
*|  |                                                                         ||*
*|  |   User A                                                                ||*
*|  |     |                                                                   ||*
*|  |     | 1. Send message to User B                                        ||*
*|  |     v                                                                   ||*
*|  |   Chat Server                                                           ||*
*|  |     |                                                                   ||*
*|  |     | 2. Lookup User B in Redis > NOT FOUND (offline)                 ||*
*|  |     |                                                                   ||*
*|  |     | 3. Produce to Kafka (messages.store + messages.notifications)   ||*
*|  |     v                                                                   ||*
*|  |   Storage Worker                      Push Worker                       ||*
*|  |     |                                     |                             ||*
*|  |     | 4. Write to                         | 5. Send push               ||*
*|  |     |    Cassandra                        |    notification            ||*
*|  |     v                                     v                             ||*
*|  |   Cassandra                          APNs / FCM                         ||*
*|  |                                           |                             ||*
*|  |                                           | 6. Push arrives            ||*
*|  |                                           v                             ||*
*|  |                                       User B's Phone                    ||*
*|  |                                       (notification shown)              ||*
*|  |                                           |                             ||*
*|  |                                           | 7. User opens app          ||*
*|  |                                           v                             ||*
*|  |                                       Chat Server                       ||*
*|  |                                           |                             ||*
*|  |                                           | 8. Sync: Fetch unread     ||*
*|  |                                           |    messages from DB        ||*
*|  |                                           v                             ||*
*|  |                                       User B sees message              ||*
*|  |                                                                         ||*
*|  +-------------------------------------------------------------------------+|*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  FLOW 3: GROUP MESSAGE (1 Sender > 500 Members)                             |*
*|                                                                              |*
*|  +-------------------------------------------------------------------------+|*
*|  |                                                                         ||*
*|  |   User A sends message to Group "Family"                               ||*
*|  |     |                                                                   ||*
*|  |     | 1. WebSocket message with group_id                               ||*
*|  |     v                                                                   ||*
*|  |   Chat Server                                                           ||*
*|  |     |                                                                   ||*
*|  |     | 2. Produce to Kafka (topic: groups.messages, key: group_id)     ||*
*|  |     v                                                                   ||*
*|  |   Kafka (groups.messages)                                               ||*
*|  |     |                                                                   ||*
*|  |     | 3. Group Fanout Service consumes                                 ||*
*|  |     v                                                                   ||*
*|  |   Group Fanout Service                                                  ||*
*|  |     |                                                                   ||*
*|  |     | 4. Fetch group members from cache/DB                             ||*
*|  |     |    Result: [user_1, user_2, ..., user_500]                       ||*
*|  |     |                                                                   ||*
*|  |     | 5. For each member:                                              ||*
*|  |     |    * Check if online (Redis lookup)                              ||*
*|  |     |    * If online: Produce to messages.outbound                     ||*
*|  |     |    * If offline: Produce to messages.notifications              ||*
*|  |     |                                                                   ||*
*|  |     | 6. Batch produce for efficiency                                  ||*
*|  |     v                                                                   ||*
*|  |   Kafka (messages.outbound)          Kafka (messages.notifications)    ||*
*|  |     |                                     |                             ||*
*|  |     |                                     |                             ||*
*|  |     v                                     v                             ||*
*|  |   Delivery Workers                    Push Workers                      ||*
*|  |     |                                     |                             ||*
*|  |     | 7. Route to                        | 8. Send push               ||*
*|  |     |    chat servers                     |    notifications           ||*
*|  |     v                                     v                             ||*
*|  |   Online members receive             Offline members get               ||*
*|  |   via WebSocket                       push notification                ||*
*|  |                                                                         ||*
*|  +-------------------------------------------------------------------------+|*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  FLOW 4: MEDIA MESSAGE (Image/Video/Document)                               |*
*|                                                                              |*
*|  +-------------------------------------------------------------------------+|*
*|  |                                                                         ||*
*|  |   User A wants to send image to User B                                 ||*
*|  |     |                                                                   ||*
*|  |     | 1. Request upload URL from Media Service                         ||*
*|  |     v                                                                   ||*
*|  |   Media Service                                                         ||*
*|  |     |                                                                   ||*
*|  |     | 2. Generate presigned S3 upload URL                              ||*
*|  |     |    (with encryption params)                                       ||*
*|  |     |                                                                   ||*
*|  |     | 3. Return URL to client                                          ||*
*|  |     v                                                                   ||*
*|  |   User A (Client)                                                       ||*
*|  |     |                                                                   ||*
*|  |     | 4. Encrypt media locally (E2EE key)                             ||*
*|  |     |                                                                   ||*
*|  |     | 5. Upload directly to S3 via presigned URL                      ||*
*|  |     v                                                                   ||*
*|  |   S3                                                                    ||*
*|  |     |                                                                   ||*
*|  |     | 6. Store encrypted blob                                          ||*
*|  |     |    Return media_id                                                ||*
*|  |     v                                                                   ||*
*|  |   User A                                                                ||*
*|  |     |                                                                   ||*
*|  |     | 7. Send message with media_id via WebSocket                      ||*
*|  |     |    { type: "image", media_id: "abc123", enc_key: "..." }        ||*
*|  |     v                                                                   ||*
*|  |   (Normal message flow to User B)                                       ||*
*|  |     |                                                                   ||*
*|  |     v                                                                   ||*
*|  |   User B receives message                                               ||*
*|  |     |                                                                   ||*
*|  |     | 8. Request download URL with media_id                            ||*
*|  |     |                                                                   ||*
*|  |     | 9. Download encrypted blob from S3/CDN                           ||*
*|  |     |                                                                   ||*
*|  |     | 10. Decrypt locally using enc_key                                ||*
*|  |     |                                                                   ||*
*|  |     | 11. Display image                                                 ||*
*|  |                                                                         ||*
*|  +-------------------------------------------------------------------------+|*
*|                                                                              |*
*+------------------------------------------------------------------------------+*

COMPONENT INTERACTION MATRIX

## +------------------------------------------------------------------------------+
*|                                                                              |*
*|  COMPONENT              TALKS TO                    PROTOCOL / PURPOSE       |*
*|  -------------------------------------------------------------------------  |*
*|                                                                              |*
*|  Client                 > Chat Server               WebSocket (bidirectional)|*
*|  Client                 > Media Service             HTTPS (upload/download)  |*
*|  Client                 > CDN                       HTTPS (media delivery)   |*
*|                                                                              |*
*|  Chat Server            > Redis                     TCP (connection registry)|*
*|  Chat Server            > Kafka                     TCP (produce messages)   |*
*|  Chat Server            > Other Chat Servers        gRPC (route messages)    |*
*|  Chat Server            > User Service              gRPC (auth, profiles)    |*
*|                                                                              |*
*|  Delivery Workers       > Kafka                     TCP (consume messages)   |*
*|  Delivery Workers       > Redis                     TCP (lookup connections) |*
*|  Delivery Workers       > Chat Servers              gRPC (deliver messages)  |*
*|                                                                              |*
*|  Storage Workers        > Kafka                     TCP (consume messages)   |*
*|  Storage Workers        > Cassandra                 CQL (write messages)     |*
*|                                                                              |*
*|  Push Workers           > Kafka                     TCP (consume messages)   |*
*|  Push Workers           > APNs/FCM                  HTTPS (send push)        |*
*|                                                                              |*
*|  Media Service          > S3/GCS                    HTTPS (presigned URLs)   |*
*|  Media Service          > PostgreSQL                SQL (metadata)           |*
*|                                                                              |*
*|  Presence Service       > Redis                     TCP (presence state)     |*
*|  Presence Service       > Kafka                     TCP (presence events)    |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*

SCALING NUMBERS

## +------------------------------------------------------------------------------+
*|                                                                              |*
*|  COMPONENT              INSTANCE COUNT         CAPACITY                      |*
*|  -------------------------------------------------------------------------  |*
*|                                                                              |*
*|  Chat Servers           200 servers            50K connections each         |*
*|                                                = 10M concurrent users        |*
*|                                                                              |*
*|  Kafka Cluster          30 brokers             500K messages/sec            |*
*|                         100 partitions/topic    replication factor = 3       |*
*|                                                                              |*
*|  Cassandra Cluster      50 nodes               1 PB storage                 |*
*|                         RF = 3                  100K writes/sec              |*
*|                                                                              |*
*|  Redis Cluster          20 nodes               500GB memory                 |*
*|                         Sharded                 100M connection entries      |*
*|                                                                              |*
*|  PostgreSQL             3 nodes                Read replicas                |*
*|                         Primary + replicas      50K queries/sec              |*
*|                                                                              |*
*|  CDN                    Edge locations         Media delivery               |*
*|                         Global                  99.9% cache hit rate         |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*

SECTION 1: ARCHITECTURE OVERVIEW (Simplified)
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SYSTEM COMPONENTS (Summary)                                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  +-------------+                                               |  |*
*|  |  |   Client    |  (Mobile App, Web, Desktop)                  |  |*
*|  |  +------+------+                                               |  |*
*|  |         |                                                       |  |*
*|  |         | WebSocket / HTTP                                     |  |*
*|  |         v                                                       |  |*
*|  |  +----------------------------------------------------------+ |  |*
*|  |  |              LOAD BALANCER (Layer 4)                     | |  |*
*|  |  |         (Sticky sessions by user_id)                     | |  |*
*|  |  +--------------------------+-------------------------------+ |  |*
*|  |                             |                                  |  |*
*|  |         +-------------------+-------------------+             |  |*
*|  |         |                   |                   |             |  |*
*|  |         v                   v                   v             |  |*
*|  |  +------------+     +------------+     +------------+        |  |*
*|  |  |    Chat    |     |    Chat    |     |    Chat    |        |  |*
*|  |  |  Server 1  |     |  Server 2  |     |  Server N  |        |  |*
*|  |  +-----+------+     +-----+------+     +-----+------+        |  |*
*|  |        |                  |                  |                |  |*
*|  |        +------------------+------------------+                |  |*
*|  |                           |                                   |  |*
*|  |                           v                                   |  |*
*|  |  +----------------------------------------------------------+|  |*
*|  |  |                    MESSAGE QUEUE                         ||  |*
*|  |  |                      (Kafka)                             ||  |*
*|  |  +--------------------------+-------------------------------+|  |*
*|  |                             |                                 |  |*
*|  |         +-------------------+-------------------+            |  |*
*|  |         |                   |                   |            |  |*
*|  |         v                   v                   v            |  |*
*|  |  +------------+     +------------+     +------------+       |  |*
*|  |  |  Message   |     |  Presence  |     |   Push     |       |  |*
*|  |  |  Storage   |     |  Service   |     |  Service   |       |  |*
*|  |  +------------+     +------------+     +------------+       |  |*
*|  |                                                               |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2: CORE COMPONENTS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  1. CHAT SERVERS (WebSocket Gateway)                                   |*
*|  ------------------------------------                                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  RESPONSIBILITIES:                                              |  |*
*|  |                                                                 |  |*
*|  |  * Maintain WebSocket connections with clients                 |  |*
*|  |  * Authenticate users                                          |  |*
*|  |  * Route messages to recipients                                |  |*
*|  |  * Send/receive real-time events                               |  |*
*|  |  * Handle typing indicators, presence                          |  |*
*|  |                                                                 |  |*
*|  |  CAPACITY PER SERVER:                                          |  |*
*|  |  * 50,000 - 100,000 concurrent connections                    |  |*
*|  |  * Memory: ~100 bytes per connection = 10 GB for 100K         |  |*
*|  |  * CPU: Message parsing, encryption                           |  |*
*|  |                                                                 |  |*
*|  |  CONNECTION MAPPING:                                           |  |*
*|  |  * In-memory map: user_id > WebSocket connection              |  |*
*|  |  * Shared across cluster: Redis hash                          |  |*
*|  |    user_id > chat_server_id                                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  2. MESSAGE QUEUE (Kafka)                                             |*
*|  -------------------------                                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  WHY KAFKA:                                                    |  |*
*|  |  * Decouples message sending from processing                  |  |*
*|  |  * Handles burst traffic (queue during spike)                |  |*
*|  |  * Durability (messages persisted to disk)                   |  |*
*|  |  * Replay capability for recovery                            |  |*
*|  |                                                                 |  |*
*|  |  TOPICS:                                                       |  |*
*|  |                                                                 |  |*
*|  |  messages.outbound                                            |  |*
*|  |  * Messages to be delivered to recipients                    |  |*
*|  |  * Partitioned by recipient_user_id                          |  |*
*|  |  * Ensures ordering per user                                 |  |*
*|  |                                                                 |  |*
*|  |  messages.store                                               |  |*
*|  |  * Messages to be persisted                                  |  |*
*|  |  * Partitioned by conversation_id                            |  |*
*|  |                                                                 |  |*
*|  |  events.presence                                              |  |*
*|  |  * Online/offline events                                     |  |*
*|  |  * Typing indicators                                         |  |*
*|  |                                                                 |  |*
*|  |  events.notifications                                         |  |*
*|  |  * Push notification requests                                |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  3. MESSAGE STORAGE                                                    |*
*|  ---------------------                                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  PRIMARY: Cassandra (or ScyllaDB)                             |  |*
*|  |                                                                 |  |*
*|  |  Why Cassandra:                                                |  |*
*|  |  * Write-optimized (append-only LSM tree)                    |  |*
*|  |  * Linear scalability (add nodes for capacity)               |  |*
*|  |  * High availability (no single point of failure)            |  |*
*|  |  * Tunable consistency                                       |  |*
*|  |  * Time-based partitioning (TTL for old messages)           |  |*
*|  |                                                                 |  |*
*|  |  TABLE: messages                                              |  |*
*|  |  +----------------+-------------+--------------------------+ |  |*
*|  |  | conversation_id| PARTITION   | Groups messages together | |  |*
*|  |  | message_id     | CLUSTERING  | Sorted by time (TIMEUUID)| |  |*
*|  |  | sender_id      |             | Who sent it              | |  |*
*|  |  | content        |             | Encrypted message body   | |  |*
*|  |  | type           |             | TEXT, IMAGE, VIDEO       | |  |*
*|  |  | created_at     |             | Timestamp                | |  |*
*|  |  | status         |             | SENT, DELIVERED, READ    | |  |*
*|  |  +----------------+-------------+--------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  PRIMARY KEY: (conversation_id, message_id)                   |  |*
*|  |  * Query: All messages in conversation, ordered by time      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  4. USER SERVICE                                                       |*
*|  ----------------                                                      |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  * User registration (phone number verification)              |  |*
*|  |  * Profile management                                         |  |*
*|  |  * Contact sync (find friends by phone number)               |  |*
*|  |  * Block/unblock users                                        |  |*
*|  |                                                                 |  |*
*|  |  Storage: PostgreSQL + Redis cache                           |  |*
*|  |                                                                 |  |*
*|  |  TABLE: users                                                 |  |*
*|  |  +----------------+-------------+--------------------------+ |  |*
*|  |  | user_id        | BIGINT PK   | Unique identifier        | |  |*
*|  |  | phone_number   | VARCHAR     | E.164 format             | |  |*
*|  |  | display_name   | VARCHAR     | User's name              | |  |*
*|  |  | profile_pic_url| VARCHAR     | Avatar                   | |  |*
*|  |  | status_text    | VARCHAR     | "Hey there! I'm using..."| |  |*
*|  |  | created_at     | TIMESTAMP   |                          | |  |*
*|  |  | last_seen_at   | TIMESTAMP   |                          | |  |*
*|  |  +----------------+-------------+--------------------------+ |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  5. PRESENCE SERVICE                                                   |*
*|  --------------------                                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Tracks user online/offline status and last seen             |  |*
*|  |                                                                 |  |*
*|  |  Storage: Redis (in-memory for speed)                        |  |*
*|  |                                                                 |  |*
*|  |  KEY: presence:{user_id}                                     |  |*
*|  |  VALUE: { "status": "online", "server_id": "chat-5" }        |  |*
*|  |  TTL: 60 seconds (heartbeat refresh)                         |  |*
*|  |                                                                 |  |*
*|  |  On connect: SET presence:{user_id} with TTL                 |  |*
*|  |  Heartbeat: EXPIRE (refresh TTL every 30 seconds)            |  |*
*|  |  On disconnect: DEL presence:{user_id}                       |  |*
*|  |  TTL expires: User considered offline                        |  |*
*|  |                                                                 |  |*
*|  |  Last seen:                                                   |  |*
*|  |  * Update on disconnect                                       |  |*
*|  |  * Store in PostgreSQL (persistent)                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  6. MEDIA SERVICE                                                      |*
*|  -----------------                                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  RESPONSIBILITIES:                                              |  |*
*|  |  * Upload media (images, videos, audio, documents)            |  |*
*|  |  * Generate thumbnails                                         |  |*
*|  |  * Compress/transcode media                                   |  |*
*|  |  * Serve media via CDN                                        |  |*
*|  |                                                                 |  |*
*|  |  UPLOAD FLOW:                                                  |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  Client                                                   ||  |*
*|  |  |    | 1. Request upload URL                               ||  |*
*|  |  |    v                                                      ||  |*
*|  |  |  Media Service                                            ||  |*
*|  |  |    | 2. Generate presigned S3 URL                        ||  |*
*|  |  |    | 3. Return URL + media_id                            ||  |*
*|  |  |    v                                                      ||  |*
*|  |  |  Client                                                   ||  |*
*|  |  |    | 4. Upload directly to S3                            ||  |*
*|  |  |    v                                                      ||  |*
*|  |  |  S3 > Lambda/Worker                                       ||  |*
*|  |  |    | 5. Generate thumbnail, transcode                    ||  |*
*|  |  |    | 6. Store metadata, update media record              ||  |*
*|  |  |    v                                                      ||  |*
*|  |  |  Client sends message with media_id                      ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  Storage:                                                      |  |*
*|  |  * S3 for actual media files                                 |  |*
*|  |  * CDN (CloudFront) for delivery                             |  |*
*|  |  * PostgreSQL for media metadata                             |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  7. PUSH NOTIFICATION SERVICE                                         |*
*|  -----------------------------                                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  For offline users:                                            |  |*
*|  |                                                                 |  |*
*|  |  * APNs for iOS                                               |  |*
*|  |  * FCM for Android                                            |  |*
*|  |  * Web Push for browsers                                      |  |*
*|  |                                                                 |  |*
*|  |  When to push:                                                 |  |*
*|  |  * User offline (no WebSocket connection)                    |  |*
*|  |  * App in background (mobile)                                |  |*
*|  |  * Conversation not muted                                    |  |*
*|  |                                                                 |  |*
*|  |  Privacy consideration (E2E encrypted):                       |  |*
*|  |  * Push only contains: "New message from {sender}"           |  |*
*|  |  * Actual content decrypted when app opens                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  8. GROUP SERVICE                                                      |*
*|  -----------------                                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Manages group conversations:                                 |  |*
*|  |                                                                 |  |*
*|  |  TABLE: groups                                                |  |*
*|  |  +----------------+-------------+--------------------------+ |  |*
*|  |  | group_id       | UUID PK     | Unique identifier        | |  |*
*|  |  | name           | VARCHAR     | Group name               | |  |*
*|  |  | icon_url       | VARCHAR     | Group icon               | |  |*
*|  |  | created_by     | BIGINT      | Creator user_id          | |  |*
*|  |  | created_at     | TIMESTAMP   |                          | |  |*
*|  |  +----------------+-------------+--------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  TABLE: group_members                                         |  |*
*|  |  +----------------+-------------+--------------------------+ |  |*
*|  |  | group_id       | UUID PK     |                          | |  |*
*|  |  | user_id        | BIGINT PK   |                          | |  |*
*|  |  | role           | ENUM        | ADMIN, MEMBER            | |  |*
*|  |  | joined_at      | TIMESTAMP   |                          | |  |*
*|  |  +----------------+-------------+--------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  Operations:                                                   |  |*
*|  |  * Create group                                               |  |*
*|  |  * Add/remove members (admin only)                           |  |*
*|  |  * Leave group                                                |  |*
*|  |  * Update group info                                         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3: CONNECTION APPROACHES - DEEP DIVE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  HOW DO TWO MOBILES CONNECT TO EACH OTHER?                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Key Insight: Mobiles DON'T connect directly to each other    |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  Mobile A ------> SERVER ------> Mobile B                ||  |*
*|  |  |           (persistent connection)                         ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  WHY NOT PEER-TO-PEER (P2P)?                                  |  |*
*|  |  * NAT traversal issues (most mobiles behind NAT)            |  |*
*|  |  * IP addresses change (mobile networks)                     |  |*
*|  |  * Offline delivery impossible                               |  |*
*|  |  * No message persistence                                    |  |*
*|  |                                                                 |  |*
*|  |  EXCEPTION: Voice/Video calls use WebRTC (P2P when possible) |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3.1: CONNECTION PROTOCOLS COMPARISON
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  1. REGULAR HTTP POLLING                                               |*
*|  ------------------------                                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  HOW IT WORKS:                                                 |  |*
*|  |                                                                 |  |*
*|  |  Client                              Server                    |  |*
*|  |    |                                   |                       |  |*
*|  |    |--- GET /messages?since=X -------->|                       |  |*
*|  |    |<-- Response (empty or messages) --|                       |  |*
*|  |    |                                   |                       |  |*
*|  |    |   (wait 2 seconds)               |                       |  |*
*|  |    |                                   |                       |  |*
*|  |    |--- GET /messages?since=X -------->|                       |  |*
*|  |    |<-- Response ----------------------|                       |  |*
*|  |    |                                   |                       |  |*
*|  |    |   (repeat every 2 seconds)       |                       |  |*
*|  |                                                                 |  |*
*|  |  PROS:                                                         |  |*
*|  |  Y Simple to implement                                        |  |*
*|  |  Y Works through all firewalls/proxies                       |  |*
*|  |  Y Stateless server                                          |  |*
*|  |                                                                 |  |*
*|  |  CONS:                                                         |  |*
*|  |  X High latency (up to polling interval)                     |  |*
*|  |  X Wastes bandwidth (mostly empty responses)                 |  |*
*|  |  X High server load (constant requests)                      |  |*
*|  |  X Battery drain on mobile                                   |  |*
*|  |                                                                 |  |*
*|  |  USE CASE: Legacy systems, very simple apps                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  2. LONG POLLING (Hanging GET)                                        |*
*|  ------------------------------                                        |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  HOW IT WORKS:                                                 |  |*
*|  |                                                                 |  |*
*|  |  Client                              Server                    |  |*
*|  |    |                                   |                       |  |*
*|  |    |--- GET /messages ---------------->|                       |  |*
*|  |    |                                   | (holds connection    |  |*
*|  |    |      (waiting...)                |  until new message   |  |*
*|  |    |                                   |  or timeout 30s)    |  |*
*|  |    |                                   |                       |  |*
*|  |    |   ~~~~~~~~~~~~~ 15 seconds pass ~~~~~~~~~~~~~            |  |*
*|  |    |                                   |                       |  |*
*|  |    |                    New message arrives!                  |  |*
*|  |    |                                   |                       |  |*
*|  |    |<-- Response (new message) --------|                       |  |*
*|  |    |                                   |                       |  |*
*|  |    |--- GET /messages ---------------->|  (immediately       |  |*
*|  |    |                                   |   reconnect)        |  |*
*|  |                                                                 |  |*
*|  |  PROS:                                                         |  |*
*|  |  Y Near real-time delivery                                   |  |*
*|  |  Y Works through most firewalls                              |  |*
*|  |  Y No special server requirements                            |  |*
*|  |  Y Good fallback for WebSocket                               |  |*
*|  |                                                                 |  |*
*|  |  CONS:                                                         |  |*
*|  |  X Server holds many open connections                        |  |*
*|  |  X Still half-duplex (one direction at a time)              |  |*
*|  |  X Timeout reconnection overhead                             |  |*
*|  |  X Each message = new HTTP request                          |  |*
*|  |                                                                 |  |*
*|  |  USE CASE: Fallback when WebSocket fails                     |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  3. SERVER-SENT EVENTS (SSE)                                          |*
*|  ----------------------------                                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  HOW IT WORKS:                                                 |  |*
*|  |                                                                 |  |*
*|  |  Client                              Server                    |  |*
*|  |    |                                   |                       |  |*
*|  |    |--- GET /events (Accept: text/event-stream) -->           |  |*
*|  |    |                                   |                       |  |*
*|  |    |<-- HTTP 200 (keep-alive) ---------|                       |  |*
*|  |    |                                   |                       |  |*
*|  |    |<-- data: {"msg": "hello"}\n\n ----|  (push)              |  |*
*|  |    |                                   |                       |  |*
*|  |    |<-- data: {"msg": "world"}\n\n ----|  (push)              |  |*
*|  |    |                                   |                       |  |*
*|  |    |   (connection stays open indefinitely)                   |  |*
*|  |                                                                 |  |*
*|  |  PROS:                                                         |  |*
*|  |  Y Built-in browser support (EventSource API)               |  |*
*|  |  Y Auto-reconnection                                         |  |*
*|  |  Y Simple text-based protocol                                |  |*
*|  |  Y Works through HTTP/1.1 proxies                           |  |*
*|  |                                                                 |  |*
*|  |  CONS:                                                         |  |*
*|  |  X ONE-WAY only (server > client)                           |  |*
*|  |  X Client sends via separate HTTP POST                      |  |*
*|  |  X Limited to UTF-8 text                                    |  |*
*|  |  X Max 6 connections per domain in browser                  |  |*
*|  |                                                                 |  |*
*|  |  USE CASE: Notifications, live feeds, stock tickers         |  |*
*|  |  NOT IDEAL FOR: Chat (need bidirectional)                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  4. WEBSOCKET ⭐ (Recommended for Chat)                               |*
*|  ------------------------------------                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  HOW IT WORKS:                                                 |  |*
*|  |                                                                 |  |*
*|  |  Client                              Server                    |  |*
*|  |    |                                   |                       |  |*
*|  |    |--- HTTP Upgrade: websocket ------>|  (handshake)         |  |*
*|  |    |<-- 101 Switching Protocols -------|                       |  |*
*|  |    |                                   |                       |  |*
*|  |    |   ======= Persistent TCP Connection =======             |  |*
*|  |    |                                   |                       |  |*
*|  |    |<-------- Server pushes message ---|                       |  |*
*|  |    |                                   |                       |  |*
*|  |    |--------> Client sends message ---->                       |  |*
*|  |    |                                   |                       |  |*
*|  |    |<-------- Server pushes another ---|                       |  |*
*|  |    |                                   |                       |  |*
*|  |    |   (full duplex - both directions simultaneously)        |  |*
*|  |                                                                 |  |*
*|  |  HANDSHAKE:                                                    |  |*
*|  |                                                                 |  |*
*|  |  Request:                                                      |  |*
*|  |  GET /chat HTTP/1.1                                           |  |*
*|  |  Upgrade: websocket                                           |  |*
*|  |  Connection: Upgrade                                          |  |*
*|  |  Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==                 |  |*
*|  |  Sec-WebSocket-Version: 13                                   |  |*
*|  |                                                                 |  |*
*|  |  Response:                                                     |  |*
*|  |  HTTP/1.1 101 Switching Protocols                            |  |*
*|  |  Upgrade: websocket                                           |  |*
*|  |  Connection: Upgrade                                          |  |*
*|  |  Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=         |  |*
*|  |                                                                 |  |*
*|  |  PROS:                                                         |  |*
*|  |  Y TRUE BIDIRECTIONAL (full duplex)                          |  |*
*|  |  Y Low latency (no HTTP overhead per message)                |  |*
*|  |  Y Efficient (small frame overhead: 2-14 bytes)             |  |*
*|  |  Y Binary and text support                                   |  |*
*|  |                                                                 |  |*
*|  |  CONS:                                                         |  |*
*|  |  X Blocked by some firewalls/proxies                        |  |*
*|  |  X Stateful (harder to scale)                               |  |*
*|  |  X Need fallback for older browsers                         |  |*
*|  |  X Connection management complexity                         |  |*
*|  |                                                                 |  |*
*|  |  USE CASE: Chat apps, gaming, real-time collaboration       |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  5. MQTT (Message Queuing Telemetry Transport)                        |*
*|  -----------------------------------------------                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  HOW IT WORKS:                                                 |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  Client A                      Client B                   ||  |*
*|  |  |     |                             |                       ||  |*
*|  |  |     | PUBLISH                     | SUBSCRIBE             ||  |*
*|  |  |     | topic: "chat/room1"         | topic: "chat/room1"   ||  |*
*|  |  |     | message: "Hello"            |                       ||  |*
*|  |  |     |                             |                       ||  |*
*|  |  |     v                             v                       ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |  |                   MQTT BROKER                       | ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  |  Routes messages from publishers to subscribers    | ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  QoS LEVELS:                                                   |  |*
*|  |  * QoS 0: At most once (fire and forget)                     |  |*
*|  |  * QoS 1: At least once (acknowledged delivery)              |  |*
*|  |  * QoS 2: Exactly once (4-way handshake)                     |  |*
*|  |                                                                 |  |*
*|  |  PROS:                                                         |  |*
*|  |  Y Very lightweight (2-byte header minimum)                  |  |*
*|  |  Y Battery efficient (designed for IoT)                      |  |*
*|  |  Y Built-in QoS levels                                       |  |*
*|  |  Y Retained messages, Last Will                              |  |*
*|  |  Y Topic-based pub/sub                                       |  |*
*|  |                                                                 |  |*
*|  |  CONS:                                                         |  |*
*|  |  X Requires separate broker (Mosquitto, HiveMQ)             |  |*
*|  |  X Not natively supported in browsers                       |  |*
*|  |  X Less common for web apps                                  |  |*
*|  |                                                                 |  |*
*|  |  USE CASE: IoT, mobile apps with battery constraints        |  |*
*|  |  Facebook Messenger uses MQTT for mobile!                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  6. PUB/SUB PATTERN (Redis, Kafka)                                    |*
*|  -----------------------------------                                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  HOW IT WORKS (SERVER-SIDE):                                   |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |     Chat Server 1              Chat Server 2              ||  |*
*|  |  |     (has User A)               (has User B)               ||  |*
*|  |  |          |                          |                     ||  |*
*|  |  |          | PUBLISH                  | SUBSCRIBE           ||  |*
*|  |  |          | channel: user_B          | channel: user_B     ||  |*
*|  |  |          |                          |                     ||  |*
*|  |  |          v                          v                     ||  |*
*|  |  |     +-------------------------------------------------+  ||  |*
*|  |  |     |              REDIS PUB/SUB                      |  ||  |*
*|  |  |     |                                                 |  ||  |*
*|  |  |     |  * Fan-out to all subscribers                  |  ||  |*
*|  |  |     |  * No persistence (fire and forget)            |  ||  |*
*|  |  |     |                                                 |  ||  |*
*|  |  |     +-------------------------------------------------+  ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  This is for SERVER-TO-SERVER communication, not client!     |  |*
*|  |                                                                 |  |*
*|  |  PROS:                                                         |  |*
*|  |  Y Decouples chat servers                                    |  |*
*|  |  Y Horizontal scaling                                        |  |*
*|  |  Y Low latency message routing                              |  |*
*|  |                                                                 |  |*
*|  |  CONS:                                                         |  |*
*|  |  X Messages lost if no subscriber (Redis)                   |  |*
*|  |  X Additional infrastructure                                |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3.2: COMPARISON TABLE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  +------------+-----------+-----------+------------+----------------+  |*
*|  | Protocol   | Direction | Latency   | Complexity | Best For       |  |*
*|  +------------+-----------+-----------+------------+----------------+  |*
*|  | Polling    | Pull      | High      | Low        | Legacy apps    |  |*
*|  |            |           | (seconds) |            |                |  |*
*|  +------------+-----------+-----------+------------+----------------+  |*
*|  | Long Poll  | Pull+Push | Medium    | Low        | WS fallback    |  |*
*|  |            |           | (100ms)   |            |                |  |*
*|  +------------+-----------+-----------+------------+----------------+  |*
*|  | SSE        | Push only | Low       | Low        | Notifications  |  |*
*|  |            |           | (50ms)    |            | Feeds          |  |*
*|  +------------+-----------+-----------+------------+----------------+  |*
*|  | WebSocket  | Full      | Very Low  | Medium     | Chat, Gaming   |  |*
*|  |            | Duplex    | (10-50ms) |            | Real-time      |  |*
*|  +------------+-----------+-----------+------------+----------------+  |*
*|  | MQTT       | Pub/Sub   | Very Low  | Medium     | IoT, Mobile    |  |*
*|  |            |           | (10ms)    |            | Low battery    |  |*
*|  +------------+-----------+-----------+------------+----------------+  |*
*|                                                                         |*
*|  RECOMMENDATION FOR CHAT APP:                                          |*
*|  * Primary: WebSocket                                                  |*
*|  * Fallback: Long Polling (for restrictive networks)                  |*
*|  * Mobile optimization: Consider MQTT                                  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3.3: WEBSOCKET BROADCAST (Group Messages)
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  HOW WEBSOCKET BROADCAST WORKS                                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  SCENARIO: 100-member group, message from User A                |  |*
*|  |                                                                 |  |*
*|  |  CHALLENGE: Users are on DIFFERENT chat servers                |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  User A --> Chat Server 1                                ||  |*
*|  |  |             (30 users online)                            ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Chat Server 2                                           ||  |*
*|  |  |  (25 users online)                                       ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Chat Server 3                                           ||  |*
*|  |  |  (20 users online)                                       ||  |*
*|  |  |                                                           ||  |*
*|  |  |  25 users offline (push notifications)                   ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  APPROACH 1: DIRECT BROADCAST (Small Scale)                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. User A sends message to Chat Server 1                     |  |*
*|  |  2. Chat Server 1 gets group member list                      |  |*
*|  |  3. For each member:                                          |  |*
*|  |     a. Lookup which server has their connection (Redis)      |  |*
*|  |     b. Send message directly to that server                  |  |*
*|  |     c. That server pushes to user's WebSocket                |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  User A                                                   ||  |*
*|  |  |    |                                                      ||  |*
*|  |  |    v                                                      ||  |*
*|  |  |  Chat Server 1                                           ||  |*
*|  |  |    |                                                      ||  |*
*|  |  |    +--> Redis: GET user_locations for group              ||  |*
*|  |  |    |                                                      ||  |*
*|  |  |    +--> Direct to Server 1 (local) > 30 WebSockets      ||  |*
*|  |  |    |                                                      ||  |*
*|  |  |    +--> HTTP/gRPC to Server 2 > 25 WebSockets           ||  |*
*|  |  |    |                                                      ||  |*
*|  |  |    +--> HTTP/gRPC to Server 3 > 20 WebSockets           ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  PROS: Simple, low latency                                    |  |*
*|  |  CONS: Sender server does all work, doesn't scale            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  APPROACH 2: PUB/SUB BROADCAST (Recommended)                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  User A                                                   ||  |*
*|  |  |    |                                                      ||  |*
*|  |  |    v                                                      ||  |*
*|  |  |  Chat Server 1                                           ||  |*
*|  |  |    |                                                      ||  |*
*|  |  |    | PUBLISH to channel: "group:123"                     ||  |*
*|  |  |    v                                                      ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |  |              REDIS PUB/SUB                          | ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  |  All chat servers SUBSCRIBE to "group:123"         | ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |         |              |              |                   ||  |*
*|  |  |         v              v              v                   ||  |*
*|  |  |    Server 1       Server 2       Server 3                ||  |*
*|  |  |         |              |              |                   ||  |*
*|  |  |         v              v              v                   ||  |*
*|  |  |    30 users       25 users       20 users                ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  FLOW:                                                         |  |*
*|  |  1. When user joins group > their server subscribes to channel|  |*
*|  |  2. Message sent > published to group channel                 |  |*
*|  |  3. All subscribed servers receive message                    |  |*
*|  |  4. Each server pushes to its local WebSocket connections    |  |*
*|  |                                                                 |  |*
*|  |  PROS: Decoupled, scalable, efficient fan-out                |  |*
*|  |  CONS: Redis pub/sub has no persistence                      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  APPROACH 3: KAFKA FOR DURABILITY + BROADCAST                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  User A > Chat Server 1                                   ||  |*
*|  |  |                 |                                         ||  |*
*|  |  |                 | Produce to Kafka                       ||  |*
*|  |  |                 | topic: groups.messages                 ||  |*
*|  |  |                 | key: group_123                          ||  |*
*|  |  |                 v                                         ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |  |                    KAFKA                            | ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  |  Topic: groups.messages                            | ||  |*
*|  |  |  |  Partition: hash(group_123) % partitions           | ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  |  * Durable (persisted to disk)                     | ||  |*
*|  |  |  |  * Replay capability                               | ||  |*
*|  |  |  |  * Ordered per partition                           | ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |                 |                                         ||  |*
*|  |  |                 v                                         ||  |*
*|  |  |  Group Fanout Service (consumer group)                   ||  |*
*|  |  |                 |                                         ||  |*
*|  |  |                 +--> Lookup online members               ||  |*
*|  |  |                 +--> Route to their chat servers         ||  |*
*|  |  |                 +--> Push notification for offline       ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  PROS: Durable, replay, exactly-once semantics               |  |*
*|  |  CONS: Higher latency (10-50ms more)                         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3.4: CONNECTION REGISTRY - HOW SERVER LOOKUP WORKS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  THE PROBLEM                                                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  You have 2000 chat servers, 100 million users online.        |  |*
*|  |                                                                 |  |*
*|  |  User A (on Server 1) sends message to User B.                |  |*
*|  |  Question: Which of the 2000 servers has User B's connection? |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  User A --> Chat Server 1 --> ? --> User B               ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Where is User B?                                        ||  |*
*|  |  |  * Server 1? Server 500? Server 1999?                   ||  |*
*|  |  |  * Maybe User B is offline?                              ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  THE SOLUTION: CONNECTION REGISTRY (Redis)                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Centralized mapping: user_id > server_id                     |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |                     REDIS CLUSTER                         ||  |*
*|  |  |                                                           ||  |*
*|  |  |   Hash: user_connections                                  ||  |*
*|  |  |   +----------------+-----------------------------------+ ||  |*
*|  |  |   | user_id        | value                             | ||  |*
*|  |  |   +----------------+-----------------------------------+ ||  |*
*|  |  |   | user_123       | chat-server-42                    | ||  |*
*|  |  |   | user_456       | chat-server-17                    | ||  |*
*|  |  |   | user_789       | chat-server-42                    | ||  |*
*|  |  |   | user_101       | chat-server-99                    | ||  |*
*|  |  |   | ...            | ...                               | ||  |*
*|  |  |   +----------------+-----------------------------------+ ||  |*
*|  |  |                                                           ||  |*
*|  |  |   100 million entries = ~2-3 GB memory                   ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  COMPLETE FLOW: USER CONNECT > MESSAGE > DELIVER                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  STEP 1: USER A CONNECTS TO CHAT SERVER                       |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  User A's Phone                                          ||  |*
*|  |  |       |                                                   ||  |*
*|  |  |       | WebSocket connect                                ||  |*
*|  |  |       v                                                   ||  |*
*|  |  |  Load Balancer                                           ||  |*
*|  |  |       |                                                   ||  |*
*|  |  |       | Routes to Chat Server 1 (any available)         ||  |*
*|  |  |       v                                                   ||  |*
*|  |  |  Chat Server 1                                           ||  |*
*|  |  |       |                                                   ||  |*
*|  |  |       | 1. Authenticate user (JWT/session)              ||  |*
*|  |  |       | 2. Accept WebSocket                              ||  |*
*|  |  |       | 3. Store in LOCAL map: user_A > ws_connection   ||  |*
*|  |  |       | 4. Register in REDIS:                           ||  |*
*|  |  |       |    HSET user_connections "user_A" "chat-server-1"|  |*
*|  |  |       |    EXPIRE user_connections:user_A 120           ||  |*
*|  |  |       |                                                   ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  CODE:                                                         |  |*
*|  |                                                                 |  |*
*|  |  async def on_websocket_connect(user_id, websocket):         |  |*
*|  |      # Store locally                                          |  |*
*|  |      local_connections[user_id] = websocket                  |  |*
*|  |                                                                 |  |*
*|  |      # Register globally in Redis                            |  |*
*|  |      await redis.hset(                                        |  |*
*|  |          "user_connections",                                  |  |*
*|  |          user_id,                                             |  |*
*|  |          MY_SERVER_ID                                         |  |*
*|  |      )                                                         |  |*
*|  |      # Set TTL for cleanup if server crashes                 |  |*
*|  |      await redis.expire(f"user_conn:{user_id}", 120)        |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  STEP 2: USER A SENDS MESSAGE TO USER B                       |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  User A: "Send 'Hello!' to User B"                       ||  |*
*|  |  |       |                                                   ||  |*
*|  |  |       | WebSocket message                                ||  |*
*|  |  |       v                                                   ||  |*
*|  |  |  Chat Server 1                                           ||  |*
*|  |  |       |                                                   ||  |*
*|  |  |       | 1. Parse message                                 ||  |*
*|  |  |       | 2. Lookup User B's server:                       ||  |*
*|  |  |       |    server = HGET user_connections "user_B"       ||  |*
*|  |  |       |                                                   ||  |*
*|  |  |       |    Result: "chat-server-42"                      ||  |*
*|  |  |       |                                                   ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  CODE:                                                         |  |*
*|  |                                                                 |  |*
*|  |  async def send_message(sender_id, recipient_id, content):   |  |*
*|  |      # Step 1: Lookup recipient's server                     |  |*
*|  |      target_server = await redis.hget(                       |  |*
*|  |          "user_connections",                                  |  |*
*|  |          recipient_id                                         |  |*
*|  |      )                                                         |  |*
*|  |                                                                 |  |*
*|  |      if target_server is None:                                |  |*
*|  |          # User B is OFFLINE                                 |  |*
*|  |          await store_offline_message(recipient_id, message)  |  |*
*|  |          await send_push_notification(recipient_id, message) |  |*
*|  |          return                                               |  |*
*|  |                                                                 |  |*
*|  |      if target_server == MY_SERVER_ID:                        |  |*
*|  |          # User B is on THIS server (local delivery)         |  |*
*|  |          await deliver_locally(recipient_id, message)        |  |*
*|  |      else:                                                     |  |*
*|  |          # User B is on DIFFERENT server (route it)          |  |*
*|  |          await route_to_server(target_server, message)       |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  STEP 3: ROUTE TO TARGET SERVER                               |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  Chat Server 1                    Chat Server 42          ||  |*
*|  |  |       |                                |                  ||  |*
*|  |  |       | gRPC/HTTP call:               |                  ||  |*
*|  |  |       | DeliverMessage(user_B, msg)   |                  ||  |*
*|  |  |       |-------------------------------->                  ||  |*
*|  |  |       |                                |                  ||  |*
*|  |  |       |                                | 1. Lookup local ||  |*
*|  |  |       |                                |    connections  ||  |*
*|  |  |       |                                |                  ||  |*
*|  |  |       |                                | 2. Find User B's||  |*
*|  |  |       |                                |    WebSocket    ||  |*
*|  |  |       |                                |                  ||  |*
*|  |  |       |                                | 3. Push message ||  |*
*|  |  |       |                                v                  ||  |*
*|  |  |       |                           User B's Phone          ||  |*
*|  |  |       |                                                   ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  ROUTING OPTIONS:                                              |  |*
*|  |                                                                 |  |*
*|  |  Option A: Direct HTTP/gRPC                                   |  |*
*|  |  * Server 1 calls Server 42 directly                         |  |*
*|  |  * Fast, but creates many inter-server connections           |  |*
*|  |                                                                 |  |*
*|  |  Option B: Redis Pub/Sub                                      |  |*
*|  |  * Server 1 publishes to channel "server:42"                 |  |*
*|  |  * Server 42 subscribes to its channel                       |  |*
*|  |  * Decoupled, but adds latency                               |  |*
*|  |                                                                 |  |*
*|  |  Option C: Kafka                                              |  |*
*|  |  * Server 1 produces to topic, partitioned by recipient      |  |*
*|  |  * All servers consume (but only process their users)       |  |*
*|  |  * Durable, but higher latency                               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  STEP 4: USER DISCONNECTS                                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  async def on_websocket_disconnect(user_id):                  |  |*
*|  |      # Remove from local map                                  |  |*
*|  |      del local_connections[user_id]                          |  |*
*|  |                                                                 |  |*
*|  |      # Remove from global registry                            |  |*
*|  |      await redis.hdel("user_connections", user_id)           |  |*
*|  |                                                                 |  |*
*|  |      # Update last_seen in database                          |  |*
*|  |      await db.execute(                                        |  |*
*|  |          "UPDATE users SET last_seen = NOW() WHERE id = ?",  |  |*
*|  |          user_id                                              |  |*
*|  |      )                                                         |  |*
*|  |                                                                 |  |*
*|  |      # Notify presence service                                |  |*
*|  |      await publish_presence_event(user_id, "offline")        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  HEARTBEAT & CLEANUP (Handling Server Crashes)                        |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Problem: If Chat Server 1 crashes, Redis still says          |  |*
*|  |           User A is on Server 1 > messages go to dead server |  |*
*|  |                                                                 |  |*
*|  |  Solution 1: TTL + Heartbeat                                  |  |*
*|  |                                                                 |  |*
*|  |  # On connect: Set with TTL                                   |  |*
*|  |  SETEX user_conn:user_A 60 "chat-server-1"                   |  |*
*|  |                                                                 |  |*
*|  |  # Heartbeat every 30 seconds: Refresh TTL                   |  |*
*|  |  async def heartbeat_loop():                                  |  |*
*|  |      while True:                                              |  |*
*|  |          for user_id in local_connections:                   |  |*
*|  |              await redis.expire(f"user_conn:{user_id}", 60) |  |*
*|  |          await asyncio.sleep(30)                             |  |*
*|  |                                                                 |  |*
*|  |  # If server crashes: No heartbeat > TTL expires in 60s     |  |*
*|  |  # User appears offline > new messages queued correctly     |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  Solution 2: Server Health Check                              |  |*
*|  |                                                                 |  |*
*|  |  # Separate health checker service                            |  |*
*|  |  async def check_server_health():                             |  |*
*|  |      for server_id in all_servers:                           |  |*
*|  |          if not await ping(server_id):                       |  |*
*|  |              # Server is down, clean up all its users        |  |*
*|  |              await redis.delete_pattern(                     |  |*
*|  |                  f"user_conn:*:{server_id}"                  |  |*
*|  |              )                                                 |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  REDIS DATA STRUCTURES FOR CONNECTION REGISTRY                        |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  OPTION 1: Hash (Simple, most common)                         |  |*
*|  |                                                                 |  |*
*|  |  HSET user_connections user_123 "chat-server-42"             |  |*
*|  |  HGET user_connections user_123  >  "chat-server-42"         |  |*
*|  |  HDEL user_connections user_123                               |  |*
*|  |                                                                 |  |*
*|  |  Pros: Single key, atomic operations                         |  |*
*|  |  Cons: No per-user TTL (hash fields don't expire)           |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  OPTION 2: Individual Keys with TTL                           |  |*
*|  |                                                                 |  |*
*|  |  SETEX user_conn:user_123 60 "chat-server-42"                |  |*
*|  |  GET user_conn:user_123  >  "chat-server-42"                 |  |*
*|  |  DEL user_conn:user_123                                       |  |*
*|  |                                                                 |  |*
*|  |  Pros: Per-user TTL, auto-cleanup                            |  |*
*|  |  Cons: More keys, slightly more memory                       |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  OPTION 3: Server > Users (Reverse Index)                    |  |*
*|  |                                                                 |  |*
*|  |  # Also maintain reverse mapping for bulk operations         |  |*
*|  |  SADD server:chat-server-42:users user_123 user_456         |  |*
*|  |                                                                 |  |*
*|  |  # When server crashes, easy to find all affected users     |  |*
*|  |  SMEMBERS server:chat-server-42:users  >  [user_123, ...]   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3.5: MULTI-DEVICE SUPPORT
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  MULTI-DEVICE SUPPORT                                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  User can be logged in on multiple devices:                   |  |*
*|  |  * Phone (primary)                                            |  |*
*|  |  * Tablet                                                      |  |*
*|  |  * Desktop app                                                 |  |*
*|  |  * Web browser                                                 |  |*
*|  |                                                                 |  |*
*|  |  Connection registry:                                          |  |*
*|  |  KEY: user_connections:{user_id}                              |  |*
*|  |  VALUE: SET of (device_id, server_id)                         |  |*
*|  |                                                                 |  |*
*|  |  On send message:                                              |  |*
*|  |  * Get all devices for user                                   |  |*
*|  |  * Send to ALL connected devices                              |  |*
*|  |  * Client handles deduplication by message_id                 |  |*
*|  |                                                                 |  |*
*|  |  Message sync:                                                 |  |*
*|  |  * New device connects > sync from last known message_id     |  |*
*|  |  * Cursor per device stored on server                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4: ARCHITECTURE DIAGRAM
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|                         REAL-TIME MESSAGING SYSTEM                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |                    +-----------------------+                    |  |*
*|  |                    |       CLIENTS         |                    |  |*
*|  |                    |  (Mobile/Web/Desktop) |                    |  |*
*|  |                    +-----------+-----------+                    |  |*
*|  |                                |                                |  |*
*|  |                    +-----------+-----------+                    |  |*
*|  |                    |   LOAD BALANCER (L4)  |                    |  |*
*|  |                    |   (Sticky Sessions)   |                    |  |*
*|  |                    +-----------+-----------+                    |  |*
*|  |                                |                                |  |*
*|  |          +---------------------+---------------------+         |  |*
*|  |          |                     |                     |         |  |*
*|  |          v                     v                     v         |  |*
*|  |    +-----------+        +-----------+        +-----------+    |  |*
*|  |    |   Chat    |        |   Chat    |        |   Chat    |    |  |*
*|  |    | Server 1  |<------>| Server 2  |<------>| Server N  |    |  |*
*|  |    |  (WS)     |  Redis |  (WS)     |  Redis |  (WS)     |    |  |*
*|  |    +-----+-----+  PubSub+-----+-----+  PubSub+-----+-----+    |  |*
*|  |          |                    |                    |          |  |*
*|  |          +--------------------+--------------------+          |  |*
*|  |                               |                                |  |*
*|  |                    +----------+----------+                     |  |*
*|  |                    |                     |                     |  |*
*|  |                    v                     v                     |  |*
*|  |          +-----------------+   +-----------------+            |  |*
*|  |          |   REDIS         |   |     KAFKA       |            |  |*
*|  |          | * Connections   |   | * messages      |            |  |*
*|  |          | * Presence      |   | * events        |            |  |*
*|  |          | * PubSub        |   | * notifications |            |  |*
*|  |          +-----------------+   +--------+--------+            |  |*
*|  |                                         |                      |  |*
*|  |          +------------------------------+------------------+  |  |*
*|  |          |                              |                  |  |  |*
*|  |          v                              v                  v  |  |*
*|  |   +------------+              +------------+      +----------+|  |*
*|  |   |  Message   |              |   Push     |      | Presence ||  |*
*|  |   |  Storage   |              |  Service   |      | Service  ||  |*
*|  |   |  Workers   |              |            |      |          ||  |*
*|  |   +------+-----+              +------+-----+      +----------+|  |*
*|  |          |                           |                        |  |*
*|  |          v                           v                        |  |*
*|  |   +------------+              +------------+                  |  |*
*|  |   | Cassandra  |              | APNs/FCM   |                  |  |*
*|  |   | (Messages) |              |            |                  |  |*
*|  |   +------------+              +------------+                  |  |*
*|  |                                                                |  |*
*|  |          +------------+                                       |  |*
*|  |          |  Media     |                                       |  |*
*|  |          |  Service   |                                       |  |*
*|  |          +------+-----+                                       |  |*
*|  |                 |                                              |  |*
*|  |          +------+------+                                      |  |*
*|  |          |             |                                      |  |*
*|  |          v             v                                      |  |*
*|  |    +----------+  +----------+                                |  |*
*|  |    |   S3     |  |   CDN    |                                |  |*
*|  |    | (Media)  |  |(Delivery)|                                |  |*
*|  |    +----------+  +----------+                                |  |*
*|  |                                                                |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 8: MULTI-DEVICE SYNC
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  MULTI-DEVICE MESSAGING                                                |*
*|                                                                         |*
*|  Users want to use WhatsApp/Telegram on:                               |*
*|  * Phone (primary)                                                      |*
*|  * Tablet                                                               |*
*|  * Desktop app                                                          |*
*|  * Web browser                                                          |*
*|                                                                         |*
*|  All devices must:                                                      |*
*|  * See the same conversations                                          |*
*|  * Receive messages in real-time                                       |*
*|  * Show same read/unread status                                        |*
*|  * Stay in sync when switching devices                                 |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  DEVICE REGISTRATION MODEL                                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Each user has multiple DEVICE RECORDS:                        |  |*
*|  |                                                                 |  |*
*|  |  User: alice                                                    |  |*
*|  |    |                                                            |  |*
*|  |    +-- Device: iPhone-14-xyz                                   |  |*
*|  |    |   * device_type: mobile                                   |  |*
*|  |    |   * push_token: APNs_token_abc                            |  |*
*|  |    |   * last_active: 2024-01-15 10:30:00                      |  |*
*|  |    |   * encryption_keys: {...}                                |  |*
*|  |    |                                                            |  |*
*|  |    +-- Device: Chrome-Web-def                                  |  |*
*|  |    |   * device_type: web                                      |  |*
*|  |    |   * push_token: null (uses WebSocket only)               |  |*
*|  |    |   * last_active: 2024-01-15 09:00:00                      |  |*
*|  |    |   * encryption_keys: {...}                                |  |*
*|  |    |                                                            |  |*
*|  |    +-- Device: MacBook-Desktop-ghi                             |  |*
*|  |        * device_type: desktop                                  |  |*
*|  |        * push_token: null                                       |  |*
*|  |        * last_active: 2024-01-14 18:00:00                      |  |*
*|  |        * encryption_keys: {...}                                |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  CONNECTION REGISTRY (Multi-Device)                                    |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  SINGLE DEVICE MODEL (simple):                                 |  |*
*|  |                                                                 |  |*
*|  |  user_connections:                                              |  |*
*|  |    "alice" > "chat-server-1"                                   |  |*
*|  |    "bob"   > "chat-server-5"                                   |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  MULTI-DEVICE MODEL:                                           |  |*
*|  |                                                                 |  |*
*|  |  user_connections:alice                                        |  |*
*|  |    "iPhone-14-xyz"      > "chat-server-1"                     |  |*
*|  |    "Chrome-Web-def"     > "chat-server-3"                     |  |*
*|  |    "MacBook-Desktop"    > "chat-server-7"                     |  |*
*|  |                                                                 |  |*
*|  |  user_connections:bob                                          |  |*
*|  |    "Pixel-8-abc"        > "chat-server-5"                     |  |*
*|  |                                                                 |  |*
*|  |  Data Structure: Hash per user                                 |  |*
*|  |  Key: user_connections:{user_id}                               |  |*
*|  |  Fields: device_id > chat_server_id                            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  MESSAGE DELIVERY TO MULTIPLE DEVICES                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  FLOW: Bob sends message to Alice (3 devices online)           |  |*
*|  |                                                                 |  |*
*|  |  Bob                                                            |  |*
*|  |    |                                                            |  |*
*|  |    | Send: "Hello Alice!"                                      |  |*
*|  |    v                                                            |  |*
*|  |  Chat Server                                                    |  |*
*|  |    |                                                            |  |*
*|  |    | 1. Lookup Alice's devices in Redis                        |  |*
*|  |    |    Result: 3 devices on 3 different servers               |  |*
*|  |    |                                                            |  |*
*|  |    | 2. For EACH device:                                       |  |*
*|  |    |    * Route message to that device's server               |  |*
*|  |    |    * Server pushes to device's WebSocket                 |  |*
*|  |    |                                                            |  |*
*|  |    |                                                            |  |*
*|  |    +----------------+----------------+----------------+        |  |*
*|  |    |                |                |                |        |  |*
*|  |    v                v                v                |        |  |*
*|  |  Chat Server 1    Chat Server 3   Chat Server 7      |        |  |*
*|  |    |                |                |                |        |  |*
*|  |    v                v                v                |        |  |*
*|  |  Alice's          Alice's         Alice's            |        |  |*
*|  |  iPhone           Web Browser     Mac Desktop        |        |  |*
*|  |                                                       |        |  |*
*|  |  All 3 devices receive message simultaneously        |        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  SYNC SCENARIOS                                                        |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SCENARIO 1: New Device Login                                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Alice logs into WhatsApp Web for first time                   |  |*
*|  |                                                                 |  |*
*|  |  1. AUTHENTICATE                                                |  |*
*|  |     * Scan QR code from phone                                  |  |*
*|  |     * Or enter phone number + OTP                              |  |*
*|  |                                                                 |  |*
*|  |  2. REGISTER DEVICE                                            |  |*
*|  |     * Generate new device_id                                   |  |*
*|  |     * Generate encryption keys for this device                 |  |*
*|  |     * Store device record in database                          |  |*
*|  |                                                                 |  |*
*|  |  3. INITIAL SYNC (History Download)                            |  |*
*|  |     * Fetch conversation list from server                      |  |*
*|  |     * Fetch last N messages per conversation                   |  |*
*|  |     * Download media thumbnails                                |  |*
*|  |                                                                 |  |*
*|  |  4. ESTABLISH REALTIME                                          |  |*
*|  |     * Open WebSocket connection                                |  |*
*|  |     * Register in connection registry                          |  |*
*|  |     * Start receiving new messages                             |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SCENARIO 2: Device Comes Back Online                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Alice's laptop was offline for 2 hours, now reconnects        |  |*
*|  |                                                                 |  |*
*|  |  1. RECONNECT                                                   |  |*
*|  |     * Re-establish WebSocket connection                        |  |*
*|  |     * Re-register in connection registry                       |  |*
*|  |                                                                 |  |*
*|  |  2. DELTA SYNC                                                  |  |*
*|  |     * Client sends: "last_sync_timestamp: 2024-01-15T08:00:00"|  |*
*|  |     * Server returns: All messages since that timestamp        |  |*
*|  |     * Client applies messages locally                          |  |*
*|  |                                                                 |  |*
*|  |  3. STATE SYNC                                                  |  |*
*|  |     * Sync read receipts (which messages marked as read)      |  |*
*|  |     * Sync deleted messages                                    |  |*
*|  |     * Sync muted conversations                                 |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SCENARIO 3: Read Receipt Sync                                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Alice reads message on Phone                                  |  |*
*|  |  > Other devices should also show as "read"                    |  |*
*|  |                                                                 |  |*
*|  |  Phone                                                          |  |*
*|  |    |                                                            |  |*
*|  |    | User views message                                        |  |*
*|  |    |                                                            |  |*
*|  |    | Send: { type: "read_receipt",                             |  |*
*|  |    |         conversation_id: "conv_123",                      |  |*
*|  |    |         read_until: "msg_456" }                           |  |*
*|  |    v                                                            |  |*
*|  |  Server                                                         |  |*
*|  |    |                                                            |  |*
*|  |    | 1. Update database: last_read_message = msg_456          |  |*
*|  |    |                                                            |  |*
*|  |    | 2. Notify Alice's OTHER devices                          |  |*
*|  |    |                                                            |  |*
*|  |    +----------------+----------------+                         |  |*
*|  |    |                |                |                         |  |*
*|  |    v                v                                          |  |*
*|  |  Web Browser      Desktop                                      |  |*
*|  |    |                |                                          |  |*
*|  |    | Update UI:     | Update UI:                               |  |*
*|  |    | Mark as read   | Mark as read                             |  |*
*|  |                                                                 |  |*
*|  |  3. Notify sender (Bob): "Alice read your message"            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SCENARIO 4: Sent Message Sync                                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Alice sends message from Web                                  |  |*
*|  |  > Phone and Desktop should also show the sent message        |  |*
*|  |                                                                 |  |*
*|  |  Web Browser                                                    |  |*
*|  |    |                                                            |  |*
*|  |    | Alice sends: "Hi Bob!"                                    |  |*
*|  |    v                                                            |  |*
*|  |  Server                                                         |  |*
*|  |    |                                                            |  |*
*|  |    | 1. Store message in database                              |  |*
*|  |    |                                                            |  |*
*|  |    | 2. Deliver to Bob                                         |  |*
*|  |    |                                                            |  |*
*|  |    | 3. SYNC to Alice's other devices:                        |  |*
*|  |    |    "You sent this message from another device"            |  |*
*|  |    |                                                            |  |*
*|  |    +----------------+----------------+                         |  |*
*|  |    |                |                |                         |  |*
*|  |    v                v                v                         |  |*
*|  |  Alice's Phone    Alice's Desktop   Bob                        |  |*
*|  |    |                |                |                         |  |*
*|  |    | Shows:        | Shows:         | Shows:                  |  |*
*|  |    | "Hi Bob!"     | "Hi Bob!"      | "Hi Bob!"               |  |*
*|  |    | (sent)        | (sent)         | (received)              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  MULTI-DEVICE ARCHITECTURE DIAGRAM                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |                          ALICE                                  |  |*
*|  |     +---------+    +---------+    +---------+                  |  |*
*|  |     |  Phone  |    |   Web   |    | Desktop |                  |  |*
*|  |     | (D1)    |    |  (D2)   |    |  (D3)   |                  |  |*
*|  |     +----+----+    +----+----+    +----+----+                  |  |*
*|  |          |              |              |                        |  |*
*|  |          | WebSocket    | WebSocket    | WebSocket             |  |*
*|  |          |              |              |                        |  |*
*|  |          v              v              v                        |  |*
*|  |     +---------+    +---------+    +---------+                  |  |*
*|  |     | Chat    |    | Chat    |    | Chat    |                  |  |*
*|  |     | Srv 1   |    | Srv 3   |    | Srv 7   |                  |  |*
*|  |     +----+----+    +----+----+    +----+----+                  |  |*
*|  |          |              |              |                        |  |*
*|  |          +--------------+--------------+                        |  |*
*|  |                         |                                       |  |*
*|  |                         v                                       |  |*
*|  |              +----------------------+                           |  |*
*|  |              |                      |                           |  |*
*|  |              |   REDIS CLUSTER      |                           |  |*
*|  |              |                      |                           |  |*
*|  |              |   user_connections:  |                           |  |*
*|  |              |   alice:             |                           |  |*
*|  |              |     D1 > srv1        |                           |  |*
*|  |              |     D2 > srv3        |                           |  |*
*|  |              |     D3 > srv7        |                           |  |*
*|  |              |                      |                           |  |*
*|  |              +----------------------+                           |  |*
*|  |                         |                                       |  |*
*|  |                         | When message arrives for Alice:       |  |*
*|  |                         | * Lookup all devices                  |  |*
*|  |                         | * Fan-out to each server              |  |*
*|  |                         | * Each server pushes to its device   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  CONFLICT RESOLUTION (Same User, Multiple Devices)                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CONFLICT: Alice deletes message on Phone,                     |  |*
*|  |            but hasn't synced to Web yet                        |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  RESOLUTION STRATEGIES:                                         |  |*
*|  |                                                                 |  |*
*|  |  1. LAST-WRITE-WINS (LWW)                                      |  |*
*|  |     * Most recent action (by timestamp) wins                   |  |*
*|  |     * Simple but may lose user intent                          |  |*
*|  |                                                                 |  |*
*|  |  2. OPERATION-BASED (CRDT-like)                                |  |*
*|  |     * Track operations, not state                              |  |*
*|  |     * "Delete" operation applied everywhere                    |  |*
*|  |     * Converges to same state                                  |  |*
*|  |                                                                 |  |*
*|  |  3. TOMBSTONES                                                  |  |*
*|  |     * Deleted messages marked as tombstone                     |  |*
*|  |     * Tombstone synced to all devices                          |  |*
*|  |     * UI hides tombstoned messages                             |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  IMPLEMENTATION:                                                |  |*
*|  |                                                                 |  |*
*|  |  Every action has:                                              |  |*
*|  |  * action_id (unique)                                          |  |*
*|  |  * timestamp (server-assigned)                                 |  |*
*|  |  * device_id (source)                                          |  |*
*|  |                                                                 |  |*
*|  |  Server ensures all devices receive all actions                |  |*
*|  |  Clients apply actions in timestamp order                      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  ENCRYPTION WITH MULTI-DEVICE (E2EE Challenge)                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  PROBLEM:                                                       |  |*
*|  |  In E2EE, message is encrypted for recipient's public key.    |  |*
*|  |  But recipient has 3 devices, each with DIFFERENT keys!       |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  SOLUTION: Encrypt for EACH device separately                  |  |*
*|  |                                                                 |  |*
*|  |  Bob sends "Hello" to Alice:                                   |  |*
*|  |                                                                 |  |*
*|  |  Bob's device                                                   |  |*
*|  |    |                                                            |  |*
*|  |    | 1. Fetch Alice's device keys from server                  |  |*
*|  |    |    Result: [Phone_pubkey, Web_pubkey, Desktop_pubkey]    |  |*
*|  |    |                                                            |  |*
*|  |    | 2. Encrypt message 3 times:                               |  |*
*|  |    |    * ciphertext_1 = encrypt("Hello", Phone_pubkey)       |  |*
*|  |    |    * ciphertext_2 = encrypt("Hello", Web_pubkey)         |  |*
*|  |    |    * ciphertext_3 = encrypt("Hello", Desktop_pubkey)     |  |*
*|  |    |                                                            |  |*
*|  |    | 3. Send all ciphertexts to server                         |  |*
*|  |    |                                                            |  |*
*|  |    v                                                            |  |*
*|  |  Server                                                         |  |*
*|  |    |                                                            |  |*
*|  |    | Route each ciphertext to appropriate device               |  |*
*|  |    |                                                            |  |*
*|  |    +-> Phone:   ciphertext_1 > decrypt with Phone_privkey     |  |*
*|  |    +-> Web:     ciphertext_2 > decrypt with Web_privkey       |  |*
*|  |    +-> Desktop: ciphertext_3 > decrypt with Desktop_privkey   |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  OPTIMIZATION: Sender Key Protocol (for groups)                |  |*
*|  |                                                                 |  |*
*|  |  Instead of encrypting N times for N devices:                  |  |*
*|  |  * Use symmetric "sender key" for message encryption           |  |*
*|  |  * Distribute sender key to each device (encrypted for them)  |  |*
*|  |  * All devices can decrypt with shared sender key              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  DEVICE LIMITS & MANAGEMENT                                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  LIMITS:                                                        |  |*
*|  |  * Max devices per user: 5-10 (to limit fan-out)              |  |*
*|  |  * WhatsApp: 1 phone + 4 companion devices                    |  |*
*|  |  * Telegram: Unlimited (but has smart session management)     |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  DEVICE REMOVAL:                                                |  |*
*|  |                                                                 |  |*
*|  |  * Auto-logout inactive devices (after 30 days no activity)   |  |*
*|  |  * User can manually remove devices from settings             |  |*
*|  |  * Suspicious login > notify other devices                    |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  PRIMARY DEVICE:                                                |  |*
*|  |                                                                 |  |*
*|  |  WhatsApp model:                                                |  |*
*|  |  * Phone is PRIMARY (required for initial setup)              |  |*
*|  |  * Web/Desktop are COMPANION (can work independently now)     |  |*
*|  |  * If phone removed > all companions logged out               |  |*
*|  |                                                                 |  |*
*|  |  Telegram model:                                                |  |*
*|  |  * All devices are EQUAL                                       |  |*
*|  |  * Any device can be used independently                       |  |*
*|  |  * No primary device concept                                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  SYNC PROTOCOL SUMMARY                                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  WHAT GETS SYNCED:                                              |  |*
*|  |                                                                 |  |*
*|  |  Y Messages (sent and received)                                |  |*
*|  |  Y Read receipts / last read position                          |  |*
*|  |  Y Deleted messages (tombstones)                               |  |*
*|  |  Y Edited messages                                              |  |*
*|  |  Y Reactions                                                    |  |*
*|  |  Y Conversation mute/archive status                            |  |*
*|  |  Y Contact names / nicknames                                   |  |*
*|  |  Y Group membership changes                                     |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  WHAT'S NOT SYNCED (Device-specific):                          |  |*
*|  |                                                                 |  |*
*|  |  X Notification settings (per-device)                          |  |*
*|  |  X Downloaded media (re-download per device)                  |  |*
*|  |  X Draft messages (usually local)                              |  |*
*|  |  X App theme/appearance                                        |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  SYNC TRIGGERS:                                                 |  |*
*|  |                                                                 |  |*
*|  |  * Realtime: Via WebSocket (for online devices)               |  |*
*|  |  * Pull: On app open / reconnect (delta sync)                 |  |*
*|  |  * Push notification: Triggers app to sync                    |  |*
*|  |  * Periodic: Background sync every N minutes                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF CHAPTER 2
