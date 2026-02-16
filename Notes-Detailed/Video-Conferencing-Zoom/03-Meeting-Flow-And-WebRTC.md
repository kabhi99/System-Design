================================================================================
         VIDEO CONFERENCING SYSTEM (ZOOM-LIKE) - HIGH LEVEL DESIGN
================================================================================

CHAPTER 3: MEETING FLOW AND WEBRTC
================================================================================


================================================================================
SECTION 3.1: MEETING JOIN FLOW
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  COMPLETE MEETING JOIN FLOW                                            │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Step 1: User clicks "Join Meeting"                            │  │
    │  │                                                                 │  │
    │  │  Client                     API Gateway                         │  │
    │  │    │                            │                               │  │
    │  │    │── GET /meetings/{id} ─────►│                               │  │
    │  │    │                            │──► Meeting Service            │  │
    │  │    │                            │    • Validate meeting exists  │  │
    │  │    │                            │    • Check password if needed │  │
    │  │    │                            │    • Check waiting room       │  │
    │  │    │◄── Meeting details + ──────│                               │  │
    │  │    │    Signaling server URL    │                               │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Step 2: Establish Signaling Connection                        │  │
    │  │                                                                 │  │
    │  │  Client                     Signaling Server                    │  │
    │  │    │                            │                               │  │
    │  │    │══ WebSocket Connect ══════►│                               │  │
    │  │    │                            │                               │  │
    │  │    │── JOIN_MEETING ───────────►│                               │  │
    │  │    │   { meeting_id,            │                               │  │
    │  │    │     user_token,            │                               │  │
    │  │    │     display_name }         │                               │  │
    │  │    │                            │──► Validate token             │  │
    │  │    │                            │──► Check meeting status       │  │
    │  │    │                            │──► Add to participant list    │  │
    │  │    │                            │                               │  │
    │  │    │◄── ROOM_INFO ──────────────│                               │  │
    │  │    │    { sfu_url,              │                               │  │
    │  │    │      ice_servers,          │                               │  │
    │  │    │      participants[] }      │                               │  │
    │  │    │                            │                               │  │
    │  │    │                            │──► Broadcast to others:       │  │
    │  │    │                            │    PARTICIPANT_JOINED         │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Step 3: Establish Media Connection (WebRTC)                   │  │
    │  │                                                                 │  │
    │  │  Client                     Signaling          SFU Server      │  │
    │  │    │                            │                  │            │  │
    │  │    │── Create PeerConnection ───│                  │            │  │
    │  │    │   (local)                  │                  │            │  │
    │  │    │                            │                  │            │  │
    │  │    │── Get local media ─────────│                  │            │  │
    │  │    │   (camera, mic)            │                  │            │  │
    │  │    │                            │                  │            │  │
    │  │    │── Create Offer (SDP) ──────│                  │            │  │
    │  │    │                            │                  │            │  │
    │  │    │── OFFER ──────────────────►│── Forward ─────►│            │  │
    │  │    │   { sdp: "..." }           │                  │            │  │
    │  │    │                            │                  │            │  │
    │  │    │                            │◄─ ANSWER ────────│            │  │
    │  │    │◄── ANSWER ─────────────────│   { sdp: "..." } │            │  │
    │  │    │                            │                  │            │  │
    │  │    │── Set Remote Description ──│                  │            │  │
    │  │    │                            │                  │            │  │
    │  │    │                            │                  │            │  │
    │  │    │══ ICE Candidate Exchange ══│                  │            │  │
    │  │    │   (trickle ICE)            │                  │            │  │
    │  │    │                            │                  │            │  │
    │  │    │══════ DTLS Handshake ══════│═════════════════►│            │  │
    │  │    │                            │                  │            │  │
    │  │    │══════ SRTP Media ══════════│═════════════════►│            │  │
    │  │    │◄═════ SRTP Media ══════════│◄════════════════│            │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 3.2: WEBRTC DEEP DIVE
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WEBRTC COMPONENTS                                                     │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  WebRTC is a collection of protocols:                          │  │
    │  │                                                                 │  │
    │  │  ┌───────────────────────────────────────────────────────────┐│  │
    │  │  │                                                           ││  │
    │  │  │    APPLICATION LAYER                                     ││  │
    │  │  │    ┌───────────────────────────────────────────────────┐ ││  │
    │  │  │    │  getUserMedia (camera, mic access)                │ ││  │
    │  │  │    │  RTCPeerConnection (connection management)        │ ││  │
    │  │  │    │  RTCDataChannel (arbitrary data)                  │ ││  │
    │  │  │    └───────────────────────────────────────────────────┘ ││  │
    │  │  │                                                           ││  │
    │  │  │    SESSION LAYER                                         ││  │
    │  │  │    ┌───────────────────────────────────────────────────┐ ││  │
    │  │  │    │  SDP (Session Description Protocol)               │ ││  │
    │  │  │    │  ICE (Interactive Connectivity Establishment)     │ ││  │
    │  │  │    └───────────────────────────────────────────────────┘ ││  │
    │  │  │                                                           ││  │
    │  │  │    SECURITY LAYER                                        ││  │
    │  │  │    ┌───────────────────────────────────────────────────┐ ││  │
    │  │  │    │  DTLS (TLS over UDP - key exchange)               │ ││  │
    │  │  │    │  SRTP (Secure Real-time Transport Protocol)       │ ││  │
    │  │  │    └───────────────────────────────────────────────────┘ ││  │
    │  │  │                                                           ││  │
    │  │  │    TRANSPORT LAYER                                       ││  │
    │  │  │    ┌───────────────────────────────────────────────────┐ ││  │
    │  │  │    │  RTP (Real-time Transport Protocol - media)       │ ││  │
    │  │  │    │  RTCP (RTP Control Protocol - feedback)           │ ││  │
    │  │  │    │  SCTP (Stream Control - data channel)             │ ││  │
    │  │  │    └───────────────────────────────────────────────────┘ ││  │
    │  │  │                                                           ││  │
    │  │  │    NETWORK LAYER                                         ││  │
    │  │  │    ┌───────────────────────────────────────────────────┐ ││  │
    │  │  │    │  UDP (primary)                                    │ ││  │
    │  │  │    │  TCP (fallback)                                   │ ││  │
    │  │  │    └───────────────────────────────────────────────────┘ ││  │
    │  │  │                                                           ││  │
    │  │  └───────────────────────────────────────────────────────────┘│  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


