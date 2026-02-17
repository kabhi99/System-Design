# VIDEO STREAMING PLATFORM
*Complete System Design (YouTube / Netflix)*

A video streaming platform handles upload, transcoding, storage, and
adaptive delivery of video content to millions of concurrent viewers
across varying network conditions and devices.

## SECTION 1: REQUIREMENTS

```
+--------------------------------------------------------------------------+
|                                                                          |
|  FUNCTIONAL REQUIREMENTS:                                                |
|  * Upload videos (up to several GB)                                      |
|  * Transcode into multiple resolutions and formats                       |
|  * Stream videos with adaptive bitrate (ABR)                             |
|  * Search and browse video catalog                                       |
|  * User interactions (like, comment, subscribe)                          |
|  * Recommendations and personalized home feed                            |
|  * Watch history and resume playback                                     |
|  * Live streaming support                                                |
|                                                                          |
|  NON-FUNCTIONAL:                                                         |
|  * Latency: video start < 2 seconds                                      |
|  * Availability: 99.99%                                                  |
|  * Scale: 1B+ daily video views, 500+ hours uploaded per minute          |
|  * Global: serve users worldwide with low buffering                      |
|  * Cost: optimize storage and bandwidth (largest cost driver)            |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 2: HIGH-LEVEL ARCHITECTURE

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

## SECTION 3: VIDEO UPLOAD AND TRANSCODING

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

## SECTION 4: ADAPTIVE BITRATE STREAMING

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

## SECTION 5: STORAGE OPTIMIZATION

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

## SECTION 6: LIVE STREAMING

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

## SECTION 7: INTERVIEW QUESTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q: How does YouTube handle 500 hours of video uploaded per minute?     |
|  A: Presigned URLs for direct-to-S3 upload. Async transcoding pipeline  |
|     (message queue + auto-scaling worker fleet). Parallel segment       |
|     transcoding. Content-aware encoding (simple scenes = lower bitrate).|
|                                                                         |
|  Q: How do you minimize video start time?                               |
|  A: CDN caches first segments (most accessed). Use short initial        |
|     segments (2s). Start at lowest quality, upgrade quickly (ABR).      |
|     Preload manifest on hover. HTTP/2 multiplexing for parallel fetch.  |
|                                                                         |
|  Q: How does Netflix reduce bandwidth costs?                            |
|  A: Per-title encoding (analyze content complexity, adjust bitrate).    |
|     Open Connect (Netflix's own CDN boxes in ISP data centers).         |
|     Pre-position popular content during off-peak hours.                 |
|     VMAF quality metric instead of fixed bitrate targets.               |
|                                                                         |
|  Q: How would you handle a viral video (sudden 100x traffic)?           |
|  A: CDN absorbs the spike (video segments are static, cacheable).       |
|     Origin serves each segment once per PoP, then PoP serves locally.   |
|     Request coalescing: CDN groups identical cache-miss requests.       |
|                                                                         |
|  Q: How is DRM (content protection) implemented?                        |
|  A: Encrypt video segments with AES-128 or CENC. Key delivered via      |
|     DRM license server (Widevine, FairPlay, PlayReady). Player          |
|     decrypts in hardware. Keys rotate per session for security.         |
|                                                                         |
+-------------------------------------------------------------------------+
```
