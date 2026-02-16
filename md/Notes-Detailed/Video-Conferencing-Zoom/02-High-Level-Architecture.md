# VIDEO CONFERENCING SYSTEM (ZOOM-LIKE) - HIGH LEVEL DESIGN

CHAPTER 2: HIGH-LEVEL ARCHITECTURE
SECTION 2.1: SYSTEM ARCHITECTURE DIAGRAM
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  ZOOM-LIKE ARCHITECTURE OVERVIEW                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |                         CLIENTS                                 |  |*
*|  |  +----------+ +----------+ +----------+ +----------+          |  |*
*|  |  | Desktop  | |  Mobile  | |   Web    | |  Phone   |          |  |*
*|  |  |  App     | |   App    | |  Client  | | (PSTN)   |          |  |*
*|  |  +----+-----+ +----+-----+ +----+-----+ +----+-----+          |  |*
*|  |       |            |            |            |                 |  |*
*|  |       +------------+------------+------------+                 |  |*
*|  |                    |            |                              |  |*
*|  +--------------------+------------+------------------------------+  |*
*|                       |            |                                  |*
*|                       v            v                                  |*
*|  +-------------------------------------------------------------------+|*
*|  |                                                                   ||*
*|  |                      EDGE LAYER (Global)                         ||*
*|  |                                                                   ||*
*|  |  +-------------------------------------------------------------+ ||*
*|  |  |                     CDN / Edge Servers                      | ||*
*|  |  |     (Static assets, WebRTC TURN servers, low latency)      | ||*
*|  |  +-------------------------------------------------------------+ ||*
*|  |                                                                   ||*
*|  |  +------------------+         +------------------+              ||*
*|  |  |  Global Load     |         |   DNS-based      |              ||*
*|  |  |  Balancer (GSLB) |         |   Geo-routing    |              ||*
*|  |  +--------+---------+         +--------+---------+              ||*
*|  |           |                            |                         ||*
*|  +-----------+----------------------------+-------------------------+|*
*|              |                            |                          |*
*|              v                            v                          |*
*|  +-------------------------------------------------------------------+|*
*|  |                                                                   ||*
*|  |                    REGIONAL DATA CENTERS                         ||*
*|  |                                                                   ||*
*|  |  +-------------------------------------------------------------+ ||*
*|  |  |                    API GATEWAY LAYER                        | ||*
*|  |  |                                                             | ||*
*|  |  |  * Authentication / Authorization                          | ||*
*|  |  |  * Rate Limiting                                           | ||*
*|  |  |  * Request Routing                                         | ||*
*|  |  |  * TLS Termination                                         | ||*
*|  |  |                                                             | ||*
*|  |  +---------------------------+---------------------------------+ ||*
*|  |                              |                                    ||*
*|  |            +-----------------+-----------------+                 ||*
*|  |            |                 |                 |                 ||*
*|  |            v                 v                 v                 ||*
*|  |  +-----------------+ +-------------+ +-----------------+        ||*
*|  |  |   Signaling     | |   Media     | |   Application   |        ||*
*|  |  |   Service       | |   Service   | |   Services      |        ||*
*|  |  |                 | |             | |                 |        ||*
*|  |  | * WebSocket     | | * SFU       | | * User Service |        ||*
*|  |  | * Meeting join  | | * TURN      | | * Meeting Svc  |        ||*
*|  |  | * Presence      | | * Recording | | * Chat Service |        ||*
*|  |  | * Events        | | * Transcode | | * Schedule Svc |        ||*
*|  |  |                 | |             | | * Billing Svc  |        ||*
*|  |  +--------+--------+ +------+------+ +-------+---------+        ||*
*|  |           |                 |                |                   ||*
*|  |           +-----------------+----------------+                   ||*
*|  |                             |                                    ||*
*|  |                             v                                    ||*
*|  |  +-------------------------------------------------------------+ ||*
*|  |  |                     DATA LAYER                              | ||*
*|  |  |                                                             | ||*
*|  |  |  +-----------+ +-----------+ +-----------+ +-----------+  | ||*
*|  |  |  |PostgreSQL | |   Redis   | | Cassandra | |    S3     |  | ||*
*|  |  |  | (Users,   | | (Session, | |(Analytics,| |(Recordings|  | ||*
*|  |  |  | Meetings) | |  Presence)| |   Logs)   | |  ,Assets) |  | ||*
*|  |  |  +-----------+ +-----------+ +-----------+ +-----------+  | ||*
*|  |  |                                                             | ||*
*|  |  +-------------------------------------------------------------+ ||*
*|  |                                                                   ||*
*|  +-------------------------------------------------------------------+|*
*|                                                                        |*
*|  +-------------------------------------------------------------------+|*
*|  |                                                                   ||*
*|  |                    MESSAGE QUEUE LAYER                           ||*
*|  |                                                                   ||*
*|  |  +-----------------------------------------------------------+   ||*
*|  |  |                       KAFKA                               |   ||*
*|  |  |                                                           |   ||*
*|  |  |  * Meeting events       * Analytics events                |   ||*
*|  |  |  * Recording jobs       * Notification triggers          |   ||*
*|  |  |  * Transcription jobs   * Audit logs                     |   ||*
*|  |  |                                                           |   ||*
*|  |  +-----------------------------------------------------------+   ||*
*|  |                                                                   ||*
*|  +-------------------------------------------------------------------+|*
*|                                                                        |*
*+------------------------------------------------------------------------+*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2.2: CORE COMPONENTS
## +------------------------------------------------------------------------------+
*|                                                                              |*
*|  COMPONENT 1: SIGNALING SERVICE                                              |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  PURPOSE: Coordinate meeting setup and control messages               | |*
*|  |                                                                        | |*
*|  |  RESPONSIBILITIES:                                                     | |*
*|  |  * WebSocket connection management                                    | |*
*|  |  * Meeting room creation/join/leave                                   | |*
*|  |  * SDP (Session Description Protocol) exchange                        | |*
*|  |  * ICE candidate exchange                                             | |*
*|  |  * Participant presence                                               | |*
*|  |  * Host controls (mute, kick, etc.)                                   | |*
*|  |  * Chat message routing (small messages)                              | |*
*|  |                                                                        | |*
*|  |  PROTOCOL: WebSocket over TLS                                         | |*
*|  |                                                                        | |*
*|  |  SCALING:                                                              | |*
*|  |  * Stateful (WebSocket connections)                                   | |*
*|  |  * Use Redis Pub/Sub for cross-instance communication                | |*
*|  |  * Consistent hashing to route same meeting to same server           | |*
*|  |                                                                        | |*
*|  |  MESSAGE TYPES:                                                        | |*
*|  |  * join_meeting, leave_meeting                                       | |*
*|  |  * offer, answer (SDP)                                               | |*
*|  |  * ice_candidate                                                     | |*
*|  |  * mute, unmute, kick_participant                                    | |*
*|  |  * start_recording, stop_recording                                   | |*
*|  |  * raise_hand, reaction                                              | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  COMPONENT 2: MEDIA SERVICE (SFU)                                            |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  PURPOSE: Handle audio/video streams                                  | |*
*|  |                                                                        | |*
*|  |  RESPONSIBILITIES:                                                     | |*
*|  |  * Receive media streams from participants                           | |*
*|  |  * Forward streams to other participants (selective)                 | |*
*|  |  * Simulcast handling (pick best quality per receiver)              | |*
*|  |  * Bandwidth estimation                                               | |*
*|  |  * DTLS/SRTP encryption                                               | |*
*|  |  * RTP/RTCP protocol handling                                        | |*
*|  |  * Audio mixing (for phone dial-in)                                  | |*
*|  |                                                                        | |*
*|  |  PROTOCOLS:                                                            | |*
*|  |  * WebRTC (RTP/RTCP over UDP)                                        | |*
*|  |  * DTLS-SRTP for encryption                                          | |*
*|  |  * ICE/STUN/TURN for NAT traversal                                   | |*
*|  |                                                                        | |*
*|  |  ARCHITECTURE:                                                         | |*
*|  |  +---------------------------------------------------------------+   | |*
*|  |  |                                                               |   | |*
*|  |  |                     SFU Server                               |   | |*
*|  |  |                                                               |   | |*
*|  |  |  +---------------------------------------------------------+ |   | |*
*|  |  |  |                  Meeting Room X                         | |   | |*
*|  |  |  |                                                         | |   | |*
*|  |  |  |  User A Stream --> +----------+ --> User B             | |   | |*
*|  |  |  |  User B Stream --> | Router/  | --> User A             | |   | |*
*|  |  |  |  User C Stream --> | Switcher | --> User C             | |   | |*
*|  |  |  |                    +----------+                         | |   | |*
*|  |  |  |                                                         | |   | |*
*|  |  |  |  Decides which streams to forward based on:            | |   | |*
*|  |  |  |  * Active speaker                                       | |   | |*
*|  |  |  |  * Receiver's bandwidth                                 | |   | |*
*|  |  |  |  * View mode (gallery vs speaker)                      | |   | |*
*|  |  |  |                                                         | |   | |*
*|  |  |  +---------------------------------------------------------+ |   | |*
*|  |  |                                                               |   | |*
*|  |  +---------------------------------------------------------------+   | |*
*|  |                                                                        | |*
*|  |  SCALING:                                                              | |*
*|  |  * Horizontally scale SFU servers                                    | |*
*|  |  * Each meeting assigned to specific SFU(s)                          | |*
*|  |  * Large meetings: Multiple SFUs cascade (hierarchical)              | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  COMPONENT 3: TURN SERVER                                                    |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  PURPOSE: NAT traversal for clients behind firewalls                  | |*
*|  |                                                                        | |*
*|  |  WHY NEEDED:                                                           | |*
*|  |  * ~15% of connections can't establish direct peer connection        | |*
*|  |  * Corporate firewalls, symmetric NAT                                 | |*
*|  |                                                                        | |*
*|  |  HOW IT WORKS:                                                         | |*
*|  |  +---------------------------------------------------------------+   | |*
*|  |  |                                                               |   | |*
*|  |  |  Client A                              Client B               |   | |*
*|  |  |  (behind NAT)                          (behind NAT)           |   | |*
*|  |  |      |                                      |                 |   | |*
*|  |  |      |                                      |                 |   | |*
*|  |  |      +----------> TURN Server <------------+                 |   | |*
*|  |  |                   (relays media)                              |   | |*
*|  |  |                                                               |   | |*
*|  |  |  Media flows: A --> TURN --> B                               |   | |*
*|  |  |                                                               |   | |*
*|  |  +---------------------------------------------------------------+   | |*
*|  |                                                                        | |*
*|  |  SCALING:                                                              | |*
*|  |  * Deploy at edge locations globally                                 | |*
*|  |  * High bandwidth cost (relaying all media)                          | |*
*|  |  * Use STUN first (free), fallback to TURN                          | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*

