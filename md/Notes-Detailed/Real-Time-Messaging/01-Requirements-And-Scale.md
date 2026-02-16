# REAL-TIME MESSAGING SYSTEM (WhatsApp-like) - HIGH LEVEL DESIGN

CHAPTER 1: REQUIREMENTS & SCALE ESTIMATION
SECTION 1: UNDERSTANDING THE PROBLEM
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHAT IS A REAL-TIME MESSAGING SYSTEM?                                 |*
*|                                                                         |*
*|  A platform enabling instant text, media, and voice communication      |*
*|  between users with features like:                                      |*
*|  * One-to-one chat                                                     |*
*|  * Group conversations                                                  |*
*|  * Media sharing (images, videos, documents)                           |*
*|  * End-to-end encryption                                               |*
*|  * Read receipts and typing indicators                                 |*
*|  * Online/offline presence                                             |*
*|                                                                         |*
*|  Examples: WhatsApp, Telegram, Signal, Facebook Messenger             |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  KEY CHARACTERISTICS                                                   |*
*|                                                                         |*
*|  1. REAL-TIME DELIVERY                                                 |*
*|     * Messages delivered in milliseconds when both users online       |*
*|     * Push notification for offline users                             |*
*|                                                                         |*
*|  2. RELIABILITY                                                        |*
*|     * Messages must never be lost                                     |*
*|     * Guaranteed delivery (eventually)                                |*
*|     * Message ordering within conversation                            |*
*|                                                                         |*
*|  3. SECURITY                                                           |*
*|     * End-to-end encryption (server can't read messages)             |*
*|     * Only sender and receiver can decrypt                            |*
*|                                                                         |*
*|  4. OFFLINE SUPPORT                                                    |*
*|     * Queue messages for offline users                                |*
*|     * Sync when user comes online                                     |*
*|                                                                         |*
*|  5. MULTI-DEVICE                                                       |*
*|     * Same account on phone, tablet, desktop, web                    |*
*|     * Messages sync across all devices                                |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2: FUNCTIONAL REQUIREMENTS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  CORE FEATURES                                                         |*
*|                                                                         |*
*|  1. ONE-TO-ONE MESSAGING                                               |*
*|     * Send text messages                                              |*
*|     * Send media (images, videos, audio, documents)                  |*
*|     * Message status: Sent > Delivered > Read                        |*
*|     * Typing indicator                                                |*
*|                                                                         |*
*|  2. GROUP MESSAGING                                                    |*
*|     * Create groups (up to 256/1024 members)                         |*
*|     * Add/remove members                                              |*
*|     * Admin controls                                                  |*
*|     * Group info (name, icon, description)                           |*
*|                                                                         |*
*|  3. PRESENCE                                                           |*
*|     * Online/Offline status                                           |*
*|     * Last seen timestamp                                             |*
*|     * Privacy controls ("hide last seen")                            |*
*|                                                                         |*
*|  4. MESSAGE FEATURES                                                   |*
*|     * Reply to specific message                                       |*
*|     * Forward messages                                                |*
*|     * Delete messages (for me / for everyone)                        |*
*|     * Edit messages (within time window)                             |*
*|     * Reactions (emoji)                                               |*
*|                                                                         |*
*|  5. MEDIA HANDLING                                                     |*
*|     * Image/video compression                                        |*
*|     * Thumbnail generation                                            |*
*|     * Progressive download                                            |*
*|     * Auto-download settings                                          |*
*|                                                                         |*
*|  6. SEARCH                                                             |*
*|     * Search within conversation                                      |*
*|     * Search across all chats                                        |*
*|     * Search by date, media type                                     |*
*|                                                                         |*
*|  7. NOTIFICATIONS                                                      |*
*|     * Push notifications for new messages                            |*
*|     * Mute conversations                                              |*
*|     * Custom notification sounds                                     |*
*|                                                                         |*
*|  8. ENCRYPTION                                                         |*
*|     * End-to-end encryption by default                               |*
*|     * Key exchange on first contact                                  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3: NON-FUNCTIONAL REQUIREMENTS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SCALE                                                                  |*
*|  * 2 billion users                                                     |*
*|  * 500 million daily active users                                     |*
*|  * 100 billion messages per day                                       |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  LATENCY                                                               |*
*|  * Message delivery: < 100ms (both online)                           |*
*|  * Message delivery: < 1s (one offline, push)                        |*
*|  * Typing indicator: < 50ms                                          |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  AVAILABILITY                                                          |*
*|  * 99.99% uptime (52 minutes downtime/year)                          |*
*|  * No single point of failure                                        |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  RELIABILITY                                                           |*
*|  * Zero message loss                                                  |*
*|  * At-least-once delivery                                            |*
*|  * Exactly-once display to user (deduplication)                     |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  CONSISTENCY                                                           |*
*|  * Messages appear in correct order within conversation              |*
*|  * Eventual consistency across devices                               |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SECURITY                                                              |*
*|  * End-to-end encryption                                             |*
*|  * Forward secrecy                                                    |*
*|  * Device verification                                               |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4: SCALE ESTIMATION
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  USER BASE                                                              |*
*|                                                                         |*
*|  * Total users: 2 billion                                             |*
*|  * Daily active users (DAU): 500 million                             |*
*|  * Monthly active users (MAU): 1.5 billion                           |*
*|  * Concurrent users (peak): 100 million                              |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  MESSAGE VOLUME                                                        |*
*|                                                                         |*
*|  Per user per day:                                                     |*
*|  * Messages sent: 50                                                  |*
*|  * Messages received: 150 (including groups)                         |*
*|                                                                         |*
*|  Daily totals:                                                         |*
*|  * 500M DAU x 50 messages = 25 billion sent/day                      |*
*|  * With groups: ~100 billion message deliveries/day                  |*
*|                                                                         |*
*|  Per second:                                                           |*
*|  * Average: 100B / 86400 ~ 1.15 million messages/second             |*
*|  * Peak (3x): 3.5 million messages/second                           |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  CONNECTIONS                                                           |*
*|                                                                         |*
*|  * 100M concurrent WebSocket connections                             |*
*|  * Each chat server handles: 50K-100K connections                    |*
*|  * Chat servers needed: 100M / 50K = 2000 servers                   |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  STORAGE                                                               |*
*|                                                                         |*
*|  Text messages:                                                        |*
*|  * Average message size: 100 bytes                                   |*
*|  * 25B messages x 100 bytes = 2.5 TB/day                            |*
*|  * Keep 30 days: 75 TB                                               |*
*|                                                                         |*
*|  Media (images, videos):                                               |*
*|  * 10% of messages have media                                        |*
*|  * Average media size: 500 KB                                        |*
*|  * 2.5B x 500 KB = 1.25 PB/day                                      |*
*|  * Keep 30 days: 37.5 PB                                            |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  BANDWIDTH                                                             |*
*|                                                                         |*
*|  Text messages:                                                        |*
*|  * 1.15M messages/sec x 100 bytes = 115 MB/s = 920 Mbps             |*
*|                                                                         |*
*|  Media (peak):                                                         |*
*|  * 115K media/sec x 500 KB = 57.5 GB/s = 460 Gbps                   |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SUMMARY TABLE                                                         |*
*|                                                                         |*
*|  +------------------------+----------------------------------------+  |*
*|  | Metric                 | Value                                  |  |*
*|  +------------------------+----------------------------------------+  |*
*|  | DAU                    | 500 million                            |  |*
*|  | Concurrent connections | 100 million                            |  |*
*|  | Messages/day           | 100 billion (including group delivery)|  |*
*|  | Messages/second (avg)  | 1.15 million                          |  |*
*|  | Messages/second (peak) | 3.5 million                           |  |*
*|  | Text storage/day       | 2.5 TB                                |  |*
*|  | Media storage/day      | 1.25 PB                               |  |*
*|  | Chat servers           | ~2000                                  |  |*
*|  +------------------------+----------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF CHAPTER 1
