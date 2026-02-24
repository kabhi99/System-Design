# CHAT SYSTEM DESIGN (WHATSAPP / SLACK)
*Complete Design: Requirements, Architecture, and Interview Guide*

A real-time chat system enables users to exchange messages instantly. At scale,
it must handle billions of messages per day, maintain message ordering, support
group conversations, and deliver messages reliably even when recipients are offline.

## SECTION 1: UNDERSTANDING THE PROBLEM

### WHAT IS A CHAT SYSTEM?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A chat system enables real-time communication between users:           |
|                                                                         |
|  USER EXPERIENCE:                                                       |
|  1. Open app, see list of conversations                                 |
|  2. Tap a conversation to view message history                          |
|  3. Type and send messages (text, images, videos, files)                |
|  4. See delivery status (sent, delivered, read)                         |
|  5. See online/offline/typing indicators                                |
|  6. Create and participate in group chats                               |
|  7. Receive notifications for new messages when app is closed           |
|                                                                         |
|  CORE CHALLENGE:                                                        |
|  Deliver messages in real-time to 2 billion users across the globe      |
|  with <100ms latency, while ensuring no message is ever lost.           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY IS THIS HARD TO BUILD?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY CHALLENGES:                                                        |
|                                                                         |
|  1. REAL-TIME DELIVERY                                                  |
|  ----------------------                                                 |
|  Messages must appear instantly (<100ms).                               |
|  HTTP request-response model is too slow (polling overhead).            |
|  Need persistent connections (WebSockets).                              |
|                                                                         |
|  2. MASSIVE CONCURRENT CONNECTIONS                                      |
|  ------------------------------------                                   |
|  50M+ users connected simultaneously.                                   |
|  Each needs a persistent WebSocket connection.                          |
|  Managing connection state at this scale is hard.                       |
|                                                                         |
|  3. MESSAGE ORDERING                                                    |
|  ---------------------                                                  |
|  Messages must appear in correct order.                                 |
|  With distributed servers, ordering is non-trivial.                     |
|  Clock skew between servers complicates timestamps.                     |
|                                                                         |
|  4. RELIABILITY                                                         |
|  ---------------                                                        |
|  Zero message loss -- messages must be durably stored.                  |
|  At-least-once delivery with deduplication.                             |
|  Handle network partitions gracefully.                                  |
|                                                                         |
|  5. GROUP CHAT FAN-OUT                                                  |
|  ----------------------                                                 |
|  A message in a 500-person group must be delivered to all members.      |
|  Different members may be on different servers.                         |
|                                                                         |
|  6. OFFLINE MESSAGE DELIVERY                                            |
|  ----------------------------                                           |
|  Users go offline frequently (mobile).                                  |
|  Must queue messages and deliver when they reconnect.                   |
|  Push notifications for offline users.                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.2: REQUIREMENTS

### FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS:                                               |
|                                                                         |
|  1. ONE-TO-ONE CHAT                                                     |
|     - Send/receive text messages in real-time                           |
|     - Send media (images, videos, voice notes, documents)               |
|     - Message delivery status: sent, delivered, read                    |
|     - Delete messages (for me / for everyone)                           |
|     - Reply to specific messages                                        |
|     - Forward messages                                                  |
|                                                                         |
|  2. GROUP CHAT                                                          |
|     - Create groups (up to 1024 members)                                |
|     - Add/remove members                                                |
|     - Admin roles and permissions                                       |
|     - Group name, description, avatar                                   |
|     - Mention specific members (@user)                                  |
|                                                                         |
|  3. PRESENCE / ONLINE STATUS                                            |
|     - Show online/offline/last seen status                              |
|     - Typing indicators ("User is typing...")                           |
|     - Privacy controls (hide last seen)                                 |
|                                                                         |
|  4. READ RECEIPTS                                                       |
|     - Double check marks (delivered + read)                             |
|     - Group: show who has read the message                              |
|                                                                         |
|  5. MEDIA SHARING                                                       |
|     - Images (with compression)                                         |
|     - Videos (with transcoding)                                         |
|     - Voice messages                                                    |
|     - Documents (PDF, etc.)                                             |
|     - Location sharing                                                  |
|                                                                         |
|  6. PUSH NOTIFICATIONS                                                  |
|     - Notify offline users of new messages                              |
|     - Badge count on app icon                                           |
|     - Configurable notification preferences per chat                    |
|                                                                         |
|  7. SEARCH                                                              |
|     - Search messages within a conversation                             |
|     - Search across all conversations                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### NON-FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NON-FUNCTIONAL REQUIREMENTS:                                           |
|                                                                         |
|  1. REAL-TIME DELIVERY                                                  |
|     - Message delivery: <100ms (p95) when both users online             |
|     - Typing indicator: <50ms                                           |
|     - Presence update: <500ms                                           |
|                                                                         |
|  2. RELIABILITY                                                         |
|     - Zero message loss (at-least-once delivery)                        |
|     - Messages must be durably stored before acknowledging              |
|     - Deduplication to handle retries                                   |
|                                                                         |
|  3. MESSAGE ORDERING                                                    |
|     - Messages in a conversation appear in correct order                |
|     - Causal ordering: if A replies to B, A appears after B             |
|                                                                         |
|  4. HIGH AVAILABILITY                                                   |
|     - 99.99% uptime                                                     |
|     - Graceful degradation (stale presence is OK)                       |
|                                                                         |
|  5. SCALABILITY                                                         |
|     - 2B registered users                                               |
|     - 50M concurrent WebSocket connections                              |
|     - 100B messages/day                                                 |
|                                                                         |
|  6. SECURITY                                                            |
|     - End-to-end encryption for 1:1 chats                               |
|     - TLS for all connections                                           |
|     - Authentication and authorization                                  |
|                                                                         |
|  7. STORAGE EFFICIENCY                                                  |
|     - Messages are write-heavy, append-only                             |
|     - Time-series access pattern (recent messages read most)            |
|     - Efficient storage for billions of messages                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: SCALE ESTIMATION

### BACK-OF-ENVELOPE CALCULATIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USER BASE:                                                             |
|  - Total registered users: 2 Billion                                    |
|  - Daily Active Users (DAU): 500 Million                                |
|  - Concurrent connections (peak): 50 Million                            |
|  - Average contacts per user: 100                                       |
|  - Average groups per user: 10                                          |
|  - Average group size: 20 members                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TRAFFIC ESTIMATES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MESSAGE TRAFFIC:                                                       |
|  - 100 Billion messages/day                                             |
|  - 100B / 86,400 = ~1.16 Million messages/second                        |
|  - Peak (3x): ~3.5 Million messages/second                              |
|                                                                         |
|  BREAKDOWN BY TYPE:                                                     |
|  - 1:1 text messages: 70B/day (70%)                                     |
|  - Group text messages: 20B/day (20%)                                   |
|  - Media messages: 10B/day (10%)                                        |
|                                                                         |
|  CONNECTION MANAGEMENT:                                                 |
|  - 50M concurrent WebSocket connections                                 |
|  - Average connection duration: 30 minutes                              |
|  - New connections/second: 50M / 1800s ~ 28,000/sec                     |
|  - Connection churn (reconnects): ~50,000/sec                           |
|                                                                         |
|  PRESENCE UPDATES:                                                      |
|  - Online/offline events: ~100M/day                                     |
|  - Heartbeat checks: 50M users x 1/30sec = 1.67M/sec                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STORAGE ESTIMATES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MESSAGE STORAGE:                                                       |
|  - Average text message size: 200 bytes                                 |
|  - 100B messages/day x 200B = 20 TB/day (text only)                     |
|  - Per year: 7.3 PB                                                     |
|  - With replication (3x): ~22 PB/year                                   |
|                                                                         |
|  MEDIA STORAGE:                                                         |
|  - 10B media messages/day                                               |
|  - Average image: 200 KB (compressed)                                   |
|  - Average video: 5 MB (compressed)                                     |
|  - 80% images, 15% videos, 5% docs                                      |
|  - Images: 8B x 200KB = 1.6 PB/day                                      |
|  - Videos: 1.5B x 5MB = 7.5 PB/day                                      |
|  - Total media: ~9 PB/day                                               |
|                                                                         |
|  METADATA STORAGE:                                                      |
|  - Message metadata (sender, timestamp, status): ~100 bytes each        |
|  - 100B x 100B = 10 TB/day                                              |
|  - Conversation metadata: negligible compared to messages               |
|                                                                         |
|  CONNECTION STATE:                                                      |
|  - Per connection: ~2 KB (user ID, device info, session)                |
|  - 50M connections x 2KB = 100 GB in memory                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### BANDWIDTH ESTIMATES