SDP (Session Description Protocol)
──────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  SDP describes media session parameters                                │
    │                                                                         │
    │  EXAMPLE SDP OFFER:                                                     │
    │                                                                         │
    │  v=0                                                                   │
    │  o=- 123456 2 IN IP4 127.0.0.1                                        │
    │  s=-                                                                   │
    │  t=0 0                                                                 │
    │  a=group:BUNDLE audio video                                           │
    │  a=msid-semantic: WMS stream1                                         │
    │                                                                         │
    │  m=audio 9 UDP/TLS/RTP/SAVPF 111 103 104                             │
    │  c=IN IP4 0.0.0.0                                                     │
    │  a=rtcp:9 IN IP4 0.0.0.0                                             │
    │  a=ice-ufrag:someufrag                                                │
    │  a=ice-pwd:somepassword                                               │
    │  a=fingerprint:sha-256 AB:CD:EF:...                                   │
    │  a=setup:actpass                                                      │
    │  a=mid:audio                                                          │
    │  a=sendrecv                                                           │
    │  a=rtpmap:111 opus/48000/2                                           │
    │  a=rtcp-fb:111 transport-cc                                          │
    │                                                                         │
    │  m=video 9 UDP/TLS/RTP/SAVPF 96 97 98                                │
    │  a=rtpmap:96 VP8/90000                                               │
    │  a=rtpmap:97 VP9/90000                                               │
    │  a=rtpmap:98 H264/90000                                              │
    │  a=rtcp-fb:96 nack                                                   │
    │  a=rtcp-fb:96 nack pli                                               │
    │  a=rtcp-fb:96 goog-remb                                              │
    │  a=simulcast:send rid=high;rid=mid;rid=low                          │
    │                                                                         │
    │  KEY PARTS:                                                             │
    │  • Codecs supported (Opus, VP8, VP9, H264)                           │
    │  • ICE credentials                                                    │
    │  • DTLS fingerprint                                                   │
    │  • Media direction (sendrecv, sendonly, recvonly)                    │
    │  • Simulcast layers                                                   │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


