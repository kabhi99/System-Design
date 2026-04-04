# VIDEO STREAMING PLATFORM
*Complete System Design (YouTube / Netflix)*

A video streaming platform handles upload, transcoding, storage, and
adaptive delivery of video content to millions of concurrent viewers
across varying network conditions and devices.

## SECTION 1: SCOPING THE PROBLEM WITH THE INTERVIEWER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INTERVIEWER-CANDIDATE DIALOGUE                                         |
|  (establishing scope before diving into design)                         |
|                                                                         |
|  CANDIDATE: Are we designing the upload + transcoding pipeline, the     |
|    streaming/playback delivery, or both?                                |
|                                                                         |
|  INTERVIEWER: Both. Cover upload, transcoding to multiple formats/      |
|    resolutions, storage, and adaptive bitrate streaming to clients.     |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: What scale?                                                 |
|                                                                         |
|  INTERVIEWER: 1B DAU, 500 hours of video uploaded per minute,           |
|    1M concurrent viewers. Think YouTube.                                |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  AGREED SCOPE:                                                          |
|                                                                         |
|  * Video platform: upload, transcode, store, stream (YouTube style)     |
|  * 1B DAU, 500 hours uploaded/min, 1M concurrent viewers                |
|  * Adaptive bitrate streaming (HLS/DASH)                                |
|  * CDN-based delivery                                                   |
|  * Deep dive: transcoding pipeline + adaptive streaming                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1: REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS:                                               |
|  * Upload videos (up to several GB)                                     |
|  * Transcode into multiple resolutions and formats                      |
|  * Stream videos with adaptive bitrate (ABR)                            |
|  * Search and browse video catalog                                      |
|  * User interactions (like, comment, subscribe)                         |
|  * Recommendations and personalized home feed                           |
|  * Watch history and resume playback                                    |
|  * Live streaming support                                               |
|                                                                         |
|  NON-FUNCTIONAL:                                                        |
|  * Latency: video start < 2 seconds                                     |
|  * Availability: 99.99%                                                 |
|  * Scale: 1B+ daily video views, 500+ hours uploaded per minute         |
|  * Global: serve users worldwide with low buffering                     |
|  * Cost: optimize storage and bandwidth (largest cost driver)           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: KEY TERMINOLOGY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TRANSCODING                                                            |
|  Converting video from one format/codec to another.                     |
|  Example: ProRes (camera raw) -> H.264 (web playable)                   |
|  Involves decoding the source then re-encoding to target format.        |
|                                                                         |
|  ENCODING                                                               |
|  Compressing raw video into a specific codec format.                    |
|  Trades CPU time for smaller file size.                                 |
|  More compression = smaller file but longer encode + quality loss.      |
|                                                                         |
|  CODEC (Coder-Decoder)                                                  |
|  Algorithm that compresses (encodes) and decompresses (decodes) video.  |
|  Examples: H.264, H.265 (HEVC), VP9, AV1                                |
|  H.264: universal support, baseline compression                         |
|  AV1:   best compression, but 10-20x slower to encode                   |
|                                                                         |
|  CONTAINER FORMAT                                                       |
|  Wrapper that packages video, audio, subtitles, and metadata together.  |
|  Examples: MP4 (.mp4), MPEG-TS (.ts), fMP4 (.m4s), MKV (.mkv)           |
|  Container != codec. MP4 can hold H.264 or H.265 inside.                |
|                                                                         |
|  BITRATE                                                                |
|  Amount of data per second of video. Measured in Mbps or Kbps.          |
|  Higher bitrate = better quality but larger file and more bandwidth.    |
|  CBR (Constant): fixed bitrate throughout.                              |
|  VBR (Variable): adjusts bitrate per scene complexity.                  |
|                                                                         |
|  RENDITION                                                              |
|  A specific version of a video at a particular resolution + bitrate.    |
|  Example: 1080p at 5 Mbps is one rendition, 720p at 2.5 Mbps another.   |
|  Platform stores multiple renditions for adaptive streaming.            |
|                                                                         |
|  GOP (Group of Pictures)                                                |
|  Sequence of frames between two keyframes (I-frames).                   |
|  I-frame: full image (large). P-frame: changes from previous (small).   |
|  B-frame: changes from both previous and next (smallest).               |
|  GOP size of 2 seconds = keyframe every 2 seconds.                      |
|  Segments must be split at GOP boundaries for clean cuts.               |
|                                                                         |
|  SEGMENT / CHUNK                                                        |
|  Small piece of a video (2-10 seconds), independently decodable.        |
|  Each segment starts with a keyframe (I-frame).                         |
|  Client downloads segments one at a time for streaming.                 |
|                                                                         |
|  MANIFEST FILE                                                          |
|  Index file that lists all available renditions and their segments.     |
|  M3U8: manifest format for HLS (Apple).                                 |
|  MPD: manifest format for DASH (open standard).                         |
|  Player reads manifest to know what quality levels + segments exist.    |
|                                                                         |
|  HLS (HTTP Live Streaming)                                              |
|  Apple's adaptive streaming protocol. Uses M3U8 manifest + .ts/.fmp4    |
|  segments. Dominant protocol, works natively on iOS/Safari.             |
|                                                                         |
|  DASH (Dynamic Adaptive Streaming over HTTP)                            |
|  Open standard adaptive streaming protocol. Uses MPD manifest + .m4s    |
|  segments. Better DRM support on Android/Chrome (Widevine).             |
|                                                                         |
|  ABR (Adaptive Bitrate Streaming)                                       |
|  Player dynamically switches between renditions based on network        |
|  conditions. Bandwidth drops -> lower quality. Improves -> higher.      |
|  Decisions made client-side, per-segment.                               |
|                                                                         |
|  CMAF (Common Media Application Format)                                 |
|  Unified container format (fMP4) that works with BOTH HLS and DASH.     |
|  One set of segments, two manifests -> saves ~50% storage.              |
|                                                                         |
|  CDN (Content Delivery Network)                                         |
|  Globally distributed edge servers that cache and serve video segments. |
|  Viewer fetches from nearest edge PoP (Point of Presence).              |
|  Reduces latency and offloads origin. Handles 99%+ of video traffic.    |
|                                                                         |
|  PRESIGNED URL                                                          |
|  Temporary URL with embedded auth that allows direct upload to object   |
|  storage (S3). Upload service generates it; client uploads directly.    |
|  Avoids routing large video files through application servers.          |
|                                                                         |
|  DRM (Digital Rights Management)                                        |
|  Encryption of video segments to prevent unauthorized copying.          |
|  Widevine (Google), FairPlay (Apple), PlayReady (Microsoft).            |
|  Player requests decryption key from license server per session.        |
|                                                                         |
|  RTMP (Real-Time Messaging Protocol)                                    |
|  Protocol used for ingesting live video from broadcaster to server.     |
|  Low latency, persistent TCP connection. Not used for playback.         |
|  Broadcaster (OBS) -> RTMP -> Ingest server -> transcode -> HLS/DASH.   |
|                                                                         |
|  PER-TITLE ENCODING (Content-Aware Encoding)                            |
|  Analyze each video's scene complexity before choosing bitrate.         |
|  Static scenes (lecture) -> lower bitrate. Action scenes -> higher.     |
|  Netflix pioneered this. Saves ~20% bandwidth with no quality loss.     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3: HIGH-LEVEL ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  VIDEO PLATFORM ARCHITECTURE                                            |
|                                                                         |
|  UPLOAD PATH:                                                           |
|                                                                         |
|  Creator -> Upload Service -> Object Store (raw) -> Message Queue       |
|                                                         |               |
|                                              +----------+----------+    |
|                                              |          |          |    |
|                                              v          v          v    |
|                                          Transcode  Thumbnail   Metadata|
|                                          Workers    Generator   Extract |
|                                              |          |          |    |
|                                              v          v          v    |
|                                          Object     Object    Metadata  |
|                                          Store      Store     DB        |
|                                          (HLS/DASH) (thumbs)            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  VIEWING PATH:                                                          |
|                                                                         |
|  Viewer -> CDN (edge cache) --> Origin (Object Store)                   |
|              |                                                          |
|              +--> Manifest file (M3U8/MPD)                              |
|              +--> Video segments (2-10 sec each)                        |
|              +--> Adaptive bitrate switching                            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  API PATH:                                                              |
|                                                                         |
|  Client -> API Gateway -> Video Metadata Service -> PostgreSQL          |
|                        -> User Service -> User DB                       |
|                        -> Recommendation Service -> ML Models           |
|                        -> Search Service -> Elasticsearch               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: VIDEO UPLOAD AND TRANSCODING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  UPLOAD FLOW:                                                           |
|                                                                         |
|  1. Client requests presigned URL from Upload Service                   |
|  2. Client uploads directly to Object Storage (S3) via presigned URL    |
|     * Multipart upload for large files (parallel chunks)                |
|     * Resumable upload (retry from last successful chunk)               |
|  3. Upload Service publishes "video.uploaded" event to queue            |
|  4. Transcoding pipeline triggered                                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  TRANSCODING PIPELINE:                                                  |
|                                                                         |
|  Raw Video (1080p, 5 GB, ProRes)                                        |
|       |                                                                 |
|       +--> Split into segments (GOP-aligned, 2-6 seconds)               |
|       |                                                                 |
|       +--> Parallel transcode each segment:                             |
|       |    * 2160p (4K)  - 15 Mbps H.265                                |
|       |    * 1080p       - 5 Mbps  H.264                                |
|       |    * 720p        - 2.5 Mbps                                     |
|       |    * 480p        - 1 Mbps                                       |
|       |    * 360p        - 0.5 Mbps                                     |
|       |    * Audio only  - 128 Kbps AAC                                 |
|       |                                                                 |
|       +--> Generate manifest (M3U8 for HLS, MPD for DASH)               |
|       +--> Generate thumbnails (every N seconds)                        |
|       +--> Extract metadata (duration, resolution, codec)               |
|       +--> Upload all outputs to Object Storage                         |
|       +--> Publish "video.ready" event                                  |
|                                                                         |
|  SCALE: 500 hrs/min uploaded x 5 renditions = 2500 hrs/min to encode    |
|  Solution: auto-scaling transcoding cluster (K8s, Spot instances)       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5: ADAPTIVE BITRATE STREAMING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HLS (HTTP Live Streaming) - Apple, most common                         |
|  DASH (Dynamic Adaptive Streaming over HTTP) - open standard            |
|                                                                         |
|  HOW IT WORKS:                                                          |
|                                                                         |
|  1. Player fetches MANIFEST file:                                       |
|     /video/abc123/manifest.m3u8                                         |
|                                                                         |
|  2. Manifest lists all available quality levels:                        |
|     #EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080            |
|     /video/abc123/1080p/playlist.m3u8                                   |
|     #EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=1280x720             |
|     /video/abc123/720p/playlist.m3u8                                    |
|                                                                         |
|  3. Player picks quality based on current bandwidth                     |
|  4. Fetches segments (2-10 sec chunks):                                 |
|     /video/abc123/1080p/segment-001.ts                                  |
|     /video/abc123/1080p/segment-002.ts                                  |
|                                                                         |
|  5. If bandwidth drops -> switches to lower quality mid-stream          |
|     If bandwidth improves -> switches to higher quality                 |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  CDN CACHING FOR VIDEO:                                                 |
|                                                                         |
|  * Manifest files: short TTL (30-60s, may change for live)              |
|  * Video segments: long TTL (24h+, immutable content)                   |
|  * Popular videos: hot in CDN cache, 99%+ cache hit rate                |
|  * Long tail: cache miss -> origin fetch -> cache at edge               |
|  * Prefetch: CDN pre-warms popular new content                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6: STORAGE OPTIMIZATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STORAGE TIERS:                                                         |
|                                                                         |
|  HOT (frequently viewed):                                               |
|  * S3 Standard / GCS Standard                                           |
|  * CDN-cached segments                                                  |
|  * All quality levels available                                         |
|                                                                         |
|  WARM (occasionally viewed):                                            |
|  * S3 Infrequent Access / GCS Nearline                                  |
|  * Only popular renditions (720p, 1080p)                                |
|  * Lower-quality renditions transcoded on-demand                        |
|                                                                         |
|  COLD (rarely viewed):                                                  |
|  * S3 Glacier / GCS Archive                                             |
|  * Only original + 1 rendition stored                                   |
|  * Re-transcode if requested (minutes to retrieve)                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  COST MATH (YouTube scale):                                             |
|  * 500 hrs/min uploaded = 720,000 hrs/day                               |
|  * Avg 10 min video, 5 renditions, avg 500 MB total = 3.6 PB/day        |
|  * S3 cost: ~$23/TB/month -> 3.6 PB x 30 x $23 = ~$2.5M/month           |
|  * Solution: tiered storage, content-aware encoding (per-title),        |
|    aggressive deletion of unpopular renditions.                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7: LIVE STREAMING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LIVE STREAMING ARCHITECTURE:                                           |
|                                                                         |
|  Broadcaster -> RTMP Ingest -> Transcoder (real-time) -> CDN -> Viewer  |
|                                                                         |
|  KEY DIFFERENCES FROM VOD:                                              |
|  * Ultra-low latency needed (2-10 seconds, not minutes)                 |
|  * Transcoding must be real-time (cannot batch)                         |
|  * Segments are very short (1-2 seconds for low latency)                |
|  * Manifest files update every segment (rolling window)                 |
|  * DVR: store recent segments for rewind/catch-up                       |
|  * Chat/reactions: separate real-time system (WebSocket)                |
|                                                                         |
|  PROTOCOLS:                                                             |
|  * RTMP (ingest from broadcaster to server)                             |
|  * HLS/DASH (delivery to viewers, 6-30 second latency)                  |
|  * LL-HLS (Low-Latency HLS, 2-4 second latency)                         |
|  * WebRTC (sub-second latency, used for interactive)                    |
|                                                                         |
|  SCALE FOR POPULAR LIVE EVENT:                                          |
|  * 10M concurrent viewers watching same stream                          |
|  * CDN serves same segments to all viewers (massive cache hit)          |
|  * Edge handles 99%+ of traffic, origin barely touched                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8: SCALE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ASSUMPTIONS (YouTube-scale):                                           |
|                                                                         |
|  * 2 billion monthly active users                                       |
|  * 1 billion daily video views                                          |
|  * 500 hours of video uploaded per minute                               |
|  * Average video length: 10 minutes                                     |
|  * 5 renditions per video (360p, 480p, 720p, 1080p, 4K)                 |
|  * Average segment size: 2-4 MB (for 4-second segment at 1080p)         |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  UPLOAD / TRANSCODING THROUGHPUT                                        |
|                                                                         |
|  500 hrs/min = 30,000 hrs/hr of raw video                               |
|  x 5 renditions = 150,000 hrs/hr of encoding work                       |
|  = ~42 hours of encoding work per second                                |
|                                                                         |
|  Each transcoder processes ~2x real-time (10 min video in 5 min)        |
|  Workers needed: 42 / 2 = ~21 workers encoding concurrently             |
|  With segment-level parallelism: much fewer machines needed             |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  STORAGE                                                                |
|                                                                         |
|  Raw upload:   500 hrs/min x avg 1 GB/hr = 500 GB/min = 720 TB/day      |
|  Transcoded:   5 renditions, avg 500 MB total per video                 |
|                500 hrs/min x (60/10) = 3000 videos/min                  |
|                3000 x 500 MB = 1.5 TB/min = 2.16 PB/day                 |
|                                                                         |
|  Monthly storage growth: ~65 PB/month (transcoded)                      |
|  At $23/TB (S3 Standard): ~$1.5M/month (without tiering)                |
|  With tiering (hot/warm/cold): ~$500K/month                             |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  BANDWIDTH (VIEWING)                                                    |
|                                                                         |
|  1B daily views, avg 10 min at avg 2.5 Mbps (720p)                      |
|  = 1B x 10 min x 60s x 2.5 Mbps / 8 = ~1.875 EB/day outbound            |
|                                                                         |
|  Peak concurrent viewers: ~100M (assumed)                               |
|  Peak bandwidth: 100M x 2.5 Mbps = 250 Pbps                             |
|                                                                         |
|  WHY CDN IS NON-NEGOTIABLE:                                             |
|  No single origin can serve this. 99%+ must be served from CDN edge.    |
|  Origin bandwidth: <1% of total = still multi-Tbps                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: API DESIGN AND DATA MODEL

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CORE APIs                                                              |
|                                                                         |
|  1. UPLOAD                                                              |
|     POST /api/v1/videos/upload-url                                      |
|     Request:  { title, description, tags[], visibility }                |
|     Response: { video_id, presigned_url, upload_id }                    |
|                                                                         |
|     PUT {presigned_url}                                                 |
|     (Client uploads file directly to S3, multipart)                     |
|                                                                         |
|     POST /api/v1/videos/{video_id}/complete                             |
|     (Client signals upload done, triggers transcoding)                  |
|                                                                         |
|  2. PLAYBACK                                                            |
|     GET /api/v1/videos/{video_id}/manifest                              |
|     Response: redirect to CDN URL for M3U8/MPD manifest                 |
|                                                                         |
|     GET /api/v1/videos/{video_id}                                       |
|     Response: { video_id, title, description, view_count, duration,     |
|                 channel, thumbnails, created_at }                       |
|                                                                         |
|  3. INTERACTIONS                                                        |
|     POST /api/v1/videos/{video_id}/like                                 |
|     POST /api/v1/videos/{video_id}/comments                             |
|     GET  /api/v1/videos/{video_id}/comments?cursor=X&limit=20           |
|                                                                         |
|  4. FEED / RECOMMENDATIONS                                              |
|     GET /api/v1/feed?cursor=X&limit=20                                  |
|     GET /api/v1/search?q=term&cursor=X                                  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  DATA MODEL                                                             |
|                                                                         |
|  VIDEOS TABLE (PostgreSQL):                                             |
|  +-----------------------------------------------------------------+    |
|  | video_id (UUID, PK)  | channel_id (FK)    | title               |    |
|  | description          | status (enum)       | visibility (enum)  |    |
|  | duration_ms          | upload_size_bytes   | created_at         |    |
|  | published_at         | tags (text[])       | category           |    |
|  +-----------------------------------------------------------------+    |
|  status: uploading | transcoding | ready | failed | deleted             |
|                                                                         |
|  VIDEO_RENDITIONS TABLE:                                                |
|  +-----------------------------------------------------------------+    |
|  | rendition_id (PK)   | video_id (FK)       | resolution          |    |
|  | bitrate_kbps         | codec               | manifest_url       |    |
|  | segment_count        | total_size_bytes    | storage_tier       |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  VIEW_COUNTS (Redis / counter service):                                 |
|  video:{id}:views -> counter (not in main DB, async aggregated)         |
|                                                                         |
|  WHY SEPARATE VIEW COUNTS?                                              |
|  * 1B views/day = ~11,500 writes/sec (too hot for single row)           |
|  * Use Redis INCR, flush to DB in batches every 30s                     |
|  * Accept approximate counts (exact isn't needed)                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10: DESIGN ALTERNATIVES AND TRADE-OFFS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ALTERNATIVE 1: HLS vs DASH vs CMAF                                     |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  | Feature          | HLS            | DASH           | CMAF       |    |
|  |------------------+----------------+----------------+------------|    |
|  | Created by       | Apple           | MPEG (open)    | Apple+MPEG|    |
|  | Container        | .ts (MPEG-TS)  | .m4s (fMP4)    | fMP4       |    |
|  | Manifest         | .m3u8          | .mpd           | Both       |    |
|  | Apple devices    | Native         | Needs player   | Native     |    |
|  | DRM support      | FairPlay       | Widevine/PR    | All        |    |
|  | Adoption         | Dominant       | Growing        | Future     |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  TRADE-OFF:                                                             |
|  * HLS: best device support (especially iOS/Safari), battle-tested      |
|  * DASH: open standard, more flexible, better for DRM on Android        |
|  * CMAF: unified container (fMP4) works with both HLS and DASH          |
|    Reduces storage by 50% (one set of segments, two manifests)          |
|                                                                         |
|  Netflix/YouTube: Use BOTH HLS + DASH (different devices)               |
|  Modern approach: CMAF (single segments, dual manifests)                |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ALTERNATIVE 2: CODEC CHOICES                                           |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  | Codec    | Quality/size  | CPU to encode | Device support       |    |
|  |----------+---------------+---------------+----------------------|    |
|  | H.264    | Baseline      | Low           | Universal (99%+)     |    |
|  | H.265    | 40% smaller   | 3-5x more     | Modern devices only  |    |
|  | VP9      | ~H.265        | 5-10x more    | Chrome, Android, YT  |    |
|  | AV1      | 30% < H.265   | 10-20x more   | Growing (2022+)      |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  TRADE-OFF:                                                             |
|  * H.264: safe default, works everywhere, but worst compression         |
|  * H.265: great compression, but licensing fees + limited browser       |
|  * VP9: YouTube uses this heavily (royalty-free, Chrome support)        |
|  * AV1: best compression, royalty-free, but encode cost is massive      |
|    Netflix uses AV1 for mobile (saves bandwidth on metered networks)    |
|                                                                         |
|  REAL-WORLD STRATEGY:                                                   |
|  Encode H.264 always (universal fallback)                               |
|  + VP9/AV1 for popular content (amortize encode cost over views)        |
|  + H.265 for 4K content (compression needed for large files)            |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ALTERNATIVE 3: CDN STRATEGY                                            |
|                                                                         |
|  OPTION A: Third-party CDN (Cloudflare, Akamai, CloudFront)             |
|  * Quick to set up, global coverage                                     |
|  * Pay-per-GB ($0.02-0.08/GB) -- expensive at scale                     |
|  * Less control over cache behavior                                     |
|                                                                         |
|  OPTION B: Own CDN (Netflix Open Connect, Google Global Cache)          |
|  * Place boxes inside ISP data centers                                  |
|  * Massive bandwidth savings (traffic stays within ISP network)         |
|  * Huge upfront investment, operational complexity                      |
|  * Only viable at massive scale (Netflix, YouTube, Facebook)            |
|                                                                         |
|  OPTION C: Hybrid                                                       |
|  * Own CDN for top markets (US, EU, India)                              |
|  * Third-party CDN for long tail regions                                |
|  * Most practical for growing platforms                                 |
|                                                                         |
|  COST COMPARISON (serving 1 EB/month):                                  |
|  Third-party CDN: $20M-80M/month                                        |
|  Own CDN (Netflix style): $5-10M/month (after 3-year amortization)      |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ALTERNATIVE 4: PUSH CDN vs PULL CDN                                    |
|                                                                         |
|  PULL (lazy):                                                           |
|  * First viewer triggers cache miss -> origin fetch -> cache at edge    |
|  * Good for: long-tail content (millions of rarely viewed videos)       |
|  * Bad: first viewer gets slow response (cache miss penalty)            |
|                                                                         |
|  PUSH (eager):                                                          |
|  * Origin pushes content to CDN edges before anyone requests it         |
|  * Good for: new popular content (trending, homepage featured)          |
|  * Bad: wastes storage at edges for content nobody watches              |
|                                                                         |
|  REAL-WORLD: Pull for long tail (99% of videos)                         |
|              Push/pre-warm for predicted popular content                |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ALTERNATIVE 5: SEGMENT DURATION TRADE-OFF                              |
|                                                                         |
|  Short segments (2s):                                                   |
|  Y Faster quality switching (ABR adapts every 2s)                       |
|  Y Lower latency for live streaming                                     |
|  X More HTTP requests (overhead)                                        |
|  X Larger manifest files                                                |
|  X Less efficient encoding (less context per segment)                   |
|                                                                         |
|  Long segments (10s):                                                   |
|  Y Fewer HTTP requests                                                  |
|  Y Better encoding efficiency                                           |
|  X Slower ABR adaptation (stuck at bad quality for 10s)                 |
|  X Higher latency for live streaming                                    |
|                                                                         |
|  Common choice: 4-6 seconds (compromise)                                |
|  Live streaming: 2 seconds (latency matters more)                       |
|  LL-HLS: partial segments (sub-second parts)                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11: COMMON ISSUES AND FAILURE SCENARIOS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ISSUE 1: THUNDERING HERD ON VIRAL VIDEO                                |
|                                                                         |
|  Problem:                                                               |
|  New video goes viral. Every CDN PoP gets cache miss simultaneously.    |
|  All PoPs request same segments from origin at once.                    |
|  Origin overloaded with thousands of concurrent requests for same file. |
|                                                                         |
|  Solution:                                                              |
|  * Request coalescing (CDN deduplicates concurrent cache-miss           |
|    requests -- only 1 request to origin per PoP per segment)            |
|  * Shield / mid-tier cache (CDN edge -> shield PoP -> origin)           |
|    Only shield hits origin, edge PoPs fetch from shield                 |
|  * Pre-warm CDN for content predicted to go viral                       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ISSUE 2: TRANSCODING PIPELINE BACKLOG                                  |
|                                                                         |
|  Problem:                                                               |
|  Sudden spike in uploads (event, trend). Transcoding queue backs up.    |
|  Videos stuck in "processing" for hours instead of minutes.             |
|                                                                         |
|  Solution:                                                              |
|  * Priority queue: premium creators, popular channels get priority      |
|  * Auto-scale transcoding workers (K8s HPA + spot instances)            |
|  * Progressive availability: publish 720p first, add others later       |
|    (user can start watching while 4K still encoding)                    |
|  * Rate limit uploads per user during extreme spikes                    |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ISSUE 3: VIDEO START LATENCY (TIME TO FIRST FRAME)                     |
|                                                                         |
|  Problem:                                                               |
|  User clicks play -> 5 second wait -> video starts. Users leave.        |
|  Studies show 1% abandonment per 100ms of additional startup time.      |
|                                                                         |
|  Causes and Solutions:                                                  |
|  * DNS lookup: use DNS pre-resolve on hover                             |
|  * TCP + TLS handshake: use HTTP/3 (QUIC) for 0-RTT                     |
|  * Manifest fetch: CDN cache with short TTL, preload on hover           |
|  * First segment fetch: cache first 2-3 segments aggressively           |
|  * Decoder init: start at lowest quality, switch up (fast start ABR)    |
|  * Buffer strategy: start playback at 1 segment buffered (not 3)        |
|                                                                         |
|  Target: < 2 seconds from click to first frame                          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ISSUE 4: INCONSISTENT VIEW COUNTS                                      |
|                                                                         |
|  Problem:                                                               |
|  Viral video: 50M views but counter shows 301 (YouTube's old bug).      |
|  Multiple services incrementing counters = double counting.             |
|  Bots inflating view counts for ad revenue fraud.                       |
|                                                                         |
|  Solution:                                                              |
|  * Deferred counting: batch view events through Kafka                   |
|  * Deduplication: (user_id + video_id + time_window) = 1 view           |
|  * Bot detection: check watch duration (< 5 sec = not a real view),     |
|    IP clustering, device fingerprinting                                 |
|  * Accept eventual consistency (count updates every 30-60 seconds)      |
|  * Separate real-time approximate (Redis) vs exact (batch job)          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ISSUE 5: STORAGE COST EXPLOSION                                        |
|                                                                         |
|  Problem:                                                               |
|  Storing 5 renditions of every video forever = petabytes/month.         |
|  90% of videos get <100 views. Storing 4K for these is waste.           |
|                                                                         |
|  Solution:                                                              |
|  * Tiered storage (hot/warm/cold) -- see Section 6                      |
|  * Delete unpopular renditions: keep only 720p + original for           |
|    videos with < 100 views after 90 days                                |
|  * On-demand transcoding: re-transcode cold videos if requested         |
|  * Content-aware encoding (per-title): analyze scene complexity,        |
|    static scenes get lower bitrate. Netflix saves 20% bandwidth.        |
|  * Deduplication: detect re-uploads of same content (hash-based)        |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ISSUE 6: CDN CACHE INVALIDATION FOR LIVE STREAMS                       |
|                                                                         |
|  Problem:                                                               |
|  Live manifest (.m3u8) updates every 2 seconds. If CDN caches it        |
|  with stale data, viewers see frozen stream or missing segments.        |
|                                                                         |
|  Solution:                                                              |
|  * Very short TTL for live manifests (1-2 seconds)                      |
|  * Viewers poll manifest frequently (every segment duration)            |
|  * CDN uses "stale-while-revalidate" for manifests                      |
|  * LL-HLS: uses HTTP/2 push or blocking playlist reload                 |
|    (player long-polls manifest, server holds until new segment ready)   |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ISSUE 7: MULTI-REGION CONSISTENCY                                      |
|                                                                         |
|  Problem:                                                               |
|  Creator uploads video in US. Viewer in India can't find it.            |
|  Metadata DB not yet replicated. CDN in India has no segments.          |
|                                                                         |
|  Solution:                                                              |
|  * Metadata: async replication with "video.ready" event propagation     |
|    (don't show video in search until all regions have metadata)         |
|  * Segments: pull-through CDN (first viewer triggers origin fetch)      |
|    OR pre-warm CDN in top regions for popular channels                  |
|  * Accept slight delay (30-60 seconds) for global availability          |
|  * Creator sees "Publishing to all regions..." status                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION N: WRAP-UP

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SUMMARY OF KEY DESIGN DECISIONS:                                       |
|                                                                         |
|  1. DAG-BASED TRANSCODING PIPELINE: upload -> split into segments ->    |
|     parallel encode to multiple resolutions/codecs -> package -> CDN.   |
|  2. ADAPTIVE BITRATE STREAMING (HLS/DASH): client selects segment       |
|     quality based on bandwidth. Smooth quality transitions.             |
|  3. CDN for delivery. Pre-push popular content to edge. Origin          |
|     pull for long-tail content.                                         |
|  4. OBJECT STORAGE (S3) for video segments. Cheap, durable, scalable.   |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  KEY TRADE-OFFS:                                                        |
|                                                                         |
|  * PRE-TRANSCODE ALL vs ON-DEMAND: Pre-transcoding all resolutions      |
|    wastes storage for rarely-watched content. On-demand saves storage   |
|    but adds latency on first view. Hybrid: popular = pre-transcode,     |
|    long-tail = on-demand.                                               |
|  * CODEC CHOICE: H.264 is universal but less efficient. H.265/AV1       |
|    are 30-50% more efficient but slower to encode and not all devices   |
|    support them. Encode both; serve best the client supports.
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12: INTERVIEW QUESTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How does YouTube handle 500 hours of video uploaded per minute?     |
|  A: Presigned URLs for direct-to-S3 upload. Async transcoding pipeline  |
|     (message queue + auto-scaling worker fleet). Parallel segment       |
|     transcoding. Content-aware encoding (simple scenes = lower bitrate).|
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q: How do you minimize video start time?                               |
|  A: CDN caches first segments (most accessed). Use short initial        |
|     segments (2s). Start at lowest quality, upgrade quickly (ABR).      |
|     Preload manifest on hover. HTTP/3 (QUIC) for 0-RTT handshake.       |
|     Target: < 2 seconds click-to-first-frame.                           |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q: How does Netflix reduce bandwidth costs?                            |
|  A: Per-title encoding (analyze content complexity, adjust bitrate).    |
|     Open Connect (Netflix's own CDN boxes in ISP data centers).         |
|     Pre-position popular content during off-peak hours.                 |
|     VMAF quality metric instead of fixed bitrate targets.               |
|     AV1 codec for mobile (30% smaller than H.265).                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q: How would you handle a viral video (sudden 100x traffic)?           |
|  A: CDN absorbs the spike (video segments are static, cacheable).       |
|     Origin serves each segment once per PoP, then PoP serves locally.   |
|     Request coalescing: CDN deduplicates concurrent cache-miss reqs.    |
|     Shield tier: edge -> shield PoP -> origin (reduces origin load).    |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q: How is DRM (content protection) implemented?                        |
|  A: Encrypt video segments with AES-128 or CENC. Key delivered via      |
|     DRM license server (Widevine, FairPlay, PlayReady). Player          |
|     decrypts in hardware. Keys rotate per session for security.         |
|     Different DRM per platform (FairPlay=iOS, Widevine=Android/Chrome). |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q: Why not store video in a database?                                  |
|  A: Videos are multi-GB binary blobs. Databases are for structured      |
|     data with queries. Object storage (S3) is purpose-built for         |
|     large files: $0.023/GB vs $0.10+/GB for DB, parallel multipart      |
|     upload, CDN integration, 99.999999999% durability.                  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q: How would you handle partial uploads / resume?                      |
|  A: Multipart upload protocol (S3 native). Client splits file into      |
|     chunks (5-100 MB each). Each chunk uploaded independently.          |
|     On failure: retry only failed chunk, not entire file.               |
|     Upload state tracked server-side (which parts received).            |
|     Timeout: auto-cleanup incomplete uploads after 24 hours.            |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q: HLS vs DASH -- which would you choose?                              |
|  A: For maximum compatibility: HLS (works natively on iOS/Safari).      |
|     For Android/web: DASH with Widevine DRM.                            |
|     Modern approach: CMAF (common media format) -- single set of        |
|     fMP4 segments, dual manifests (m3u8 + mpd). Saves 50% storage.      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q: How do you handle 10M concurrent viewers for a live event?          |
|  A: CDN is the hero. All viewers watch same stream = same segments.     |
|     Each CDN PoP fetches segment once from origin, serves to all        |
|     local viewers. Cache hit rate: 99.99%.                              |
|     Pre-scale CDN capacity. Graceful degradation tiers.                 |
|     Proactive scaling for predicted peaks (see Hotstar/IPL approach).   |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q: How would you design video recommendations?                         |
|  A: Collaborative filtering (users who watched X also watched Y).       |
|     Content-based (video tags, category, description embeddings).       |
|     Two-stage: candidate generation (fast, 1000s) -> ranking            |
|     (ML model scores top 100). Pre-compute for top users,               |
|     real-time for active sessions. A/B test ranking models.             |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  Q: What metrics would you monitor?                                     |
|  A:                                                                     |
|     VIDEO HEALTH:                                                       |
|     * Time to first frame (p50, p99)                                    |
|     * Rebuffering ratio (% of play time spent buffering)                |
|     * Bitrate served vs available bandwidth                             |
|     * Video start failure rate                                          |
|                                                                         |
|     INFRASTRUCTURE:                                                     |
|     * CDN cache hit ratio (target: >95%)                                |
|     * Origin request rate (should be very low)                          |
|     * Transcoding queue depth and processing time                       |
|     * Storage growth rate and cost per view                             |
|                                                                         |
|     BUSINESS:                                                           |
|     * Watch time per user (most important for YouTube)                  |
|     * Abandonment rate by startup latency                               |
|     * Upload-to-ready time (creator experience)                         |
|                                                                         |
+-------------------------------------------------------------------------+
```
