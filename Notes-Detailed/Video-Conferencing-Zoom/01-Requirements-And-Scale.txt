================================================================================
         VIDEO CONFERENCING SYSTEM (ZOOM-LIKE) - HIGH LEVEL DESIGN
================================================================================

CHAPTER 1: REQUIREMENTS AND SCALE
================================================================================


================================================================================
SECTION 1.1: FUNCTIONAL REQUIREMENTS
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CORE FEATURES                                                         │
    │                                                                         │
    │  1. VIDEO CALLING                                                      │
    │     • 1:1 video calls                                                 │
    │     • Group video calls (up to 1000 participants)                     │
    │     • HD video quality (720p, 1080p)                                  │
    │     • Adaptive video quality based on bandwidth                       │
    │                                                                         │
    │  2. AUDIO                                                               │
    │     • High quality audio                                              │
    │     • Noise cancellation                                              │
    │     • Mute/unmute                                                     │
    │     • Phone dial-in option                                            │
    │                                                                         │
    │  3. SCREEN SHARING                                                      │
    │     • Share entire screen                                             │
    │     • Share specific application window                               │
    │     • Share portion of screen                                         │
    │     • Multiple participants can share                                 │
    │                                                                         │
    │  4. MEETING MANAGEMENT                                                  │
    │     • Create instant meetings                                         │
    │     • Schedule meetings                                               │
    │     • Recurring meetings                                              │
    │     • Meeting links with passwords                                    │
    │     • Waiting room                                                    │
    │     • Host controls (mute all, remove participant)                   │
    │                                                                         │
    │  5. CHAT                                                                │
    │     • In-meeting chat                                                 │
    │     • Private chat between participants                               │
    │     • File sharing                                                    │
    │     • Reactions/emojis                                                │
    │                                                                         │
    │  6. RECORDING                                                           │
    │     • Local recording                                                 │
    │     • Cloud recording                                                 │
    │     • Transcription                                                   │
    │                                                                         │
    │  7. VIRTUAL BACKGROUNDS                                                 │
    │     • Blur background                                                 │
    │     • Custom backgrounds                                              │
    │                                                                         │
    │  8. BREAKOUT ROOMS                                                      │
    │     • Split meeting into smaller groups                               │
    │     • Host can move between rooms                                     │
    │                                                                         │
    │  9. WHITEBOARD                                                          │
    │     • Collaborative drawing                                           │
    │     • Annotations on shared screen                                    │
    │                                                                         │
    │  10. INTEGRATIONS                                                       │
    │      • Calendar integration (Google, Outlook)                        │
    │      • Slack, Teams integration                                      │
    │      • SSO (Single Sign-On)                                          │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 1.2: NON-FUNCTIONAL REQUIREMENTS
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  LATENCY                                                               │
    │  ═══════                                                                │
    │                                                                         │
    │  • End-to-end latency: < 150ms (ideal), < 400ms (acceptable)         │
    │  • Audio latency: < 100ms                                             │
    │  • Video latency: < 200ms                                             │
    │                                                                         │
    │  WHY LATENCY MATTERS:                                                   │
    │  ┌────────────────────────────────────────────────────────────────┐   │
    │  │                                                                │   │
    │  │  < 150ms   │ Natural conversation, imperceptible delay        │   │
    │  │  150-300ms │ Slight delay, manageable                          │   │
    │  │  300-500ms │ Noticeable, people start talking over each other │   │
    │  │  > 500ms   │ Unusable for real-time conversation              │   │
    │  │                                                                │   │
    │  └────────────────────────────────────────────────────────────────┘   │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  AVAILABILITY                                                          │
    │  ════════════                                                           │
    │                                                                         │
    │  • 99.99% uptime (< 52 minutes downtime/year)                        │
    │  • No single point of failure                                         │
    │  • Graceful degradation (reduce quality vs drop call)                │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  SCALABILITY                                                           │
    │  ═══════════                                                            │
    │                                                                         │
    │  • Support 300M+ daily meeting participants                           │
    │  • 100K+ concurrent meetings                                          │
    │  • Meetings with up to 1000 participants                             │
    │  • Webinars with 50,000 view-only attendees                          │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  QUALITY                                                               │
    │  ═══════                                                                │
    │                                                                         │
    │  Video Quality Options:                                                │
    │  • 360p (low bandwidth): 0.3 Mbps                                    │
    │  • 720p (HD): 1.5 Mbps                                               │
    │  • 1080p (Full HD): 3.0 Mbps                                         │
    │                                                                         │
    │  Audio: 64-128 kbps                                                   │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  SECURITY                                                              │
    │  ════════                                                               │
    │                                                                         │
    │  • End-to-end encryption (E2EE) option                               │
    │  • TLS for all communications                                        │
    │  • Meeting passwords                                                  │
    │  • Waiting room                                                       │
    │  • Host controls                                                      │
    │  • GDPR/HIPAA compliance                                             │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 1.3: SCALE ESTIMATION
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ZOOM'S ACTUAL SCALE (Reference)                                       │
    │                                                                         │
    │  • 300 million daily meeting participants                             │
    │  • 3.3 trillion annual meeting minutes                                │
    │  • Peak: 300+ million concurrent users (pandemic peak)                │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  BANDWIDTH CALCULATIONS                                                │
    │                                                                         │
    │  Per User (720p video):                                                │
    │  • Upload: 1.5 Mbps                                                   │
    │  • Download: 1.5 Mbps × N participants (gallery view)                │
    │    Or: 1.5 Mbps × 1 (speaker view with SFU)                         │
    │                                                                         │
    │  Meeting with 10 participants (720p, SFU):                            │
    │  • Each user uploads: 1.5 Mbps                                       │
    │  • Each user downloads: ~10 × 1.5 = 15 Mbps                          │
    │  • SFU server handles: 10 × 1.5 = 15 Mbps in, 10 × 15 = 150 Mbps out │
    │                                                                         │
    │  100K concurrent meetings × 10 participants avg × 15 Mbps             │
    │  = 15 Tbps total bandwidth!                                           │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  STORAGE (Cloud Recording)                                             │
    │                                                                         │
    │  1 hour 1080p recording ≈ 1-2 GB                                      │
    │  If 1% of meetings recorded:                                          │
    │  100K meetings × 1% × 1 hour × 1.5 GB = 1.5 TB/hour                   │
    │  Daily: 1.5 TB × 24 = 36 TB/day                                       │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  SIGNALING                                                             │
    │                                                                         │
    │  Join/leave events: 300M participants × 2 events = 600M events/day   │
    │  = ~7000 events/second average                                        │
    │  Peak: 20-50K events/second                                           │
    │                                                                         │
    │  Signaling messages per meeting (chat, reactions, mute):             │
    │  ~50-100 messages per participant per meeting                        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 1.4: MEDIA TRANSMISSION APPROACHES
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  THREE APPROACHES FOR MULTI-PARTY VIDEO                                │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  1. PEER-TO-PEER (P2P) - Mesh                                  │  │
    │  │  ════════════════════════════                                   │  │
    │  │                                                                 │  │
    │  │       ┌────┐                                                   │  │
    │  │       │ A  │                                                   │  │
    │  │       └─┬──┘                                                   │  │
    │  │        ╱│╲                                                     │  │
    │  │       ╱ │ ╲                                                    │  │
    │  │      ╱  │  ╲                                                   │  │
    │  │  ┌──▼┐  │  ┌▼──┐                                              │  │
    │  │  │ B │◄─┼──►│ C │                                              │  │
    │  │  └───┘  │  └───┘                                              │  │
    │  │         │                                                      │  │
    │  │  Each participant sends to ALL other participants             │  │
    │  │                                                                 │  │
    │  │  Bandwidth per user: (N-1) × bitrate (upload AND download)   │  │
    │  │  4 participants: 3 × 1.5 = 4.5 Mbps up + 4.5 Mbps down       │  │
    │  │                                                                 │  │
    │  │  PROS: No server, lowest latency, simple                      │  │
    │  │  CONS: Doesn't scale (bandwidth explodes), no server features│  │
    │  │  USE: 1:1 calls, small groups (2-4)                          │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  2. SFU (Selective Forwarding Unit) ← MOST COMMON            │  │
    │  │  ═══════════════════════════════════════════════              │  │
    │  │                                                                 │  │
    │  │       ┌────┐                                                   │  │
    │  │       │ A  │───┐                                               │  │
    │  │       └────┘   │                                               │  │
    │  │                ▼                                               │  │
    │  │       ┌────┐ ┌──────────┐ ┌────┐                              │  │
    │  │       │ B  │◄│   SFU    │►│ C  │                              │  │
    │  │       └────┘ │  Server  │ └────┘                              │  │
    │  │              │          │                                      │  │
    │  │       ┌────┐ │ Forwards │ ┌────┐                              │  │
    │  │       │ D  │◄│ streams  │►│ E  │                              │  │
    │  │       └────┘ │selectively└────┘                              │  │
    │  │              └──────────┘                                      │  │
    │  │                                                                 │  │
    │  │  Each participant sends ONE stream to server                  │  │
    │  │  Server forwards to all other participants                    │  │
    │  │                                                                 │  │
    │  │  Bandwidth per user: 1 × bitrate (up) + (N-1) × bitrate (down)│  │
    │  │  But download can be optimized with simulcast!                │  │
    │  │                                                                 │  │
    │  │  PROS: Scalable, server can do smart routing                 │  │
    │  │  CONS: Server cost, slightly higher latency                  │  │
    │  │  USE: Most video conferencing (Zoom, Meet, Teams)            │  │
    │  │                                                                 │  │
    │  │  ────────────────────────────────────────────────────────────  │  │
    │  │                                                                 │  │
    │  │  3. MCU (Multipoint Control Unit)                             │  │
    │  │  ═════════════════════════════════                             │  │
    │  │                                                                 │  │
    │  │       ┌────┐                                                   │  │
    │  │       │ A  │───┐                                               │  │
    │  │       └────┘   │                                               │  │
    │  │                ▼                                               │  │
    │  │       ┌────┐ ┌──────────┐ ┌────┐                              │  │
    │  │       │ B  │◄│   MCU    │►│ C  │                              │  │
    │  │       └────┘ │  Server  │ └────┘                              │  │
    │  │              │          │                                      │  │
    │  │              │ Decodes, │                                      │  │
    │  │              │ Mixes,   │                                      │  │
    │  │              │ Encodes  │                                      │  │
    │  │              └──────────┘                                      │  │
    │  │                                                                 │  │
    │  │  Server DECODES all streams, MIXES into ONE, sends to all    │  │
    │  │                                                                 │  │
    │  │  Bandwidth per user: 1 × bitrate (up) + 1 × bitrate (down)   │  │
    │  │  Lowest client bandwidth!                                      │  │
    │  │                                                                 │  │
    │  │  PROS: Lowest client bandwidth, works on weak devices        │  │
    │  │  CONS: Very CPU intensive, higher latency, expensive         │  │
    │  │  USE: Legacy systems, PSTN gateways, webinars                │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ZOOM USES: SFU with Simulcast                                        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 1.5: SIMULCAST AND ADAPTIVE STREAMING
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  SIMULCAST                                                             │
    │                                                                         │
    │  Client encodes video at MULTIPLE resolutions simultaneously          │
    │  Server selects best quality to forward to each receiver              │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Sender encodes:                                               │  │
    │  │                                                                 │  │
    │  │  ┌─────────────┐                                               │  │
    │  │  │   Camera    │                                               │  │
    │  │  └──────┬──────┘                                               │  │
    │  │         │                                                       │  │
    │  │    ┌────┴────┬────────┐                                        │  │
    │  │    ▼         ▼        ▼                                        │  │
    │  │  1080p     720p     360p                                       │  │
    │  │  3 Mbps   1.5 Mbps  0.3 Mbps                                  │  │
    │  │    │         │        │                                        │  │
    │  │    └────┬────┴────────┘                                        │  │
    │  │         │                                                       │  │
    │  │         ▼                                                       │  │
    │  │  ┌──────────────┐                                              │  │
    │  │  │  SFU Server  │                                              │  │
    │  │  └──────┬───────┘                                              │  │
    │  │         │                                                       │  │
    │  │    ┌────┴────┬────────┐                                        │  │
    │  │    ▼         ▼        ▼                                        │  │
    │  │  User A    User B   User C                                    │  │
    │  │  (good     (poor    (mobile                                   │  │
    │  │  network)  network)  3G)                                       │  │
    │  │    │         │        │                                        │  │
    │  │  1080p     720p     360p                                       │  │
    │  │                                                                 │  │
    │  │  Server picks best quality for each receiver!                 │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  ADAPTIVE BITRATE:                                                      │
    │  Server monitors receiver's bandwidth and switches quality             │
    │  dynamically (like Netflix adaptive streaming)                        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
END OF CHAPTER 1
================================================================================