ICE (Interactive Connectivity Establishment)
────────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ICE finds the best path to connect peers                             │
    │                                                                         │
    │  CANDIDATE TYPES:                                                       │
    │                                                                         │
    │  ┌────────────────────────────────────────────────────────────────┐   │
    │  │                                                                │   │
    │  │  1. HOST CANDIDATE                                             │   │
    │  │     Direct IP address of device                               │   │
    │  │     Example: 192.168.1.100:54321                             │   │
    │  │     Works: Only on same network                               │   │
    │  │                                                                │   │
    │  │  2. SRFLX (Server Reflexive) - via STUN                       │   │
    │  │     Public IP as seen by STUN server                         │   │
    │  │     Example: 203.0.113.50:12345                               │   │
    │  │     Works: Through most NATs                                  │   │
    │  │                                                                │   │
    │  │  3. RELAY - via TURN                                          │   │
    │  │     TURN server relays traffic                                │   │
    │  │     Example: turn.example.com:443                             │   │
    │  │     Works: Through any firewall (TCP fallback)               │   │
    │  │                                                                │   │
    │  └────────────────────────────────────────────────────────────────┘   │
    │                                                                         │
    │  ICE CANDIDATE EXAMPLE:                                                 │
    │                                                                         │
    │  a=candidate:1 1 UDP 2130706431 192.168.1.100 54321 typ host         │
    │  a=candidate:2 1 UDP 1694498815 203.0.113.50 12345 typ srflx         │
    │  a=candidate:3 1 UDP 16777215 10.0.0.1 443 typ relay                 │
    │                                                                         │
    │  ICE PRIORITY:                                                          │
    │  1. Host (fastest, free)                                              │
    │  2. SRFLX (fast, free)                                                │
    │  3. Relay (slowest, costs bandwidth)                                  │
    │                                                                         │
    │  CONNECTIVITY CHECK:                                                    │
    │  ICE tries all candidate pairs and measures RTT                       │
    │  Selects best working pair                                            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