SECTION 2.3: MEETING SERVICE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  MEETING SERVICE RESPONSIBILITIES                                      |*
*|                                                                         |*
*|  * Create meetings (instant, scheduled, recurring)                    |*
*|  * Generate meeting IDs and passwords                                 |*
*|  * Store meeting metadata                                             |*
*|  * Manage meeting settings                                            |*
*|  * Handle meeting lifecycle                                           |*
*|                                                                         |*
*|  MEETING DATA MODEL:                                                    |*
*|                                                                         |*
*|  +----------------------------------------------------------------+   |*
*|  |                                                                |   |*
*|  |  Meeting {                                                     |   |*
*|  |    meeting_id: string (unique, e.g., "123-456-789")          |   |*
*|  |    host_user_id: uuid                                        |   |*
*|  |    topic: string                                              |   |*
*|  |    password: string (optional, hashed)                       |   |*
*|  |    type: INSTANT | SCHEDULED | RECURRING                     |   |*
*|  |    start_time: timestamp (for scheduled)                     |   |*
*|  |    duration_minutes: int                                     |   |*
*|  |    timezone: string                                          |   |*
*|  |    recurrence: {                                             |   |*
*|  |      type: DAILY | WEEKLY | MONTHLY                          |   |*
*|  |      interval: int                                           |   |*
*|  |      end_date: timestamp                                     |   |*
*|  |    }                                                          |   |*
*|  |    settings: {                                                |   |*
*|  |      waiting_room: boolean                                   |   |*
*|  |      join_before_host: boolean                               |   |*
*|  |      mute_on_entry: boolean                                  |   |*
*|  |      allow_recording: boolean                                |   |*
*|  |      e2ee_enabled: boolean                                   |   |*
*|  |    }                                                          |   |*
*|  |    status: SCHEDULED | STARTED | ENDED                       |   |*
*|  |    created_at: timestamp                                     |   |*
*|  |  }                                                             |   |*
*|  |                                                                |   |*
*|  +----------------------------------------------------------------+   |*
*|                                                                         |*
*|  MEETING ID GENERATION:                                                 |*
*|                                                                         |*
*|  Option 1: Sequential with checksum                                   |*
*|  123-456-7890 (10-11 digits, includes checksum for validation)       |*
*|                                                                         |*
*|  Option 2: Random                                                      |*
*|  Random 9-11 digits, check uniqueness                                |*
*|                                                                         |*
*|  Zoom uses: Personal Meeting ID (PMI) + generated IDs                |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2.4: RECORDING SERVICE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  RECORDING ARCHITECTURE                                                |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TWO TYPES OF RECORDING:                                       |  |*
*|  |                                                                 |  |*
*|  |  1. LOCAL RECORDING                                            |  |*
*|  |     Client captures and encodes locally                       |  |*
*|  |     Saves to user's disk                                      |  |*
*|  |     No server involvement                                     |  |*
*|  |                                                                 |  |*
*|  |  2. CLOUD RECORDING                                            |  |*
*|  |     Server-side recording                                     |  |*
*|  |     Stores in cloud storage                                   |  |*
*|  |     Requires processing pipeline                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  CLOUD RECORDING PIPELINE:                                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  +-----------+     +------------+     +------------+          |  |*
*|  |  |   SFU     |---->|  Recording |---->|   Kafka    |          |  |*
*|  |  |  Server   |     |   Agent    |     |   Queue    |          |  |*
*|  |  +-----------+     +------------+     +-----+------+          |  |*
*|  |                                             |                  |  |*
*|  |                                             v                  |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |                PROCESSING WORKERS                        ||  |*
*|  |  |                                                           ||  |*
*|  |  |  +-------------+  +-------------+  +-------------+       ||  |*
*|  |  |  | Transcoding |  |Transcription|  |  Thumbnail  |       ||  |*
*|  |  |  |   Worker    |  |   Worker    |  |   Worker    |       ||  |*
*|  |  |  +------+------+  +------+------+  +------+------+       ||  |*
*|  |  |         |                |                |               ||  |*
*|  |  |         +----------------+----------------+               ||  |*
*|  |  |                          |                                ||  |*
*|  |  |                          v                                ||  |*
*|  |  |                    +-----------+                          ||  |*
*|  |  |                    |    S3     |                          ||  |*
*|  |  |                    |  Storage  |                          ||  |*
*|  |  |                    +-----------+                          ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  RECORDING AGENT:                                                       |*
*|  * Joins meeting as hidden participant                                |*
*|  * Receives all media streams from SFU                                |*
*|  * Mixes audio/video in real-time                                     |*
*|  * Writes to temporary storage                                        |*
*|  * On meeting end, uploads to S3 and triggers processing             |*
*|                                                                         |*
*|  POST-PROCESSING:                                                       |*
*|  * Transcode to multiple formats (MP4, M4A audio-only)               |*
*|  * Generate thumbnails                                                |*
*|  * Speech-to-text transcription (optional)                           |*
*|  * Speaker identification                                             |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2.5: GLOBAL ARCHITECTURE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  ZOOM'S GLOBAL INFRASTRUCTURE                                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |                 GLOBAL DISTRIBUTION                             |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |     +------+         +------+         +------+         |  |  |*
*|  |  |     |  NA  |         |  EU  |         | APAC |         |  |  |*
*|  |  |     | Data |         | Data |         | Data |         |  |  |*
*|  |  |     |Centers|        |Centers|        |Centers|        |  |  |*
*|  |  |     +---+--+         +---+--+         +---+--+         |  |  |*
*|  |  |         |                |                |             |  |  |*
*|  |  |         +----------------+----------------+             |  |  |*
*|  |  |                          |                              |  |  |*
*|  |  |                          v                              |  |  |*
*|  |  |           +------------------------------+              |  |  |*
*|  |  |           |   Global Control Plane       |              |  |  |*
*|  |  |           |   (User data, Billing,       |              |  |  |*
*|  |  |           |    Meeting scheduling)       |              |  |  |*
*|  |  |           +------------------------------+              |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  |  PRINCIPLES:                                                    |  |*
*|  |                                                                 |  |*
*|  |  1. MEDIA STAYS REGIONAL                                       |  |*
*|  |     If all participants in US, media stays in US data center  |  |*
*|  |     Minimizes latency                                          |  |*
*|  |                                                                 |  |*
*|  |  2. CLOSEST SFU                                                 |  |*
*|  |     Route participant to geographically closest SFU           |  |*
*|  |                                                                 |  |*
*|  |  3. SFU CASCADING                                               |  |*
*|  |     For global meetings, SFUs in different regions connect    |  |*
*|  |     to each other                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  SFU CASCADING FOR GLOBAL MEETINGS:                                    |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  User in US              User in EU             User in APAC   |  |*
*|  |      |                       |                       |         |  |*
*|  |      v                       v                       v         |  |*
*|  |  +-------+               +-------+               +-------+    |  |*
*|  |  |SFU-US |<----cascade---|SFU-EU |<----cascade---|SFU-APAC|   |  |*
*|  |  +-------+               +-------+               +-------+    |  |*
*|  |                                                                 |  |*
*|  |  Each user connects to closest SFU                            |  |*
*|  |  SFUs share streams between regions                           |  |*
*|  |  Reduces individual user latency                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF CHAPTER 2