```
+--------------------------------------------------------------------------+
|                                                                          |
|  TEXT MESSAGES:                                                          |
|  - 1.16M msgs/sec x 200 bytes = ~232 MB/sec = ~1.86 Gbps                 |
|                                                                          |
|  MEDIA:                                                                  |
|  - Images: ~18.5 GB/sec (inbound, before CDN caching)                    |
|  - Videos: ~86.8 GB/sec (inbound)                                        |
|  - Outbound served mostly from CDN edge                                  |
|                                                                          |
|  WEBSOCKET OVERHEAD:                                                     |
|  - Heartbeat: 50M users x 32 bytes x 1/30sec = ~53 MB/sec                |
|  - Presence: negligible compared to messages                             |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 3: COMMUNICATION PROTOCOLS

### WEBSOCKET VS LONG POLLING VS SSE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROTOCOL COMPARISON:                                                   |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  | Feature          | WebSocket  | Long Polling | SSE               |   |
|  +------------------------------------------------------------------+   |
|  | Direction        | Bi-direct. | Client-init  | Server->Client    |   |
|  | Latency          | Very low   | Medium       | Low               |   |
|  | Connection       | Persistent | Repeated     | Persistent        |   |
|  | Server overhead  | 1 conn     | Many conns   | 1 conn            |   |
|  | Binary support   | Yes        | Yes          | No (text only)    |   |
|  | Firewall issues  | Some       | None         | None              |   |
|  | Scalability      | Stateful   | Stateless    | Stateful          |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  LONG POLLING:                                                          |
|  Client sends request -> Server holds until new data -> Responds        |
|  -> Client immediately sends new request                                |
|  - Overhead: new TCP connection each time                               |
|  - Higher latency: time to establish connection                         |
|  - Simpler: works with standard HTTP infrastructure                     |
|                                                                         |
|  SERVER-SENT EVENTS (SSE):                                              |
|  Server pushes data to client over HTTP connection                      |
|  - One-directional: server to client only                               |
|  - Client must use separate HTTP POST for sending messages              |
|  - No binary support (text/event-stream format)                         |
|  - Auto-reconnection built in                                           |
|                                                                         |
|  WEBSOCKET (CHOSEN):                                                    |
|  Full-duplex communication over single TCP connection                   |
|  - Bi-directional: both sides can send anytime                          |
|  - Very low overhead after initial handshake                            |
|  - Ideal for chat: both sending and receiving messages                  |
|  - Challenge: stateful connections require sticky routing               |
|                                                                         |
|  DECISION: WebSocket for chat delivery, HTTP for media upload           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WEBSOCKET CONNECTION LIFECYCLE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WEBSOCKET CONNECTION LIFECYCLE:                                        |
|                                                                         |
|  Client                        Server                                   |
|    |                              |                                     |
|    |--- HTTP Upgrade Request ---->|  (includes auth token)              |
|    |                              |                                     |
|    |<-- 101 Switching Protocols --|  (connection established)           |
|    |                              |                                     |
|    |<===== WebSocket Open =======>|                                     |
|    |                              |                                     |
|    |--- Auth message ------------>|  (verify JWT, load session)         |
|    |<-- Auth ACK ----------------|                                      |
|    |                              |                                     |
|    |<-- Pending messages ---------|  (messages received while offline)  |
|    |--- ACK for each ----------->|                                      |
|    |                              |                                     |
|    |--- Send message ------------>|  (normal operation)                 |
|    |<-- Message ACK --------------|                                     |
|    |<-- Incoming message ---------|                                     |
|    |--- Read receipt ------------>|                                     |
|    |                              |                                     |
|    |--- Ping -------------------->|  (heartbeat every 30 sec)           |
|    |<-- Pong --------------------|                                      |
|    |                              |                                     |
|    |--- Close ------------------->|  (or timeout after missed pings)    |
|    |<-- Close ACK ----------------|                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

### SYSTEM OVERVIEW

```
+-------------------------------------------------------------------------+
|                                                                         |
|                        HIGH-LEVEL ARCHITECTURE                          |
|                                                                         |
|  +----------+     +-----------+     +-------------------+               |
|  |  Client  |---->|   Load    |---->| WebSocket Gateway |               |
|  |  (App/   |     |  Balancer |     | (Connection Mgmt) |               |
|  |   Web)   |     | (L4/L7)  |     +-------------------+                |
|  +----------+     +-----------+            |                            |
|                                            v                            |
|                                   +-------------------+                 |
|                                   |   Chat Service    |                 |
|                                   | (Message Routing) |                 |
|                                   +-------------------+                 |
|                                            |                            |
|               +----------------------------+------------------+         |
|               |              |             |                  |         |
|               v              v             v                  v         |
|        +-----------+  +-----------+  +-----------+  +-------------+     |
|        | Message   |  | Presence  |  |  Group    |  | Notification|     |
|        | Store     |  | Service   |  |  Service  |  | Service     |     |
|        | (Cassandra|  | (Redis)   |  |           |  | (Push)      |     |
|        |  / HBase) |  +-----------+  +-----------+  +-------------+     |
|        +-----------+                                                    |
|                                                                         |
|  SUPPORTING SERVICES:                                                   |
|  +-------------+  +---------------+  +-------------+  +----------+      |
|  | User Service|  | Media Service |  | Key Mgmt    |  | Search   |      |
|  | (Profiles)  |  | (Upload/CDN)  |  | (E2E Encr.) |  | Service  |      |
|  +-------------+  +---------------+  +-------------+  +----------+      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CONNECTION MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WEBSOCKET GATEWAY (Connection Manager):                                |
|                                                                         |
|  Manages millions of persistent WebSocket connections.                  |
|                                                                         |
|  ARCHITECTURE:                                                          |
|  - Fleet of WebSocket servers (100s of machines)                        |
|  - Each server handles ~500K connections                                |
|  - L4 load balancer (HAProxy) for initial connection routing            |
|  - Sticky sessions: user reconnects to same server when possible        |
|                                                                         |
|  CONNECTION REGISTRY:                                                   |
|  Mapping of user_id -> which WS server they're connected to             |
|  Stored in Redis for fast lookups:                                      |
|                                                                         |
|  conn:user_123 = {                                                      |
|    server: "ws-server-42",                                              |
|    connected_at: 1708000001,                                            |
|    device: "iphone",                                                    |
|    last_heartbeat: 1708000500                                           |
|  }                                                                      |
|                                                                         |
|  MULTI-DEVICE SUPPORT:                                                  |
|  conn:user_123:iphone = { server: "ws-42", ... }                        |
|  conn:user_123:web    = { server: "ws-17", ... }                        |
|  - Message delivered to ALL active devices                              |
|  - Read receipt from any device marks as read on all devices            |
|                                                                         |
|  FAILOVER:                                                              |
|  - If WS server crashes, clients detect via missed heartbeat            |
|  - Client reconnects (to potentially different server)                  |
|  - New server pulls undelivered messages from message store             |
|  - Connection registry updated automatically                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5: MESSAGE FLOW (THE CORE)

