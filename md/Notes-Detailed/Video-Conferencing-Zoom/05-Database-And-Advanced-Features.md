# VIDEO CONFERENCING SYSTEM (ZOOM-LIKE)
*Chapter 5: Database Design and Advanced Features*

## SECTION 5.1: DATABASE DESIGN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATABASE CHOICES BY DATA TYPE                                         |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  Data Type              Database          Why                 |   |
|  |  ------------------------------------------------------------ |   |
|  |                                                                |   |
|  |  Users, Meetings,       PostgreSQL        ACID, relationships |   |
|  |  Billing                                                       |   |
|  |                                                                |   |
|  |  Session State,         Redis             Fast, ephemeral     |   |
|  |  Presence, Mapping                                            |   |
|  |                                                                |   |
|  |  Chat Messages          Cassandra         High write volume,  |   |
|  |  (persistent)                             time-series         |   |
|  |                                                                |   |
|  |  Analytics, Logs        Cassandra /       Write-heavy,        |   |
|  |                         ClickHouse        analytics queries   |   |
|  |                                                                |   |
|  |  Recordings             S3 / GCS          Large blobs,        |   |
|  |                                           cheap storage       |   |
|  |                                                                |   |
|  |  Search (recordings,    Elasticsearch     Full-text search    |   |
|  |  transcripts)                                                 |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### POSTGRESQL SCHEMA

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USERS TABLE                                                           |
|                                                                         |
|  CREATE TABLE users (                                                  |
|      user_id         UUID PRIMARY KEY,                                 |
|      email           VARCHAR(255) UNIQUE NOT NULL,                     |
|      password_hash   VARCHAR(255),                                     |
|      display_name    VARCHAR(255),                                     |
|      avatar_url      VARCHAR(500),                                     |
|      pmi             VARCHAR(11) UNIQUE,  -- Personal Meeting ID      |
|      account_type    VARCHAR(20),  -- free, pro, business             |
|      timezone        VARCHAR(50),                                      |
|      sso_provider    VARCHAR(50),                                      |
|      sso_id          VARCHAR(255),                                     |
|      created_at      TIMESTAMP DEFAULT NOW(),                          |
|      updated_at      TIMESTAMP DEFAULT NOW()                           |
|  );                                                                     |
|                                                                         |
|  CREATE INDEX idx_users_email ON users(email);                         |
|  CREATE INDEX idx_users_pmi ON users(pmi);                             |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  MEETINGS TABLE                                                        |
|                                                                         |
|  CREATE TABLE meetings (                                               |
|      meeting_id      VARCHAR(11) PRIMARY KEY,  -- 123-456-7890        |
|      host_user_id    UUID REFERENCES users(user_id),                   |
|      topic           VARCHAR(255),                                     |
|      password_hash   VARCHAR(255),                                     |
|      meeting_type    VARCHAR(20),  -- instant, scheduled, recurring   |
|      start_time      TIMESTAMP,                                        |
|      duration_mins   INTEGER,                                          |
|      timezone        VARCHAR(50),                                      |
|      status          VARCHAR(20),  -- scheduled, started, ended       |
|      settings        JSONB,  -- waiting_room, mute_on_entry, etc.    |
|      recurrence      JSONB,  -- recurrence pattern                    |
|      created_at      TIMESTAMP DEFAULT NOW(),                          |
|      ended_at        TIMESTAMP                                         |
|  );                                                                     |
|                                                                         |
|  CREATE INDEX idx_meetings_host ON meetings(host_user_id);             |
|  CREATE INDEX idx_meetings_start ON meetings(start_time);              |
|  CREATE INDEX idx_meetings_status ON meetings(status);                 |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  MEETING PARTICIPANTS (Historical)                                     |
|                                                                         |
|  CREATE TABLE meeting_participants (                                   |
|      id              UUID PRIMARY KEY,                                 |
|      meeting_id      VARCHAR(11) REFERENCES meetings(meeting_id),      |
|      user_id         UUID REFERENCES users(user_id),                   |
|      display_name    VARCHAR(255),  -- for guests                     |
|      email           VARCHAR(255),                                     |
|      join_time       TIMESTAMP,                                        |
|      leave_time      TIMESTAMP,                                        |
|      duration_mins   INTEGER,                                          |
|      device_type     VARCHAR(50),  -- desktop, mobile, web            |
|      role            VARCHAR(20)   -- host, co-host, participant      |
|  );                                                                     |
|                                                                         |
|  CREATE INDEX idx_participants_meeting ON                               |
|      meeting_participants(meeting_id);                                 |
|  CREATE INDEX idx_participants_user ON                                  |
|      meeting_participants(user_id);                                    |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  RECORDINGS TABLE                                                      |
|                                                                         |
|  CREATE TABLE recordings (                                             |
|      recording_id    UUID PRIMARY KEY,                                 |
|      meeting_id      VARCHAR(11) REFERENCES meetings(meeting_id),      |
|      recording_type  VARCHAR(20),  -- cloud, shared_screen            |
|      storage_path    VARCHAR(500),  -- S3 path                        |
|      file_size       BIGINT,                                          |
|      duration_secs   INTEGER,                                          |
|      format          VARCHAR(10),  -- mp4, m4a                        |
|      status          VARCHAR(20),  -- processing, ready, deleted      |
|      transcript_path VARCHAR(500),                                     |
|      created_at      TIMESTAMP DEFAULT NOW(),                          |
|      expires_at      TIMESTAMP                                         |
|  );                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### REDIS DATA STRUCTURES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REAL-TIME DATA IN REDIS                                               |
|                                                                         |
|  1. ACTIVE MEETING STATE                                               |
|                                                                         |
|  Key: meeting:{meeting_id}:state                                       |
|  Type: Hash                                                            |
|  {                                                                      |
|    "status": "active",                                                 |
|    "host_id": "uuid",                                                  |
|    "start_time": "1705000000",                                         |
|    "participant_count": "15",                                          |
|    "recording": "true",                                                |
|    "sfu_server": "sfu-us-west-1.zoom.us"                              |
|  }                                                                      |
|  TTL: Auto-expire after meeting end + buffer                          |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. MEETING PARTICIPANTS (Real-time)                                   |
|                                                                         |
|  Key: meeting:{meeting_id}:participants                                |
|  Type: Hash                                                            |
|  {                                                                      |
|    "user_uuid_1": '{"name":"Alice","role":"host","muted":false}',    |
|    "user_uuid_2": '{"name":"Bob","role":"participant","muted":true}' |
|  }                                                                      |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. USER PRESENCE                                                      |
|                                                                         |
|  Key: presence:{user_id}                                              |
|  Type: Hash                                                            |
|  {                                                                      |
|    "status": "in_meeting",                                             |
|    "meeting_id": "123-456-789",                                        |
|    "device": "desktop",                                                |
|    "last_active": "1705000000"                                         |
|  }                                                                      |
|  TTL: 60 seconds (refreshed by heartbeat)                             |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  4. SIGNALING SERVER > USER MAPPING                                    |
|                                                                         |
|  Key: user_connection:{user_id}                                        |
|  Type: String                                                          |
|  Value: "signaling-server-3.us-west-1"                                |
|                                                                         |
|  Used to route messages to correct signaling server                   |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  5. MEETING > SFU MAPPING                                              |
|                                                                         |
|  Key: meeting_sfu:{meeting_id}                                         |
|  Type: String                                                          |
|  Value: "sfu-us-west-2.zoom.us:5004"                                  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  6. WAITING ROOM                                                       |
|                                                                         |
|  Key: meeting:{meeting_id}:waiting_room                               |
|  Type: List                                                            |
|  ["user_uuid_1", "user_uuid_2", ...]                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.2: CHAT SYSTEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IN-MEETING CHAT ARCHITECTURE                                          |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  TWO TYPES:                                                    |  |
|  |                                                                 |  |
|  |  1. PUBLIC CHAT (to everyone)                                  |  |
|  |     * Routed through signaling server                         |  |
|  |     * Broadcast to all participants                           |  |
|  |     * Stored for meeting history                              |  |
|  |                                                                 |  |
|  |  2. PRIVATE CHAT (to specific person)                         |  |
|  |     * Routed through signaling server                         |  |
|  |     * Sent only to recipient                                  |  |
|  |     * Optional storage                                        |  |
|  |                                                                 |  |
|  |  FLOW:                                                         |  |
|  |                                                                 |  |
|  |  User A -> Signaling -> Redis Pub/Sub -> Signaling -> User B |  |
|  |              |                              |                  |  |
|  |              |                              |                  |  |
|  |              +-------> Kafka -> Cassandra (persist)          |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  CHAT MESSAGE SCHEMA (Cassandra):                                       |
|                                                                         |
|  CREATE TABLE chat_messages (                                          |
|      meeting_id    TEXT,                                               |
|      message_id    TIMEUUID,                                           |
|      sender_id     UUID,                                               |
|      sender_name   TEXT,                                               |
|      recipient_id  UUID,  -- null for public                          |
|      content       TEXT,                                               |
|      message_type  TEXT,  -- text, file, reaction                     |
|      created_at    TIMESTAMP,                                          |
|      PRIMARY KEY ((meeting_id), message_id)                           |
|  ) WITH CLUSTERING ORDER BY (message_id ASC);                         |
|                                                                         |
|  Partitioned by meeting_id for efficient retrieval                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.3: BREAKOUT ROOMS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BREAKOUT ROOMS ARCHITECTURE                                           |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Main Meeting (meeting_id: 123-456-789)                        |  |
|  |  +---------------------------------------------------------+  |  |
|  |  |                        SFU                              |  |  |
|  |  |           (all participants initially)                  |  |  |
|  |  +---------------------------------------------------------+  |  |
|  |                                                                 |  |
|  |  Host creates breakout rooms:                                  |  |
|  |                                                                 |  |
|  |  +-------------+  +-------------+  +-------------+           |  |
|  |  | Breakout 1  |  | Breakout 2  |  | Breakout 3  |           |  |
|  |  | (sub-room)  |  | (sub-room)  |  | (sub-room)  |           |  |
|  |  | Users A,B,C |  | Users D,E,F |  | Users G,H,I |           |  |
|  |  +-------------+  +-------------+  +-------------+           |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  IMPLEMENTATION OPTIONS:                                                |
|                                                                         |
|  OPTION 1: Sub-rooms on same SFU                                      |
|  * Breakout rooms are logical groupings                               |
|  * Same SFU server handles all                                        |
|  * SFU routes media only within each room                            |
|  * PROS: Simple, fast switching                                       |
|  * CONS: Single SFU capacity limit                                    |
|                                                                         |
|  OPTION 2: Separate SFU per breakout                                  |
|  * Each breakout room gets own SFU                                    |
|  * PROS: Scales better                                                |
|  * CONS: Slower room switching, more complex                         |
|                                                                         |
|  ZOOM USES: Option 1 for small breakouts, Option 2 for large meetings|
|                                                                         |
|  DATA MODEL:                                                            |
|                                                                         |
|  meeting:{meeting_id}:breakout_rooms = {                              |
|    "room_1": ["user_a", "user_b", "user_c"],                         |
|    "room_2": ["user_d", "user_e", "user_f"],                         |
|    "room_3": ["user_g", "user_h", "user_i"]                          |
|  }                                                                      |
|                                                                         |
|  HOST CAPABILITIES:                                                     |
|  * Create/delete rooms                                                |
|  * Assign participants                                                |
|  * Broadcast message to all rooms                                     |
|  * Move between rooms                                                 |
|  * Close all rooms (return to main)                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.4: VIRTUAL BACKGROUNDS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  VIRTUAL BACKGROUND IMPLEMENTATION                                     |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  PROCESSING PIPELINE (Client-side):                            |  |
|  |                                                                 |  |
|  |  Camera -> Segmentation -> Background Replace -> Encoder -> SFU|  |
|  |    |           |                  |                            |  |
|  |    |           |                  |                            |  |
|  |    v           v                  v                            |  |
|  |  Raw       Person mask      Composited                        |  |
|  |  frame     (foreground)     frame                             |  |
|  |                                                                 |  |
|  |  SEGMENTATION APPROACHES:                                      |  |
|  |                                                                 |  |
|  |  1. ML Model (Most common)                                    |  |
|  |     * TensorFlow.js / WebML                                   |  |
|  |     * MediaPipe Selfie Segmentation                          |  |
|  |     * Runs on GPU (WebGL)                                    |  |
|  |     * ~30fps on modern devices                               |  |
|  |                                                                 |  |
|  |  2. Green Screen                                              |  |
|  |     * Color keying (chroma key)                               |  |
|  |     * Requires physical green screen                          |  |
|  |     * Most accurate edges                                     |  |
|  |                                                                 |  |
|  |  BLUR EFFECT:                                                  |  |
|  |  Same segmentation, but apply Gaussian blur to background    |  |
|  |  instead of replacement                                       |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  PERFORMANCE CONSIDERATIONS:                                            |
|  * GPU required for real-time ML                                      |
|  * Falls back to lower quality on weak devices                        |
|  * ~10-20% additional CPU usage                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.5: PHONE DIAL-IN (PSTN GATEWAY)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PSTN INTEGRATION                                                      |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |  Phone User                        Zoom Infrastructure         |  |
|  |                                                                 |  |
|  |   --- PSTN --> Carrier --> SIP Trunk --> PSTN Gateway --> SFU  |  |
|  |                                                |                |  |
|  |                                          Transcodes:            |  |
|  |                                          G.711 - Opus          |  |
|  |                                          RTP - WebRTC          |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  FLOW:                                                                  |
|  1. User dials toll-free number (1-888-XXX-XXXX)                      |
|  2. IVR prompts for meeting ID                                        |
|  3. PSTN gateway looks up meeting                                     |
|  4. Gateway joins meeting as hidden participant                       |
|  5. Audio transcoded and mixed with other participants                |
|                                                                         |
|  PROVIDERS:                                                             |
|  * Twilio (SIP trunking)                                              |
|  * Bandwidth.com                                                       |
|  * Direct carrier relationships                                        |
|                                                                         |
|  DIAL-OUT (Zoom calls you):                                            |
|  Meeting host requests dial-out > Gateway initiates call to phone    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.6: INTERVIEW QUESTIONS & ANSWERS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q1: How would you handle a meeting with 1000 participants?           |
|                                                                         |
|  A: Use SFU cascading architecture:                                    |
|  * Split participants across multiple SFU servers (100-200 each)     |
|  * SFUs connect to each other to share active speaker streams        |
|  * Only forward active speaker + few recent speakers (not all 1000)  |
|  * Gallery view shows video of subset, thumbnails for others         |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  Q2: Why WebRTC over other protocols?                                  |
|                                                                         |
|  A: WebRTC advantages:                                                 |
|  * Browser-native (no plugin)                                         |
|  * Low latency (optimized for real-time)                             |
|  * Built-in encryption (DTLS-SRTP)                                    |
|  * NAT traversal (ICE/STUN/TURN)                                      |
|  * Adaptive bitrate built-in                                          |
|  Alternative: Zoom's desktop app uses proprietary protocol for        |
|  additional optimizations                                              |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  Q3: How do you ensure low latency globally?                          |
|                                                                         |
|  A:                                                                     |
|  * Deploy SFUs in multiple regions                                    |
|  * Route users to nearest SFU (geo DNS)                              |
|  * Use SFU cascading for global meetings                             |
|  * TURN servers at edge locations                                    |
|  * UDP preferred over TCP                                            |
|  * Measure RTT, optimize routing                                     |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  Q4: SFU vs MCU - when to use each?                                   |
|                                                                         |
|  A:                                                                     |
|  SFU (Selective Forwarding Unit):                                     |
|  * Most video conferencing (Zoom, Meet, Teams)                       |
|  * Lower server CPU (no transcoding)                                 |
|  * Lower latency                                                      |
|  * Flexible client layouts                                            |
|                                                                         |
|  MCU (Multipoint Control Unit):                                       |
|  * PSTN gateways (phone dial-in)                                     |
|  * Very weak clients (can only decode single stream)                 |
|  * Fixed layout requirements                                          |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  Q5: How does E2EE work with SFU?                                     |
|                                                                         |
|  A: Insertable Streams API:                                           |
|  1. Client encrypts media BEFORE WebRTC encoding                     |
|  2. Encrypted payload goes through normal WebRTC pipeline            |
|  3. SFU forwards encrypted packets without decrypting               |
|  4. Receiving client decrypts after WebRTC decoding                 |
|  5. Keys exchanged via signaling (also encrypted)                   |
|  Limitation: SFU can't do simulcast selection efficiently           |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  Q6: How do you handle poor network conditions?                       |
|                                                                         |
|  A: Adaptive strategies:                                               |
|  1. Simulcast: Sender encodes multiple resolutions                   |
|  2. SFU picks appropriate quality per receiver                       |
|  3. Congestion control: Reduce bitrate on packet loss                |
|  4. FEC: Forward error correction for audio                          |
|  5. Jitter buffer: Smooth out packet timing variations               |
|  6. Graceful degradation: Video > audio-only if needed              |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  Q7: How would you implement cloud recording?                         |
|                                                                         |
|  A:                                                                     |
|  1. Recording bot joins meeting (hidden participant)                 |
|  2. Receives all streams from SFU                                    |
|  3. Mixes/composes video in real-time                               |
|  4. Writes to temporary storage                                      |
|  5. On meeting end: Upload to S3, trigger processing                |
|  6. Post-processing: Transcode, generate thumbnails, transcript     |
|  7. Notify user when ready                                           |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  Q8: Capacity estimation for 1M concurrent meetings?                  |
|                                                                         |
|  A:                                                                     |
|  Assumptions:                                                          |
|  * Average 5 participants per meeting                                |
|  * 720p video: 1.5 Mbps per stream                                   |
|                                                                         |
|  Per meeting bandwidth:                                               |
|  * Upload: 5 x 1.5 = 7.5 Mbps to SFU                                |
|  * Download: 5 x (5-1) x 1.5 = 30 Mbps from SFU (worst case)        |
|  * With simulcast: ~15 Mbps from SFU                                 |
|                                                                         |
|  SFU capacity: ~200 participants per server                          |
|  Meetings per SFU: 200/5 = 40 meetings                               |
|  SFUs needed: 1M/40 = 25,000 SFU servers                             |
|                                                                         |
|  Plus: Signaling servers, TURN servers, storage, etc.                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.7: COMPLETE SYSTEM SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ZOOM-LIKE SYSTEM - KEY COMPONENTS SUMMARY                             |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  Component          Technology          Purpose               |   |
|  |  ------------------------------------------------------------ |   |
|  |                                                                |   |
|  |  Media Transport    WebRTC/RTP/SRTP     Audio/video streams   |   |
|  |  Media Server       SFU                 Route media           |   |
|  |  Signaling          WebSocket           Coordination          |   |
|  |  NAT Traversal      STUN/TURN           Connectivity          |   |
|  |  Codec (Video)      H.264/VP8/VP9       Video encoding        |   |
|  |  Codec (Audio)      Opus                Audio encoding        |   |
|  |  User DB            PostgreSQL          Persistent data       |   |
|  |  Real-time State    Redis               Ephemeral state       |   |
|  |  Chat Storage       Cassandra           Message history       |   |
|  |  Recordings         S3                  Video storage         |   |
|  |  Message Bus        Kafka               Event streaming       |   |
|  |  Load Balancing     GSLB + L7 LB        Traffic distribution  |   |
|  |  CDN                CloudFront/Akamai   Static assets         |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
|  KEY DESIGN DECISIONS:                                                  |
|                                                                         |
|  1. SFU over MCU (scalability, latency)                               |
|  2. WebRTC for browser support                                        |
|  3. Simulcast for adaptive quality                                    |
|  4. Regional SFUs with cascading for global                          |
|  5. E2EE optional (impacts features)                                  |
|  6. CDN for webinars (scale to millions)                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

END OF ZOOM HLD
