# VIDEO CONFERENCING SYSTEM (ZOOM-LIKE) - HIGH LEVEL DESIGN

CHAPTER 4: SCALING AND SECURITY
SECTION 4.1: SCALING THE SFU
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SFU SCALING CHALLENGES                                                |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CHALLENGE 1: Single Meeting Size Limit                        |  |*
*|  |                                                                 |  |*
*|  |  One SFU server capacity:                                      |  |*
*|  |  * CPU: Packet processing, encryption                         |  |*
*|  |  * Bandwidth: Input x (N-1) output per participant           |  |*
*|  |  * Memory: Connection state, buffers                          |  |*
*|  |                                                                 |  |*
*|  |  Typical capacity: ~100-200 participants per SFU              |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  CHALLENGE 2: Large Meetings (1000+ participants)             |  |*
*|  |                                                                 |  |*
*|  |  SOLUTION: SFU Cascading                                      |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  Participants         Participants       Participants   |  |  |*
*|  |  |    1-100               101-200            201-300       |  |  |*
*|  |  |      |                    |                  |          |  |  |*
*|  |  |      v                    v                  v          |  |  |*
*|  |  |  +-------+           +-------+           +-------+     |  |  |*
*|  |  |  | SFU 1 |<-cascade->| SFU 2 |<-cascade->| SFU 3 |     |  |  |*
*|  |  |  +-------+           +-------+           +-------+     |  |  |*
*|  |  |                          |                              |  |  |*
*|  |  |                          | cascade                      |  |  |*
*|  |  |                          |                              |  |  |*
*|  |  |                          v                              |  |  |*
*|  |  |                      +-------+                          |  |  |*
*|  |  |                      | SFU 4 | <-- More SFUs...         |  |  |*
*|  |  |                      +-------+                          |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  SFUs forward active streams to each other             |  |  |*
*|  |  |  Star or mesh topology between SFUs                    |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  CHALLENGE 3: Horizontal Scaling (many meetings)              |  |*
*|  |                                                                 |  |*
*|  |  SOLUTION: Meeting-to-SFU Assignment                          |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  Meeting Room Service:                                  |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  1. Client requests to join meeting                    |  |  |*
*|  |  |  2. Room Service checks meeting -> SFU mapping         |  |  |*
*|  |  |     - If exists: return SFU address                    |  |  |*
*|  |  |     - If new: pick least loaded SFU, create mapping    |  |  |*
*|  |  |  3. Client connects to assigned SFU                    |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  Meeting > SFU mapping stored in:                      |  |  |*
*|  |  |  * Redis (fast lookup)                                 |  |  |*
*|  |  |  * Consistent hashing for deterministic routing        |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*WEBINAR MODE (50K+ Viewers)*
*---------------------------*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  WEBINAR ARCHITECTURE                                                  |*
*|                                                                         |*
*|  Different from meetings: Few broadcasters, many view-only attendees  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Panelists (10)                                                |  |*
*|  |      |                                                          |  |*
*|  |      v                                                          |  |*
*|  |  +-------+                                                     |  |*
*|  |  |  SFU  | (handles interactive panelists)                    |  |*
*|  |  +---+---+                                                     |  |*
*|  |      |                                                          |  |*
*|  |      | Transcode to HLS/DASH                                  |  |*
*|  |      |                                                          |  |*
*|  |      v                                                          |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                    CDN                                    ||  |*
*|  |  |                                                           ||  |*
*|  |  |  +---------+  +---------+  +---------+  +---------+     ||  |*
*|  |  |  | Edge 1  |  | Edge 2  |  | Edge 3  |  | Edge N  |     ||  |*
*|  |  |  +----+----+  +----+----+  +----+----+  +----+----+     ||  |*
*|  |  |       |            |            |            |           ||  |*
*|  |  +-------+------------+------------+------------+-----------+|  |*
*|  |          |            |            |            |            |  |*
*|  |          v            v            v            v            |  |*
*|  |     Viewers       Viewers      Viewers      Viewers          |  |*
*|  |     (10K)         (10K)        (10K)        (10K)           |  |*
*|  |                                                                 |  |*
*|  |  KEY DIFFERENCE:                                               |  |*
*|  |  * Viewers use HLS/DASH (CDN-cacheable), not WebRTC           |  |*
*|  |  * Higher latency (5-30 seconds) but infinite scale           |  |*
*|  |  * Q&A via separate signaling channel                         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4.2: SIGNALING SERVER SCALING
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SIGNALING SCALING PATTERN                                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CHALLENGE:                                                    |  |*
*|  |  * WebSocket connections are stateful                         |  |*
*|  |  * Participants in same meeting may connect to different servers| |*
*|  |  * Need to route messages between servers                     |  |*
*|  |                                                                 |  |*
*|  |  SOLUTION: Redis Pub/Sub                                       |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  User A                User B                User C       ||  |*
*|  |  |  (Server 1)            (Server 2)            (Server 1)   ||  |*
*|  |  |      |                     |                     |        ||  |*
*|  |  |      v                     v                     v        ||  |*
*|  |  |  +---------+          +---------+          +---------+   ||  |*
*|  |  |  |Signaling|          |Signaling|          |Signaling|   ||  |*
*|  |  |  |Server 1 |          |Server 2 |          |Server 1 |   ||  |*
*|  |  |  +----+----+          +----+----+          +----+----+   ||  |*
*|  |  |       |                    |                    |        ||  |*
*|  |  |       |    +---------------+---------------+    |        ||  |*
*|  |  |       |    |               |               |    |        ||  |*
*|  |  |       +----+---> Redis Pub/Sub <-----------+----+        ||  |*
*|  |  |            |   (channel: meeting:123)      |             ||  |*
*|  |  |            |                               |             ||  |*
*|  |  |            |  All servers subscribe to     |             ||  |*
*|  |  |            |  meeting channels             |             ||  |*
*|  |  |            |                               |             ||  |*
*|  |  +------------+-------------------------------+-------------+|  |*
*|  |               |                               |              |  |*
*|  |                                                                 |  |*
*|  |  MESSAGE FLOW:                                                 |  |*
*|  |  1. User A sends message via WebSocket to Server 1            |  |*
*|  |  2. Server 1 publishes to Redis channel "meeting:123"         |  |*
*|  |  3. All servers subscribed receive message                    |  |*
*|  |  4. Server 2 forwards to User B                               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ALTERNATIVE: Sticky Sessions                                          |*
*|  Route all participants of same meeting to same server                |*
*|  Simpler but less resilient (server failure affects all)              |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4.3: GLOBAL LOAD BALANCING
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  GEO-ROUTING STRATEGY                                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. DNS-BASED ROUTING                                          |  |*
*|  |     User queries api.zoom.us                                  |  |*
*|  |     DNS returns IP of nearest data center                     |  |*
*|  |     (Route 53 Geolocation, Cloudflare Load Balancing)        |  |*
*|  |                                                                 |  |*
*|  |  2. ANYCAST                                                    |  |*
*|  |     Same IP announced from multiple locations                 |  |*
*|  |     BGP routes to nearest (used for TURN servers)            |  |*
*|  |                                                                 |  |*
*|  |  3. CLIENT-SIDE LATENCY MEASUREMENT                           |  |*
*|  |     Client pings multiple regions                             |  |*
*|  |     Selects lowest latency                                    |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  ZOOM'S APPROACH:                                              |  |*
*|  |                                                                 |  |*
*|  |  1. Client joins meeting                                      |  |*
*|  |  2. Server checks locations of all participants               |  |*
*|  |  3. Selects optimal SFU region(s)                            |  |*
*|  |  4. May use multiple SFUs with cascading for global meetings |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4.4: SECURITY
## ENCRYPTION
*----------*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  ENCRYPTION LAYERS                                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. TRANSPORT ENCRYPTION (Default)                             |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  Client A === DTLS/SRTP ===> SFU === DTLS/SRTP ===> B  |  |  |*
*|  |  |              (encrypted)      |       (encrypted)        |  |  |*
*|  |  |                               |                          |  |  |*
*|  |  |                     SFU can see content                 |  |  |*
*|  |  |                     (needed for routing decisions)      |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  |  Protects against: Network eavesdropping                      |  |*
*|  |  Doesn't protect against: Malicious server                   |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  2. END-TO-END ENCRYPTION (E2EE) - Optional                   |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  Client A ======= Encrypted Media ==============> B    |  |  |*
*|  |  |     |                    |                          |   |  |  |*
*|  |  |     |                    v                          |   |  |  |*
*|  |  |     |               SFU (can't                     |   |  |  |*
*|  |  |     |               decrypt)                       |   |  |  |*
*|  |  |     |                                               |   |  |  |*
*|  |  |     +---------- Keys shared directly ---------------+   |  |  |*
*|  |  |                 (via signaling)                          |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  |  HOW E2EE WORKS:                                              |  |*
*|  |  1. Meeting creator generates symmetric key                   |  |*
*|  |  2. Key shared with participants (encrypted exchange)        |  |*
*|  |  3. Media encrypted before entering WebRTC pipeline          |  |*
*|  |  4. SFU forwards encrypted packets without decrypting        |  |*
*|  |                                                                 |  |*
*|  |  CHALLENGES:                                                   |  |*
*|  |  * Recording: Can't server-record (client must record)       |  |*
*|  |  * Phone dial-in: Not supported                              |  |*
*|  |  * Performance: Extra encryption layer                       |  |*
*|  |  * Key management: Rotation when participants change         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ZOOM'S E2EE:                                                          |*
*|  * Uses Insertable Streams API (encrypt before RTP)                   |*
*|  * AES-256-GCM encryption                                             |*
*|  * Per-meeting key                                                    |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*MEETING SECURITY*
*----------------*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  SECURITY FEATURES                                                     |*
*|                                                                         |*
*|  1. MEETING PASSWORD                                                   |*
*|     * Stored hashed (bcrypt)                                          |*
*|     * Verified on join                                                |*
*|     * Embedded in invite links (encrypted)                            |*
*|                                                                         |*
*|  2. WAITING ROOM                                                       |*
*|     * Host must admit each participant                                |*
*|     * Name/email verification                                         |*
*|     * Prevents "zoom bombing"                                         |*
*|                                                                         |*
*|  3. MEETING LOCK                                                       |*
*|     * Host can lock meeting after start                               |*
*|     * No new participants can join                                    |*
*|                                                                         |*
*|  4. PARTICIPANT CONTROLS                                               |*
*|     * Mute all                                                        |*
*|     * Disable video                                                   |*
*|     * Disable screen sharing for non-hosts                           |*
*|     * Remove participant                                              |*
*|     * Report user                                                     |*
*|                                                                         |*
*|  5. AUTHENTICATION                                                     |*
*|     * SSO integration                                                 |*
*|     * OAuth (Google, Microsoft)                                       |*
*|     * Require authentication to join                                  |*
*|                                                                         |*
*|  6. DOMAIN RESTRICTIONS                                                |*
*|     * Only users from specific email domains                         |*
*|     * Restrict to company accounts                                    |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4.5: RELIABILITY
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  HANDLING FAILURES                                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. PACKET LOSS                                                 |  |*
*|  |                                                                 |  |*
*|  |  Audio (Opus):                                                 |  |*
*|  |  * Forward Error Correction (FEC)                             |  |*
*|  |  * Packet Loss Concealment (interpolate missing samples)      |  |*
*|  |                                                                 |  |*
*|  |  Video:                                                        |  |*
*|  |  * NACK (Negative Acknowledgment) - request retransmission   |  |*
*|  |  * PLI (Picture Loss Indication) - request keyframe          |  |*
*|  |  * FEC for video (optional)                                   |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  2. NETWORK SWITCH (Wi-Fi > LTE)                              |  |*
*|  |                                                                 |  |*
*|  |  ICE Restart:                                                 |  |*
*|  |  * Detect network change                                      |  |*
*|  |  * Generate new ICE candidates                                |  |*
*|  |  * Renegotiate connection                                     |  |*
*|  |  * ~1-3 second interruption                                   |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  3. SFU SERVER FAILURE                                         |  |*
*|  |                                                                 |  |*
*|  |  Detection:                                                    |  |*
*|  |  * Health checks (signaling server monitors SFUs)            |  |*
*|  |  * Client detects connection loss                            |  |*
*|  |                                                                 |  |*
*|  |  Recovery:                                                     |  |*
*|  |  * Automatic reconnection to backup SFU                      |  |*
*|  |  * Meeting state reconstructed from signaling server         |  |*
*|  |  * Brief interruption (2-5 seconds)                          |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  4. SIGNALING SERVER FAILURE                                   |  |*
*|  |                                                                 |  |*
*|  |  * Multiple signaling servers (active-active)                 |  |*
*|  |  * WebSocket reconnects to healthy server                    |  |*
*|  |  * Meeting state in Redis (survives server death)            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  GRACEFUL DEGRADATION:                                                  |*
*|                                                                         |*
*|  When bandwidth drops:                                                 |*
*|  1. Reduce video resolution                                           |*
*|  2. Reduce frame rate                                                 |*
*|  3. Switch to audio-only                                              |*
*|  4. Never drop the call entirely                                      |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4.6: MONITORING AND QUALITY
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  QUALITY METRICS TO MONITOR                                            |*
*|                                                                         |*
*|  +----------------------------------------------------------------+   |*
*|  |                                                                |   |*
*|  |  Metric              Good         Warning      Bad            |   |*
*|  |  ------------------------------------------------------------ |   |*
*|  |                                                                |   |*
*|  |  Packet Loss         < 0.5%       0.5-2%       > 2%           |   |*
*|  |  Jitter              < 20ms       20-50ms      > 50ms         |   |*
*|  |  RTT                 < 100ms      100-300ms    > 300ms        |   |*
*|  |  Bitrate             Target       -20%         -50%           |   |*
*|  |  Frame Rate          Target       -30%         -50%           |   |*
*|  |  Resolution          Target       -1 level     -2 levels      |   |*
*|  |                                                                |   |*
*|  +----------------------------------------------------------------+   |*
*|                                                                         |*
*|  WEBRTC STATS API:                                                      |*
*|                                                                         |*
*|  pc.getStats() returns:                                                |*
*|  * Bytes sent/received                                                |*
*|  * Packets sent/received/lost                                         |*
*|  * Round trip time                                                    |*
*|  * Jitter                                                             |*
*|  * Current bitrate                                                    |*
*|  * Frame rate                                                         |*
*|  * Resolution                                                         |*
*|                                                                         |*
*|  CLIENT-SIDE REPORTING:                                                 |*
*|  * Clients periodically report quality metrics                        |*
*|  * Aggregated in analytics pipeline                                   |*
*|  * Alert on degraded quality                                          |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF CHAPTER 4