### 1:1 MESSAGE FLOW

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ONE-TO-ONE MESSAGE DELIVERY:                                            |
|                                                                          |
|  Alice sends "Hello" to Bob                                              |
|                                                                          |
|  Alice's       WS Server     Chat        Message     WS Server   Bob's   |
|  Phone           #3         Service       Store        #7        Phone   |
|    |               |           |            |           |            |   |
|    |--msg: Hello-->|           |            |           |            |   |
|    |               |--route--->|            |           |            |   |
|    |               |           |--store---->|           |            |   |
|    |               |           |<--ack------|           |            |   |
|    |<--sent ack----|<--ack-----|            |           |            |   |
|    |               |           |                       |             |   |
|    |               |           |---lookup Bob's conn-->|             |   |
|    |               |           |   (from Redis)        |             |   |
|    |               |           |                       |             |   |
|    |               |           |---forward msg-------->|             |   |
|    |               |           |                       |--deliver->  |   |
|    |               |           |                       |<-del.ack----|   |
|    |               |           |<--delivered ack-------|             |   |
|    |<--delivered----|<--status--|            |           |           |   |
|    |               |           |            |           |            |   |
|    |               |           |            |           |   (Bob     |   |
|    |               |           |            |           |   reads)   |   |
|    |               |           |                       |<-read ack---|   |
|    |               |           |<--read receipt--------|             |   |
|    |<--read---------|<--status--|            |           |           |   |
|                                                                          |
|  MESSAGE STATES:                                                         |
|  1. SENT: Server received and stored the message                         |
|  2. DELIVERED: Message reached recipient's device                        |
|  3. READ: Recipient opened and viewed the message                        |
|                                                                          |
+--------------------------------------------------------------------------+
```

### GROUP MESSAGE FLOW

```
+--------------------------------------------------------------------------+
|                                                                          |
|  GROUP MESSAGE DELIVERY:                                                 |
|                                                                          |
|  Alice sends "Hi team" to a group with Bob, Carol, Dave                  |
|                                                                          |
|  Alice       Chat          Message     Group         WS Gateway          |
|  Phone      Service        Store      Service        (multiple)          |
|    |           |              |           |              |               |
|    |--msg----->|              |           |              |               |
|    |           |--store------>|           |              |               |
|    |           |<--ack--------|           |              |               |
|    |<--sent----|              |           |              |               |
|    |           |              |           |              |               |
|    |           |--get members----------->|              |                |
|    |           |<--[Bob,Carol,Dave]-------|              |               |
|    |           |                                        |                |
|    |           |---For each member:                     |                |
|    |           |   lookup connection & deliver--------->|                |
|    |           |                                        |---> Bob        |
|    |           |                                        |---> Carol      |
|    |           |                                        |--X  Dave       |
|    |           |                                        |   (offline)    |
|    |           |                                        |                |
|    |           |<--delivered: Bob, Carol-----------------|               |
|    |           |                                        |                |
|    |           |---queue for Dave (offline delivery)     |               |
|    |           |---push notification to Dave's phone     |               |
|                                                                          |
|  OPTIMIZATIONS FOR LARGE GROUPS:                                         |
|  - Fan-out done in parallel across multiple threads                      |
|  - Members on same WS server batched into single dispatch                |
|  - Rate limit for very large groups (send in waves)                      |
|                                                                          |
+--------------------------------------------------------------------------+
```

### OFFLINE MESSAGE HANDLING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OFFLINE MESSAGE QUEUE:                                                 |
|                                                                         |
|  When recipient is offline:                                             |
|                                                                         |
|  1. Message is stored in Message Store (always happens)                 |
|  2. Chat Service detects no active connection for recipient             |
|  3. Message added to offline queue (Redis sorted set)                   |
|     Key: offline:{user_id}                                              |
|     Score: message timestamp                                            |
|     Value: message_id                                                   |
|                                                                         |
|  4. Push notification sent via APNs (iOS) / FCM (Android)               |
|                                                                         |
|  When user comes back online:                                           |
|  1. WebSocket connection established                                    |
|  2. Server checks offline queue for pending messages                    |
|  3. Deliver all pending messages in order                               |
|  4. Client ACKs each message                                            |
|  5. Remove from offline queue after ACK                                 |
|                                                                         |
|  PUSH NOTIFICATION CONTENT:                                             |
|  - Sender name + preview text                                           |
|  - Badge count (total unread messages)                                  |
|  - Encrypted: notification server only sees metadata                    |
|  - Collapsed: "3 new messages from Alice" (not 3 separate)              |
|                                                                         |
|  OFFLINE QUEUE SIZING:                                                  |
|  - Max messages in queue: 10,000 per user                               |
|  - Queue TTL: 30 days (messages in DB persist forever)                  |
|  - At reconnect, fetch last sync_timestamp, get newer messages          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DLQ AND FAILURE HANDLING IN CHAT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DLQ (DEAD LETTER QUEUE) IN CHAT SYSTEMS                                |
|  =========================================                              |
|                                                                         |
|  Chat has TWO delivery paths. Failures handled differently:             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  PATH 1: REAL-TIME (WebSocket)                                    |  |
|  |  User A --> WS Server --> Chat Service --> lookup conn registry    | |
|  |                                        --> WS Server --> User B   |  |
|  |                                                                   |  |
|  |  Failure? --> Offline Queue (Redis) + Push Notification           |  |
|  |  NOT a DLQ. Just "deliver later when user reconnects."            |  |
|  |                                                                   |  |
|  |  ---------------------------------------------------------------  |  |
|  |                                                                   |  |
|  |  PATH 2: ASYNC PROCESSING (Kafka consumers)                      |   |
|  |  Message --> Kafka "messages" topic                               |  |
|  |              |                                                    |  |
|  |              +--> Store in Cassandra                              |  |
|  |              +--> Update unread counters                          |  |
|  |              +--> Push notification (APNs/FCM)                    |  |
|  |              +--> Search indexing (Elasticsearch)                 |  |
|  |              +--> Analytics / audit log                           |  |
|  |                                                                   |  |
|  |  Any consumer fails after 3 retries? --> DLQ topic                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  WHAT GOES TO DLQ (async failures):                                     |
|                                                                         |
|  1. PUSH NOTIFICATION FAILURE                                           |
|     APNs/FCM returns error (invalid token, rate limited)                |
|     Consumer retries 3x with backoff -> still fails -> DLQ              |
|     DLQ action: check device token validity, retry or drop              |
|                                                                         |
|  2. CASSANDRA WRITE FAILURE                                             |
|     Node down, timeout, write consistency not met                       |
|     Critical: message could be lost if not retried!                     |
|     DLQ action: high-priority alert, replay immediately                 |
|                                                                         |
|  3. SEARCH INDEX FAILURE                                                |
|     Elasticsearch overloaded or cluster rebalancing                     |
|     Non-critical: chat works fine, search is eventually consistent      |
|     DLQ action: batch replay after ES is healthy                        |
|                                                                         |
|  4. UNREAD COUNTER FAILURE                                              |
|     Redis counter update failed (rare, network blip)                    |
|     DLQ action: recalculate counter from Cassandra on replay            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  WHAT DOES NOT GO TO DLQ:                                               |
|                                                                         |
|  * WebSocket delivery failure -> Offline Queue (not DLQ)                |
|  * User is offline -> Offline Queue + Push Notification                 |
|  * Message dedup rejection -> expected, just skip                       |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  DLQ STRUCTURE:                                                         |
|                                                                         |
|  Topic: chat.messages.dlq                                               |
|                                                                         |
|  Each DLQ message contains:                                             |
|  {                                                                      |
|    "original_topic": "chat.messages",                                   |
|    "original_offset": 12345,                                            |
|    "failure_reason": "APNS_INVALID_TOKEN",                              |
|    "consumer_group": "push-notification-service",                       |
|    "retry_count": 3,                                                    |
|    "first_failed_at": "2025-02-22T10:00:00Z",                           |
|    "last_failed_at": "2025-02-22T10:05:00Z",                            |
|    "original_payload": { ... message event ... }                        |
|  }                                                                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  OFFLINE QUEUE vs DLQ — KEY DIFFERENCE:                                 |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |               | Offline Queue         | DLQ                       |  |
|  |---------------|-----------------------|---------------------------|  |
|  | Purpose       | User not connected    | Backend processing failed |  |
|  | Storage       | Redis sorted set      | Kafka DLQ topic           |  |
|  | Trigger       | No WS connection      | Consumer error after      |  |
|  |               | for recipient         | max retries               |  |
|  | Consumed when | User comes online     | After root cause fix      |  |
|  | Data          | Message IDs (small)   | Full event + error info   |  |
|  | Priority      | Auto (on reconnect)   | Manual / automated replay |  |
|  | Example       | "Deliver these 5 msgs | "Push to APNs failed 3x   |  |
|  |               | when Alice reconnects"| for msg-789, token invalid|  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  DLQ HANDLING STRATEGY:                                                 |
|                                                                         |
|  CRITICAL (message storage failed):                                     |
|    --> Alert immediately. Auto-retry every 30s.                         |
|    --> If still failing: page on-call engineer.                         |
|    --> Messages are in Kafka (retained), not truly lost.                |
|                                                                         |
|  IMPORTANT (push notification, unread counter):                         |
|    --> Auto-retry with exponential backoff (1m, 5m, 30m).               |
|    --> After 24h: move to permanent DLQ for investigation.              |
|    --> Invalid device tokens: clean up from user's device list.         |
|                                                                         |
|  NON-CRITICAL (search index, analytics):                                |
|    --> Batch replay during low-traffic hours.                           |
|    --> Acceptable to be hours behind.                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6: MESSAGE STORAGE

### DATABASE CHOICE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY NOT A RELATIONAL DATABASE FOR MESSAGES?                            |
|                                                                         |
|  Messages have these properties:                                        |
|  - Write-heavy (100B writes/day vs reads mostly for recent)             |
|  - Append-only (messages are never updated)                             |
|  - Time-series access pattern (read recent messages mostly)             |
|  - No complex joins needed                                              |
|  - Need to scale to petabytes                                           |
|                                                                         |
|  OPTION 1: CASSANDRA (Chosen for 1:1 chats)                             |
|  + Write-optimized (LSM tree)                                           |
|  + Linear scalability (add nodes)                                       |
|  + Time-series friendly (clustering key = timestamp)                    |
|  + No single point of failure                                           |
|  - Eventually consistent (tunable, use LOCAL_QUORUM)                    |
|                                                                         |
|  OPTION 2: HBASE                                                        |
|  + Great for sequential reads (sorted by row key)                       |
|  + Strong consistency per row                                           |
|  + Built-in versioning                                                  |
|  - Depends on HDFS/Zookeeper (operational complexity)                   |
|                                                                         |
|  OPTION 3: MYSQL + SHARDING (Acceptable for smaller scale)              |
|  + Familiar, well-understood                                            |
|  + Strong consistency                                                   |
|  - Sharding complexity                                                  |
|  - Not optimized for append-only workloads                              |
|                                                                         |
|  DECISION: Cassandra for message storage, MySQL for user/group          |
|  metadata, Redis for caches and online state.                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CASSANDRA DATA MODEL

```
+--------------------------------------------------------------------------+
|                                                                          |
|  CASSANDRA TABLE: messages_by_conversation                               |
|                                                                          |
|  CREATE TABLE messages_by_conversation (                                 |
|    conversation_id  UUID,      -- Partition key                          |
|    message_id       TIMEUUID,  -- Clustering key (time-ordered)          |
|    sender_id        BIGINT,                                              |
|    content          TEXT,                                                |
|    content_type     TEXT,      -- text, image, video, file               |
|    media_url        TEXT,                                                |
|    reply_to_id      TIMEUUID,                                            |
|    is_deleted       BOOLEAN,                                             |
|    created_at       TIMESTAMP,                                           |
|    PRIMARY KEY (conversation_id, message_id)                             |
|  ) WITH CLUSTERING ORDER BY (message_id DESC);                           |
|                                                                          |
|  ACCESS PATTERNS:                                                        |
|  1. Get recent messages for a conversation:                              |
|     SELECT * FROM messages_by_conversation                               |
|     WHERE conversation_id = ?                                            |
|     LIMIT 50;  (returns latest 50 due to DESC ordering)                  |
|                                                                          |
|  2. Paginate older messages:                                             |
|     SELECT * FROM messages_by_conversation                               |
|     WHERE conversation_id = ?                                            |
|     AND message_id < ?  (cursor)                                         |
|     LIMIT 50;                                                            |
|                                                                          |
|  CONVERSATION ID GENERATION:                                             |
|  - 1:1 chat: deterministic from sorted user IDs                          |
|    conv_id = hash(min(user_a, user_b) + ":" + max(user_a, user_b))       |
|  - Group chat: randomly generated UUID at group creation                 |
|                                                                          |
+--------------------------------------------------------------------------+
```

### PARTITIONING STRATEGY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CASSANDRA PARTITIONING:                                                |
|                                                                         |
|  PARTITION KEY: conversation_id                                         |
|  - All messages for a conversation on same partition                    |
|  - Single partition read for "load recent messages"                     |
|  - Efficient range scans within a conversation                          |
|                                                                         |
|  PROBLEM: HOT PARTITIONS                                                |
|  - Very active group with millions of messages                          |
|  - Single partition can grow too large (>100MB)                         |
|                                                                         |
|  SOLUTION: TIME-BUCKETED PARTITIONS                                     |
|  PRIMARY KEY ((conversation_id, bucket), message_id)                    |
|                                                                         |
|  bucket = year_month (e.g., "2024_01")                                  |
|                                                                         |
|  - Recent messages: query current month's bucket                        |
|  - Older messages: query previous month's buckets                       |
|  - Each partition stays manageable size                                 |
|  - Slight complexity: may need to query 2 buckets at boundary           |
|                                                                         |
|  RETENTION POLICY:                                                      |
|  - Hot data (last 30 days): SSD-backed Cassandra                        |
|  - Warm data (30 days - 1 year): HDD-backed Cassandra                   |
|  - Cold data (>1 year): Compressed in S3 / archival storage             |
|  - Tiered storage significantly reduces cost                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7: MESSAGE ORDERING AND CONSISTENCY

### THE ORDERING PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY IS MESSAGE ORDERING HARD?                                          |
|                                                                         |
|  SCENARIO:                                                              |
|  Alice and Bob both send messages at "the same time"                    |
|                                                                         |
|  Alice sends "Let's meet at 5" at 12:00:00.000 (her clock)              |
|  Bob sends "How about 6?" at 12:00:00.000 (his clock)                   |
|                                                                         |
|  But their clocks may differ by milliseconds (clock skew).              |
|  Different servers receive messages at different times.                 |
|  Network delays vary. Which message came first?                         |
|                                                                         |
|  REQUIREMENT:                                                           |
|  - All participants must see messages in the SAME order                 |
|  - Causal ordering: replies must appear after the original              |
|  - Total ordering within a conversation                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ORDERING SOLUTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SOLUTION 1: SERVER-ASSIGNED TIMESTAMPS                                 |
|  - Chat server assigns a monotonic timestamp on receipt                 |
|  - Simple and works when single server handles a conversation           |
|  - Problem: if conversation spans servers, clocks may differ            |
|  - Mitigation: use NTP sync + sequence number as tiebreaker             |
|                                                                         |
|  SOLUTION 2: SEQUENCE NUMBERS PER CONVERSATION                          |
|  - Each conversation has an auto-incrementing sequence counter          |
|  - Stored in Redis: INCR conv_seq:{conversation_id}                     |
|  - Guarantees total ordering within a conversation                      |
|  - Problem: Redis becomes single point of contention                    |
|  - Mitigation: partition conversations across Redis nodes               |
|                                                                         |
|  SOLUTION 3: LAMPORT TIMESTAMPS                                         |
|  - Each message carries a logical clock value                           |
|  - clock = max(local_clock, received_clock) + 1                         |
|  - Guarantees causal ordering (if A caused B, A < B)                    |
|  - Does NOT guarantee total ordering for concurrent messages            |
|  - Use (lamport_timestamp, server_id) for total order                   |
|                                                                         |
|  SOLUTION 4: SNOWFLAKE-LIKE IDS (Recommended)                           |
|  - Generate time-ordered unique IDs                                     |
|  - timestamp (41 bits) + machine_id (10 bits) + sequence (12 bits)      |
|  - Roughly time-ordered (within ms), globally unique                    |
|  - No coordination needed between servers                               |
|  - Combined with per-conversation sequence for strict ordering          |
|                                                                         |
|  CHOSEN APPROACH:                                                       |
|  - Snowflake IDs for global message identity                            |
|  - Per-conversation sequence number for display ordering                |
|  - Sequence assigned by the Chat Service (single writer per conv)       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### VECTOR CLOCKS (FOR ADVANCED SCENARIOS)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  VECTOR CLOCKS (Used in distributed editing / conflict resolution):     |
|                                                                         |
|  Each participant maintains a vector of counters:                       |
|  [Alice: 3, Bob: 2, Carol: 1]                                           |
|                                                                         |
|  When Alice sends message:                                              |
|  - Increment own counter: [Alice: 4, Bob: 2, Carol: 1]                  |
|  - Attach vector to message                                             |
|                                                                         |
|  When Bob receives Alice's message:                                     |
|  - Merge: max each component                                            |
|  - Bob's vector becomes: [Alice: 4, Bob: 2, Carol: 1]                   |
|  - When Bob sends: [Alice: 4, Bob: 3, Carol: 1]                         |
|                                                                         |
|  COMPARING VECTORS:                                                     |
|  - V1 < V2 if all components of V1 <= V2 and at least one is <          |
|  - V1 || V2 (concurrent) if neither V1 < V2 nor V2 < V1                 |
|                                                                         |
|  PRACTICAL USAGE IN CHAT:                                               |
|  - Overkill for simple message ordering                                 |
|  - Useful for: offline editing, conflict resolution, sync protocols     |
|  - WhatsApp uses simpler approach: server-assigned sequence numbers     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8: PRESENCE / ONLINE STATUS SERVICE

### PRESENCE ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PRESENCE SERVICE:                                                      |
|                                                                         |
|  Tracks who is online, offline, or "last seen at X".                    |
|                                                                         |
|  STORAGE: Redis Hash                                                    |
|  presence:{user_id} = {                                                 |
|    status: "online" | "offline",                                        |
|    last_seen: 1708000500,                                               |
|    device: "iphone"                                                     |
|  }                                                                      |
|  TTL: 5 minutes (auto-expire if no heartbeat)                           |
|                                                                         |
|  HOW IT WORKS:                                                          |
|                                                                         |
|  1. USER COMES ONLINE:                                                  |
|     - WebSocket connection established                                  |
|     - Set status = "online" in Redis                                    |
|     - Notify friends via their WebSocket connections                    |
|                                                                         |
|  2. HEARTBEAT (every 30 seconds):                                       |
|     - Client sends ping over WebSocket                                  |
|     - Server refreshes TTL on presence key                              |
|     - If 3 consecutive heartbeats missed -> mark offline                |
|                                                                         |
|  3. USER GOES OFFLINE:                                                  |
|     - Explicit: client sends disconnect message                         |
|     - Implicit: heartbeat timeout (90 seconds)                          |
|     - Set status = "offline", last_seen = now                           |
|     - Notify friends                                                    |
|                                                                         |
|  SCALING CHALLENGE:                                                     |
|  - User with 500 friends comes online                                   |
|  - Must notify 500 friends -> 500 WebSocket pushes                      |
|  - 100M online/offline events per day x 200 avg friends = 20B pushes    |
|                                                                         |
|  OPTIMIZATION:                                                          |
|  - Only notify friends who have the chat app in foreground              |
|  - Batch presence updates (aggregate over 5 seconds)                    |
|  - For users with 1000+ friends: lazy presence (query on demand)        |
|  - Only push presence for users in active conversations                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TYPING INDICATORS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TYPING INDICATORS:                                                     |
|                                                                         |
|  "Alice is typing..." appears when Alice starts typing.                 |
|                                                                         |
|  IMPLEMENTATION:                                                        |
|  1. Client detects keypress -> send typing_start event                  |
|  2. Server forwards to conversation participants                        |
|  3. Client sends typing_stop after 3 seconds of no input                |
|  4. Recipient shows indicator for 3 seconds (auto-dismiss)              |
|                                                                         |
|  OPTIMIZATION:                                                          |
|  - Throttle: send typing event at most once per 3 seconds               |
|  - Don't persist typing events (purely ephemeral)                       |
|  - Don't send typing events in large groups (>20 members)               |
|  - UDP-like delivery: best effort, no ACK needed                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: END-TO-END ENCRYPTION

### E2E ENCRYPTION OVERVIEW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  END-TO-END ENCRYPTION (Signal Protocol):                               |
|                                                                         |
|  The server NEVER sees plaintext messages.                              |
|  Only sender and recipient can decrypt.                                 |
|                                                                         |
|  KEY CONCEPTS:                                                          |
|                                                                         |
|  1. KEY PAIRS                                                           |
|     - Each device generates a public/private key pair                   |
|     - Public key uploaded to Key Server                                 |
|     - Private key NEVER leaves the device                               |
|                                                                         |
|  2. KEY EXCHANGE (X3DH - Extended Triple Diffie-Hellman)                |
|     Alice wants to message Bob (first time):                            |
|     a. Alice fetches Bob's public key bundle from server                |
|     b. Alice computes shared secret using ECDH                          |
|     c. Alice encrypts message with shared secret                        |
|     d. Bob receives and computes same shared secret                     |
|     e. Bob decrypts message                                             |
|                                                                         |
|  3. DOUBLE RATCHET ALGORITHM                                            |
|     - New encryption key for EVERY message                              |
|     - Forward secrecy: compromising current key doesn't                 |
|       reveal past messages                                              |
|     - Future secrecy: compromising current key doesn't                  |
|       reveal future messages (after next ratchet step)                  |
|                                                                         |
|  SERVER'S ROLE:                                                         |
|  - Store and forward encrypted blobs                                    |
|  - Store public keys for key exchange                                   |
|  - Cannot read message content                                          |
|  - Can see: who messages whom, when, message size (metadata)            |
|                                                                         |
|  GROUP ENCRYPTION:                                                      |
|  - Sender encrypts once with group key                                  |
|  - Group key distributed via pairwise encrypted channels                |
|  - Key rotated when members join/leave                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10: DATABASE SCHEMA (MYSQL - METADATA)

### CORE METADATA TABLES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TABLE: users                                                           |
|  +------------------+-------------+--------------------------------+    |
|  | Column           | Type        | Notes                          |    |
|  +------------------+-------------+--------------------------------+    |
|  | user_id          | BIGINT (PK) | Snowflake ID                   |    |
|  | phone_number     | VARCHAR(20) | Unique, indexed (login key)    |    |
|  | display_name     | VARCHAR(100)|                                |    |
|  | profile_pic_url  | VARCHAR(500)| CDN URL                        |    |
|  | status_message   | VARCHAR(200)| "Hey there! I'm using Chat"    |    |
|  | last_seen        | TIMESTAMP   |                                |    |
|  | privacy_settings | JSON        | last_seen, profile pic, etc.   |    |
|  | created_at       | TIMESTAMP   |                                |    |
|  +------------------+-------------+--------------------------------+    |
|                                                                         |
|  TABLE: conversations                                                   |
|  +------------------+-------------+--------------------------------+    |
|  | Column           | Type        | Notes                          |    |
|  +------------------+-------------+--------------------------------+    |
|  | conversation_id  | UUID (PK)   |                                |    |
|  | type             | ENUM        | DIRECT, GROUP                  |    |
|  | name             | VARCHAR(100)| NULL for direct chats          |    |
|  | avatar_url       | VARCHAR(500)| Group avatar                   |    |
|  | created_by       | BIGINT (FK) |                                |    |
|  | created_at       | TIMESTAMP   |                                |    |
|  | updated_at       | TIMESTAMP   |                                |    |
|  +------------------+-------------+--------------------------------+    |
|                                                                         |
|  TABLE: conversation_members                                            |
|  +------------------+-------------+--------------------------------+    |
|  | Column           | Type        | Notes                          |    |
|  +------------------+-------------+--------------------------------+    |
|  | conversation_id  | UUID (FK)   |                                |    |
|  | user_id          | BIGINT (FK) |                                |    |
|  | role             | ENUM        | MEMBER, ADMIN, OWNER           |    |
|  | muted_until      | TIMESTAMP   | NULL if not muted              |    |
|  | last_read_msg_id | TIMEUUID    | For unread count calculation   |    |
|  | joined_at        | TIMESTAMP   |                                |    |
|  +------------------+-------------+--------------------------------+    |
|  Primary key: (conversation_id, user_id)                                |
|  Index: (user_id) for "list my conversations"                           |
|                                                                         |
|  TABLE: user_conversations (denormalized for fast listing)              |
|  +------------------+-------------+--------------------------------+    |
|  | Column           | Type        | Notes                          |    |
|  +------------------+-------------+--------------------------------+    |
|  | user_id          | BIGINT      | Partition key                  |    |
|  | conversation_id  | UUID        |                                |    |
|  | last_message_at  | TIMESTAMP   | For sorting conversations      |    |
|  | last_message_pre | VARCHAR(100)| Preview text                   |    |
|  | unread_count     | INT         |                                |    |
|  +------------------+-------------+--------------------------------+    |
|  Primary key: (user_id, last_message_at DESC)                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11: API DESIGN

### REST + WEBSOCKET API

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HTTP APIs (for non-real-time operations):                              |
|                                                                         |
|  POST /api/v1/auth/login                                                |
|  Body: { phone_number, verification_code }                              |
|  Response: { token, user_id }                                           |
|                                                                         |
|  GET /api/v1/conversations?cursor=...&limit=20                          |
|  Response: { conversations: [{id, name, last_msg, unread}, ...] }       |
|                                                                         |
|  GET /api/v1/conversations/{conv_id}/messages?cursor=...&limit=50       |
|  Response: { messages: [...], next_cursor, has_more }                   |
|                                                                         |
|  POST /api/v1/conversations                                             |
|  Body: { type: "group", name: "Team", member_ids: [...] }               |
|  Response: { conversation_id }                                          |
|                                                                         |
|  POST /api/v1/media/upload                                              |
|  Response: { upload_url, media_id }                                     |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  WEBSOCKET MESSAGES (for real-time operations):                         |
|                                                                         |
|  CLIENT -> SERVER:                                                      |
|  {                                                                      |
|    "type": "send_message",                                              |
|    "conversation_id": "uuid",                                           |
|    "client_msg_id": "uuid",   // For dedup and ACK matching             |
|    "content": "Hello!",                                                 |
|    "content_type": "text",                                              |
|    "reply_to": null                                                     |
|  }                                                                      |
|                                                                         |
|  SERVER -> CLIENT:                                                      |
|  {                                                                      |
|    "type": "new_message",                                               |
|    "conversation_id": "uuid",                                           |
|    "message_id": "timeuuid",                                            |
|    "sender_id": 12345,                                                  |
|    "content": "Hello!",                                                 |
|    "created_at": "2024-02-15T12:00:00Z"                                 |
|  }                                                                      |
|                                                                         |
|  ACK Messages:                                                          |
|  { "type": "msg_ack", "client_msg_id": "uuid", "status": "sent" }       |
|  { "type": "delivery_receipt", "message_id": "...", "user_id": ... }    |
|  { "type": "read_receipt", "conversation_id": "...", "up_to": "..." }   |
|                                                                         |
|  Presence:                                                              |
|  { "type": "typing_start", "conversation_id": "uuid" }                  |
|  { "type": "typing_stop", "conversation_id": "uuid" }                   |
|  { "type": "presence_update", "user_id": ..., "status": "online" }      |
|                                                                         |
|  DEDUPLICATION:                                                         |
|  - client_msg_id (UUID generated by client) ensures idempotency         |
|  - If server receives duplicate client_msg_id, return existing ACK      |
|  - Server maintains recent msg IDs in Redis (TTL: 24 hours)             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12: SCALING AND RELIABILITY

### HORIZONTAL SCALING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALING EACH COMPONENT:                                                |
|                                                                         |
|  WEBSOCKET GATEWAY:                                                     |
|  - 500K connections per server                                          |
|  - 50M connections / 500K = 100 servers                                 |
|  - L4 load balancer (connection-level, not request-level)               |
|  - Scale by adding more gateway servers                                 |
|                                                                         |
|  CHAT SERVICE:                                                          |
|  - Stateless: scale horizontally behind load balancer                   |
|  - Partition by conversation_id for cache locality                      |
|  - 50+ instances                                                        |
|                                                                         |
|  MESSAGE STORE (Cassandra):                                             |
|  - 100+ node cluster                                                    |
|  - Replication factor: 3                                                |
|  - Consistency: LOCAL_QUORUM for writes, LOCAL_ONE for reads            |
|  - Add nodes to increase capacity (linear scaling)                      |
|                                                                         |
|  REDIS (Presence + Caches):                                             |
|  - Redis Cluster: 30+ shards                                            |
|  - Presence data: ~100 GB                                               |
|  - Connection registry: ~10 GB                                          |
|  - Offline queues: ~50 GB                                               |
|                                                                         |
|  MEDIA STORAGE:                                                         |
|  - S3 / blob store (virtually unlimited)                                |
|  - CDN for delivery (CloudFront / Akamai)                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### RELIABILITY AND FAULT TOLERANCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FAILURE SCENARIOS AND MITIGATIONS:                                     |
|                                                                         |
|  1. WEBSOCKET SERVER CRASH                                              |
|     - Clients detect via missed heartbeat (30-90 sec)                   |
|     - Auto-reconnect to different server                                |
|     - Fetch undelivered messages from message store                     |
|     - Connection registry auto-expires stale entries (TTL)              |
|                                                                         |
|  2. CHAT SERVICE CRASH                                                  |
|     - Messages already stored in Cassandra are safe                     |
|     - In-flight messages: client retries with same client_msg_id        |
|     - Dedup ensures no double delivery                                  |
|                                                                         |
|  3. CASSANDRA NODE FAILURE                                              |
|     - Replication factor 3: 2 replicas still serve reads/writes         |
|     - Hinted handoff: writes queued for failed node                     |
|     - Anti-entropy repair after node recovery                           |
|                                                                         |
|  4. REDIS FAILURE                                                       |
|     - Presence: gracefully degrade (show "last seen" only)              |
|     - Connection registry: rebuild from WS server heartbeats            |
|     - Offline queue: messages still in Cassandra as backup              |
|                                                                         |
|  5. NETWORK PARTITION                                                   |
|     - Clients queue messages locally                                    |
|     - Sync when connectivity restored                                   |
|     - Conflict resolution via message timestamps                        |
|                                                                         |
|  6. ENTIRE REGION FAILURE                                               |
|     - DNS failover to secondary region                                  |
|     - Cassandra multi-DC replication                                    |
|     - Some messages may be delayed but none lost                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MULTI-REGION DEPLOYMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MULTI-REGION ARCHITECTURE:                                             |
|                                                                         |
|  +--------------------+          +--------------------+                 |
|  |   US-EAST          |          |   ASIA-PACIFIC     |                 |
|  |                    |          |                    |                 |
|  | +------+ +-------+|  Async   | +------+ +-------+|                   |
|  | |WS    | |Chat   ||  Repli-  | |WS    | |Chat   ||                   |
|  | |Gate- | |Service||<-------->| |Gate- | |Service||                   |
|  | |way   | |       ||  cation  | |way   | |       ||                   |
|  | +------+ +-------+|          | +------+ +-------+|                   |
|  |                    |          |                    |                 |
|  | +-------+ +------+|          | +-------+ +------+|                   |
|  | |Cassan-| |Redis ||          | |Cassan-| |Redis ||                   |
|  | |dra DC1| |      ||          | |dra DC2| |      ||                   |
|  | +-------+ +------+|          | +-------+ +------+|                   |
|  +--------------------+          +--------------------+                 |
|                                                                         |
|  CROSS-REGION MESSAGING:                                                |
|  - Alice (US) messages Bob (Asia)                                       |
|  - Message stored in US Cassandra DC                                    |
|  - Async replicated to Asia Cassandra DC                                |
|  - Chat Service in Asia detects Bob is local                            |
|  - Delivers via Asia WS Gateway                                         |
|  - Total latency: ~200ms (cross-region network)                         |
|                                                                         |
|  OPTIMIZATION: Route messages directly between regions                  |
|  via inter-region message bus (skip DB replication path)                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 13: INTERVIEW Q&A

### QUESTION 1: WHY WEBSOCKETS OVER LONG POLLING?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: Why choose WebSockets over long polling for a chat system?          |
|                                                                         |
|  A: WebSockets provide full-duplex communication over a single          |
|  persistent TCP connection, which is ideal for chat because:            |
|                                                                         |
|  1. LATENCY: Messages are pushed instantly (no polling delay)           |
|  2. EFFICIENCY: No repeated HTTP handshake overhead                     |
|  3. BI-DIRECTIONAL: Both sending and receiving on same connection       |
|  4. LOWER SERVER LOAD: One connection vs thousands of HTTP requests     |
|                                                                         |
|  Long polling drawbacks for chat:                                       |
|  - Each response requires a new HTTP request (header overhead)          |
|  - Higher latency (time to establish new connection)                    |
|  - Server must hold many pending HTTP connections                       |
|  - Not truly bi-directional (client initiates all requests)             |
|                                                                         |
|  Long polling IS acceptable as a fallback when WebSockets are           |
|  blocked (corporate firewalls, older browsers).                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 2: HOW TO ENSURE MESSAGE ORDERING?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How do you guarantee message ordering in a distributed system?      |
|                                                                         |
|  A: We use a per-conversation sequence number:                          |
|                                                                         |
|  1. Each conversation has a sequence counter in Redis                   |
|  2. When a message arrives, atomically increment and assign:            |
|     seq = INCR conv_seq:{conversation_id}                               |
|  3. Messages are displayed ordered by sequence number                   |
|  4. Client detects gaps (e.g., received seq 5 then 7) and               |
|     requests missing messages                                           |
|                                                                         |
|  WHY NOT JUST TIMESTAMPS?                                               |
|  - Clocks on different servers can differ (clock skew)                  |
|  - Two messages at "same" millisecond need tiebreaker                   |
|  - NTP sync is typically within 1-10ms but not guaranteed               |
|                                                                         |
|  TRADE-OFF: The Redis INCR is a single point of serialization per       |
|  conversation. This is fine because:                                    |
|  - Messages in one conversation are naturally sequential                |
|  - Even the busiest group sends maybe 100 msgs/sec                      |
|  - Redis INCR handles 100K+ ops/sec per key                             |
|  - Different conversations hit different Redis shards                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 3: HOW TO HANDLE GROUP MESSAGE FAN-OUT?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How do you efficiently deliver messages to a large group?           |
|                                                                         |
|  A: Fan-out strategy depends on group size:                             |
|                                                                         |
|  SMALL GROUPS (<100 members):                                           |
|  - Direct fan-out: send to each member's WS connection                  |
|  - Batch members on same WS server into single dispatch                 |
|  - All done in Chat Service synchronously                               |
|                                                                         |
|  MEDIUM GROUPS (100-1000 members):                                      |
|  - Async fan-out via message queue (Kafka)                              |
|  - Multiple fan-out workers process in parallel                         |
|  - Don't block the sender waiting for all deliveries                    |
|                                                                         |
|  VERY LARGE GROUPS (1000+ members, like channels):                      |
|  - Use pub/sub model instead of direct delivery                         |
|  - Group has a "channel" in Redis Pub/Sub                               |
|  - WS servers subscribe to channels for their connected users           |
|  - Single publish, multiple WS servers receive and distribute           |
|                                                                         |
|  Note: WhatsApp caps groups at 1024 members. Slack channels             |
|  can be larger but use a different delivery model (pull on open).       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 4: HOW DOES READ RECEIPT WORK AT SCALE?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How do read receipts work, especially in groups?                    |
|                                                                         |
|  A: Read receipts are implemented differently for 1:1 vs groups:        |
|                                                                         |
|  1:1 CHAT:                                                              |
|  - When Bob opens conversation with Alice:                              |
|    a. Client sends: read_receipt(conversation_id, last_msg_id)          |
|    b. Server updates last_read_msg_id in conversation_members           |
|    c. Server forwards receipt to Alice's device                         |
|    d. All messages up to last_msg_id marked as "read"                   |
|                                                                         |
|  GROUP CHAT:                                                            |
|  - Same mechanism but DON'T fan-out read receipts to all members        |
|  - Instead, store read position per member in DB                        |
|  - When someone taps "message info", query read positions               |
|  - This avoids N^2 messages (N members x N read receipts)               |
|                                                                         |
|  OPTIMIZATION:                                                          |
|  - Batch read receipts: send one receipt for "read up to msg X"         |
|  - Don't send receipt for every individual message                      |
|  - Debounce: wait 1 second after last scroll before sending             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 5: HOW TO HANDLE MESSAGE DEDUPLICATION?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How do you prevent duplicate messages?                              |
|                                                                         |
|  A: Duplicates can occur when:                                          |
|  - Client retries after network timeout (didn't receive ACK)            |
|  - Server processes message but ACK is lost in transit                  |
|  - Network reconnection replays buffered messages                       |
|                                                                         |
|  SOLUTION: Client-generated idempotency key                             |
|                                                                         |
|  1. Client generates UUID (client_msg_id) for each message              |
|  2. Sends message with client_msg_id                                    |
|  3. Server checks Redis: EXISTS dedup:{client_msg_id}                   |
|     - If exists: return previous ACK (duplicate, skip processing)       |
|     - If not: process message, SET dedup:{client_msg_id} with TTL       |
|  4. TTL: 24 hours (long enough for any retry to be caught)              |
|                                                                         |
|  WHY CLIENT-GENERATED ID?                                               |
|  - Client can retry safely without knowing if server processed it       |
|  - Server doesn't need to track "was this already sent?"                |
|  - Works even if client loses connection and reconnects to              |
|    a different server                                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 6: HOW TO IMPLEMENT UNREAD COUNT?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How do you efficiently track unread message counts?                 |
|                                                                         |
|  A: Each conversation_member has a last_read_msg_id field:              |
|                                                                         |
|  UNREAD COUNT CALCULATION:                                              |
|  unread_count = count of messages in conversation                       |
|                 WHERE message_id > last_read_msg_id                     |
|                                                                         |
|  BUT: Counting every time is expensive at scale.                        |
|                                                                         |
|  OPTIMIZATION:                                                          |
|  1. Maintain denormalized unread_count per user per conversation        |
|  2. When new message arrives: INCREMENT unread_count                    |
|  3. When user reads conversation: RESET unread_count to 0               |
|     and update last_read_msg_id                                         |
|  4. Store in Redis: unread:{user_id}:{conv_id} = count                  |
|  5. Total badge count: SUM of all unread counts for a user              |
|     - Maintain total_unread:{user_id} separately                        |
|     - Increment/decrement atomically with per-conversation count        |
|                                                                         |
|  Edge case: user opens conversation on one device but not another       |
|  - Sync last_read_msg_id across devices                                 |
|  - Read on any device updates the shared last_read_msg_id               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 7: WHAT ABOUT DATA PRIVACY AND COMPLIANCE?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How do you handle data privacy regulations (GDPR, etc.)?            |
|                                                                         |
|  A: Key considerations:                                                 |
|                                                                         |
|  1. E2E ENCRYPTION                                                      |
|     - Server only stores encrypted blobs                                |
|     - Cannot read message content even if compelled                     |
|     - Metadata (who, when) is still visible to server                   |
|                                                                         |
|  2. DATA DELETION (Right to be forgotten)                               |
|     - User can delete their account                                     |
|     - All messages in 1:1 chats: mark as deleted for this user          |
|     - Group messages: replace sender with "Deleted User"                |
|     - Media files: queue for deletion from object store                 |
|     - Propagate deletion to all replicas and backups                    |
|                                                                         |
|  3. DATA PORTABILITY                                                    |
|     - Export chat history feature                                       |
|     - Decrypt on device, export as readable format                      |
|                                                                         |
|  4. DATA RESIDENCY                                                      |
|     - Some countries require data stored locally                        |
|     - Route users to regional clusters                                  |
|     - Cross-region messaging: store in both regions                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 8: HOW TO HANDLE MEDIA IN MESSAGES?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How does media sharing work in the chat system?                     |
|                                                                         |
|  A: Media is NOT stored inline with messages:                           |
|                                                                         |
|  UPLOAD FLOW:                                                           |
|  1. Client requests upload URL from Media Service                       |
|  2. Media Service returns pre-signed S3 upload URL + media_id           |
|  3. Client uploads media directly to S3 (bypasses chat server)          |
|  4. Client sends message with media_id reference                        |
|  5. Recipients download media from CDN when viewing                     |
|                                                                         |
|  OPTIMIZATIONS:                                                         |
|  - Client compresses images before upload (reduce bandwidth)            |
|  - Generate thumbnail server-side for message preview                   |
|  - Progressive loading: show blur -> thumbnail -> full image            |
|  - Videos: stream via HLS, don't download entire file                   |
|  - Media URLs have expiring tokens (security)                           |
|                                                                         |
|  E2E ENCRYPTION FOR MEDIA:                                              |
|  - Client encrypts media with random AES key before upload              |
|  - AES key sent in the (E2E encrypted) message body                     |
|  - Server stores encrypted blob, cannot decrypt                         |
|  - Recipient decrypts using key from message                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 9: WHAT IF A USER HAS 100K CONVERSATIONS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How do you handle users with many conversations efficiently?        |
|                                                                         |
|  A: The conversation list is the most frequently accessed view.         |
|                                                                         |
|  DESIGN:                                                                |
|  1. user_conversations table sorted by last_message_at DESC             |
|  2. Only load top 20 conversations initially (pagination)               |
|  3. Each entry is lightweight (~200 bytes: name, preview, count)        |
|  4. Cache top 50 conversations per user in Redis                        |
|                                                                         |
|  WHEN NEW MESSAGE ARRIVES:                                              |
|  - Update last_message_at for the conversation                          |
|  - Move conversation to top of the list                                 |
|  - Increment unread count                                               |
|  - Push update to client's conversation list view                       |
|                                                                         |
|  ARCHIVING:                                                             |
|  - Users can archive conversations (move out of main list)              |
|  - Archived conversations don't appear in default view                  |
|  - Still receive messages (but muted)                                   |
|  - Reduces the active conversation list for heavy users                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 10: HOW WOULD YOU IMPLEMENT SEARCH?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How would you implement message search across conversations?        |
|                                                                         |
|  A: This is challenging with E2E encryption:                            |
|                                                                         |
|  WITHOUT E2E ENCRYPTION:                                                |
|  - Index messages in Elasticsearch                                      |
|  - Full-text search across user's conversations                         |
|  - Server-side search is straightforward                                |
|                                                                         |
|  WITH E2E ENCRYPTION (WhatsApp approach):                               |
|  - Server cannot index encrypted messages                               |
|  - Search happens ON DEVICE only                                        |
|  - Client maintains a local SQLite database of decrypted messages       |
|  - Full-text search on local DB                                         |
|  - Limitation: can only search messages on current device               |
|                                                                         |
|  HYBRID (Slack approach - no E2E by default):                           |
|  - Messages stored in plaintext server-side                             |
|  - Elasticsearch index of all messages                                  |
|  - Server-side search with access control (only your channels)          |
|  - Faster and more comprehensive but less private                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 11: HOW TO HANDLE MESSAGE EDITING AND DELETION?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How do message edit and delete operations work?                     |
|                                                                         |
|  A: These are more complex than they seem:                              |
|                                                                         |
|  MESSAGE EDIT:                                                          |
|  1. Client sends edit request with message_id and new content           |
|  2. Server validates: only author can edit, within time window          |
|  3. Update message in Cassandra (or append edit version)                |
|  4. Send "message_edited" event to all participants via WS              |
|  5. Clients update the message in their local view                      |
|  6. Offline users receive edit when they sync                           |
|                                                                         |
|  MESSAGE DELETE ("Delete for Everyone"):                                |
|  1. Client sends delete request with message_id                         |
|  2. Server validates: only author, within time window (e.g., 1 hour)    |
|  3. Set is_deleted = true in Cassandra (soft delete)                    |
|  4. Send "message_deleted" event to all participants                    |
|  5. Clients replace message with "This message was deleted"             |
|  6. Actual content purged after 30 days (for abuse reports)             |
|                                                                         |
|  MESSAGE DELETE ("Delete for Me"):                                      |
|  1. Client-side only operation                                          |
|  2. Add message_id to local "hidden messages" list                      |
|  3. Filter out when rendering conversation                              |
|  4. Message remains visible to other participants                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### QUESTION 12: WHAT METRICS WOULD YOU MONITOR?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Q: What key metrics would you track for this system?                    |
|                                                                          |
|  A:                                                                      |
|                                                                          |
|  DELIVERY METRICS:                                                       |
|  - Message delivery latency (p50, p95, p99)                              |
|  - Delivery success rate (target: 99.99%)                                |
|  - Time to deliver for offline users (after reconnect)                   |
|  - Message loss rate (target: 0%)                                        |
|                                                                          |
|  CONNECTION METRICS:                                                     |
|  - Active WebSocket connections                                          |
|  - Connection churn rate (connects/disconnects per second)               |
|  - Handshake latency                                                     |
|  - Connection lifetime distribution                                      |
|                                                                          |
|  STORAGE METRICS:                                                        |
|  - Cassandra write latency (p99)                                         |
|  - Cassandra partition size distribution                                 |
|  - Storage growth rate                                                   |
|  - Compaction lag                                                        |
|                                                                          |
|  PRESENCE METRICS:                                                       |
|  - Presence update latency                                               |
|  - False offline rate (user online but shown offline)                    |
|  - Heartbeat timeout rate                                                |
|                                                                          |
|  BUSINESS METRICS:                                                       |
|  - Messages sent per DAU                                                 |
|  - Group creation rate                                                   |
|  - Media message percentage                                              |
|  - Notification open rate                                                |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 14: QUICK REFERENCE SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHAT SYSTEM - QUICK REFERENCE                                          |
|                                                                         |
|  SCALE: 2B users, 100B msgs/day, 50M concurrent connections             |
|                                                                         |
|  KEY DECISIONS:                                                         |
|  1. WebSocket for real-time bi-directional communication                |
|  2. Cassandra for message storage (write-optimized, time-series)        |
|  3. Redis for presence, connection registry, offline queues             |
|  4. Per-conversation sequence numbers for message ordering              |
|  5. Client-generated IDs for deduplication                              |
|  6. E2E encryption via Signal Protocol (Double Ratchet)                 |
|  7. Async fan-out for group messages via Kafka                          |
|  8. Push notifications for offline users (APNs/FCM)                     |
|                                                                         |
|  LATENCY BUDGET:                                                        |
|  Message delivery (both online): <100ms                                 |
|  Message storage: <10ms (Cassandra write)                               |
|  Presence update: <500ms                                                |
|  Conversation list load: <200ms                                         |
|                                                                         |
|  MAIN TRADEOFFS:                                                        |
|  - Stateful connections (WS) vs stateless (HTTP) -> chose WS            |
|  - Consistency vs availability for presence -> chose availability       |
|  - E2E encryption vs server-side search -> depends on product           |
|  - Cassandra (AP) vs MySQL (CP) for messages -> chose AP                |
|                                                                         |
+-------------------------------------------------------------------------+
```
