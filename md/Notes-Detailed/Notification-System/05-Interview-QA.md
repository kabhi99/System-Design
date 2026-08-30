# NOTIFICATION SYSTEM
*Chapter 5: Interview Q&A*

This chapter is your interview cheat sheet. Read it right before the
interview. Everything here is designed for verbal delivery: short
answers, memorable numbers, and clear tradeoffs.

## SECTION 5.1: 60-SECOND ELEVATOR PITCH

```
+-------------------------------------------------------------------------+
|                                                                         |
|  "We built a notification system that delivers 1.6 billion messages    |
|  per day across push, SMS, email, and in-app channels, with peaks      |
|  of 200K per second.                                                    |
|                                                                         |
|  It has three layers:                                                  |
|                                                                         |
|    1. A synchronous API tier that validates, checks user preferences,  |
|       enforces rate limits, and enqueues to Kafka.                     |
|                                                                         |
|    2. Kafka with separate topics per (channel, priority) for isolation |
|       and per-user ordering.                                           |
|                                                                         |
|    3. Async channel workers that call providers with a circuit         |
|       breaker and provider failover.                                   |
|                                                                         |
|  At-least-once delivery. Idempotency keys prevent duplicates on the    |
|  API. Client-side dedup on the mobile app handles the last mile.      |
|                                                                         |
|  Hot users get dedicated Kafka partitions to prevent noisy-neighbor    |
|  latency. Multi-region active-active for the critical path."          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.2: THE TRADEOFF TABLE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +----------------------+----------------+-------------+--------------+ |
|  | Decision             | Chose          | Alternative | Why          | |
|  +----------------------+----------------+-------------+--------------+ |
|  | Delivery guarantee   | At-least-once  | Exactly-once| Impossible   | |
|  |                      |                |             | at boundary  | |
|  | Message queue        | Kafka          | RabbitMQ    | Ordering +   | |
|  |                      |                |             | throughput   | |
|  | Priority isolation   | Topic-per-pri  | Priority    | Kafka has no | |
|  |                      |                | field       | native prio  | |
|  | Preference lookup    | Redis cache    | DB per send | 200x latency | |
|  | Fanout               | At API layer   | At worker   | Simpler,     | |
|  |                      |                |             | isolation    | |
|  | Content              | Template + var | Fully render| Localization | |
|  |                      |                | upstream    | central      | |
|  | Batching             | 100 ms window  | None        | 1000x fewer  | |
|  |                      |                |             | API calls    | |
|  | Notification history | Cassandra      | Postgres    | Write-heavy  | |
|  | Scheduling           | Redis ZSET     | Cron        | Sub-second   | |
|  |                      |                |             | resolution   | |
|  | Multi-region         | Active-active  | Active-pas  | Zero-failover| |
|  |                      | (critical)     |             | for critical | |
|  +----------------------+----------------+-------------+--------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.3: COMMON FOLLOW-UP QUESTIONS

### Q: HOW DO YOU HANDLE A USER WITH MULTIPLE DEVICES?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Store all device tokens for a user (device_tokens table).              |
|  Push worker fetches all valid tokens for that user_id.                 |
|  Sends the same notification to each token in a single APNs/FCM batch.  |
|  If any token is invalidated (410 Gone), mark it invalid but keep       |
|  sending to others.                                                     |
|                                                                         |
|  Extension: some products dedup at the "user" level -- if the user     |
|  has 3 devices and the notif was read on device 1, silently dismiss    |
|  on devices 2 and 3. This uses APNs "app group" or FCM "collapse_key". |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: TWO SYSTEMS TRIGGER THE SAME NOTIFICATION -- HOW DO YOU DEDUPE?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Two paths:                                                             |
|                                                                         |
|  1. Same client, retries -> Idempotency-Key catches this in Redis.      |
|                                                                         |
|  2. Two different services both send "you have a new message":          |
|     -- The idempotency key should be derived from the underlying event  |
|        (e.g., "chat_message_78493_notif") so both services would use    |
|        the same key.                                                    |
|     -- Requires convention across teams: derive keys from the domain    |
|        event, not from HTTP request context.                            |
|     -- If they use different keys, we send twice. Client-side dedup     |
|        on the device catches the visible duplication.                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: HOW DO YOU A/B TEST NOTIFICATION CONTENT?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Two techniques:                                                        |
|                                                                         |
|  1. TEMPLATE VERSIONING                                                 |
|     * template_active table maps (template_id, locale) -> version       |
|     * Point half of users at version A, other half at version B         |
|     * Assignment logic: user_id % 100 < 50 -> A else B                  |
|     * Track open + click rates by version in analytics                  |
|                                                                         |
|  2. HOLDOUT GROUPS                                                      |
|     * 1% of users receive nothing (control group)                       |
|     * Compare downstream metric (e.g., app opens) between control       |
|       and treated groups                                                |
|     * Measures the INCREMENTAL impact of the notification itself        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: HOW DO YOU AVOID NOTIFICATION FATIGUE?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Multi-layer defense:                                                   |
|                                                                         |
|  1. Per-user rate limits (from Section 4.3):                            |
|     e.g., max 20 push/day, 3 SMS/day, 10 email/day                      |
|                                                                         |
|  2. Coalescing (from Section 4.4):                                      |
|     "5 new messages from John" instead of 5 separate notifs             |
|                                                                         |
|  3. Time-based backoff:                                                 |
|     Don't send another push within N seconds of a previous one          |
|                                                                         |
|  4. ML send-time optimization (advanced):                               |
|     Predict when a user is most likely to engage; delay until then      |
|                                                                         |
|  5. Category-level opt-outs:                                            |
|     User controls "marketing off, orders on" granularity                |
|                                                                         |
|  6. Signal from user behavior:                                          |
|     If user has dismissed 5 marketing pushes in a row, auto-suppress    |
|     marketing for 30 days.                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: HOW DOES END-TO-END ENCRYPTED PUSH WORK?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Standard push: our server renders the message, sends to APNs, APNs     |
|  delivers to device. APNs sees the content.                             |
|                                                                         |
|  Encrypted push (Signal, iMessage-style):                               |
|                                                                         |
|  1. Client publishes its public key to our server                       |
|  2. Sending client encrypts the notification content with recipient's   |
|     public key                                                          |
|  3. Server routes the OPAQUE ciphertext to APNs                         |
|  4. APNs delivers the ciphertext                                        |
|  5. Recipient device decrypts locally                                   |
|                                                                         |
|  APNs and our server both see nothing but ciphertext. Metadata          |
|  (who sent to whom, when) is still visible to us. For metadata-blind    |
|  systems, look at Signal's sealed sender.                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: HOW DO YOU ADD RICH MEDIA (IMAGES) TO PUSH?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  APNs and FCM both support media attachments (up to ~10 MB).            |
|                                                                         |
|  But the payload itself is capped at 4 KB (APNs) / 4 KB (FCM data).     |
|  So the notification carries a URL, not the image.                      |
|                                                                         |
|  Flow:                                                                  |
|    1. Backend uploads image to CDN, gets URL                            |
|    2. Notification payload includes {image_url: "https://cdn.../x.jpg"} |
|    3. On device, iOS "Notification Service Extension" or Android's      |
|       BigPictureStyle fetches and renders the image before display      |
|    4. If fetch fails, fall back to text-only                            |
|                                                                         |
|  Considerations:                                                        |
|    * CDN cost scales with delivery count (not send count)               |
|    * Extension has a 30s time budget on iOS; keep image < 1 MB          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: HOW DO YOU HANDLE A USER CHANGING THEIR PHONE NUMBER?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Phone number is stored on user profile (Postgres users table).         |
|                                                                         |
|  Change flow:                                                           |
|    1. User verifies new number (OTP to new number)                      |
|    2. Update users.phone                                                |
|    3. Invalidate cache: DEL user_profile:{user_id}                      |
|    4. Notifications in-flight (already enqueued) go to OLD number       |
|       -- Not typically a problem; enqueued msgs process in seconds      |
|    5. For scheduled notifications, they use user_id lookup, so they'll  |
|       pick up the new number at send time                               |
|                                                                         |
|  Edge: old number is now assigned to a different user (carrier          |
|  recycles numbers). If they receive our OTP for the previous owner,    |
|  they're confused. Mitigation: OTP includes app name ("Your Uber        |
|  OTP is..."), and rate-limit strict on OTP requests per number.        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: WHAT'S THE COST OF RUNNING THIS SYSTEM?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ROUGH MONTHLY BREAKDOWN AT 1.6B/DAY (all-in production)                |
|                                                                         |
|  +--------------------+----------------+-----------------+              |
|  | Component          | Monthly cost   | Note            |              |
|  +--------------------+----------------+-----------------+              |
|  | SMS (Twilio+Nexmo) | ~$2.4M         | 300M SMS x $0.008|             |
|  | Email (SendGrid)   | ~$3M           | 3B x $0.001     |              |
|  | Push (APNs+FCM)    | $0             | Free            |              |
|  | Kafka cluster      | ~$40K          | 30 brokers      |              |
|  | Cassandra ring     | ~$60K          | 40 nodes        |              |
|  | Redis cluster      | ~$25K          | 50 nodes        |              |
|  | Postgres HA        | ~$8K           | 2 replicas      |              |
|  | API + worker fleet | ~$50K          | 300 pods        |              |
|  | S3 / Glacier       | ~$5K           | 500 TB archive  |              |
|  | Monitoring         | ~$10K          | Datadog etc     |              |
|  +--------------------+----------------+-----------------+              |
|  | TOTAL              | ~$5.6M         |                 |              |
|  +--------------------+----------------+-----------------+              |
|                                                                         |
|  KEY OBSERVATION                                                        |
|                                                                         |
|  SMS and Email account for 95% of cost. Infra is a rounding error.     |
|  This is why:                                                           |
|    * Rate limits, dedup, and prefs enforcement pay for themselves      |
|    * Reducing SMS by 10% = $240K/mo saved                               |
|    * The engineering budget for those features is trivial vs savings   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: HOW DO YOU TEST IN PRODUCTION WITHOUT SPAMMING REAL USERS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. Test users tagged as "internal": always go to a fake provider       |
|                                                                         |
|  2. Shadow send: real code path runs to the provider call, but the      |
|     provider call is replaced with a no-op that returns success.        |
|     Metrics, latency, and errors are captured but no message goes out.  |
|                                                                         |
|  3. Canary rollout: new code deploys to 1% of traffic, watch metrics,   |
|     gradually shift.                                                    |
|                                                                         |
|  4. Provider sandbox: APNs sandbox environment is a real endpoint       |
|     that never delivers to real devices; use for integration tests.     |
|                                                                         |
|  5. Synthetic monitoring: send OTP to a real test phone every minute,   |
|     verify latency and delivery.                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: GDPR RIGHT TO BE FORGOTTEN -- HOW?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  User requests deletion:                                                |
|                                                                         |
|  Immediate (within 24h):                                                |
|    * DELETE user profile row                                            |
|    * DELETE all device_tokens for user                                  |
|    * DELETE user_preferences                                            |
|    * DEL Redis inbox:{user_id}, prefs:{user_id}                         |
|                                                                         |
|  Within 30 days:                                                        |
|    * Cassandra notifications: TTL takes care of most (30d)              |
|    * S3 archive: tombstone the user, re-partition compact              |
|    * ClickHouse analytics: DELETE by user_id                            |
|    * Backup snapshots: delete on next rotation cycle (90d worst case)   |
|                                                                         |
|  Idempotency keys: 24h TTL so no action needed                          |
|                                                                         |
|  Audit log of deletion request itself: retain for compliance            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q: HOW DO YOU PROVE DELIVERY (LEGAL / DISPUTE)?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  For each notification, we retain:                                      |
|                                                                         |
|    * notification_id (our system)                                       |
|    * provider_message_id (Twilio SID, SendGrid message ID)              |
|    * timestamp of provider ack                                          |
|    * webhook delivery event with timestamp                              |
|    * user's device token (which device it went to)                      |
|                                                                         |
|  Cassandra 30d hot + S3 1y+ archive gives us a legal audit trail.       |
|                                                                         |
|  However:                                                               |
|    * Provider ack means "provider accepted", not "device received"      |
|    * Carrier delivery reports are the closest to proof                  |
|    * For push: no proof beyond APNs ack (device may have been offline)  |
|                                                                         |
|  When a dispute arises ("I didn't get the OTP"), we can show:           |
|    * We accepted the request at T                                       |
|    * We sent to Twilio at T+50 ms                                       |
|    * Twilio acked at T+250 ms with SID xxxxx                            |
|    * Twilio's delivery report at T+3s says "delivered"                  |
|                                                                         |
|  This is enough for 99% of disputes.                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.4: FAILURE MODE GRID

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +------------------------+--------------------+----------------------+ |
|  | Failure                | Detection          | Mitigation           | |
|  +------------------------+--------------------+----------------------+ |
|  | API tier overload      | 5xx rate > 1%      | HPA + shed low prio  | |
|  | Kafka broker down      | Producer errors    | acks=all + retry     | |
|  | Kafka partition hot    | Consumer lag spike | Hot-user re-partition| |
|  | Worker OOM             | Pod crash loop     | HPA memory + smaller | |
|  |                        |                    | batches              | |
|  | Provider outage        | Error rate > 25%   | Circuit + failover   | |
|  | All providers down     | All circuits open  | Queue in Kafka +     | |
|  |                        |                    | Postgres for hours   | |
|  | Cassandra timeout      | Write timeout      | Buffer to retry topic| |
|  | Redis eviction         | Cache miss up      | Increase mem + LRU   | |
|  | DLQ growing            | Alert on size      | Manual + reprocess   | |
|  | Bad template deployed  | Rendering errors   | Auto-revert to prev  | |
|  | Certificate expired    | APNs 403 spike     | Auto-rotate + alert  | |
|  | Region failure         | Health checks fail | Active-active switch | |
|  | Idem key Redis down    | SETNX errors       | Fail open + log dedup| |
|  | Preference cache miss  | DB CPU spike       | Warm cache + query   | |
|  |                        |                    | rate limit           | |
|  | Push token flood inval | 410 rate up 10x    | Batch invalidation + | |
|  |                        |                    | postmortem           | |
|  +------------------------+--------------------+----------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.5: NUMBERS TO MEMORIZE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALE                                                                  |
|    100M DAU                                                             |
|    1.6B notifications/day                                               |
|    18.5K/sec avg, 200K/sec peak                                         |
|                                                                         |
|  LATENCY BUDGETS                                                        |
|    API p99: 50 ms                                                       |
|    End-to-end p99 (critical): 1s                                        |
|    End-to-end p50 (normal): 30s                                         |
|                                                                         |
|  DATA SIZES                                                             |
|    Notification record: ~800 bytes                                      |
|    Payload limit: APNs 4 KB, FCM 4 KB, SMS 160 char                     |
|    In-app inbox: 200 items x 200 bytes = 40 KB per user                 |
|                                                                         |
|  STORAGE                                                                |
|    Cassandra 30d hot: 38 TB                                             |
|    S3 1y cold: 467 TB                                                   |
|                                                                         |
|  PROVIDER LIMITS                                                        |
|    APNs: 1000 concurrent HTTP/2 streams per connection                  |
|    FCM: 500 tokens per batch call                                       |
|    SendGrid Pro: 3K/sec                                                 |
|    Twilio: 5K/sec                                                       |
|                                                                         |
|  COST                                                                   |
|    SMS: $0.008 per send (US)                                            |
|    Email: $0.001 per send                                               |
|    Push: free                                                           |
|    Monthly infra + provider: ~$5.6M                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.6: HIGH-VALUE TALKING POINTS

Sentences the interviewer will nod at:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  * "Exactly-once is impossible at the provider boundary, so we do       |
|    at-least-once with idempotency keys and client-side dedup."          |
|                                                                         |
|  * "Kafka has no native priority queues, so we simulate priority via    |
|    topic-per-priority with independent consumer groups. Prevents the    |
|    marketing flood from starving OTPs."                                 |
|                                                                         |
|  * "The 24-hour idempotency TTL is a sweet spot: shorter risks          |
|    duplicates from slow client retries, longer explodes Redis memory."  |
|                                                                         |
|  * "Circuit breaker per provider means one bad provider doesn't cascade |
|    across channels. Twilio going down doesn't affect email."            |
|                                                                         |
|  * "Preference cache with 5-min TTL gives us 98% hit rate and 200x     |
|    lower latency than DB lookups. Invalidation on PUT keeps it fresh."  |
|                                                                         |
|  * "Hot users need dedicated Kafka partitions. Celebrity users on the   |
|    default hash-partition scheme cause noisy-neighbor lag for others."  |
|                                                                         |
|  * "The outbox pattern is how upstream services avoid sending           |
|    notifications for transactions that get rolled back."                |
|                                                                         |
|  * "SMS costs $2.4M/month. Every rate limit and dedup pays for itself   |
|    many times over. This is where engineering investment matters."      |
|                                                                         |
|  * "Multi-region active-active for the critical path (< 5 min RTO).    |
|    Active-passive for templates and analytics (10x cheaper, longer RTO |
|    acceptable)."                                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.7: CROSS-REFERENCES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RELATED TOPICS IN OTHER NOTES                                          |
|                                                                         |
|  * Kafka partitioning:                                                  |
|      System Design/Kafka/02-Architecture-Deep-Dive.md                   |
|                                                                         |
|  * Rate limiting algorithms:                                            |
|      System Design/Rate-Limiter/01-Requirements-And-Algorithms.md       |
|      System Design/Rate-Limiter/02-Distributed-Architecture.md          |
|                                                                         |
|  * Idempotency patterns:                                                |
|      System Design/Fundamentals/22-Idempotent-API-Design.md             |
|                                                                         |
|  * Outbox pattern / distributed transactions:                           |
|      System Design/Fundamentals/09-Distributed-Transactions.md          |
|                                                                         |
|  * Circuit breaker / resilience:                                        |
|      System Design/Microservices-Architecture/                          |
|      03-Resilience-And-Deployment.md                                    |
|                                                                         |
|  * Cassandra data modeling:                                             |
|      System Design/Fundamentals/20-Database-Internals-Deep-Dive.md      |
|                                                                         |
|  * Redis persistence for scheduler:                                     |
|      System Design/Redis/03-Persistence-Replication-Clustering.md       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.8: THE ONE-DIAGRAM SUMMARY

If you can only draw one diagram in the interview, draw this:

```
+-------------------------------------------------------------------------+
|                                                                         |
|                                                                         |
|      Upstream Services                                                  |
|            |                                                            |
|            | POST /notify (Idempotency-Key)                             |
|            v                                                            |
|      +-------------+  Redis (dedup, prefs cache, rate limit)            |
|      | Notif API   |----.                                               |
|      +-------------+     `--- Postgres (prefs, templates, tokens)      |
|            |                                                            |
|            | Kafka produce (acks=all)                                   |
|            v                                                            |
|      +----------------------------------------+                         |
|      |    Kafka: topic per (channel, prio)    |                         |
|      |    partitioned by user_id              |                         |
|      +----------------------------------------+                         |
|            |         |         |         |                              |
|            v         v         v         v                              |
|         Push      SMS      Email     In-app                             |
|         Worker    Worker   Worker    Worker                             |
|            |         |         |         |                              |
|         CircuitBreaker + Retry + DLQ                                    |
|            |         |         |         |                              |
|            v         v         v         v                              |
|        APNs/FCM   Twilio  SendGrid   Redis                              |
|                   (Nexmo) (Mailgun)  (ZSET)                             |
|                                                                         |
|            +----all workers emit events----->                           |
|                        Kafka --> Flink --> ClickHouse                   |
|                        Kafka --> Cassandra (audit)                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

Learn to draw this in 2 minutes. Every other detail hangs off this skeleton.

## INTERVIEW CRUX — SAY THIS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NOTIFICATION SYSTEM — WHAT TO SAY IN THE INTERVIEW                     |
|                                                                         |
|  DEFAULT ANSWER (when asked "how would you design X?"):                 |
|  * Sync API tier validates + checks user_preferences + rate-            |
|      limits + writes idempotency key -> produces to Kafka               |
|  * Kafka: separate topic per (channel, priority) so a marketing         |
|      flood cannot starve OTP; partition by user_id for ordering         |
|  * Async channel workers (push/SMS/email/in-app) call providers         |
|      behind circuit breakers + retry with jitter                        |
|  * Providers: APNs+FCM (push), Twilio+Nexmo (SMS), SendGrid             |
|      (email); each channel has a failover provider                      |
|  * Cassandra stores notification history; Redis for in-app inbox        |
|                                                                         |
|  IF ASKED "how do you handle X?" (~3-5 common follow-ups):              |
|  * delivery guarantee? At-least-once (exactly-once impossible at        |
|      provider boundary); idempotency key + client dedup                 |
|  * provider outage (Twilio down)? Circuit breaker opens, requests       |
|      route to Nexmo; when circuit half-open, canary probe               |
|  * hot user (celeb, notification storm)? Detect via QPS; assign         |
|      dedicated partitions; coalesce N pushes -> 1 summary               |
|  * notification fatigue? Per-user daily caps by channel; ML             |
|      send-time optimization; auto-suppress after dismissals             |
|  * same event triggers duplicate? Idempotency-Key derived from          |
|      domain event (chat_msg_id) shared across services                  |
|  * scheduled sends? Redis ZSET keyed by fire_time; scheduler            |
|      pops due items via Lua atomic pop-and-produce                      |
|                                                                         |
|  NUMBERS TO DROP:                                                       |
|  * 1.6B notifications/day (18.5K/s avg, 200K/s peak)                    |
|  * OTP end-to-end p99 < 1 s; normal p50 ~30 s                           |
|  * Payload caps: APNs 4 KB, FCM 4 KB, SMS 160 chars                     |
|  * SMS $0.008 per send -> ~$2.4M/month at scale                         |
|  * Idempotency key TTL: 24 h (sweet spot vs Redis memory)               |
|  * Cassandra retention 30 d hot + S3 1 y cold (~500 TB)                 |
|                                                                         |
|  REAL-WORLD PATTERNS TO NAME-DROP:                                      |
|  * Uber: multi-channel + hot-user isolation + provider failover         |
|  * Slack: in-app inbox + push via APNs/FCM + email digest               |
|  * SendGrid / Mailgun: use them as provider, don't rebuild SMTP         |
|  * Twilio: SMS + WhatsApp provider; delivery webhooks -> Kafka          |
|                                                                         |
|  ONE-LINE CRUX:                                                         |
|  "Sync API + Kafka priority topics + async channel workers with circuit |
|   breakers, at-least-once + idempotency key."                           |
|                                                                         |
+-------------------------------------------------------------------------+
```
