# REAL-TIME MESSAGING SYSTEM - HIGH LEVEL DESIGN

CHAPTER 3: MESSAGE FLOW & DELIVERY GUARANTEES
SECTION 1: ONE-TO-ONE MESSAGE FLOW
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SCENARIO: User A sends message to User B                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CASE 1: Both users ONLINE                                     |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  User A                              User B             |  |  |*
*|  |  |    |                                   ^                |  |  |*
*|  |  |    | 1. Send message                   | 6. Receive    |  |  |*
*|  |  |    v                                   |                |  |  |*
*|  |  |  Chat Server A                    Chat Server B        |  |  |*
*|  |  |    |                                   ^                |  |  |*
*|  |  |    | 2. Store locally (ack pending)   | 5. Forward     |  |  |*
*|  |  |    | 3. Lookup B's server             |                |  |  |*
*|  |  |    |    (Redis)                       |                |  |  |*
*|  |  |    |                                   |                |  |  |*
*|  |  |    | 4. Route via Kafka or directly   |                |  |  |*
*|  |  |    +-----------------------------------+                |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  7. Server B sends ACK to Server A                      |  |  |*
*|  |  |  8. Server A sends "delivered" status to User A         |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CASE 2: User B OFFLINE                                        |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  User A                                                 |  |  |*
*|  |  |    |                                                    |  |  |*
*|  |  |    | 1. Send message                                   |  |  |*
*|  |  |    v                                                    |  |  |*
*|  |  |  Chat Server A                                         |  |  |*
*|  |  |    |                                                    |  |  |*
*|  |  |    | 2. Lookup B > NOT FOUND in Redis                 |  |  |*
*|  |  |    |                                                    |  |  |*
*|  |  |    | 3. Publish to Kafka (messages.store)             |  |  |*
*|  |  |    | 4. Publish to Kafka (notifications)              |  |  |*
*|  |  |    |                                                    |  |  |*
*|  |  |    | 5. Return "sent" ACK to User A                   |  |  |*
*|  |  |    |                                                    |  |  |*
*|  |  |    v                                                    |  |  |*
*|  |  |  Kafka > Storage Worker > Cassandra (persist)         |  |  |*
*|  |  |  Kafka > Push Service > APNs/FCM > User B's phone    |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  Later: User B comes online                            |  |  |*
*|  |  |    |                                                    |  |  |*
*|  |  |    v                                                    |  |  |*
*|  |  |  Chat Server (any) fetches pending messages from DB    |  |  |*
*|  |  |  Sends to User B                                       |  |  |*
*|  |  |  Sends "delivered" to User A (if online)              |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2: GROUP MESSAGE FLOW
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SCENARIO: User A sends message to Group G (100 members)              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  User A sends "Hello group!"                                   |  |*
*|  |    |                                                            |  |*
*|  |    v                                                            |  |*
*|  |  Chat Server A                                                 |  |*
*|  |    |                                                            |  |*
*|  |    | 1. Validate A is member of group G                       |  |*
*|  |    | 2. Get group member list (cached in Redis or DB)         |  |*
*|  |    | 3. Publish to Kafka: messages.group.{group_id}           |  |*
*|  |    |                                                            |  |*
*|  |    v                                                            |  |*
*|  |  Kafka > Group Message Worker                                  |  |*
*|  |    |                                                            |  |*
*|  |    | 4. Fan out to each member:                               |  |*
*|  |    |    For each member_id in group.members:                  |  |*
*|  |    |      - Lookup member's chat server                       |  |*
*|  |    |      - If online: route message                         |  |*
*|  |    |      - If offline: store + push notification            |  |*
*|  |    |                                                            |  |*
*|  |    | 5. Store message once (group_id, message_id)            |  |*
*|  |    |                                                            |  |*
*|  |    v                                                            |  |*
*|  |  Delivery to 100 members (parallel)                           |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  FAN-OUT STRATEGIES                                                    |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. SMALL GROUPS (< 100 members): Fan-out on write            |  |*
*|  |     * Immediately deliver to all online members               |  |*
*|  |     * Store in each member's inbox                            |  |*
*|  |     * Fast delivery, more storage                             |  |*
*|  |                                                                 |  |*
*|  |  2. LARGE GROUPS (> 1000 members): Fan-out on read           |  |*
*|  |     * Store message once in group                             |  |*
*|  |     * Members fetch from group when they connect              |  |*
*|  |     * Less storage, slightly higher read latency             |  |*
*|  |                                                                 |  |*
*|  |  3. HYBRID (WhatsApp approach):                               |  |*
*|  |     * Store message in group                                  |  |*
*|  |     * Push to online members immediately                      |  |*
*|  |     * Offline members sync on connect                         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3: MESSAGE STATUS TRACKING
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  STATUS PROGRESSION                                                    |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  SENT (Single checkmark Y)                                    |  |*
*|  |    | Message reached server and stored                        |  |*
*|  |    |                                                           |  |*
*|  |    v                                                           |  |*
*|  |  DELIVERED (Double checkmark YY)                              |  |*
*|  |    | Message received by recipient's device                  |  |*
*|  |    |                                                           |  |*
*|  |    v                                                           |  |*
*|  |  READ (Blue checkmarks YY)                                    |  |*
*|  |      Recipient opened the conversation                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  IMPLEMENTATION                                                        |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  SENT:                                                         |  |*
*|  |  * Server ACKs message receipt                                |  |*
*|  |  * Client updates UI to show Y                               |  |*
*|  |                                                                 |  |*
*|  |  DELIVERED:                                                    |  |*
*|  |  * Recipient's device sends delivery_receipt                  |  |*
*|  |  * Server routes receipt to sender                            |  |*
*|  |  * Sender's client updates UI to show YY                     |  |*
*|  |                                                                 |  |*
*|  |  {                                                              |  |*
*|  |    "type": "delivery_receipt",                                |  |*
*|  |    "message_id": "msg-123",                                   |  |*
*|  |    "conversation_id": "conv-456",                             |  |*
*|  |    "delivered_at": "2024-01-15T10:00:00Z"                    |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  READ:                                                         |  |*
*|  |  * Recipient opens conversation                               |  |*
*|  |  * Client sends read_receipt for all unread messages         |  |*
*|  |  * Batched: "read up to message_id X"                        |  |*
*|  |                                                                 |  |*
*|  |  {                                                              |  |*
*|  |    "type": "read_receipt",                                    |  |*
*|  |    "conversation_id": "conv-456",                             |  |*
*|  |    "read_up_to": "msg-125",                                   |  |*
*|  |    "read_at": "2024-01-15T10:05:00Z"                         |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  GROUP READ RECEIPTS                                                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Option 1: Full tracking (like WhatsApp)                      |  |*
*|  |  * Track per-member read status                               |  |*
*|  |  * Storage: O(messages x members)                             |  |*
*|  |  * UI: "Read by 50 of 100 members"                           |  |*
*|  |                                                                 |  |*
*|  |  Option 2: Simplified                                         |  |*
*|  |  * Only show if read by at least one person                  |  |*
*|  |  * Less storage, simpler                                      |  |*
*|  |                                                                 |  |*
*|  |  Option 3: No group read receipts (like Telegram)            |  |*
*|  |  * Privacy-focused                                            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4: DELIVERY GUARANTEES
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  AT-LEAST-ONCE DELIVERY                                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Messages may be delivered more than once, but never lost.    |  |*
*|  |                                                                 |  |*
*|  |  Achieved via:                                                 |  |*
*|  |  1. Persistent storage (Kafka + Cassandra)                    |  |*
*|  |  2. Acknowledgment protocol                                   |  |*
*|  |  3. Retry mechanism                                           |  |*
*|  |                                                                 |  |*
*|  |  SENDER RETRY FLOW:                                            |  |*
*|  |                                                                 |  |*
*|  |  Client sends message                                          |  |*
*|  |    |                                                           |  |*
*|  |    +-> If ACK received within 5 seconds > Done               |  |*
*|  |    |                                                           |  |*
*|  |    +-> If no ACK > Retry (up to 3 times)                     |  |*
*|  |           |                                                    |  |*
*|  |           +-> If still fails > Queue locally, retry later    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DEDUPLICATION (Client-side)                                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Since at-least-once means duplicates possible:               |  |*
*|  |                                                                 |  |*
*|  |  CLIENT SIDE:                                                  |  |*
*|  |  * Each message has unique message_id (UUID)                  |  |*
*|  |  * Client maintains set of received message_ids               |  |*
*|  |  * On receive: if message_id seen, ignore                    |  |*
*|  |                                                                 |  |*
*|  |  SERVER SIDE:                                                  |  |*
*|  |  * Cassandra: INSERT IF NOT EXISTS on message_id             |  |*
*|  |  * Idempotent storage                                         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  MESSAGE ORDERING                                                      |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  REQUIREMENT:                                                  |  |*
*|  |  Messages from same sender should appear in order            |  |*
*|  |                                                                 |  |*
*|  |  IMPLEMENTATION:                                               |  |*
*|  |                                                                 |  |*
*|  |  1. SEQUENCE NUMBERS                                          |  |*
*|  |     * Client assigns seq_num per conversation                |  |*
*|  |     * seq_num = last_sent_seq + 1                            |  |*
*|  |     * Server validates: incoming seq = expected seq          |  |*
*|  |                                                                 |  |*
*|  |  2. TIMESTAMP + MESSAGE_ID                                    |  |*
*|  |     * Use server timestamp for ordering                      |  |*
*|  |     * Tie-breaker: message_id (lexicographic)                |  |*
*|  |                                                                 |  |*
*|  |  3. KAFKA PARTITIONING                                        |  |*
*|  |     * Partition by conversation_id                           |  |*
*|  |     * Single partition = ordered processing                  |  |*
*|  |                                                                 |  |*
*|  |  CLIENT REORDERING:                                            |  |*
*|  |  * Client may receive out of order (network)                 |  |*
*|  |  * Client sorts by (timestamp, message_id) before display    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4.5: MESSAGE QUEUES & DEAD LETTER QUEUES (DLQ)
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHY USE MESSAGE QUEUES (Kafka)?                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  WITHOUT QUEUE:                                                |  |*
*|  |                                                                 |  |*
*|  |  User A > Chat Server 1 > (direct to) Chat Server 42 > User B |  |*
*|  |                                                                 |  |*
*|  |  Problems:                                                     |  |*
*|  |  * If Server 42 is down > message lost!                       |  |*
*|  |  * If Server 42 is slow > Server 1 blocks                    |  |*
*|  |  * Burst traffic > Server 1 overwhelmed                      |  |*
*|  |  * No replay if something fails                               |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  WITH QUEUE:                                                   |  |*
*|  |                                                                 |  |*
*|  |  User A > Chat Server 1 > KAFKA > Chat Server 42 > User B    |  |*
*|  |                            ^                                   |  |*
*|  |                            |                                   |  |*
*|  |                    (persisted to disk)                        |  |*
*|  |                                                                 |  |*
*|  |  Benefits:                                                     |  |*
*|  |  Y Durability: Messages persisted, never lost                |  |*
*|  |  Y Decoupling: Servers don't need direct connection         |  |*
*|  |  Y Buffering: Handle traffic spikes                         |  |*
*|  |  Y Replay: Can reprocess messages on failure                |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  KAFKA TOPIC DESIGN FOR MESSAGING                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TOPICS:                                                       |  |*
*|  |                                                                 |  |*
*|  |  1. messages.outbound                                         |  |*
*|  |     * Messages to be delivered to users                       |  |*
*|  |     * Partitioned by: recipient_user_id                       |  |*
*|  |     * Ensures ordering per recipient                          |  |*
*|  |                                                                 |  |*
*|  |  2. messages.store                                            |  |*
*|  |     * Messages to persist in Cassandra                        |  |*
*|  |     * Partitioned by: conversation_id                         |  |*
*|  |                                                                 |  |*
*|  |  3. messages.notifications                                    |  |*
*|  |     * Push notifications for offline users                   |  |*
*|  |     * Partitioned by: user_id                                 |  |*
*|  |                                                                 |  |*
*|  |  4. messages.dlq (Dead Letter Queue)                         |  |*
*|  |     * Failed messages after max retries                      |  |*
*|  |     * For manual investigation                               |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |                      KAFKA                                ||  |*
*|  |  |                                                           ||  |*
*|  |  |  messages.outbound  --> Delivery Workers --> WebSocket   ||  |*
*|  |  |                              |                            ||  |*
*|  |  |                              | (on failure)               ||  |*
*|  |  |                              v                            ||  |*
*|  |  |  messages.retry     <-- Retry with backoff               ||  |*
*|  |  |                              |                            ||  |*
*|  |  |                              | (after max retries)        ||  |*
*|  |  |                              v                            ||  |*
*|  |  |  messages.dlq       <-- Dead Letter Queue                ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  MESSAGE DELIVERY FLOW WITH QUEUE                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  STEP 1: User A sends message                            ||  |*
*|  |  |                                                           ||  |*
*|  |  |  User A --> Chat Server                                   ||  |*
*|  |  |                  |                                        ||  |*
*|  |  |                  | Produce to Kafka                      ||  |*
*|  |  |                  | (acks = all for durability)           ||  |*
*|  |  |                  v                                        ||  |*
*|  |  |              messages.outbound                           ||  |*
*|  |  |              Key: recipient_user_id                      ||  |*
*|  |  |              Value: {                                    ||  |*
*|  |  |                "msg_id": "uuid",                         ||  |*
*|  |  |                "sender": "user_A",                       ||  |*
*|  |  |                "recipient": "user_B",                    ||  |*
*|  |  |                "content": "encrypted...",               ||  |*
*|  |  |                "timestamp": 1705123456,                  ||  |*
*|  |  |                "retry_count": 0                          ||  |*
*|  |  |              }                                           ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Return ACK to User A: "Message sent Y"                 ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  STEP 2: Delivery Worker consumes                        ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Delivery Worker (consumer group)                        ||  |*
*|  |  |       |                                                   ||  |*
*|  |  |       | Poll Kafka                                       ||  |*
*|  |  |       |                                                   ||  |*
*|  |  |       +-> Lookup User B's server (Redis)                ||  |*
*|  |  |       |                                                   ||  |*
*|  |  |       +-> If User B online:                             ||  |*
*|  |  |       |      Route to Chat Server holding User B        ||  |*
*|  |  |       |      Chat Server pushes via WebSocket           ||  |*
*|  |  |       |      Commit Kafka offset                        ||  |*
*|  |  |       |                                                   ||  |*
*|  |  |       +-> If User B offline:                            ||  |*
*|  |  |              Store in Cassandra for later sync          ||  |*
*|  |  |              Send push notification                     ||  |*
*|  |  |              Commit Kafka offset                        ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  RETRY MECHANISM                                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  FAILURE SCENARIOS:                                            |  |*
*|  |  * Target chat server temporarily unreachable                 |  |*
*|  |  * Database write fails                                       |  |*
*|  |  * Push notification service timeout                         |  |*
*|  |  * Network partition                                          |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  ERROR CLASSIFICATION:                                         |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  TEMPORARY ERRORS (Retriable)                            ||  |*
*|  |  |  * Server temporarily down                               ||  |*
*|  |  |  * Network timeout                                       ||  |*
*|  |  |  * Database connection pool exhausted                   ||  |*
*|  |  |  * Rate limited by external service                     ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Action: RETRY with exponential backoff                  ||  |*
*|  |  |                                                           ||  |*
*|  |  |  ------------------------------------------------------  ||  |*
*|  |  |                                                           ||  |*
*|  |  |  PERMANENT ERRORS (Non-retriable)                        ||  |*
*|  |  |  * User account deleted                                  ||  |*
*|  |  |  * Invalid message format                                ||  |*
*|  |  |  * User blocked sender                                   ||  |*
*|  |  |  * Message too old to deliver                           ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Action: Send directly to DLQ, no retry                  ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  RETRY FLOW:                                                   |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  Message arrives                                         ||  |*
*|  |  |       |                                                   ||  |*
*|  |  |       v                                                   ||  |*
*|  |  |  Attempt delivery                                        ||  |*
*|  |  |       |                                                   ||  |*
*|  |  |       +-- Success --> Commit offset, done Y             ||  |*
*|  |  |       |                                                   ||  |*
*|  |  |       +-- Failure                                        ||  |*
*|  |  |              |                                            ||  |*
*|  |  |              +-- Permanent error --> DLQ immediately     ||  |*
*|  |  |              |                                            ||  |*
*|  |  |              +-- Temporary error                         ||  |*
*|  |  |                     |                                     ||  |*
*|  |  |                     | Retry count < MAX_RETRIES (e.g. 3)?||  |*
*|  |  |                     |                                     ||  |*
*|  |  |                     +-- Yes --> Send to retry topic     ||  |*
*|  |  |                     |           (with delay)             ||  |*
*|  |  |                     |                                     ||  |*
*|  |  |                     +-- No --> DLQ (exhausted retries)  ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  EXPONENTIAL BACKOFF WITH JITTER:                              |  |*
*|  |                                                                 |  |*
*|  |  Concept: Each retry waits longer than the previous one,      |  |*
*|  |           with some randomness to avoid thundering herd.      |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  Retry #    Base Delay    With Jitter (~10%)             ||  |*
*|  |  |  -------    ----------    -----------------              ||  |*
*|  |  |  1          1 second      0.9 - 1.1 seconds              ||  |*
*|  |  |  2          2 seconds     1.8 - 2.2 seconds              ||  |*
*|  |  |  3          4 seconds     3.6 - 4.4 seconds              ||  |*
*|  |  |  4          8 seconds     7.2 - 8.8 seconds              ||  |*
*|  |  |  5          16 seconds    14.4 - 17.6 seconds            ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Formula: delay = min(base x 2^attempt, max_delay)       ||  |*
*|  |  |           + random(0, 10% of delay)                      ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Cap at max delay (e.g., 60 seconds) to prevent          ||  |*
*|  |  |  extremely long waits                                    ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DEAD LETTER QUEUE (DLQ)                                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  WHAT GOES TO DLQ:                                             |  |*
*|  |  * Messages that failed after max retries                    |  |*
*|  |  * Malformed/invalid messages                                |  |*
*|  |  * Messages for deleted users                                |  |*
*|  |  * Poison messages (cause consumer crash)                    |  |*
*|  |                                                                 |  |*
*|  |  DLQ MESSAGE FORMAT:                                           |  |*
*|  |                                                                 |  |*
*|  |  {                                                              |  |*
*|  |    "original_message": {                                       |  |*
*|  |      "msg_id": "uuid-123",                                    |  |*
*|  |      "sender": "user_A",                                      |  |*
*|  |      "recipient": "user_B",                                   |  |*
*|  |      "content": "encrypted...",                               |  |*
*|  |      "timestamp": 1705123456                                  |  |*
*|  |    },                                                          |  |*
*|  |    "error": "Target server unreachable after 3 retries",     |  |*
*|  |    "retry_count": 3,                                          |  |*
*|  |    "first_attempt": "2024-01-15T10:00:00Z",                  |  |*
*|  |    "last_attempt": "2024-01-15T10:00:35Z",                   |  |*
*|  |    "dlq_timestamp": "2024-01-15T10:00:36Z",                  |  |*
*|  |    "source_topic": "messages.outbound",                      |  |*
*|  |    "source_partition": 5,                                     |  |*
*|  |    "source_offset": 12345                                     |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  DLQ HANDLING:                                                 |  |*
*|  |                                                                 |  |*
*|  |  1. ALERTING                                                   |  |*
*|  |     * Monitor DLQ size                                        |  |*
*|  |     * Alert if > threshold (e.g., 1000 messages)             |  |*
*|  |     * PagerDuty for critical spikes                          |  |*
*|  |                                                                 |  |*
*|  |  2. INVESTIGATION                                              |  |*
*|  |     * Dashboard to view DLQ messages                         |  |*
*|  |     * Group by error type                                     |  |*
*|  |     * Find root cause                                         |  |*
*|  |                                                                 |  |*
*|  |  3. REPLAY                                                     |  |*
*|  |     * After fixing the issue (e.g., server back online)      |  |*
*|  |     * Admin tool to replay DLQ messages to main topic        |  |*
*|  |     * Selective replay (by time range, error type)          |  |*
*|  |     * Reset retry count to 0, send back to main queue       |  |*
*|  |     * Mark as "replayed" in DLQ for tracking                |  |*
*|  |                                                                 |  |*
*|  |  4. DISCARD                                                    |  |*
*|  |     * Some messages can't be delivered (user deleted)        |  |*
*|  |     * Mark as permanently failed                              |  |*
*|  |     * Keep for audit trail, expire after 30 days            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DELAYED/SCHEDULED RETRY APPROACHES                                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  PROBLEM: Kafka doesn't support delayed messages natively.    |  |*
*|  |           How do we wait before retrying?                     |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  SOLUTION 1: Multiple Retry Topics by Delay Bucket            |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  messages.retry.1s   --> Consumer built-in 1s delay      ||  |*
*|  |  |  messages.retry.5s   --> Consumer built-in 5s delay      ||  |*
*|  |  |  messages.retry.30s  --> Consumer built-in 30s delay     ||  |*
*|  |  |  messages.retry.5m   --> Consumer built-in 5m delay      ||  |*
*|  |  |                                                           ||  |*
*|  |  |  On failure > route to appropriate delay topic           ||  |*
*|  |  |  Consumer sleeps for delay duration before processing    ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  Pros: Simple, native Kafka                                   |  |*
*|  |  Cons: Fixed delay buckets, consumer idle time               |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  SOLUTION 2: Redis Sorted Set as Delay Queue                  |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  On failure:                                              ||  |*
*|  |  |  * Add message to Redis sorted set                       ||  |*
*|  |  |  * Score = future timestamp when should retry            ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Scheduler (polls every second):                         ||  |*
*|  |  |  * Query: All messages with score < current time        ||  |*
*|  |  |  * For each due message:                                 ||  |*
*|  |  |    - Produce back to main Kafka topic                   ||  |*
*|  |  |    - Remove from sorted set                              ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  Pros: Precise timing, flexible delays                       |  |*
*|  |  Cons: Additional infrastructure, Redis as critical path    |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  SOLUTION 3: Timing Wheel (Advanced)                          |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  In-memory circular buffer of time slots                 ||  |*
*|  |  |  * Each slot = 1 second                                  ||  |*
*|  |  |  * 60 slots = 1 minute wheel                             ||  |*
*|  |  |  * Messages placed in future slot                        ||  |*
*|  |  |  * Pointer advances every second                         ||  |*
*|  |  |  * Process messages in current slot                      ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  Pros: O(1) insertion and retrieval                          |  |*
*|  |  Cons: Memory usage, complexity                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  COMPLETE RELIABILITY ARCHITECTURE                                    |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  User A                                                   ||  |*
*|  |  |    |                                                      ||  |*
*|  |  |    v                                                      ||  |*
*|  |  |  Chat Server                                              ||  |*
*|  |  |    |                                                      ||  |*
*|  |  |    | 1. Produce (acks=all)                               ||  |*
*|  |  |    v                                                      ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |  |              KAFKA CLUSTER                          | ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  |  messages.outbound (main topic)                    | ||  |*
*|  |  |  |         |                                          | ||  |*
*|  |  |  |         | 2. Consumer group                        | ||  |*
*|  |  |  |         v                                          | ||  |*
*|  |  |  |  Delivery Workers                                  | ||  |*
*|  |  |  |         |                                          | ||  |*
*|  |  |  |         +-- Success --> Commit offset             | ||  |*
*|  |  |  |         |                                          | ||  |*
*|  |  |  |         +-- Failure --> messages.retry.{delay}    | ||  |*
*|  |  |  |                                |                   | ||  |*
*|  |  |  |                                | 3. Delayed retry  | ||  |*
*|  |  |  |                                v                   | ||  |*
*|  |  |  |                          Retry Workers             | ||  |*
*|  |  |  |                                |                   | ||  |*
*|  |  |  |                                +-- Success --> Y  | ||  |*
*|  |  |  |                                |                   | ||  |*
*|  |  |  |                                +-- Max retries    | ||  |*
*|  |  |  |                                       |            | ||  |*
*|  |  |  |                                       v            | ||  |*
*|  |  |  |                              messages.dlq          | ||  |*
*|  |  |  |                                       |            | ||  |*
*|  |  |  |                                       v            | ||  |*
*|  |  |  |                              Alert + Dashboard     | ||  |*
*|  |  |  |                                       |            | ||  |*
*|  |  |  |                                       v            | ||  |*
*|  |  |  |                              Manual Replay/Discard | ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 5: TYPING INDICATORS & PRESENCE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  TYPING INDICATOR                                                      |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  "Alice is typing..."                                          |  |*
*|  |                                                                 |  |*
*|  |  FLOW:                                                         |  |*
*|  |                                                                 |  |*
*|  |  Alice starts typing                                          |  |*
*|  |    |                                                           |  |*
*|  |    | Send: { "type": "typing_start", "conv_id": "123" }      |  |*
*|  |    | (Throttle: max 1 per 3 seconds)                         |  |*
*|  |    v                                                           |  |*
*|  |  Server                                                        |  |*
*|  |    |                                                           |  |*
*|  |    | Route to other participants in conversation              |  |*
*|  |    | (Don't persist - ephemeral)                              |  |*
*|  |    v                                                           |  |*
*|  |  Bob's client                                                  |  |*
*|  |    |                                                           |  |*
*|  |    | Show "Alice is typing..."                               |  |*
*|  |    | Auto-hide after 5 seconds if no update                  |  |*
*|  |                                                                 |  |*
*|  |  OPTIMIZATION:                                                 |  |*
*|  |  * Ephemeral: Don't persist to DB                            |  |*
*|  |  * Throttle: Client sends max once per 3 seconds             |  |*
*|  |  * TTL: Auto-expire on recipient if no refresh               |  |*
*|  |  * Fire-and-forget: No ACK needed (lossy is OK)             |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  ONLINE/OFFLINE PRESENCE                                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TRACKING:                                                     |  |*
*|  |                                                                 |  |*
*|  |  Redis key: presence:{user_id}                                |  |*
*|  |  Value: { "status": "online", "last_active": timestamp }      |  |*
*|  |  TTL: 60 seconds                                              |  |*
*|  |                                                                 |  |*
*|  |  On connect:                                                   |  |*
*|  |    SET presence:{user_id} { online, now }                     |  |*
*|  |    PUBLISH presence_channel {user_id: online}                 |  |*
*|  |                                                                 |  |*
*|  |  Heartbeat (every 30s):                                       |  |*
*|  |    EXPIRE presence:{user_id} 60                               |  |*
*|  |                                                                 |  |*
*|  |  On disconnect:                                                |  |*
*|  |    DEL presence:{user_id}                                     |  |*
*|  |    UPDATE users SET last_seen = now WHERE user_id = ?        |  |*
*|  |    PUBLISH presence_channel {user_id: offline}                |  |*
*|  |                                                                 |  |*
*|  |  SUBSCRIBING TO PRESENCE:                                      |  |*
*|  |  * User subscribes to presence of their contacts              |  |*
*|  |  * Redis PubSub or polling                                    |  |*
*|  |  * Challenge: 500 contacts x 100M users = massive fan-out    |  |*
*|  |                                                                 |  |*
*|  |  OPTIMIZATION:                                                 |  |*
*|  |  * Only subscribe to presence of open conversations          |  |*
*|  |  * Batch presence queries                                     |  |*
*|  |  * Cache presence client-side for 30 seconds                 |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  LAST SEEN PRIVACY                                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Privacy options:                                              |  |*
*|  |  * Everyone can see my last seen                             |  |*
*|  |  * Only my contacts                                           |  |*
*|  |  * Nobody                                                      |  |*
*|  |                                                                 |  |*
*|  |  Implementation:                                               |  |*
*|  |  * Store privacy setting per user                            |  |*
*|  |  * On presence query, check viewer's permission              |  |*
*|  |  * If hidden: return "last seen: unavailable"                |  |*
*|  |                                                                 |  |*
*|  |  Reciprocity (WhatsApp style):                                |  |*
*|  |  * If you hide your last seen, you can't see others'        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 6: OFFLINE MESSAGE SYNC
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SYNC ON RECONNECT                                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  User was offline for 2 days, comes back online               |  |*
*|  |                                                                 |  |*
*|  |  FLOW:                                                         |  |*
*|  |                                                                 |  |*
*|  |  Client connects                                               |  |*
*|  |    |                                                           |  |*
*|  |    | Send: { "type": "sync", "last_message_id": "msg-100" }  |  |*
*|  |    |                                                           |  |*
*|  |    v                                                           |  |*
*|  |  Server                                                        |  |*
*|  |    |                                                           |  |*
*|  |    | Query: SELECT * FROM messages                           |  |*
*|  |    |        WHERE user_id = ?                                |  |*
*|  |    |        AND message_id > 'msg-100'                       |  |*
*|  |    |        ORDER BY message_id                              |  |*
*|  |    |        LIMIT 1000                                       |  |*
*|  |    |                                                           |  |*
*|  |    | Return: 500 new messages                                |  |*
*|  |    |                                                           |  |*
*|  |    v                                                           |  |*
*|  |  Client                                                        |  |*
*|  |    |                                                           |  |*
*|  |    | Process messages                                         |  |*
*|  |    | If more available: request next batch                   |  |*
*|  |    | Update last_message_id cursor                           |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  MULTI-DEVICE SYNC                                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  User has Phone + Desktop + Web                               |  |*
*|  |                                                                 |  |*
*|  |  Each device maintains:                                        |  |*
*|  |  * Its own cursor (last_synced_message_id)                   |  |*
*|  |  * Local database (SQLite on mobile)                         |  |*
*|  |                                                                 |  |*
*|  |  DEVICE-SPECIFIC CURSOR:                                       |  |*
*|  |                                                                 |  |*
*|  |  Server stores: user_device_cursors                           |  |*
*|  |  +-------------+------------+---------------------+           |  |*
*|  |  | user_id     | device_id  | last_synced_msg_id  |           |  |*
*|  |  | 123         | phone      | msg-500             |           |  |*
*|  |  | 123         | desktop    | msg-450             |           |  |*
*|  |  | 123         | web        | msg-480             |           |  |*
*|  |  +-------------+------------+---------------------+           |  |*
*|  |                                                                 |  |*
*|  |  Desktop connects > sync from msg-450                         |  |*
*|  |  Phone connects > sync from msg-500                           |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF CHAPTER 3
