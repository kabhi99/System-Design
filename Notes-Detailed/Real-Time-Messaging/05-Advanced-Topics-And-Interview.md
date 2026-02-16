================================================================================
REAL-TIME MESSAGING SYSTEM - HIGH LEVEL DESIGN
================================================================================

CHAPTER 5: ADVANCED TOPICS & INTERVIEW QUESTIONS
================================================================================


================================================================================
SECTION 1: ADVANCED REAL-WORLD PROBLEMS
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  HANDLING CHAT SERVER FAILURE                                          │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Problem: Chat server crashes with 50K active connections      │  │
    │  │                                                                 │  │
    │  │  Solution: Graceful failover                                   │  │
    │  │                                                                 │  │
    │  │  1. DETECTION                                                  │  │
    │  │     • Load balancer health checks (every 5 seconds)           │  │
    │  │     • Server heartbeat to coordinator                         │  │
    │  │     • Redis connection registry TTL expires                   │  │
    │  │                                                                 │  │
    │  │  2. CLIENT RECONNECTION                                        │  │
    │  │     • Client detects disconnect                               │  │
    │  │     • Exponential backoff: 1s, 2s, 4s, 8s...                 │  │
    │  │     • Reconnect to any healthy server (via LB)               │  │
    │  │     • Re-register in connection registry                      │  │
    │  │                                                                 │  │
    │  │  3. MESSAGE RECOVERY                                           │  │
    │  │     • Messages in-flight stored in Kafka                      │  │
    │  │     • On reconnect: sync from last_message_id                │  │
    │  │     • No message loss                                         │  │
    │  │                                                                 │  │
    │  │  4. SEAMLESS HANDOFF                                           │  │
    │  │     • If server knows it's shutting down (graceful)          │  │
    │  │     • Notify clients to reconnect to different server        │  │
    │  │     • Transfer state before shutdown                          │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  CROSS-REGION / GLOBAL DEPLOYMENT                                     │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Problem: Users in US messaging users in India                │  │
    │  │           High latency (200ms+ RTT)                           │  │
    │  │                                                                 │  │
    │  │  Solution: Multi-region architecture                          │  │
    │  │                                                                 │  │
    │  │  ┌───────────────────────────────────────────────────────────┐│  │
    │  │  │                                                           ││  │
    │  │  │   US Region                      India Region             ││  │
    │  │  │                                                           ││  │
    │  │  │  User A ◄──► Chat Servers   Chat Servers ◄──► User B     ││  │
    │  │  │               │                   │                       ││  │
    │  │  │               │                   │                       ││  │
    │  │  │               └───── Kafka ───────┘                       ││  │
    │  │  │                     (cross-region)                        ││  │
    │  │  │                                                           ││  │
    │  │  └───────────────────────────────────────────────────────────┘│  │
    │  │                                                                 │  │
    │  │  DESIGN:                                                       │  │
    │  │  • User connects to nearest region (GeoDNS)                  │  │
    │  │  • Messages routed via Kafka MirrorMaker                     │  │
    │  │  • Each region has complete infrastructure                   │  │
    │  │  • Cross-region latency only for inter-region messages      │  │
    │  │                                                                 │  │
    │  │  DATA RESIDENCY:                                               │  │
    │  │  • EU users' messages stored in EU (GDPR)                    │  │
    │  │  • Route by user's home region                               │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  SPAM & ABUSE PREVENTION                                              │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Challenge: E2EE means server can't read content              │  │
    │  │                                                                 │  │
    │  │  SOLUTIONS:                                                    │  │
    │  │                                                                 │  │
    │  │  1. RATE LIMITING                                             │  │
    │  │     • Max messages per minute to new contacts                │  │
    │  │     • Max new conversations per day                          │  │
    │  │     • Slow down suspected spammers                           │  │
    │  │                                                                 │  │
    │  │  2. METADATA ANALYSIS                                         │  │
    │  │     • Message frequency patterns                              │  │
    │  │     • Number of unique recipients                            │  │
    │  │     • Bulk sending behavior                                  │  │
    │  │                                                                 │  │
    │  │  3. USER REPORTS                                              │  │
    │  │     • "Report spam" button                                   │  │
    │  │     • User forwards message to trust & safety team          │  │
    │  │     • This decrypts it voluntarily for review               │  │
    │  │                                                                 │  │
    │  │  4. ML ON METADATA                                            │  │
    │  │     • Account age + behavior patterns                        │  │
    │  │     • Similar to email spam detection (without content)     │  │
    │  │                                                                 │  │
    │  │  5. PHONE NUMBER VERIFICATION                                 │  │
    │  │     • Barrier to creating spam accounts                      │  │
    │  │     • Rate limit SMS verifications per number               │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  MESSAGE SEARCH (With E2EE)                                           │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Challenge: Server can't search encrypted messages            │  │
    │  │                                                                 │  │
    │  │  Solution: CLIENT-SIDE SEARCH                                 │  │
    │  │                                                                 │  │
    │  │  1. Local database (SQLite) stores decrypted messages        │  │
    │  │  2. Full-text search index on device                         │  │
    │  │  3. Search happens entirely on client                        │  │
    │  │                                                                 │  │
    │  │  Limitations:                                                  │  │
    │  │  • Can only search messages synced to this device            │  │
    │  │  • New device needs to sync all history first                │  │
    │  │  • Storage constraints on mobile                             │  │
    │  │                                                                 │  │
    │  │  WhatsApp approach:                                           │  │
    │  │  • Local search only                                         │  │
    │  │  • Recent messages cached locally                            │  │
    │  │  • Old messages require scroll/fetch                        │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  DISAPPEARING MESSAGES                                                 │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Messages auto-delete after viewing or after time period      │  │
    │  │                                                                 │  │
    │  │  IMPLEMENTATION:                                               │  │
    │  │                                                                 │  │
    │  │  1. TIME-BASED (WhatsApp)                                     │  │
    │  │     • Message metadata includes: expires_at                  │  │
    │  │     • Client deletes locally after expiry                    │  │
    │  │     • Server deletes after expiry (if not E2EE concern)     │  │
    │  │                                                                 │  │
    │  │  2. VIEW-ONCE (Instagram, Snapchat style)                    │  │
    │  │     • Client marks "viewed" after opening                   │  │
    │  │     • Immediately delete locally after view                  │  │
    │  │     • Notify sender that it was viewed                       │  │
    │  │                                                                 │  │
    │  │  LIMITATIONS:                                                  │  │
    │  │  • Recipient can screenshot (can detect on some platforms)  │  │
    │  │  • Can photograph with another device                        │  │
    │  │  • Not truly enforceable                                     │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  VOICE & VIDEO CALLS                                                   │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  SIGNALING:                                                    │  │
    │  │  • Use existing WebSocket connection                         │  │
    │  │  • Exchange ICE candidates (STUN/TURN)                       │  │
    │  │  • SDP offer/answer exchange                                  │  │
    │  │                                                                 │  │
    │  │  MEDIA TRANSPORT:                                              │  │
    │  │  • WebRTC for peer-to-peer                                   │  │
    │  │  • SRTP encryption                                            │  │
    │  │  • Direct connection if possible                             │  │
    │  │  • TURN relay if NAT traversal fails                        │  │
    │  │                                                                 │  │
    │  │  ┌───────────────────────────────────────────────────────────┐│  │
    │  │  │                                                           ││  │
    │  │  │  Alice                              Bob                   ││  │
    │  │  │    │                                 │                    ││  │
    │  │  │    │──────── Signaling Server ───────│                    ││  │
    │  │  │    │         (WebSocket)             │                    ││  │
    │  │  │    │                                 │                    ││  │
    │  │  │    │◄════════ Direct P2P ══════════►│                    ││  │
    │  │  │    │        (WebRTC/SRTP)            │                    ││  │
    │  │  │                                                           ││  │
    │  │  └───────────────────────────────────────────────────────────┘│  │
    │  │                                                                 │  │
    │  │  GROUP CALLS:                                                  │  │
    │  │  • SFU (Selective Forwarding Unit) architecture              │  │
    │  │  • Each participant sends to server                          │  │
    │  │  • Server relays to all others                               │  │
    │  │  • More scalable than mesh P2P                               │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  STATUS / STORIES                                                      │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Ephemeral content that disappears after 24 hours             │  │
    │  │                                                                 │  │
    │  │  STORAGE:                                                      │  │
    │  │  • Encrypted media on CDN                                    │  │
    │  │  • Metadata in database with TTL                             │  │
    │  │  • Auto-delete after 24 hours                                │  │
    │  │                                                                 │  │
    │  │  DELIVERY:                                                     │  │
    │  │  • Pull model (unlike push for messages)                     │  │
    │  │  • Client fetches status from contacts                       │  │
    │  │  • Less critical than messages                               │  │
    │  │                                                                 │  │
    │  │  PRIVACY:                                                      │  │
    │  │  • Who can see (everyone, contacts, selected)               │  │
    │  │  • View list (who saw your status)                          │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 2: INTERVIEW QUESTIONS & ANSWERS
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  COMMON INTERVIEW QUESTIONS                                            │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Q: How do you ensure messages are delivered in order?        │  │
    │  │  A: Sequence numbers per conversation, client-side reordering,│  │
    │  │     Kafka partitioned by conversation_id for server-side     │  │
    │  │     ordering.                                                  │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  Q: How do you handle offline users?                          │  │
    │  │  A: Store messages in Cassandra, send push notification,     │  │
    │  │     on reconnect client syncs from last_message_id cursor.   │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  Q: How do you scale to 100M concurrent connections?         │  │
    │  │  A: Each chat server handles 50-100K connections.            │  │
    │  │     2000 servers total. Horizontal scaling.                  │  │
    │  │     Connections mapped in Redis for routing.                 │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  Q: How does end-to-end encryption work?                     │  │
    │  │  A: Signal Protocol. X3DH for key exchange, Double Ratchet  │  │
    │  │     for forward secrecy. Server only sees encrypted blobs.  │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  Q: How do you handle group messages efficiently?            │  │
    │  │  A: Sender Keys. Each sender distributes one key to group.  │  │
    │  │     Encrypt once, broadcast to all. Rotate on member change.│  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  Q: What happens if a chat server crashes?                   │  │
    │  │  A: Clients reconnect to another server via load balancer.  │  │
    │  │     Messages in-flight are in Kafka, so no loss.            │  │
    │  │     Sync from cursor on reconnect.                           │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  Q: How do you implement read receipts?                      │  │
    │  │  A: Client sends read_receipt when conversation opened.     │  │
    │  │     Batched: "read up to message X". Server routes to       │  │
    │  │     sender if online, or stores for later sync.             │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  Q: WebSocket vs Long Polling vs MQTT?                       │  │
    │  │  A: WebSocket for full duplex, low latency.                 │  │
    │  │     Long Polling as fallback for restrictive networks.      │  │
    │  │     MQTT for mobile battery efficiency.                      │  │
    │  │     WhatsApp uses custom XMPP-based protocol.               │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  Q: How do you prevent duplicate messages?                   │  │
    │  │  A: Each message has unique UUID. At-least-once delivery.   │  │
    │  │     Client deduplicates by message_id before display.       │  │
    │  │     Server uses idempotent writes.                           │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  Q: How do you route messages between chat servers?          │  │
    │  │  A: Redis hash maps user_id → server_id. On send, lookup    │  │
    │  │     recipient's server, route directly or via Kafka.        │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 3: QUICK REFERENCE SUMMARY
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ARCHITECTURE SUMMARY                                                   │
    │                                                                         │
    │  Client → LB (L4) → Chat Servers (WS) → Kafka → Services              │
    │                                                                         │
    │  KEY COMPONENTS:                                                        │
    │  • Chat Servers: WebSocket connections, 50K each                       │
    │  • Kafka: Message queue, partitioned by user/conversation             │
    │  • Cassandra: Message storage (write-optimized)                        │
    │  • Redis: Presence, connection registry, caching                       │
    │  • S3 + CDN: Media storage and delivery                               │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  KEY NUMBERS                                                            │
    │                                                                         │
    │  ┌────────────────────────┬────────────────────────────────────────┐  │
    │  │ Metric                 │ Value                                  │  │
    │  ├────────────────────────┼────────────────────────────────────────┤  │
    │  │ DAU                    │ 500 million                            │  │
    │  │ Concurrent connections │ 100 million                            │  │
    │  │ Messages/second        │ 1.15M avg, 3.5M peak                  │  │
    │  │ Chat servers           │ ~2000                                  │  │
    │  │ Connections per server │ 50,000 - 100,000                      │  │
    │  │ Message delivery       │ < 100ms (both online)                 │  │
    │  │ Storage per day        │ 2.5 TB text + 1.25 PB media          │  │
    │  └────────────────────────┴────────────────────────────────────────┘  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  KEY DESIGN DECISIONS                                                   │
    │                                                                         │
    │  1. CONNECTION PROTOCOL: WebSocket (primary) + Long Polling fallback │
    │                                                                         │
    │  2. MESSAGE QUEUE: Kafka for durability and decoupling               │
    │                                                                         │
    │  3. DATABASE: Cassandra for messages (write-optimized, scalable)     │
    │                                                                         │
    │  4. PRESENCE: Redis with TTL-based heartbeat                         │
    │                                                                         │
    │  5. ENCRYPTION: Signal Protocol (X3DH + Double Ratchet)              │
    │                                                                         │
    │  6. DELIVERY: At-least-once with client deduplication                │
    │                                                                         │
    │  7. ORDERING: Sequence numbers + timestamp + Kafka partitioning      │
    │                                                                         │
    │  8. OFFLINE: Store and forward + push notification                   │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  TRADE-OFFS DISCUSSED                                                   │
    │                                                                         │
    │  • E2EE vs Server Features (can't search, moderate content)         │
    │  • Cassandra vs PostgreSQL (write perf vs query flexibility)        │
    │  • Fan-out on write vs read (latency vs storage)                    │
    │  • WebSocket vs MQTT (ubiquity vs battery efficiency)               │
    │  • Push vs Pull for presence (real-time vs scalability)            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
COMPLETE ARCHITECTURE DIAGRAM
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │                    REAL-TIME MESSAGING SYSTEM                          │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │     ┌─────────┐    ┌─────────┐    ┌─────────┐                 │  │
    │  │     │ Mobile  │    │   Web   │    │ Desktop │                 │  │
    │  │     │  App    │    │  Client │    │   App   │                 │  │
    │  │     └────┬────┘    └────┬────┘    └────┬────┘                 │  │
    │  │          │              │              │                       │  │
    │  │          └──────────────┼──────────────┘                       │  │
    │  │                         │                                      │  │
    │  │                         ▼                                      │  │
    │  │          ┌─────────────────────────────────┐                  │  │
    │  │          │      LOAD BALANCER (L4)        │                  │  │
    │  │          │   (Sticky by user_id hash)     │                  │  │
    │  │          └─────────────────┬───────────────┘                  │  │
    │  │                            │                                   │  │
    │  │      ┌─────────────────────┼─────────────────────┐            │  │
    │  │      │                     │                     │            │  │
    │  │      ▼                     ▼                     ▼            │  │
    │  │  ┌────────────┐    ┌────────────┐    ┌────────────┐          │  │
    │  │  │   Chat     │    │   Chat     │    │   Chat     │          │  │
    │  │  │ Server 1   │◄──►│ Server 2   │◄──►│ Server N   │          │  │
    │  │  │ (50K conn) │    │ (50K conn) │    │ (50K conn) │          │  │
    │  │  └─────┬──────┘    └─────┬──────┘    └─────┬──────┘          │  │
    │  │        │                 │                 │                  │  │
    │  │        └─────────────────┼─────────────────┘                  │  │
    │  │                          │                                    │  │
    │  │         ┌────────────────┼────────────────┐                   │  │
    │  │         │                │                │                   │  │
    │  │         ▼                ▼                ▼                   │  │
    │  │   ┌──────────┐    ┌──────────┐    ┌──────────┐               │  │
    │  │   │  REDIS   │    │  KAFKA   │    │  User    │               │  │
    │  │   │          │    │          │    │ Service  │               │  │
    │  │   │•Presence │    │•messages │    │          │               │  │
    │  │   │•Conn Map │    │•events   │    └────┬─────┘               │  │
    │  │   │•Cache    │    │•notif    │         │                     │  │
    │  │   └──────────┘    └────┬─────┘         ▼                     │  │
    │  │                        │         ┌──────────┐                │  │
    │  │        ┌───────────────┼────┐    │PostgreSQL│                │  │
    │  │        │               │    │    │ (Users)  │                │  │
    │  │        ▼               ▼    ▼    └──────────┘                │  │
    │  │  ┌──────────┐   ┌──────────┐  ┌──────────┐                   │  │
    │  │  │ Storage  │   │   Push   │  │ Presence │                   │  │
    │  │  │ Workers  │   │ Service  │  │ Service  │                   │  │
    │  │  └────┬─────┘   └────┬─────┘  └──────────┘                   │  │
    │  │       │              │                                        │  │
    │  │       ▼              ▼                                        │  │
    │  │  ┌──────────┐  ┌──────────┐                                  │  │
    │  │  │Cassandra │  │APNs/FCM  │                                  │  │
    │  │  │(Messages)│  │          │                                  │  │
    │  │  └──────────┘  └──────────┘                                  │  │
    │  │                                                               │  │
    │  │  ┌──────────────────────────────────────────────────────────┐│  │
    │  │  │                    MEDIA PIPELINE                        ││  │
    │  │  │                                                          ││  │
    │  │  │  Upload API → S3 → Lambda (transcode) → CDN (delivery) ││  │
    │  │  │                                                          ││  │
    │  │  └──────────────────────────────────────────────────────────┘│  │
    │  │                                                               │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
END OF REAL-TIME MESSAGING SYSTEM DESIGN
================================================================================