STUN and TURN Servers
─────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  STUN (Session Traversal Utilities for NAT)                           │
    │                                                                         │
    │  Purpose: Discover public IP address                                   │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Client                          STUN Server                   │  │
    │  │  (behind NAT)                    (public)                      │  │
    │  │      │                               │                         │  │
    │  │      │── Binding Request ───────────►│                         │  │
    │  │      │   (from 192.168.1.100:5000)  │                         │  │
    │  │      │                               │                         │  │
    │  │      │◄── Binding Response ──────────│                         │  │
    │  │      │    "Your public IP is         │                         │  │
    │  │      │     203.0.113.50:12345"       │                         │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  TURN (Traversal Using Relays around NAT)                             │
    │                                                                         │
    │  Purpose: Relay media when direct connection fails                    │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Client A                 TURN Server              Client B    │  │
    │  │      │                        │                        │       │  │
    │  │      │── Allocate Request ───►│                        │       │  │
    │  │      │◄── Allocate Response ──│                        │       │  │
    │  │      │    (relay IP:port)     │                        │       │  │
    │  │      │                        │                        │       │  │
    │  │      │══ Media ══════════════►│══ Forward ════════════►│       │  │
    │  │      │◄═ Media ═══════════════│◄═ Forward ═════════════│       │  │
    │  │      │                        │                        │       │  │
    │  │                                                                 │  │
    │  │  All media flows through TURN (expensive!)                     │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ICE SERVER CONFIGURATION:                                              │
    │                                                                         │
    │  {                                                                      │
    │    "iceServers": [                                                     │
    │      { "urls": "stun:stun.example.com:3478" },                        │
    │      {                                                                  │
    │        "urls": "turn:turn.example.com:443",                           │
    │        "username": "user",                                             │
    │        "credential": "pass"                                            │
    │      },                                                                 │
    │      {                                                                  │
    │        "urls": "turns:turn.example.com:443",  // TURN over TLS       │
    │        "username": "user",                                             │
    │        "credential": "pass"                                            │
    │      }                                                                  │
    │    ]                                                                    │
    │  }                                                                      │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 3.3: VIDEO/AUDIO CODECS
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  VIDEO CODECS                                                          │
    │                                                                         │
    │  ┌────────────────────────────────────────────────────────────────┐   │
    │  │                                                                │   │
    │  │  Codec      Quality    CPU Usage   Latency   Patent Free      │   │
    │  │  ──────────────────────────────────────────────────────────── │   │
    │  │                                                                │   │
    │  │  VP8        Good       Medium      Low       Yes              │   │
    │  │                                                                │   │
    │  │  VP9        Better     High        Low       Yes              │   │
    │  │                                                                │   │
    │  │  H.264      Excellent  Low*        Low       No (licensed)    │   │
    │  │             (*hardware)                                        │   │
    │  │                                                                │   │
    │  │  AV1        Best       Very High   Medium    Yes              │   │
    │  │             (future)                                           │   │
    │  │                                                                │   │
    │  └────────────────────────────────────────────────────────────────┘   │
    │                                                                         │
    │  ZOOM USES: H.264 (primary), VP8/VP9 (fallback)                       │
    │  H.264 advantage: Hardware acceleration widely available              │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  AUDIO CODECS                                                          │
    │                                                                         │
    │  ┌────────────────────────────────────────────────────────────────┐   │
    │  │                                                                │   │
    │  │  Codec      Bitrate      Quality   Latency   Use Case         │   │
    │  │  ──────────────────────────────────────────────────────────── │   │
    │  │                                                                │   │
    │  │  Opus       6-510 kbps   Excellent  Low      Speech & Music   │   │
    │  │             (variable)                        (preferred)      │   │
    │  │                                                                │   │
    │  │  G.722      64 kbps      Good       Low      HD Voice         │   │
    │  │                                                                │   │
    │  │  G.711      64 kbps      Basic      Low      PSTN compatible  │   │
    │  │                                                                │   │
    │  └────────────────────────────────────────────────────────────────┘   │
    │                                                                         │
    │  OPUS IS STANDARD for WebRTC:                                          │
    │  • Variable bitrate (adapts to network)                               │
    │  • Great for both speech and music                                    │
    │  • Built-in forward error correction                                  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 3.4: BANDWIDTH ESTIMATION AND ADAPTATION
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CONGESTION CONTROL                                                    │
    │                                                                         │
    │  WebRTC uses feedback to estimate available bandwidth                  │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  SENDER                          RECEIVER                      │  │
    │  │    │                                 │                         │  │
    │  │    │══ RTP Packets ════════════════►│                         │  │
    │  │    │   (with sequence numbers)      │                         │  │
    │  │    │                                 │                         │  │
    │  │    │◄═ RTCP Feedback ═══════════════│                         │  │
    │  │    │   • Packet loss %              │                         │  │
    │  │    │   • RTT (round trip time)      │                         │  │
    │  │    │   • Jitter                     │                         │  │
    │  │    │   • REMB (bandwidth estimate)  │                         │  │
    │  │    │   • Transport-CC               │                         │  │
    │  │    │                                 │                         │  │
    │  │    │── Adjust bitrate ──────────────│                         │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ADAPTATION STRATEGIES:                                                 │
    │                                                                         │
    │  1. RESOLUTION REDUCTION                                               │
    │     1080p → 720p → 480p → 360p                                       │
    │                                                                         │
    │  2. FRAME RATE REDUCTION                                               │
    │     30fps → 24fps → 15fps → 10fps                                     │
    │                                                                         │
    │  3. ENCODER QUALITY                                                    │
    │     Lower quantization = more compression = less quality              │
    │                                                                         │
    │  4. SIMULCAST LAYER SWITCHING                                          │
    │     SFU switches to lower resolution layer                            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 3.5: ACTIVE SPEAKER DETECTION
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  HOW ACTIVE SPEAKER IS DETECTED                                        │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  METHOD 1: Audio Level Detection (Common)                      │  │
    │  │                                                                 │  │
    │  │  Each client sends audio level in RTP header extension        │  │
    │  │  SFU monitors audio levels from all participants              │  │
    │  │  Highest audio level = active speaker                         │  │
    │  │                                                                 │  │
    │  │  Algorithm:                                                    │  │
    │  │  • Smooth audio levels (avoid flicker)                        │  │
    │  │  • Threshold to filter noise                                  │  │
    │  │  • Hysteresis (don't switch too fast)                        │  │
    │  │  • Minimum duration before switching                          │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  METHOD 2: Voice Activity Detection (VAD)                      │  │
    │  │                                                                 │  │
    │  │  Client-side: Detect when user is speaking                    │  │
    │  │  Send metadata to SFU                                         │  │
    │  │                                                                 │  │
    │  │  Benefits:                                                     │  │
    │  │  • Can mute audio when not speaking (saves bandwidth)        │  │
    │  │  • More accurate than pure level detection                   │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  SFU ACTION ON ACTIVE SPEAKER:                                         │
    │                                                                         │
    │  • Forward high-quality stream of active speaker                      │
    │  • May reduce quality of non-speakers                                 │
    │  • Notify clients for UI update (highlight active speaker)           │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 3.6: SCREEN SHARING
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  SCREEN SHARING IMPLEMENTATION                                         │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  HOW IT WORKS:                                                  │  │
    │  │                                                                 │  │
    │  │  1. Browser API: getDisplayMedia()                             │  │
    │  │     • Captures screen/window/tab                               │  │
    │  │     • User selects what to share                               │  │
    │  │                                                                 │  │
    │  │  2. Creates separate video track                               │  │
    │  │     • Camera: Track 1                                          │  │
    │  │     • Screen: Track 2                                          │  │
    │  │                                                                 │  │
    │  │  3. Different encoding settings                                │  │
    │  │     • Screen: Higher resolution (1080p-4K)                    │  │
    │  │     • Screen: Lower frame rate (5-15 fps is fine)             │  │
    │  │     • Screen: Optimized for text/graphics                      │  │
    │  │                                                                 │  │
    │  │  ENCODING SETTINGS:                                            │  │
    │  │                                                                 │  │
    │  │  Camera:      720p @ 30fps, motion optimized                  │  │
    │  │  Screen:      1080p @ 10fps, detail optimized                 │  │
    │  │                                                                 │  │
    │  │  WHY DIFFERENT?                                                │  │
    │  │  • Camera: Smooth motion matters (faces)                      │  │
    │  │  • Screen: Sharp text matters (documents, code)               │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  CONTENT TYPE HINTS:                                                    │
    │                                                                         │
    │  track.contentHint = "motion"  // Video, animation                   │
    │  track.contentHint = "detail"  // Text, screenshots                  │
    │  track.contentHint = "text"    // Primarily text                      │
    │                                                                         │
    │  Encoder uses hint to optimize compression                            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
END OF CHAPTER 3
================================================================================

