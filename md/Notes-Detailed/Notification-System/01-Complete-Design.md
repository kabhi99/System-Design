# NOTIFICATION SYSTEM DESIGN (PUSH / SMS / EMAIL)
*Complete Design: Requirements, Architecture, and Interview Guide*

A notification system sends timely, relevant messages to users across multiple
channels (push, SMS, email, in-app). At scale, it must handle billions of
notifications per day with priority routing, rate limiting, and delivery tracking
while respecting user preferences and minimizing notification fatigue.

## SECTION 1: SCOPING THE PROBLEM WITH THE INTERVIEWER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INTERVIEWER-CANDIDATE DIALOGUE                                         |
|  (establishing scope before diving into design)                         |
|                                                                         |
|  CANDIDATE: What types of notifications should we support?              |
|    Just push notifications, or also SMS, email, and in-app?             |
|                                                                         |
|  INTERVIEWER: All four: push (iOS APNs + Android FCM), SMS,             |
|    email, and in-app. The system should be channel-agnostic.            |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: Are notifications real-time (immediate) or can they         |
|    be batched and sent in digests?                                      |
|                                                                         |
|  INTERVIEWER: Both. Some are urgent (payment alerts) and must be        |
|    immediate. Others (social updates) can be batched into digests.      |
|    Priority levels determine the behavior.                              |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: What scale are we targeting?                                |
|                                                                         |
|  INTERVIEWER: 100M DAU, 500M notifications per day across all           |
|    channels. Peak during events like Black Friday or flash sales.       |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: Should I handle user preferences and opt-out? For           |
|    example, "don't send me marketing emails."                           |
|                                                                         |
|  INTERVIEWER: Yes. Users control which channels and categories          |
|    they receive. This is critical for compliance (CAN-SPAM, GDPR).      |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: What delivery guarantee do we need? At-least-once,          |
|    exactly-once, or best-effort?                                        |
|                                                                         |
|  INTERVIEWER: At-least-once for critical notifications (payments,       |
|    security). Best-effort for social notifications. Design for          |
|    at-least-once with deduplication at the client.                      |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  CANDIDATE: Should the system generate notification content, or         |
|    do upstream services provide the full message?                       |
|                                                                         |
|  INTERVIEWER: Upstream services send a notification request with        |
|    a template ID and parameters. The notification system renders        |
|    the final message using templates. Good question.                    |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  AGREED SCOPE:                                                          |
|                                                                         |
|  * Multi-channel: push (APNs/FCM), SMS, email, in-app                   |
|  * 100M DAU, 500M notifications/day                                     |
|  * Priority levels: urgent (immediate) vs normal (batchable)            |
|  * User preference management and opt-out                               |
|  * Template-based message rendering                                     |
|  * At-least-once delivery with client-side dedup                        |
|  * Rate limiting per user to prevent notification fatigue               |
|  * Delivery tracking and analytics                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: UNDERSTANDING THE PROBLEM
```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS A NOTIFICATION SYSTEM?                                         |
|                                                                         |
|  A service that sends timely, relevant messages to users across         |
|  multiple channels (push, SMS, email, in-app).                          |
|                                                                         |
|  Examples:                                                              |
|  * "Your order has been shipped" (Push + Email)                         |
|  * "John liked your photo" (Push + In-app)                              |
|  * "Your OTP is 123456" (SMS)                                           |
|  * "Weekly digest: 5 new connections" (Email)                           |
|  * "Price drop alert!" (Push)                                           |
|                                                                         |
|  Real-world systems:                                                    |
|  * AWS SNS, Firebase Cloud Messaging                                    |
|  * Twilio (SMS), SendGrid (Email)                                       |
|  * Custom systems at Twitter, Facebook, Uber                            |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  NOTIFICATION CHANNELS                                                  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. PUSH NOTIFICATIONS                                            |  |
|  |     * Mobile (iOS APNs, Android FCM)                              |  |
|  |     * Web (Web Push API)                                          |  |
|  |     * Desktop (native apps)                                       |  |
|  |     * Instant delivery, requires device token                     |  |
|  |                                                                   |  |
|  |  2. SMS                                                           |  |
|  |     * Text messages via telecom carriers                          |  |
|  |     * High open rate (98%)                                        |  |
|  |     * Expensive, limited content                                  |  |
|  |     * Best for: OTP, urgent alerts                                |  |
|  |                                                                   |  |
|  |  3. EMAIL                                                         |  |
|  |     * Rich content (HTML, attachments)                            |  |
|  |     * Cheap at scale                                              |  |
|  |     * Lower engagement, spam risk                                 |  |
|  |     * Best for: Newsletters, receipts, detailed info              |  |
|  |                                                                   |  |
|  |  4. IN-APP NOTIFICATIONS                                          |  |
|  |     * Bell icon / notification center                             |  |
|  |     * Only visible when user is in app                            |  |
|  |     * No external delivery cost                                   |  |
|  |     * Best for: Social interactions, updates                      |  |
|  |                                                                   |  |
|  |  5. WEBHOOK                                                       |  |
|  |     * HTTP callback to external systems                           |  |
|  |     * For B2B integrations                                        |  |
|  |     * Best for: Developer notifications, integrations             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  KEY CHALLENGES                                                         |
|                                                                         |
|  1. SCALE                                                               |
|     * Billions of notifications per day                                 |
|     * Burst traffic (Black Friday, breaking news)                       |
|                                                                         |
|  2. RELIABILITY                                                         |
|     * Messages must not be lost                                         |
|     * At-least-once delivery guarantee                                  |
|                                                                         |
|  3. LATENCY                                                             |
|     * Real-time for push/SMS (seconds)                                  |
|     * Near real-time for email (minutes)                                |
|                                                                         |
|  4. USER PREFERENCES                                                    |
|     * Respect opt-out per channel/category                              |
|     * Don't spam users                                                  |
|                                                                         |
|  5. RATE LIMITING                                                       |
|     * Provider limits (APNs, FCM, SMS carriers)                         |
|     * Per-user limits (no notification bombing)                         |
|                                                                         |
|  6. DEDUPLICATION                                                       |
|     * Same notification shouldn't be sent twice                         |
|                                                                         |
```

*+-------------------------------------------------------------------------+*

## SECTION 2: REQUIREMENTS
```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS                                                |
|                                                                         |
|  1. MULTI-CHANNEL DELIVERY                                              |
|     * Send push, SMS, email, in-app notifications                       |
|     * Support for multiple channels per notification                    |
|                                                                         |
|  2. TEMPLATE MANAGEMENT                                                 |
|     * Create/update notification templates                              |
|     * Variable substitution (Hi {{name}}, your order {{order_id}})      |
|     * Localization (multi-language)                                     |
|                                                                         |
|  3. USER PREFERENCES                                                    |
|     * Opt-in/opt-out per channel                                        |
|     * Opt-in/opt-out per notification category                          |
|     * Quiet hours (no notifications 10 PM - 8 AM)                       |
|                                                                         |
|  4. SCHEDULING                                                          |
|     * Send immediately                                                  |
|     * Schedule for future time                                          |
|     * Recurring notifications                                           |
|                                                                         |
|  5. PRIORITY LEVELS                                                     |
|     * Critical (OTP, security alerts) - send immediately                |
|     * High (order updates) - send within seconds                        |
|     * Normal (social) - send within minutes                             |
|     * Low (marketing) - batch and send                                  |
|                                                                         |
|  6. TRACKING & ANALYTICS                                                |
|     * Delivery status (sent, delivered, failed)                         |
|     * Open rates, click rates                                           |
|     * Unsubscribe tracking                                              |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  NON-FUNCTIONAL REQUIREMENTS                                            |
|                                                                         |
|  1. SCALE                                                               |
|     * 10 billion notifications/day                                      |
|     * 100K notifications/second peak                                    |
|                                                                         |
|  2. AVAILABILITY                                                        |
|     * 99.99% uptime                                                     |
|     * No single point of failure                                        |
|                                                                         |
|  3. LATENCY                                                             |
|     * Critical: < 1 second                                              |
|     * Normal: < 30 seconds                                              |
|                                                                         |
|  4. RELIABILITY                                                         |
|     * At-least-once delivery                                            |
|     * No message loss                                                   |
|                                                                         |
|  5. EXTENSIBILITY                                                       |
|     * Easy to add new channels                                          |
|     * Pluggable provider architecture                                   |
|                                                                         |
```

*+-------------------------------------------------------------------------+*

## SECTION 3: KEY TERMINOLOGY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PUSH NOTIFICATION                                                      |
|  Message delivered to a user's device via platform services             |
|  (APNs for iOS, FCM for Android). Appears on the lock screen            |
|  or notification tray even when the app is not open.                    |
|                                                                         |
|  APNs (APPLE PUSH NOTIFICATION SERVICE)                                 |
|  Apple's gateway for delivering push notifications to iOS and           |
|  macOS devices. Requires a device token, HTTP/2 connection,             |
|  and JWT authentication with a 4 KB payload limit.                      |
|                                                                         |
|  FCM (FIREBASE CLOUD MESSAGING)                                         |
|  Google's service for delivering push notifications to Android          |
|  and web clients. Supports topic-based and device-based                 |
|  targeting with a 4 KB payload limit per message.                       |
|                                                                         |
|  IN-APP NOTIFICATION                                                    |
|  Notification displayed within the application UI (bell icon,           |
|  notification center). Only visible when the user is active             |
|  in the app, with zero external delivery cost.                          |
|                                                                         |
|  TEMPLATE                                                               |
|  Pre-defined notification format with variable placeholders             |
|  (e.g., 'Hi {{name}}, your order {{id}} shipped'). Enables              |
|  consistent messaging, localization, and A/B testing.                   |
|                                                                         |
|  NOTIFICATION CHANNEL / PREFERENCE                                      |
|  User-configurable settings controlling how and when they               |
|  receive notifications. Includes per-channel opt-in/out,                |
|  per-category controls, and quiet hours with timezone support.          |
|                                                                         |
|  DELIVERY RATE                                                          |
|  Percentage of notifications successfully reaching the end              |
|  device. Affected by invalid tokens, provider outages, and              |
|  device connectivity. A key reliability metric to monitor.              |
|                                                                         |
|  RATE LIMITING                                                          |
|  Capping notifications per user, per service, or globally to            |
|  prevent spam. Enforced at multiple levels: per-user daily              |
|  caps, per-service quotas, and provider-imposed limits.                 |
|                                                                         |
|  FAN-OUT                                                                |
|  Distributing a single notification event to many recipients.           |
|  A campaign targeting 10M users requires efficient batching             |
|  and queue partitioning to avoid overwhelming providers.                |
|                                                                         |
|  DEAD LETTER QUEUE (DLQ)                                                |
|  Queue for notifications that failed after all retry attempts.          |
|  Enables alerting, root-cause analysis, and batch reprocessing          |
|  once the underlying provider or system issue is resolved.              |
|                                                                         |
+-------------------------------------------------------------------------+
```

*+-------------------------------------------------------------------------+*

## SECTION 4: SCALE ESTIMATION
```
+-------------------------------------------------------------------------+
|                                                                         |
|  USER BASE                                                              |
|                                                                         |
|  * 500 million registered users                                         |
|  * 100 million daily active users                                       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  NOTIFICATION VOLUME                                                    |
|                                                                         |
|  Per user per day:                                                      |
|  * Push: 5 notifications                                                |
|  * Email: 1 notification                                                |
|  * SMS: 0.1 (occasional OTP)                                            |
|  * In-app: 10 notifications                                             |
|                                                                         |
|  Daily totals:                                                          |
|  * Push: 100M x 5 = 500 million/day                                     |
|  * Email: 100M x 1 = 100 million/day                                    |
|  * SMS: 100M x 0.1 = 10 million/day                                     |
|  * In-app: 100M x 10 = 1 billion/day                                    |
|  * TOTAL: ~1.6 billion/day                                              |
|                                                                         |
|  Per second (average):                                                  |
|  * 1.6B / 86400 ~ 18,500 notifications/second                           |
|                                                                         |
|  Per second (peak 10x):                                                 |
|  * 185,000 notifications/second                                         |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  STORAGE                                                                |
|                                                                         |
|  Notification record:                                                   |
|  * notification_id: 16 bytes                                            |
|  * user_id: 8 bytes                                                     |
|  * channel: 10 bytes                                                    |
|  * content: 500 bytes                                                   |
|  * metadata: 200 bytes                                                  |
|  * Total: ~750 bytes                                                    |
|                                                                         |
|  Daily storage:                                                         |
|  * 1.6B x 750 bytes = 1.2 TB/day                                        |
|                                                                         |
|  Keep 30 days:                                                          |
|  * 1.2 TB x 30 = 36 TB                                                  |
|                                                                         |
```

*+-------------------------------------------------------------------------+*

## SECTION 5: HIGH-LEVEL ARCHITECTURE
```
+-------------------------------------------------------------------------+
|                                                                         |
|  ARCHITECTURE OVERVIEW                                                  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |                     INTERNAL SERVICES                             |  |
|  |         (Order Service, User Service, etc.)                       |  |
|  |                          |                                        |  |
|  |                          | Send notification request              |  |
|  |                          v                                        |  |
|  |               +----------------------+                            |  |
|  |               |   NOTIFICATION API   |                            |  |
|  |               |                      |                            |  |
|  |               |  * Validate request  |                            |  |
|  |               |  * Enrich with user  |                            |  |
|  |               |  * Check preferences |                            |  |
|  |               |  * Rate limit        |                            |  |
|  |               +----------+-----------+                            |  |
|  |                          |                                        |  |
|  |                          v                                        |  |
|  |               +----------------------+                            |  |
|  |               |    MESSAGE QUEUE     |                            |  |
|  |               |      (Kafka)         |                            |  |
|  |               |                      |                            |  |
|  |               |  Partitioned by      |                            |  |
|  |               |  priority + channel  |                            |  |
|  |               +----------+-----------+                            |  |
|  |                          |                                        |  |
|  |     +--------------------+--------------------+                   |  |
|  |     |                    |                    |                   |  |
|  |     v                    v                    v                   |  |
|  |  +--------+        +----------+        +----------+               |  |
|  |  |  PUSH  |        |   SMS    |        |  EMAIL   |               |  |
|  |  | WORKER |        |  WORKER  |        |  WORKER  |               |  |
|  |  +---+----+        +----+-----+        +----+-----+               |  |
|  |      |                  |                   |                     |  |
|  |      v                  v                   v                     |  |
|  |  +--------+        +----------+        +----------+               |  |
|  |  |  APNs  |        |  Twilio  |        | SendGrid |               |  |
|  |  |  FCM   |        |          |        |   SES    |               |  |
|  |  +--------+        +----------+        +----------+               |  |
|  |                                                                   |  |
|  |                  +--------------+                                 |  |
|  |                  |   IN-APP     |                                 |  |
|  |                  |   WORKER     |                                 |  |
|  |                  +------+-------+                                 |  |
|  |                         |                                         |  |
|  |                         v                                         |  |
|  |                  +--------------+                                 |  |
|  |                  |    Redis     | --> WebSocket to client         |  |
|  |                  |  (In-app DB) |                                 |  |
|  |                  +--------------+                                 |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
```

*+-------------------------------------------------------------------------+*

## SECTION 6: COMPONENT DEEP DIVE
```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. NOTIFICATION API SERVICE                                            |
|  ------------------------------                                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  RESPONSIBILITIES:                                                |  |
|  |                                                                   |  |
|  |  1. Request Validation                                            |  |
|  |     * Required fields present                                     |  |
|  |     * Valid user_id, channel, template_id                         |  |
|  |                                                                   |  |
|  |  2. User Enrichment                                               |  |
|  |     * Fetch user preferences                                      |  |
|  |     * Get device tokens (for push)                                |  |
|  |     * Get email address, phone number                             |  |
|  |                                                                   |  |
|  |  3. Preference Check                                              |  |
|  |     * Is user opted-in for this channel?                          |  |
|  |     * Is user opted-in for this category?                         |  |
|  |     * Is it quiet hours?                                          |  |
|  |                                                                   |  |
|  |  4. Rate Limiting                                                 |  |
|  |     * Per-user limits (max 50 push/day)                           |  |
|  |     * Per-service limits (calling service quota)                  |  |
|  |                                                                   |  |
|  |  5. Template Rendering                                            |  |
|  |     * Fetch template by ID                                        |  |
|  |     * Substitute variables                                        |  |
|  |     * Apply localization                                          |  |
|  |                                                                   |  |
|  |  6. Deduplication                                                 |  |
|  |     * Check if same notification sent recently                    |  |
|  |     * Idempotency key check                                       |  |
|  |                                                                   |  |
|  |  7. Enqueue                                                       |  |
|  |     * Put message on Kafka with priority                          |  |
|  |     * Return notification_id                                      |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  2. MESSAGE QUEUE (Kafka)                                               |
|  -------------------------                                              |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  TOPIC STRUCTURE:                                                 |  |
|  |                                                                   |  |
|  |  notifications.push.critical    (OTP, security)                   |  |
|  |  notifications.push.high        (transactional)                   |  |
|  |  notifications.push.normal      (social)                          |  |
|  |  notifications.push.low         (marketing)                       |  |
|  |                                                                   |  |
|  |  notifications.sms.critical     (OTP)                             |  |
|  |  notifications.sms.high         (alerts)                          |  |
|  |                                                                   |  |
|  |  notifications.email.high       (receipts, confirmations)         |  |
|  |  notifications.email.normal     (updates)                         |  |
|  |  notifications.email.low        (newsletters, marketing)          |  |
|  |                                                                   |  |
|  |  notifications.inapp            (all in-app)                      |  |
|  |                                                                   |  |
|  |  WHY SEPARATE TOPICS:                                             |  |
|  |  * Different SLAs per priority                                    |  |
|  |  * Scale workers independently per channel                        |  |
|  |  * Isolate failures (SMS down doesn't affect push)                |  |
|  |                                                                   |  |
|  |  PARTITIONING:                                                    |  |
|  |  * By user_id hash (for ordering per user)                        |  |
|  |  * Ensures same user's notifications processed in order           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  3. CHANNEL WORKERS                                                     |
|  -------------------                                                    |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  PUSH WORKER:                                                     |  |
|  |                                                                   |  |
|  |  1. Consume from Kafka                                            |  |
|  |  2. Batch notifications by platform (iOS/Android)                 |  |
|  |  3. Send to APNs (iOS) or FCM (Android)                           |  |
|  |  4. Handle responses:                                             |  |
|  |     * Success > Update status                                     |  |
|  |     * Invalid token > Remove token from user profile              |  |
|  |     * Rate limited > Retry with backoff                           |  |
|  |     * Server error > Retry with backoff                           |  |
|  |                                                                   |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  SMS WORKER:                                                      |  |
|  |                                                                   |  |
|  |  1. Consume from Kafka                                            |  |
|  |  2. Format message (160 char limit)                               |  |
|  |  3. Select SMS provider (Twilio, Nexmo, etc.)                     |  |
|  |     * Primary provider                                            |  |
|  |     * Fallback if primary fails                                   |  |
|  |  4. Handle country-specific routing                               |  |
|  |  5. Track delivery status via webhooks                            |  |
|  |                                                                   |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  EMAIL WORKER:                                                    |  |
|  |                                                                   |  |
|  |  1. Consume from Kafka                                            |  |
|  |  2. Render HTML template                                          |  |
|  |  3. Generate text version (for plaintext clients)                 |  |
|  |  4. Add tracking pixel (for open tracking)                        |  |
|  |  5. Rewrite links (for click tracking)                            |  |
|  |  6. Send via SendGrid/SES/Mailgun                                 |  |
|  |  7. Handle bounces and complaints via webhooks                    |  |
|  |                                                                   |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  IN-APP WORKER:                                                   |  |
|  |                                                                   |  |
|  |  1. Consume from Kafka                                            |  |
|  |  2. Store in database (Cassandra/Redis)                           |  |
|  |  3. If user online > push via WebSocket                           |  |
|  |  4. Update unread count                                           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
```

*+-------------------------------------------------------------------------+*

## SECTION 7: DATA MODEL
```
+-------------------------------------------------------------------------+
|                                                                         |
|  CORE TABLES                                                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  TABLE: notification_templates                                    |  |
|  |  +-----------------+---------------+----------------------------+ |  |
|  |  | template_id     | VARCHAR (PK)  | "order_shipped"            | |  |
|  |  | channel         | ENUM          | PUSH, SMS, EMAIL           | |  |
|  |  | category        | VARCHAR       | "transactional"            | |  |
|  |  | title_template  | TEXT          | "Order {{order_id}}"       | |  |
|  |  | body_template   | TEXT          | "Your order shipped"       | |  |
|  |  | html_template   | TEXT          | For email HTML             | |  |
|  |  | language        | VARCHAR       | "en", "es", "fr"           | |  |
|  |  | created_at      | TIMESTAMP     |                            | |  |
|  |  | updated_at      | TIMESTAMP     |                            | |  |
|  |  +-----------------+---------------+----------------------------+ |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  TABLE: user_preferences                                          |  |
|  |  +-----------------+---------------+----------------------------+ |  |
|  |  | user_id         | BIGINT (PK)   | User identifier            | |  |
|  |  | push_enabled    | BOOLEAN       | Opt-in for push            | |  |
|  |  | sms_enabled     | BOOLEAN       | Opt-in for SMS             | |  |
|  |  | email_enabled   | BOOLEAN       | Opt-in for email           | |  |
|  |  | quiet_start     | TIME          | 22:00 (10 PM)              | |  |
|  |  | quiet_end       | TIME          | 08:00 (8 AM)               | |  |
|  |  | timezone        | VARCHAR       | "America/New_York"         | |  |
|  |  | language        | VARCHAR       | "en"                       | |  |
|  |  | categories      | JSON          | {"marketing": false}       | |  |
|  |  +-----------------+---------------+----------------------------+ |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  TABLE: device_tokens                                             |  |
|  |  +-----------------+---------------+----------------------------+ |  |
|  |  | token_id        | UUID (PK)     | Unique identifier          | |  |
|  |  | user_id         | BIGINT        | Owner                      | |  |
|  |  | token           | VARCHAR       | APNs/FCM token             | |  |
|  |  | platform        | ENUM          | IOS, ANDROID, WEB          | |  |
|  |  | device_id       | VARCHAR       | Device identifier          | |  |
|  |  | app_version     | VARCHAR       | "3.2.1"                    | |  |
|  |  | created_at      | TIMESTAMP     |                            | |  |
|  |  | last_used_at    | TIMESTAMP     | Last notification sent     | |  |
|  |  | is_valid        | BOOLEAN       | False if token expired     | |  |
|  |  +-----------------+---------------+----------------------------+ |  |
|  |                                                                   |  |
|  |  INDEX: (user_id, is_valid)                                       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  TABLE: notifications (Write-heavy, use Cassandra)                |  |
|  |  +-----------------+---------------+----------------------------+ |  |
|  |  | notification_id | UUID (PK)     | Unique identifier          | |  |
|  |  | user_id         | BIGINT        | Recipient                  | |  |
|  |  | channel         | ENUM          | PUSH, SMS, EMAIL           | |  |
|  |  | template_id     | VARCHAR       | Template used              | |  |
|  |  | title           | VARCHAR       | Rendered title             | |  |
|  |  | body            | TEXT          | Rendered content           | |  |
|  |  | status          | ENUM          | PENDING, SENT,             | |  |
|  |  |                 |               | DELIVERED, FAILED          | |  |
|  |  | priority        | ENUM          | CRITICAL, HIGH, etc.       | |  |
|  |  | created_at      | TIMESTAMP     | Request time               | |  |
|  |  | sent_at         | TIMESTAMP     | When sent to provider      | |  |
|  |  | delivered_at    | TIMESTAMP     | Provider confirmation      | |  |
|  |  | opened_at       | TIMESTAMP     | User opened (if track)     | |  |
|  |  | clicked_at      | TIMESTAMP     | User clicked link          | |  |
|  |  | error_code      | VARCHAR       | If failed                  | |  |
|  |  | error_message   | TEXT          | If failed                  | |  |
|  |  | retry_count     | INT           | Retry attempts             | |  |
|  |  | metadata        | JSON          | Extra context              | |  |
|  |  +-----------------+---------------+----------------------------+ |  |
|  |                                                                   |  |
|  |  Partition key: user_id (for "my notifications" query)            |  |
|  |  Clustering key: created_at DESC                                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  TABLE: in_app_notifications (For notification center)            |  |
|  |  +-----------------+---------------+----------------------------+ |  |
|  |  | user_id         | BIGINT (PK)   | Recipient                  | |  |
|  |  | notification_id | UUID (PK)     | Notification               | |  |
|  |  | title           | VARCHAR       | Display title              | |  |
|  |  | body            | TEXT          | Display text               | |  |
|  |  | icon_url        | VARCHAR       | Notification icon          | |  |
|  |  | action_url      | VARCHAR       | Deep link                  | |  |
|  |  | is_read         | BOOLEAN       | User has seen              | |  |
|  |  | created_at      | TIMESTAMP     | When created               | |  |
|  |  | expires_at      | TIMESTAMP     | TTL for cleanup            | |  |
|  |  +-----------------+---------------+----------------------------+ |  |
|  |                                                                   |  |
|  |  Query: Get unread notifications for user                         |  |
|  |  SELECT * FROM in_app_notifications                               |  |
|  |  WHERE user_id = ? AND is_read = false                            |  |
|  |  ORDER BY created_at DESC LIMIT 50;                               |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
```

*+-------------------------------------------------------------------------+*

## SECTION 8: API DESIGN
```
+-------------------------------------------------------------------------+
|                                                                         |
|  SEND NOTIFICATION API                                                  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  POST /api/v1/notifications                                       |  |
|  |                                                                   |  |
|  |  Request:                                                         |  |
|  |  {                                                                |  |
|  |    "user_id": "12345",                                            |  |
|  |    "template_id": "order_shipped",                                |  |
|  |    "channels": ["push", "email"],                                 |  |
|  |    "priority": "high",                                            |  |
|  |    "variables": {                                                 |  |
|  |      "order_id": "ORD-789",                                       |  |
|  |      "tracking_url": "https://..."                                |  |
|  |    },                                                             |  |
|  |    "idempotency_key": "order-789-shipped",                        |  |
|  |    "scheduled_at": null,  // or ISO timestamp                     |  |
|  |    "metadata": {                                                  |  |
|  |      "source": "order-service",                                   |  |
|  |      "order_id": "789"                                            |  |
|  |    }                                                              |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  |  Response:                                                        |  |
|  |  {                                                                |  |
|  |    "notification_id": "ntf-uuid-123",                             |  |
|  |    "status": "queued",                                            |  |
|  |    "channels_queued": ["push", "email"]                           |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  BATCH SEND (For bulk notifications)                              |  |
|  |                                                                   |  |
|  |  POST /api/v1/notifications/batch                                 |  |
|  |                                                                   |  |
|  |  Request:                                                         |  |
|  |  {                                                                |  |
|  |    "template_id": "weekly_digest",                                |  |
|  |    "channel": "email",                                            |  |
|  |    "priority": "low",                                             |  |
|  |    "recipients": [                                                |  |
|  |      { "user_id": "123", "variables": {...} },                    |  |
|  |      { "user_id": "456", "variables": {...} },                    |  |
|  |      ...                                                          |  |
|  |    ]                                                              |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  |  Response:                                                        |  |
|  |  {                                                                |  |
|  |    "batch_id": "batch-uuid-789",                                  |  |
|  |    "status": "processing",                                        |  |
|  |    "total_recipients": 10000,                                     |  |
|  |    "queued": 10000                                                |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  GET NOTIFICATION STATUS                                          |  |
|  |                                                                   |  |
|  |  GET /api/v1/notifications/{notification_id}                      |  |
|  |                                                                   |  |
|  |  Response:                                                        |  |
|  |  {                                                                |  |
|  |    "notification_id": "ntf-uuid-123",                             |  |
|  |    "user_id": "12345",                                            |  |
|  |    "channels": {                                                  |  |
|  |      "push": {                                                    |  |
|  |        "status": "delivered",                                     |  |
|  |        "sent_at": "2024-01-15T10:00:00Z",                         |  |
|  |        "delivered_at": "2024-01-15T10:00:01Z"                     |  |
|  |      },                                                           |  |
|  |      "email": {                                                   |  |
|  |        "status": "opened",                                        |  |
|  |        "sent_at": "2024-01-15T10:00:00Z",                         |  |
|  |        "opened_at": "2024-01-15T10:05:00Z"                        |  |
|  |      }                                                            |  |
|  |    }                                                              |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  USER PREFERENCES API                                             |  |
|  |                                                                   |  |
|  |  GET /api/v1/users/{user_id}/preferences                          |  |
|  |  PUT /api/v1/users/{user_id}/preferences                          |  |
|  |                                                                   |  |
|  |  {                                                                |  |
|  |    "push_enabled": true,                                          |  |
|  |    "email_enabled": true,                                         |  |
|  |    "sms_enabled": false,                                          |  |
|  |    "quiet_hours": {                                               |  |
|  |      "enabled": true,                                             |  |
|  |      "start": "22:00",                                            |  |
|  |      "end": "08:00"                                               |  |
|  |    },                                                             |  |
|  |    "categories": {                                                |  |
|  |      "marketing": false,                                          |  |
|  |      "social": true,                                              |  |
|  |      "transactional": true                                        |  |
|  |    }                                                              |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  IN-APP NOTIFICATIONS API (For client apps)                       |  |
|  |                                                                   |  |
|  |  GET /api/v1/users/{user_id}/notifications                        |  |
|  |  Query: ?unread_only=true&limit=20&cursor=xxx                     |  |
|  |                                                                   |  |
|  |  POST /api/v1/users/{user_id}/notifications/mark-read             |  |
|  |  { "notification_ids": ["ntf-1", "ntf-2"] }                       |  |
|  |                                                                   |  |
|  |  POST /api/v1/users/{user_id}/notifications/mark-all-read         |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
```

*+-------------------------------------------------------------------------+*

## SECTION 9: PUSH NOTIFICATION DEEP DIVE
```
+-------------------------------------------------------------------------+
|                                                                         |
|  iOS (APNs) vs Android (FCM)                                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  APPLE PUSH NOTIFICATION SERVICE (APNs)                           |  |
|  |                                                                   |  |
|  |  +-----------------------------------------------------------+    |  |
|  |  |                                                           |    |  |
|  |  |  Your Server                                              |    |  |
|  |  |      |                                                    |    |  |
|  |  |      | HTTP/2 connection (keep-alive)                    |     |  |
|  |  |      | JWT authentication                                |     |  |
|  |  |      v                                                    |    |  |
|  |  |  APNs Server (api.push.apple.com)                        |     |  |
|  |  |      |                                                    |    |  |
|  |  |      |                                                    |    |  |
|  |  |      v                                                    |    |  |
|  |  |  iPhone                                                   |    |  |
|  |  |                                                           |    |  |
|  |  +-----------------------------------------------------------+    |  |
|  |                                                                   |  |
|  |  Payload format:                                                  |  |
|  |  {                                                                |  |
|  |    "aps": {                                                       |  |
|  |      "alert": {                                                   |  |
|  |        "title": "Order Shipped",                                  |  |
|  |        "body": "Your order is on its way!"                        |  |
|  |      },                                                           |  |
|  |      "badge": 5,                                                  |  |
|  |      "sound": "default",                                          |  |
|  |      "content-available": 1  // silent push                       |  |
|  |    },                                                             |  |
|  |    "custom_data": {...}                                           |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  |  Limits:                                                          |  |
|  |  * Payload max: 4 KB                                              |  |
|  |  * No rate limit (but Apple may throttle if abusive)              |  |
|  |                                                                   |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  FIREBASE CLOUD MESSAGING (FCM)                                   |  |
|  |                                                                   |  |
|  |  +-----------------------------------------------------------+    |  |
|  |  |                                                           |    |  |
|  |  |  Your Server                                              |    |  |
|  |  |      |                                                    |    |  |
|  |  |      | HTTP POST to fcm.googleapis.com                   |     |  |
|  |  |      | OAuth 2.0 authentication                          |     |  |
|  |  |      v                                                    |    |  |
|  |  |  FCM Server                                               |    |  |
|  |  |      |                                                    |    |  |
|  |  |      v                                                    |    |  |
|  |  |  Android Device                                           |    |  |
|  |  |                                                           |    |  |
|  |  +-----------------------------------------------------------+    |  |
|  |                                                                   |  |
|  |  Payload format:                                                  |  |
|  |  {                                                                |  |
|  |    "message": {                                                   |  |
|  |      "token": "device_token_here",                                |  |
|  |      "notification": {                                            |  |
|  |        "title": "Order Shipped",                                  |  |
|  |        "body": "Your order is on its way!"                        |  |
|  |      },                                                           |  |
|  |      "data": {                                                    |  |
|  |        "order_id": "123",                                         |  |
|  |        "deep_link": "myapp://orders/123"                          |  |
|  |      },                                                           |  |
|  |      "android": {                                                 |  |
|  |        "priority": "high",                                        |  |
|  |        "notification": {                                          |  |
|  |          "channel_id": "orders"                                   |  |
|  |        }                                                          |  |
|  |      }                                                            |  |
|  |    }                                                              |  |
|  |  }                                                                |  |
|  |                                                                   |  |
|  |  Limits:                                                          |  |
|  |  * Payload max: 4 KB                                              |  |
|  |  * Rate limit: ~240 messages/min per device                       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  DEVICE TOKEN MANAGEMENT                                                |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Token lifecycle:                                                 |  |
|  |                                                                   |  |
|  |  1. App installed > Register token with APNs/FCM                  |  |
|  |  2. Send token to your server                                     |  |
|  |  3. Store: (user_id, token, platform, timestamp)                  |  |
|  |  4. Token can change! (app update, reinstall)                     |  |
|  |  5. On push failure "invalid token" > delete from DB              |  |
|  |                                                                   |  |
|  |  Multiple devices per user:                                       |  |
|  |  * User may have iPhone + iPad + Android                          |  |
|  |  * Send to ALL valid tokens                                       |  |
|  |  * Dedupe on device_id to avoid multiple tokens per device        |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
```

*+-------------------------------------------------------------------------+*

## SECTION 10: RELIABILITY & RETRY HANDLING
```
+-------------------------------------------------------------------------+
|                                                                         |
|  RETRY STRATEGY                                                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  NOT ALL FAILURES SHOULD RETRY:                                   |  |
|  |                                                                   |  |
|  |  +-----------------+----------------+------------------------+    |  |
|  |  | Error Type      | Retry?         | Action                 |    |  |
|  |  +-----------------+----------------+------------------------+    |  |
|  |  | Invalid token   | NO             | Delete token, don't   |     |  |
|  |  |                 |                | retry                  |    |  |
|  |  | User unsubscri. | NO             | Update preferences    |     |  |
|  |  | Rate limited    | YES            | Retry with backoff    |     |  |
|  |  | Server error    | YES            | Retry with backoff    |     |  |
|  |  | Timeout         | YES            | Retry immediately     |     |  |
|  |  | Malformed req   | NO             | Log, alert, fix bug   |     |  |
|  |  +-----------------+----------------+------------------------+    |  |
|  |                                                                   |  |
|  |  EXPONENTIAL BACKOFF:                                             |  |
|  |                                                                   |  |
|  |  Attempt 1: Immediate                                             |  |
|  |  Attempt 2: 1 second                                              |  |
|  |  Attempt 3: 2 seconds                                             |  |
|  |  Attempt 4: 4 seconds                                             |  |
|  |  Attempt 5: 8 seconds                                             |  |
|  |  Max attempts: 5                                                  |  |
|  |                                                                   |  |
|  |  After max attempts: Move to Dead Letter Queue                    |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  DEAD LETTER QUEUE (DLQ)                                                |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Purpose: Store notifications that repeatedly failed              |  |
|  |                                                                   |  |
|  |  +-----------------------------------------------------------+    |  |
|  |  |                                                           |    |  |
|  |  |  Main Queue > Worker > [Fail] > Retry Queue              |     |  |
|  |  |                                     |                     |    |  |
|  |  |                                     | (after max retries) |    |  |
|  |  |                                     v                     |    |  |
|  |  |                              Dead Letter Queue            |    |  |
|  |  |                                     |                     |    |  |
|  |  |                                     v                     |    |  |
|  |  |                              Manual Review / Alert        |    |  |
|  |  |                                                           |    |  |
|  |  +-----------------------------------------------------------+    |  |
|  |                                                                   |  |
|  |  Actions on DLQ:                                                  |  |
|  |  * Alert on-call if critical notification                         |  |
|  |  * Batch retry after provider issue resolved                      |  |
|  |  * Analyze patterns (why so many failures?)                       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  PROVIDER FALLBACK                                                      |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  For SMS and Email, maintain multiple providers:                  |  |
|  |                                                                   |  |
|  |  SMS:                                                             |  |
|  |  * Primary: Twilio                                                |  |
|  |  * Fallback: Nexmo                                                |  |
|  |  * Fallback 2: AWS SNS                                            |  |
|  |                                                                   |  |
|  |  Email:                                                           |  |
|  |  * Primary: SendGrid                                              |  |
|  |  * Fallback: AWS SES                                              |  |
|  |  * Fallback 2: Mailgun                                            |  |
|  |                                                                   |  |
|  |  Implementation:                                                  |  |
|  |                                                                   |  |
|  |  def send_sms(phone, message):                                    |  |
|  |      providers = [twilio, nexmo, aws_sns]                         |  |
|  |      for provider in providers:                                   |  |
|  |          try:                                                     |  |
|  |              return provider.send(phone, message)                 |  |
|  |          except ProviderError:                                    |  |
|  |              log.warn(f"{provider} failed, trying next")          |  |
|  |              continue                                             |  |
|  |      raise AllProvidersFailed()                                   |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
```

*+-------------------------------------------------------------------------+*

## SECTION 11: RATE LIMITING & THROTTLING
```
+-------------------------------------------------------------------------+
|                                                                         |
|  MULTIPLE LEVELS OF RATE LIMITING                                       |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. PER-USER LIMITS (Prevent spam)                                |  |
|  |     * Max 50 push notifications/day                               |  |
|  |     * Max 5 SMS/day                                               |  |
|  |     * Max 10 marketing emails/week                                |  |
|  |                                                                   |  |
|  |  2. PER-SERVICE LIMITS (Prevent runaway services)                 |  |
|  |     * Order service: 10K notifications/minute                     |  |
|  |     * Marketing service: 100K emails/hour                         |  |
|  |                                                                   |  |
|  |  3. GLOBAL LIMITS (Protect infrastructure)                        |  |
|  |     * Total push: 100K/second                                     |  |
|  |     * Total SMS: 10K/second                                       |  |
|  |     * Total email: 50K/second                                     |  |
|  |                                                                   |  |
|  |  4. PROVIDER LIMITS (External constraints)                        |  |
|  |     * APNs: Varies (throttles if too aggressive)                  |  |
|  |     * FCM: 240 messages/minute per device                         |  |
|  |     * Twilio: Based on account tier                               |  |
|  |     * SendGrid: Based on plan                                     |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  QUIET HOURS IMPLEMENTATION                                             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  def should_send_now(user_id, notification):                      |  |
|  |      # Critical always sends                                      |  |
|  |      if notification.priority == "critical":                      |  |
|  |          return True                                              |  |
|  |                                                                   |  |
|  |      prefs = get_user_preferences(user_id)                        |  |
|  |      if not prefs.quiet_hours_enabled:                            |  |
|  |          return True                                              |  |
|  |                                                                   |  |
|  |      user_local_time = get_local_time(prefs.timezone)             |  |
|  |      quiet_start = prefs.quiet_start  # 22:00                     |  |
|  |      quiet_end = prefs.quiet_end      # 08:00                     |  |
|  |                                                                   |  |
|  |      if is_within_quiet_hours(user_local_time,                    |  |
|  |                               quiet_start, quiet_end):            |  |
|  |          # Queue for delivery after quiet hours                   |  |
|  |          schedule_for(notification, quiet_end)                    |  |
|  |          return False                                             |  |
|  |                                                                   |  |
|  |      return True                                                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  NOTIFICATION BATCHING                                                  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Problem: User gets 10 likes in 1 minute                          |  |
|  |           Don't send 10 separate push notifications!              |  |
|  |                                                                   |  |
|  |  Solution: Batch similar notifications                            |  |
|  |                                                                   |  |
|  |  Instead of:                                                      |  |
|  |  * "Alice liked your post"                                        |  |
|  |  * "Bob liked your post"                                          |  |
|  |  * "Carol liked your post"                                        |  |
|  |                                                                   |  |
|  |  Send:                                                            |  |
|  |  * "Alice, Bob, and 8 others liked your post"                     |  |
|  |                                                                   |  |
|  |  Implementation:                                                  |  |
|  |  * Window-based batching (collect for 30 seconds)                 |  |
|  |  * Key: (user_id, notification_type, target_object)               |  |
|  |  * Aggregate count during window                                  |  |
|  |  * Send summary after window closes                               |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
```

*+-------------------------------------------------------------------------+*

## SECTION 12: ANALYTICS & TRACKING
```
+-------------------------------------------------------------------------+
|                                                                         |
|  TRACKING PIPELINE                                                      |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Notification Sent                                                |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  +-------------------------------------------------------------+  |  |
|  |  |  EVENT: notification_sent                                   |  |  |
|  |  |  { notification_id, user_id, channel, timestamp }           |  |  |
|  |  +-------------------------------------------------------------+  |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  Provider Webhook (Delivered)                                     |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  +-------------------------------------------------------------+  |  |
|  |  |  EVENT: notification_delivered                              |  |  |
|  |  |  { notification_id, timestamp }                             |  |  |
|  |  +-------------------------------------------------------------+  |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  User Opens (Tracking pixel / app open)                           |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  +-------------------------------------------------------------+  |  |
|  |  |  EVENT: notification_opened                                 |  |  |
|  |  |  { notification_id, timestamp }                             |  |  |
|  |  +-------------------------------------------------------------+  |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  User Clicks Link                                                 |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  +-------------------------------------------------------------+  |  |
|  |  |  EVENT: notification_clicked                                |  |  |
|  |  |  { notification_id, link_url, timestamp }                   |  |  |
|  |  +-------------------------------------------------------------+  |  |
|  |                                                                   |  |
|  |  All events > Kafka > Analytics DB (ClickHouse/BigQuery)          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  METRICS DASHBOARD                                                      |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  KEY METRICS:                                                     |  |
|  |                                                                   |  |
|  |  Delivery Metrics:                                                |  |
|  |  * Sent count (by channel, template, priority)                    |  |
|  |  * Delivery rate = delivered / sent                               |  |
|  |  * Failure rate (by error code)                                   |  |
|  |  * Average latency (sent to delivered)                            |  |
|  |                                                                   |  |
|  |  Engagement Metrics:                                              |  |
|  |  * Open rate = opened / delivered                                 |  |
|  |  * Click rate = clicked / opened                                  |  |
|  |  * Unsubscribe rate                                               |  |
|  |                                                                   |  |
|  |  System Metrics:                                                  |  |
|  |  * Queue depth (by priority)                                      |  |
|  |  * Processing latency                                             |  |
|  |  * Worker throughput                                              |  |
|  |  * Provider availability                                          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
```

*+-------------------------------------------------------------------------+*

## SECTION 13: ADVANCED TOPICS & REAL-WORLD PROBLEMS
```
+-------------------------------------------------------------------------+
|                                                                         |
|  NOTIFICATION FATIGUE                                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Problem: Users disable all notifications because too many        |  |
|  |                                                                   |  |
|  |  Solutions:                                                       |  |
|  |                                                                   |  |
|  |  1. SMART FREQUENCY CAPPING                                       |  |
|  |     * ML model predicts optimal notification frequency            |  |
|  |     * Reduce for users who don't engage                           |  |
|  |     * "This user opens 10% of pushes, send max 2/day"             |  |
|  |                                                                   |  |
|  |  2. NOTIFICATION SCORING                                          |  |
|  |     * Score each notification by importance                       |  |
|  |     * Only send if score > user's threshold                       |  |
|  |     * Threshold adapts based on engagement                        |  |
|  |                                                                   |  |
|  |  3. DIGEST MODE                                                   |  |
|  |     * Batch low-priority into daily/weekly digest                 |  |
|  |     * User preference: real-time vs digest                        |  |
|  |                                                                   |  |
|  |  4. CATEGORY MANAGEMENT                                           |  |
|  |     * Let users control by category                               |  |
|  |     * "Turn off marketing but keep order updates"                 |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  EMAIL DELIVERABILITY                                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Problem: Emails going to spam folder                             |  |
|  |                                                                   |  |
|  |  Solutions:                                                       |  |
|  |                                                                   |  |
|  |  1. AUTHENTICATION                                                |  |
|  |     * SPF (Sender Policy Framework)                               |  |
|  |     * DKIM (DomainKeys Identified Mail)                           |  |
|  |     * DMARC (Domain-based Message Authentication)                 |  |
|  |                                                                   |  |
|  |  2. IP REPUTATION                                                 |  |
|  |     * Use dedicated IPs for marketing vs transactional            |  |
|  |     * Warm up new IPs gradually                                   |  |
|  |     * Monitor blacklists                                          |  |
|  |                                                                   |  |
|  |  3. LIST HYGIENE                                                  |  |
|  |     * Remove bounced emails                                       |  |
|  |     * Remove unengaged users (no opens in 6 months)               |  |
|  |     * Double opt-in for marketing                                 |  |
|  |                                                                   |  |
|  |  4. CONTENT BEST PRACTICES                                        |  |
|  |     * Avoid spam trigger words                                    |  |
|  |     * Good text-to-image ratio                                    |  |
|  |     * Working unsubscribe link (required by law)                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  MULTI-REGION DEPLOYMENT                                                |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  For global users, deploy in multiple regions:                    |  |
|  |                                                                   |  |
|  |  +-----------------------------------------------------------+    |  |
|  |  |                                                           |    |  |
|  |  |  US Users          EU Users          APAC Users          |     |  |
|  |  |      |                 |                 |                |    |  |
|  |  |      v                 v                 v                |    |  |
|  |  |  US Region         EU Region        APAC Region          |     |  |
|  |  |  Workers           Workers           Workers              |    |  |
|  |  |      |                 |                 |                |    |  |
|  |  |      v                 v                 v                |    |  |
|  |  |  APNs/FCM          APNs/FCM         APNs/FCM             |     |  |
|  |  |                                                           |    |  |
|  |  +-----------------------------------------------------------+    |  |
|  |                                                                   |  |
|  |  Benefits:                                                        |  |
|  |  * Lower latency to APNs/FCM (they have regional endpoints)       |  |
|  |  * Data residency compliance (GDPR)                               |  |
|  |  * Fault isolation                                                |  |
|  |                                                                   |  |
|  |  Routing:                                                         |  |
|  |  * Route by user's region (stored in profile)                     |  |
|  |  * Or by device token prefix (FCM has regional hints)             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  A/B TESTING NOTIFICATIONS                                              |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Test different:                                                  |  |
|  |  * Message copy                                                   |  |
|  |  * Send time                                                      |  |
|  |  * Frequency                                                      |  |
|  |  * Channel combination                                            |  |
|  |                                                                   |  |
|  |  Implementation:                                                  |  |
|  |                                                                   |  |
|  |  def select_template(user_id, template_id, experiment_id):        |  |
|  |      bucket = hash(user_id, experiment_id) % 100                  |  |
|  |                                                                   |  |
|  |      if bucket < 50:  # Control                                   |  |
|  |          return template_id + "_control"                          |  |
|  |      else:            # Variant                                   |  |
|  |          return template_id + "_variant"                          |  |
|  |                                                                   |  |
|  |  Track: experiment_id with each notification                      |  |
|  |  Analyze: Compare open/click rates between variants               |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  PERSONALIZATION / ML-POWERED NOTIFICATIONS                             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. SEND TIME OPTIMIZATION                                        |  |
|  |     * ML predicts when user most likely to engage                 |  |
|  |     * Based on historical open patterns                           |  |
|  |     * "User opens notifications around 8 AM and 6 PM"             |  |
|  |                                                                   |  |
|  |  2. CHANNEL SELECTION                                             |  |
|  |     * Some users prefer email, some prefer push                   |  |
|  |     * ML selects optimal channel per user                         |  |
|  |                                                                   |  |
|  |  3. CONTENT PERSONALIZATION                                       |  |
|  |     * Dynamic subject lines based on user interests               |  |
|  |     * Product recommendations in notification                     |  |
|  |                                                                   |  |
|  |  4. PREDICTIVE NOTIFICATIONS                                      |  |
|  |     * Predict user needs before they act                          |  |
|  |     * "Your usual order? Tap to reorder"                          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
```

*+-------------------------------------------------------------------------+*

### DETAILED WRITE/READ PATHS AND STATE MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                        |
|  1. ENTITY STATE MACHINE (Notification Lifecycle)                      |
|                                                                        |
|    [CREATED] --> [QUEUED] --> [SENDING] --> [DELIVERED]                |
|        |            |            |              |                      |
|        |            |            |              +---> [OPENED/CLICKED] |
|        |            |            |                                     |
|        |            |            +---> [FAILED] ---> [RETRYING]        |
|        |            |                                    |             |
|        |            |                   +----------------+             |
|        |            |                   |                              |
|        |            |                   v                              |
|        |            |              [DEAD_LETTER]                       |
|        |            |                                                  |
|        |            +---> [DROPPED]  (rate limit, user opted out,      |
|        |                              quiet hours)                     |
|        +---> [DROPPED]  (preference check failed at API layer)         |
|                                                                        |
|    CREATED:    Notification API receives request, validates input      |
|    QUEUED:     Written to Kafka topic (partitioned by priority)        |
|    SENDING:    Channel worker picked up, calling provider (APNs/FCM)   |
|    DELIVERED:  Provider confirmed delivery (or best-effort sent)       |
|    FAILED:     Provider returned error (token invalid, rate limit)     |
|    RETRYING:   Re-enqueued with exponential backoff                    |
|    DEAD_LETTER: Max retries exceeded, moved to DLQ for inspection      |
|    DROPPED:    Filtered by preferences, rate limit, or quiet hours     |
|    OPENED:     User tapped push / opened email (tracking pixel)        |
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  2. CRITICAL WRITE PATH (Notification Dispatch)                        |
|                                                                        |
|    Internal Service: POST /api/v1/notifications                        |
|      { user_id, template_id, channel, data, priority }                 |
|      |                                                                 |
|      v                                                                 |
|    Step 1: Validate request and render template                        |
|      |     SELECT * FROM notification_templates                        |
|      |       WHERE template_id = 'order_shipped';                      |
|      |     Render title/body with {{order_id}} placeholders            |
|      v                                                                 |
|    Step 2: Check user preferences (cached in Redis)                    |
|      |     GET user_prefs:{user_id}                                    |
|      |     Cache miss -> SELECT * FROM user_preferences                |
|      |       WHERE user_id = ?;                                        |
|      |     Check: channel enabled? category opted in?                  |
|      |     Check: quiet_start/quiet_end in user's timezone             |
|      |     If quiet hours -> schedule for after quiet_end              |
|      |     If opted out -> DROP, return { status: "filtered" }         |
|      v                                                                 |
|    Step 3: Rate limit check                                            |
|      |     Redis: INCR notif_rate:{user_id}:{channel} EX 3600          |
|      |     If count > per_user_limit -> DROP                           |
|      v                                                                 |
|    Step 4: Persist notification record                                 |
|      |     INSERT INTO notifications                                   |
|      |       (notification_id, user_id, channel, template_id,          |
|      |        title, body, status, priority, created_at,               |
|      |        retry_count, metadata)                                   |
|      |     VALUES (uuid(), ?, 'PUSH', 'order_shipped',                 |
|      |        'Order Shipped', 'Your order...', 'QUEUED',              |
|      |        'HIGH', NOW(), 0, '{}');                                 |
|      v                                                                 |
|    Step 5: Enqueue to Kafka (priority-based topic)                     |
|      |     Topic: push.high  (channel.priority)                        |
|      |     Key: user_id (partition by user for ordering)               |
|      |     Payload: { notification_id, user_id, channel, title,        |
|      |               body, device_tokens, priority }                   |
|      v                                                                 |
|    Step 6: Channel worker consumes from Kafka                          |
|      |     Fetch device tokens:                                        |
|      |       SELECT token, platform FROM device_tokens                 |
|      |         WHERE user_id = ? AND is_valid = true;                  |
|      |     Call provider: APNs (iOS) or FCM (Android)                  |
|      |     Batch up to 500 notifications per FCM request               |
|      v                                                                 |
|    Step 7: Update status on provider response                          |
|      |     UPDATE notifications SET status = 'DELIVERED',              |
|      |       sent_at = NOW(), delivered_at = NOW()                     |
|      |       WHERE notification_id = ?;                                |
|      |     If provider error:                                          |
|      |       If token_invalid -> UPDATE device_tokens SET              |
|      |         is_valid = false WHERE token = ?;                       |
|      |       If transient -> re-enqueue with backoff                   |
|      |       If max retries -> move to DLQ                             |
|                                                                        |
|    WRITE ORDER: PostgreSQL (notifications) -> Kafka -> Provider        |
|                 -> PostgreSQL (status update)                          |
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  3. READ PATH (Notification Inbox - Paginated)                         |
|                                                                        |
|    User: GET /api/v1/notifications?cursor=...&limit=20                 |
|      |                                                                 |
|      v                                                                 |
|    Step 1: Redis check for in-app notifications                        |
|      |     ZREVRANGEBYSCORE in_app:{user_id} +inf <cursor> LIMIT 20    |
|      |     HIT -> return from cache                                    |
|      |     MISS -> Step 2                                              |
|      v                                                                 |
|    Step 2: Query Cassandra (optimized for this access pattern)         |
|      |     SELECT * FROM in_app_notifications                          |
|      |       WHERE user_id = ? ORDER BY created_at DESC LIMIT 20;      |
|      v                                                                 |
|    Step 3: Return paginated list                                       |
|            Unread count: Redis GET unread_count:{user_id}              |
|                                                                        |
|    Mark as Read:                                                       |
|      POST /api/v1/notifications/{id}/read                              |
|      UPDATE in_app_notifications SET is_read = true                    |
|        WHERE user_id = ? AND notification_id = ?;                      |
|      Redis: DECR unread_count:{user_id}                                |
|                                                                        |
|    Real-Time Delivery:                                                 |
|      In-app worker writes to Redis sorted set + publishes              |
|      via WebSocket to connected clients immediately                    |
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  4. FAILURE SCENARIOS                                                  |
|                                                                        |
|  What Fails               | Impact & Recovery                          |
|  -------------------------+--------------------------------------------+
|  APNs/FCM provider down   | Push notifications queue in Kafka. Workers |
|                           | retry with exponential backoff. Switch to  |
|                           | backup channel (email) for critical notifs.|
|                           | Kafka retains messages until provider up.  |
|  -------------------------+--------------------------------------------+
|  Kafka down               | API cannot enqueue. Return 503 to callers. |
|                           | Notifications persisted in DB with status  |
|                           | QUEUED. Recovery sweeper picks them up     |
|                           | when Kafka recovers (DB as fallback queue).|
|  -------------------------+--------------------------------------------+
|  Worker crash mid-send    | Kafka offset not committed. Message is     |
|                           | redelivered to another worker. Dedup via   |
|                           | notification_id check (idempotent update). |
|  -------------------------+--------------------------------------------+
|  SMS provider throttled   | Twilio returns 429. Worker backs off.      |
|                           | Fall back to secondary provider (Nexmo).   |
|                           | Critical SMS (OTP) gets priority retry.    |
|  -------------------------+--------------------------------------------+
|                                                                        |
|  ====================================================================  |
|                                                                        |
|  5. CLEANUP / EXPIRY                                                   |
|                                                                        |
|    In-App Notification Expiry:                                         |
|      in_app_notifications.expires_at checked on read                   |
|      Background job: DELETE FROM in_app_notifications                  |
|        WHERE expires_at < NOW();  (daily, batch of 50K)                |
|      Redis: ZREMRANGEBYSCORE in_app:{user_id} -inf <30_days_ago>       |
|                                                                        |
|    Dead Letter Queue Cleanup:                                          |
|      DLQ entries reviewed by ops team weekly                           |
|      Auto-purge after 30 days if not replayed                          |
|                                                                        |
|    Stale Device Token Removal:                                         |
|      Tokens marked is_valid=false by provider feedback                 |
|      Weekly job: DELETE FROM device_tokens                             |
|        WHERE is_valid = false AND last_used_at < NOW()-INTERVAL 90d;   |
|                                                                        |
|    Redis Cache TTL:                                                    |
|      user_prefs:{user_id}: EX 3600 (1h, refreshed on update)           |
|      unread_count:{user_id}: no TTL (maintained by INCR/DECR)          |
|      notif_rate:{user_id}:{channel}: EX 3600 (auto-expire window)      |
|                                                                        |
+-------------------------------------------------------------------------+
```

## SECTION 14: SCALING TO 30K+ NOTIFICATIONS/SECOND

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TARGET LOAD                                                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Average:  ~18,500 notifications/sec  (~1.6B/day)                 |  |
|  |  Peak:     ~30,000 - 185,000 notifications/sec  (10x burst)       |  |
|  |                                                                   |  |
|  |  Sources of bursts:                                               |  |
|  |   - Marketing blast: 50M emails kicked off at 9 AM                |  |
|  |   - Breaking news push: 100M users in 60 seconds                  |  |
|  |   - Black Friday: 5x normal traffic for 4 hours                   |  |
|  |   - Outage recovery: backlog drain when provider returns          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  BOTTLENECK ANALYSIS  (where 30k/sec actually breaks)                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Layer              | Limit (typical)  | Mitigation               |  |
|  |  -------------------+------------------+------------------------- |  |
|  |  Notification API   | ~5k req/sec/node | Horizontal scale + LB    |  |
|  |  Redis (rate limit) | ~100k ops/sec    | Cluster + local cache    |  |
|  |  DB insert (PG)     | ~10k writes/sec  | Async, batch, Cassandra  |  |
|  |  Kafka producer     | ~1M msg/sec      | Partition + batch + zstd |  |
|  |  Channel worker     | ~500 req/sec/wkr | Pool size + HTTP/2 reuse |  |
|  |  APNs / FCM         | ~50k+ msg/sec    | HTTP/2 multiplex, retry  |  |
|  |  SMS (Twilio)       | ~100 msg/sec/num | Provision more numbers   |  |
|  |  Email (SendGrid)   | ~10k msg/sec     | Multiple IPs, accounts   |  |
|  |                                                                   |  |
|  |  TIGHTEST BOTTLENECK is usually:                                  |  |
|  |   1) Provider rate limits (especially SMS)                        |  |
|  |   2) DB write throughput (without async/batch)                    |  |
|  |   3) Worker concurrency (without HTTP/2 reuse)                    |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  CAPACITY MATH  (sizing for 30k push/sec sustained)                     |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. KAFKA PARTITIONS                                              |  |
|  |     Each partition: ~10k msg/sec safely                           |  |
|  |     30k / 5k (safe headroom) = 6 partitions minimum               |  |
|  |     Use 32 partitions for parallelism + future headroom           |  |
|  |                                                                   |  |
|  |  2. WORKER COUNT                                                  |  |
|  |     One worker pod ~ 500 calls/sec (HTTP/2 to FCM)                |  |
|  |     30,000 / 500 = 60 worker pods                                 |  |
|  |     +50% headroom -> 90 worker pods                               |  |
|  |     Each pod runs ~200 concurrent coroutines (async I/O)          |  |
|  |                                                                   |  |
|  |  3. DB WRITE THROUGHPUT                                           |  |
|  |     30k inserts/sec on one PG node = NOT OK                       |  |
|  |     Options:                                                      |  |
|  |     - Cassandra (LSM): 30k writes/sec/node trivially              |  |
|  |     - PG with batch INSERT (1000 rows/txn) = 30 txn/sec OK        |  |
|  |     - Shard by user_id across N PG primaries                      |  |
|  |     - Async write (worker writes after enqueue, not before)       |  |
|  |                                                                   |  |
|  |  4. CONNECTION POOLING                                            |  |
|  |     FCM HTTP/2: each conn multiplexes ~100 concurrent streams     |  |
|  |     30,000 / 100 = 300 concurrent streams across pool             |  |
|  |     -> 10 HTTP/2 conns per pod x 90 pods = 900 total              |  |
|  |     FCM allows thousands of concurrent connections per project    |  |
|  |                                                                   |  |
|  |  5. RATE LIMITER (Redis)                                          |  |
|  |     30k INCR ops/sec on one Redis = OK (Redis does 100k+/sec)     |  |
|  |     For safety, use Redis cluster sharded by user_id              |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  KAFKA PARTITIONING STRATEGY                                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  PARTITION KEY:  hash(user_id)                                    |  |
|  |   - Same user's notifications stay ordered per partition          |  |
|  |   - Hot users distributed if partition count is large enough      |  |
|  |   - DO NOT key by notification_id (kills ordering per user)       |  |
|  |                                                                   |  |
|  |  TOPICS BY CHANNEL x PRIORITY:                                    |  |
|  |    notifications.push.critical    ( 4 partitions, OTP/security)   |  |
|  |    notifications.push.high        (16 partitions, transactional)  |  |
|  |    notifications.push.normal      (32 partitions, social)         |  |
|  |    notifications.push.low         (32 partitions, marketing)      |  |
|  |    notifications.email.high       ( 8 partitions)                 |  |
|  |    notifications.email.low        (16 partitions)                 |  |
|  |    notifications.sms.critical     ( 4 partitions, OTP)            |  |
|  |                                                                   |  |
|  |  WHY SPLIT BY PRIORITY (not just channel):                        |  |
|  |   - Dedicated worker pool per topic                               |  |
|  |   - Critical never blocked behind marketing backlog               |  |
|  |   - Independent scaling and lag SLOs per priority                 |  |
|  |   - Low-priority workers can run on spot/preemptible instances    |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  WORKER POOL DESIGN  (push worker, single pod)                          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |   Kafka consumer (poll batch of 500 msgs)                         |  |
|  |        |                                                          |  |
|  |        v                                                          |  |
|  |   In-memory bounded queue (10k slots)  <- backpressure here       |  |
|  |        |                                                          |  |
|  |        v                                                          |  |
|  |   Async worker pool: 200 coroutines                               |  |
|  |        |                                                          |  |
|  |        v                                                          |  |
|  |   HTTP/2 connection pool (10 conns to FCM)                        |  |
|  |        |                                                          |  |
|  |        v                                                          |  |
|  |   FCM /send (multiplexed streams)                                 |  |
|  |                                                                   |  |
|  |  SKETCH (async pseudocode):                                       |  |
|  |                                                                   |  |
|  |    consumer = kafka.subscribe("notifications.push.high")          |  |
|  |    pool     = HttpPool(host="fcm.googleapis.com", conns=10)       |  |
|  |    sem      = Semaphore(200)   # max in-flight                    |  |
|  |                                                                   |  |
|  |    async for batch in consumer.poll(500):                         |  |
|  |        coros = [send_one(m, pool, sem) for m in batch]            |  |
|  |        await gather(*coros)                                       |  |
|  |        consumer.commit(batch.last_offset)                         |  |
|  |                                                                   |  |
|  |    async def send_one(msg, pool, sem):                            |  |
|  |        async with sem:                                            |  |
|  |            try:                                                   |  |
|  |                resp = await pool.post("/send", payload=msg, ...)  |  |
|  |                await update_status(msg.id, "DELIVERED")           |  |
|  |            except RetryableError:                                 |  |
|  |                await retry_queue.enqueue(msg)                     |  |
|  |                                                                   |  |
|  |  KEY POINTS:                                                      |  |
|  |   - One Kafka commit per BATCH, not per message (10x faster)      |  |
|  |   - Semaphore caps in-flight so we don't OOM on bursts            |  |
|  |   - Connection pool keeps HTTP/2 conns warm                       |  |
|  |   - Status update is fire-and-forget (async) to keep latency low  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  HTTP/2 MULTIPLEXING  (key to high throughput)                          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  HTTP/1.1:  1 in-flight request per TCP connection                |  |
|  |   - Need 1000 connections to send 1000 concurrent reqs            |  |
|  |   - Connection setup/teardown + TLS overhead each time            |  |
|  |   - Easy to exhaust ephemeral ports / TLS handshakes              |  |
|  |                                                                   |  |
|  |  HTTP/2:   ~100 concurrent streams per connection (default)       |  |
|  |   - 10 connections -> 1000 in-flight requests                     |  |
|  |   - Single TLS handshake amortized across many requests           |  |
|  |   - APNs and FCM both REQUIRE HTTP/2                              |  |
|  |                                                                   |  |
|  |  THROUGHPUT IMPACT:                                               |  |
|  |   HTTP/1.1: ~50 req/sec/worker (connection-bound)                 |  |
|  |   HTTP/2:   ~500 req/sec/worker (10x improvement)                 |  |
|  |                                                                   |  |
|  |  APNs SPECIFIC:                                                   |  |
|  |   - Persistent HTTP/2 to api.push.apple.com                       |  |
|  |   - JWT-based auth (sign once per hour, reuse on every request)   |  |
|  |   - ~1000 concurrent streams per connection                       |  |
|  |   - Pre-warm connections at pod startup                           |  |
|  |                                                                   |  |
|  |  FCM SPECIFIC:                                                    |  |
|  |   - HTTP v1 API uses OAuth2 access tokens (cache 50 min)          |  |
|  |   - Multicast endpoint: up to 500 tokens per request              |  |
|  |   - Use multicast for broadcasts (1 req = 500 sends)              |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  PROVIDER BATCHING  (reducing request count)                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  FCM Multicast:                                                   |  |
|  |    POST /v1/projects/{p}/messages:sendEach                        |  |
|  |    Body: { tokens: [tok1...tok500], message: {...} }              |  |
|  |    Result: up to 500 sends in 1 HTTP request                      |  |
|  |    Throughput multiplier: 500x                                    |  |
|  |    Use for: marketing blast, breaking news, broadcasts            |  |
|  |    Don't use for: personalized notifications (body differs)       |  |
|  |                                                                   |  |
|  |  APNs:                                                            |  |
|  |    No native multicast - rely on HTTP/2 stream multiplexing       |  |
|  |    Send N individual reqs on the same connection in parallel      |  |
|  |                                                                   |  |
|  |  SendGrid:                                                        |  |
|  |    /v3/mail/send accepts up to 1000 personalizations/req          |  |
|  |    Group recipients with same template into one API call          |  |
|  |                                                                   |  |
|  |  Twilio:                                                          |  |
|  |    No bulk endpoint, but Messaging Service rotates across many    |  |
|  |    sender numbers automatically to multiply throughput            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  BACKPRESSURE AND LOAD SHEDDING                                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  When input rate > processing rate, options are:                  |  |
|  |                                                                   |  |
|  |  1. BUFFER  (Kafka does this naturally)                           |  |
|  |     - Kafka retains messages; consumer lag grows                  |  |
|  |     - OK for non-realtime (marketing, digests)                    |  |
|  |     - NOT ok for critical (OTP must arrive in seconds)            |  |
|  |                                                                   |  |
|  |  2. BACKPRESSURE TO PRODUCER                                      |  |
|  |     - Producer.send blocks if topic backlog past threshold        |  |
|  |     - API returns 503 to calling service                          |  |
|  |     - Caller retries with backoff (or dead-letters)               |  |
|  |                                                                   |  |
|  |  3. LOAD SHEDDING  (drop low priority first)                      |  |
|  |     - Worker checks consumer lag for its topic                    |  |
|  |     - If lag > 5 min on `.low` topic: drop msg, emit metric       |  |
|  |     - critical and high are NEVER shed                            |  |
|  |                                                                   |  |
|  |  4. CIRCUIT BREAKER  (provider down)                              |  |
|  |     - If FCM error rate > 50% for 30s: open circuit               |  |
|  |     - Workers pause; messages stay in Kafka                       |  |
|  |     - Probe every 30s until provider recovers                     |  |
|  |     - Avoids hammering a broken provider                          |  |
|  |                                                                   |  |
|  |  5. SCHEDULER-LEVEL THROTTLING                                    |  |
|  |     - Marketing blasts use token bucket (e.g. 10k/sec global)     |  |
|  |     - Smooths burst over time, protects downstream                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  AUTO-SCALING TRIGGERS                                                  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Scale workers UP when:                                           |  |
|  |   - Kafka consumer lag > 30s on critical/high topics              |  |
|  |   - p95 dispatch latency > 2s                                     |  |
|  |   - CPU > 70% sustained for 3 min                                 |  |
|  |                                                                   |  |
|  |  Scale workers DOWN when:                                         |  |
|  |   - Consumer lag near 0 AND CPU < 30% for 10 min                  |  |
|  |   - Keep minReplicas high enough to absorb sudden bursts          |  |
|  |                                                                   |  |
|  |  KEDA (Kubernetes Event-Driven Autoscaling):                      |  |
|  |    trigger:        kafka                                          |  |
|  |    topic:          notifications.push.high                        |  |
|  |    lagThreshold:   1000 msgs per partition                        |  |
|  |    minReplicas:    10                                             |  |
|  |    maxReplicas:    200                                            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

*+-------------------------------------------------------------------------+*

## SECTION 15: SCHEDULED NOTIFICATIONS DEEP DIVE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY SCHEDULING IS HARD                                                 |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Use cases:                                                       |  |
|  |   - Reminders: "Your appointment is in 1 hour"                    |  |
|  |   - Deferred: "Send after quiet hours end at 8 AM local"          |  |
|  |   - Marketing blast: "Send to 50M users at 9 AM tomorrow"         |  |
|  |   - Drip campaign: "Day 1: welcome, Day 3: tip, Day 7: upsell"    |  |
|  |   - Recurring: "Weekly digest every Monday 9 AM"                  |  |
|  |                                                                   |  |
|  |  Challenges:                                                      |  |
|  |   - 100M+ scheduled notifications outstanding at any moment       |  |
|  |   - Must fire at correct time +/- a few seconds                   |  |
|  |   - Bursts: 50M jobs all firing at 9 AM sharp                     |  |
|  |   - Cancellation (user unsubscribed before send)                  |  |
|  |   - Timezone-aware (per-user local time)                          |  |
|  |   - Exactly-once dispatch is impossible (best: at-least-once)     |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  APPROACH 1: DB-BACKED SCHEDULE + SWEEPER  (simple, small scale)        |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Schema:                                                          |  |
|  |    scheduled_notifications (                                      |  |
|  |       id          UUID PRIMARY KEY,                               |  |
|  |       user_id     BIGINT,                                         |  |
|  |       payload     JSONB,                                          |  |
|  |       fire_at     TIMESTAMP,                                      |  |
|  |       status      VARCHAR  -- PENDING | FIRED | CANCELLED         |  |
|  |    );                                                             |  |
|  |    INDEX (status, fire_at);                                       |  |
|  |                                                                   |  |
|  |  Sweeper loop (every 5 seconds):                                  |  |
|  |    SELECT * FROM scheduled_notifications                          |  |
|  |    WHERE status = 'PENDING' AND fire_at <= NOW()                  |  |
|  |    ORDER BY fire_at                                               |  |
|  |    LIMIT 10000                                                    |  |
|  |    FOR UPDATE SKIP LOCKED;          -- avoid double-fire          |  |
|  |                                                                   |  |
|  |    Then: push each onto Kafka, then:                              |  |
|  |    UPDATE scheduled_notifications SET status = 'FIRED'            |  |
|  |    WHERE id IN (...);                                             |  |
|  |                                                                   |  |
|  |  Pros: simple, transactional, easy cancellation                   |  |
|  |  Cons: doesn't scale past ~1M rows scanned/sec; spikes hit DB     |  |
|  |  Use: small/medium (<10M scheduled, low fire rate)                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  APPROACH 2: REDIS SORTED SET (ZSET)  (most common at scale)            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  IDEA: Store scheduled jobs in a ZSET keyed by fire-time epoch.   |  |
|  |                                                                   |  |
|  |  ZADD schedule:queue  <fire_at_epoch>  <notification_id>          |  |
|  |  ZADD schedule:queue  1730000000      ntf-abc-123                 |  |
|  |                                                                   |  |
|  |  Sweeper (runs every 1 second):                                   |  |
|  |    now = epoch_now()                                              |  |
|  |    ids = ZRANGEBYSCORE schedule:queue -inf <now> LIMIT 5000       |  |
|  |    ZREM schedule:queue <ids...>                                   |  |
|  |    For each id: produce to Kafka                                  |  |
|  |                                                                   |  |
|  |  ATOMIC POP via Lua (avoids race):                                |  |
|  |    local ids = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf',       |  |
|  |                            ARGV[1], 'LIMIT', 0, ARGV[2])          |  |
|  |    if #ids > 0 then redis.call('ZREM', KEYS[1], unpack(ids)) end  |  |
|  |    return ids                                                     |  |
|  |                                                                   |  |
|  |  SHARDING for 100M scheduled jobs:                                |  |
|  |    Key by time bucket: schedule:queue:<minute>                    |  |
|  |    Each sweeper handles its own minute bucket                     |  |
|  |    Or shard by hash(user_id) into N ZSETs                         |  |
|  |                                                                   |  |
|  |  CANCELLATION:                                                    |  |
|  |    ZREM schedule:queue <notification_id>  (O(log N))              |  |
|  |    If already fired: send a "cancel" marker downstream            |  |
|  |                                                                   |  |
|  |  Pros: very fast, scales to 100M+ scheduled, cheap O(log N)       |  |
|  |  Cons: not durable by default (use AOF + replicas)                |  |
|  |  Used by: Stripe, Uber, Slack (variants of this pattern)          |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  APPROACH 3: HIERARCHICAL TIMER WHEEL                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  IDEA: Circular array of buckets, each bucket = 1 time slot.      |  |
|  |        Higher wheel ticks slower (sec -> min -> hour -> day).     |  |
|  |        Insert/expire are O(1).                                    |  |
|  |                                                                   |  |
|  |    Wheel A (seconds, 60 slots, ticks every 1s)                    |  |
|  |    Wheel B (minutes, 60 slots, ticks when A wraps)                |  |
|  |    Wheel C (hours,   24 slots, ticks when B wraps)                |  |
|  |    Wheel D (days,    30 slots, ticks when C wraps)                |  |
|  |                                                                   |  |
|  |  On tick, current slot's jobs are either fired (Wheel A) or       |  |
|  |  cascaded down (re-bucketed at finer resolution).                 |  |
|  |                                                                   |  |
|  |  Used by: Kafka, Netty, Linux kernel (timer subsystem).           |  |
|  |                                                                   |  |
|  |  Pros: O(1) add / fire / cancel; very low memory per timer        |  |
|  |  Cons: in-memory only; needs persistent log for restart safety    |  |
|  |  Use: high-frequency short timeouts (retry, session expiry)       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  APPROACH 4: KAFKA + DELAY TOPICS                                       |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  IDEA: Use Kafka topics dedicated to fixed delays.                |  |
|  |                                                                   |  |
|  |    notifications.delay.5s                                         |  |
|  |    notifications.delay.30s                                        |  |
|  |    notifications.delay.5m                                         |  |
|  |    notifications.delay.1h                                         |  |
|  |    notifications.delay.1d                                         |  |
|  |                                                                   |  |
|  |  Worker for delay.5m:                                             |  |
|  |    msg = consumer.poll()                                          |  |
|  |    if now() - msg.timestamp < 5min: sleep(remaining)              |  |
|  |    else: produce to notifications.push.high                       |  |
|  |                                                                   |  |
|  |  For arbitrary delays: bucket to nearest delay topic, then hop    |  |
|  |  through finer-grained ones (delay.1d -> delay.1h -> ... ).       |  |
|  |                                                                   |  |
|  |  Apache Pulsar has native delayed delivery (supersedes this).     |  |
|  |  RabbitMQ has TTL + dead-letter exchanges to emulate.             |  |
|  |                                                                   |  |
|  |  Pros: reuses existing Kafka infra; durable                       |  |
|  |  Cons: clumsy for arbitrary delays; ordering across buckets weak  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  APPROACH 5: TEMPORAL / QUARTZ / WORKFLOW ENGINE                        |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  For COMPLEX schedules (multi-step drip campaigns, cron jobs):    |  |
|  |   - Temporal.io / Cadence: workflow engine with durable timers    |  |
|  |   - Quartz Scheduler (Java): cron expressions, persistent jobs    |  |
|  |   - AWS EventBridge Scheduler: managed cron at scale              |  |
|  |                                                                   |  |
|  |  Temporal example (drip campaign):                                |  |
|  |                                                                   |  |
|  |    @workflow                                                      |  |
|  |    async def welcome_drip(user_id):                               |  |
|  |        send_notification(user_id, "welcome")                      |  |
|  |        await sleep(timedelta(days=1))                             |  |
|  |        send_notification(user_id, "day_2_tip")                    |  |
|  |        await sleep(timedelta(days=4))                             |  |
|  |        send_notification(user_id, "day_7_upsell")                 |  |
|  |                                                                   |  |
|  |  Temporal persists the workflow state, so an idle 7-day sleep is  |  |
|  |  free -- the workflow rehydrates on the right day.                |  |
|  |                                                                   |  |
|  |  Pros: durable, replay-safe, expresses complex flows naturally    |  |
|  |  Cons: heavier infra; not optimized for 100M one-shot timers      |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  TIMEZONE-AWARE SCHEDULING  (the "send at 9 AM local" problem)          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Goal: deliver to every user at 9 AM IN THEIR LOCAL TIMEZONE.     |  |
|  |                                                                   |  |
|  |  Naive: store fire_at as UTC -- but "9 AM local" is 24 distinct   |  |
|  |  UTC instants (one per timezone).                                 |  |
|  |                                                                   |  |
|  |  Pattern:                                                         |  |
|  |    1. Group users by timezone (cached in user_preferences).       |  |
|  |    2. For each TZ, compute "9 AM in TZ" -> UTC fire_at.           |  |
|  |    3. Schedule each user with their own fire_at.                  |  |
|  |                                                                   |  |
|  |  CODE:                                                            |  |
|  |    for tz in distinct_user_timezones():                           |  |
|  |        fire_utc = local_9am(tz).astimezone(UTC)                   |  |
|  |        users   = SELECT user_id FROM user_prefs WHERE tz = ?      |  |
|  |        for u in users:                                            |  |
|  |            schedule(u, fire_utc, payload)                         |  |
|  |                                                                   |  |
|  |  DST gotcha: use tzdata-aware libs (zoneinfo, IANA), not fixed    |  |
|  |  UTC offsets. "America/New_York" handles DST; "UTC-5" does not.   |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  RECURRING SCHEDULES (cron-style)                                       |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  PATTERN: store a cron expression + a "next_fire_at"              |  |
|  |                                                                   |  |
|  |    recurring_jobs (                                               |  |
|  |       id,                                                         |  |
|  |       cron        VARCHAR,   -- '0 9 * * MON'                     |  |
|  |       tz          VARCHAR,                                        |  |
|  |       next_fire   TIMESTAMP, -- precomputed UTC                   |  |
|  |       status                                                      |  |
|  |    );                                                             |  |
|  |                                                                   |  |
|  |  On each fire:                                                    |  |
|  |   1. Dispatch the notification (via Kafka).                       |  |
|  |   2. Compute next_fire = croniter(cron, tz).next().               |  |
|  |   3. UPDATE recurring_jobs SET next_fire = ? WHERE id = ?.        |  |
|  |                                                                   |  |
|  |  Sweeper queries WHERE next_fire <= NOW().                        |  |
|  |  Idempotency: include next_fire timestamp in the dedup key so a   |  |
|  |  double-tick doesn't double-fire the same occurrence.             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  CANCELLATION                                                           |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Two windows where cancel can happen:                             |  |
|  |                                                                   |  |
|  |  1. BEFORE fire (in scheduler store):                             |  |
|  |     - DB approach:  UPDATE status = 'CANCELLED' WHERE id = ?      |  |
|  |     - Redis ZSET:   ZREM schedule:queue <id>                      |  |
|  |                                                                   |  |
|  |  2. AFTER fire, before delivery (already in Kafka):               |  |
|  |     - Worker checks a "cancellations" set in Redis before send:   |  |
|  |         if SISMEMBER cancellations:set <notification_id>: skip    |  |
|  |     - Or: a "tombstone" message overrides original via dedup      |  |
|  |                                                                   |  |
|  |  3. AFTER provider call:                                          |  |
|  |     - Cannot un-send. Best effort: client-side suppress on        |  |
|  |       opening if the underlying entity (order, message) is gone.  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  COMPARISON                                                             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Approach        | Scale     | Latency  | Best for                |  |
|  |  ----------------+-----------+----------+------------------------ |  |
|  |  DB + sweeper    | <10M      | ~5s      | MVP, low volume         |  |
|  |  Redis ZSET      | 100M+     | ~1s      | High volume, popular    |  |
|  |  Timer wheel     | 10M (mem) | ms       | Short timeouts, in-proc |  |
|  |  Kafka delays    | 100M+     | bucketed | Reusing Kafka infra     |  |
|  |  Temporal        | 10M       | ms-sec   | Complex workflows       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

*+-------------------------------------------------------------------------+*

## SECTION 16: BATCHING DEEP DIVE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TWO DISTINCT KINDS OF BATCHING                                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. PER-RECIPIENT BATCHING  (UX concern)                          |  |
|  |     Goal: don't spam a user with 10 separate pushes.              |  |
|  |     Combine many events into one summary notification.            |  |
|  |                                                                   |  |
|  |     Before: "Alice liked", "Bob liked", "Carol liked", ...        |  |
|  |     After:  "Alice, Bob, and 8 others liked your post"            |  |
|  |                                                                   |  |
|  |  2. PER-PROVIDER BATCHING  (efficiency concern)                   |  |
|  |     Goal: reduce HTTP requests to APNs / FCM / SendGrid.          |  |
|  |     Combine many independent notifications into one API call.    |  |
|  |                                                                   |  |
|  |     Before: 500 HTTP POSTs to FCM (one per user)                  |  |
|  |     After:  1 HTTP POST to FCM multicast with 500 tokens          |  |
|  |                                                                   |  |
|  |  These are SEPARATE concerns; both are needed at scale.           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  PER-RECIPIENT BATCHING (UX)                                            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  AGGREGATION KEY:                                                 |  |
|  |    (user_id, event_type, target_object_id)                        |  |
|  |    e.g. (user=42, type='LIKE', object='post-789')                 |  |
|  |                                                                   |  |
|  |  WINDOW TYPES:                                                    |  |
|  |                                                                   |  |
|  |  Tumbling: fixed non-overlapping windows                          |  |
|  |    [0-60s] [60-120s] [120-180s]                                   |  |
|  |    Simple but bad UX (event at t=59 fires at t=60; event at       |  |
|  |    t=61 fires at t=120).                                          |  |
|  |                                                                   |  |
|  |  Sliding (debounce): reset window on each new event               |  |
|  |    First event at t=0, second at t=10 -> window resets to t=10    |  |
|  |    Fire when no new events for N seconds                          |  |
|  |    Risk: never fires if events keep streaming (so set a max)      |  |
|  |                                                                   |  |
|  |  Hybrid (PREFERRED):                                              |  |
|  |    Fire at max(first_event + max_delay, last_event + min_delay)   |  |
|  |    e.g. min_delay = 30s (cool down), max_delay = 5 min (cap)      |  |
|  |    Good balance of UX + responsiveness                            |  |
|  |                                                                   |  |
|  |  IMPLEMENTATION (Redis):                                          |  |
|  |                                                                   |  |
|  |    On each new event:                                             |  |
|  |       key = batch:{user_id}:{event_type}:{object_id}              |  |
|  |       INCR  {key}:count                                           |  |
|  |       LPUSH {key}:actors  <actor_id>     (cap list size)          |  |
|  |       SET   {key}:first_at <now> NX                               |  |
|  |       SET   {key}:last_at  <now>                                  |  |
|  |       EXPIRE {key}:*       <max_window>                           |  |
|  |       ZADD  pending_batches <fire_at>   <key>                     |  |
|  |                                                                   |  |
|  |    Sweeper (every second):                                        |  |
|  |       Pop ready keys from pending_batches                         |  |
|  |       Read aggregate, render template, enqueue 1 notification     |  |
|  |       Delete batch keys                                           |  |
|  |                                                                   |  |
|  |  COPY TEMPLATES:                                                  |  |
|  |    count=1:  "Alice liked your post"                              |  |
|  |    count=2:  "Alice and Bob liked your post"                      |  |
|  |    count=3:  "Alice, Bob, and Carol liked your post"              |  |
|  |    count>3:  "Alice, Bob, and N-2 others liked your post"         |  |
|  |                                                                   |  |
|  |  LATE-ARRIVING EVENTS:                                            |  |
|  |    If an event arrives AFTER the batch fired, options:            |  |
|  |     - Start a new batch with cool-down (most common)              |  |
|  |     - Edit prior in-app notification (if same UI list)            |  |
|  |     - Drop if interval < min_separation (de-fatigue)              |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  PER-PROVIDER BATCHING (efficiency)                                     |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  FCM MULTICAST:                                                   |  |
|  |    Up to 500 device tokens per request                            |  |
|  |    Same message body for all (broadcast use case)                 |  |
|  |    Worker accumulates tokens in a 100ms window, then flushes:     |  |
|  |                                                                   |  |
|  |       buffer = []                                                 |  |
|  |       last_flush = now()                                          |  |
|  |       for msg in consumer:                                        |  |
|  |           buffer.append(msg.token)                                |  |
|  |           if len(buffer) >= 500 or                                |  |
|  |              now() - last_flush > 100ms:                          |  |
|  |               fcm.multicast(buffer, body)                         |  |
|  |               buffer.clear(); last_flush = now()                  |  |
|  |                                                                   |  |
|  |  SENDGRID PERSONALIZATIONS:                                       |  |
|  |    Up to 1000 personalizations per /v3/mail/send                  |  |
|  |    Each has its own variables; one template; one API call         |  |
|  |    Great for transactional bulk (order-shipped notices)           |  |
|  |                                                                   |  |
|  |  APNs (no native bulk):                                           |  |
|  |    Send N independent reqs on one HTTP/2 connection in parallel   |  |
|  |    With 100 concurrent streams: ~100x improvement over HTTP/1.1   |  |
|  |                                                                   |  |
|  |  DB WRITE BATCHING:                                               |  |
|  |    Batch status updates from worker:                              |  |
|  |       UPDATE notifications SET status='DELIVERED'                 |  |
|  |       WHERE notification_id IN (?, ?, ?, ...);                    |  |
|  |    1000 updates per batch -> DB load drops 1000x                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  TRADE-OFFS: BATCH SIZE vs LATENCY                                      |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Larger batch  -> fewer HTTP reqs -> cheaper, higher throughput   |  |
|  |  Larger batch  -> longer flush wait -> higher delivery latency    |  |
|  |                                                                   |  |
|  |  RULES OF THUMB:                                                  |  |
|  |    Critical (OTP):     batch_size=1, flush=immediate (no batch)   |  |
|  |    High (txn):         batch_size=50, flush_every=100ms           |  |
|  |    Normal (social):    batch_size=200, flush_every=500ms          |  |
|  |    Low (marketing):    batch_size=500, flush_every=1s             |  |
|  |                                                                   |  |
|  |  Use SEPARATE batch buffers per priority topic so OTP isn't       |  |
|  |  sitting behind a half-full marketing batch.                      |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

*+-------------------------------------------------------------------------+*

## SECTION 17: IDEMPOTENCY AND DELIVERY GUARANTEES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE THREE GUARANTEES                                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  AT-MOST-ONCE  (fire-and-forget)                                  |  |
|  |    - Send once, no retry                                          |  |
|  |    - Possible loss; never duplicate                               |  |
|  |    - Used by: UDP, basic UDP-style logging                        |  |
|  |    - For notifications: only OK for trivial stuff (typing dots)   |  |
|  |                                                                   |  |
|  |  AT-LEAST-ONCE  (retry until ack)                                 |  |
|  |    - Send, wait ack, retry on timeout                             |  |
|  |    - Never lost; possible duplicates                              |  |
|  |    - This is the realistic default for notifications              |  |
|  |    - Must combine with idempotency to be safe                     |  |
|  |                                                                   |  |
|  |  EXACTLY-ONCE  (the holy grail)                                   |  |
|  |    - Sent and delivered exactly once, period                      |  |
|  |    - PROVABLY IMPOSSIBLE end-to-end across an untrusted network   |  |
|  |       (Two Generals problem; FLP impossibility)                   |  |
|  |    - Best we can do: at-least-once + idempotent receiver          |  |
|  |       = "effectively-once" from the user's perspective            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  WHY EXACTLY-ONCE IS IMPOSSIBLE END-TO-END                              |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Suppose worker calls FCM and we want to know "did FCM get it     |  |
|  |  AND did we record success?" atomically.                          |  |
|  |                                                                   |  |
|  |  Scenarios after FCM returns 200:                                 |  |
|  |   - Worker crashes before writing DB status                       |  |
|  |     -> on restart, we don't know it succeeded                     |  |
|  |     -> if we retry, FCM sends AGAIN (duplicate)                   |  |
|  |     -> if we don't retry, we mis-report failure                   |  |
|  |                                                                   |  |
|  |  Scenarios on timeout:                                            |  |
|  |   - Worker sent, FCM processed, ACK lost in transit               |  |
|  |     -> worker thinks failure, retries                             |  |
|  |     -> user receives 2 pushes                                     |  |
|  |                                                                   |  |
|  |  No 2PC is available with APNs / FCM (you can't write a           |  |
|  |  distributed transaction into Apple's servers).                   |  |
|  |                                                                   |  |
|  |  CONCLUSION: aim for "effectively-once"                           |  |
|  |              = at-least-once delivery + idempotent at every layer |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  IDEMPOTENCY LAYER 1: API ENDPOINT (CALLER -> NOTIFICATION SERVICE)     |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Caller sends Idempotency-Key header (or in body).                |  |
|  |  Example: order-service sends key = "order-789-shipped".          |  |
|  |                                                                   |  |
|  |  API logic:                                                       |  |
|  |    cached = redis.get(f"idem:{key}")                              |  |
|  |    if cached:                                                     |  |
|  |        return cached.response                                     |  |
|  |    if not redis.set(f"idem:{key}", "processing",                  |  |
|  |                     nx=True, ex=24h):                             |  |
|  |        return 409 "in progress"                                   |  |
|  |    try:                                                           |  |
|  |        resp = process_notification(...)                           |  |
|  |        redis.set(f"idem:{key}", resp, ex=24h)                     |  |
|  |        return resp                                                |  |
|  |    except TransientError:                                         |  |
|  |        redis.delete(f"idem:{key}")    # allow retry               |  |
|  |        raise                                                      |  |
|  |                                                                   |  |
|  |  KEY DESIGN:                                                      |  |
|  |    - Caller-provided keys are best (caller knows business intent) |  |
|  |    - Scope by (api_key, key, endpoint) to avoid cross-merchant    |  |
|  |      collisions                                                   |  |
|  |    - TTL ~ 24h (enough for retries; not unbounded growth)         |  |
|  |    - Cache the SUCCESSFUL response so duplicate requests get      |  |
|  |      the same notification_id back                                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  IDEMPOTENCY LAYER 2: PRODUCER -> KAFKA                                 |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Use Kafka's idempotent producer (enable.idempotence=true):       |  |
|  |   - Producer assigns sequence numbers; broker dedups within a     |  |
|  |     5-message window per partition.                               |  |
|  |   - Eliminates duplicates from producer retries.                  |  |
|  |   - "Exactly-once within Kafka," but only WITHIN Kafka.           |  |
|  |                                                                   |  |
|  |  Kafka Transactions (transactional.id) extend this to             |  |
|  |  "consume-transform-produce" within Kafka -- still doesn't span   |  |
|  |  Kafka + external systems (APNs, DB writes outside).              |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  IDEMPOTENCY LAYER 3: WORKER -> DATABASE                                |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Worker may consume the same Kafka message twice (consumer        |  |
|  |  restart, partition rebalance). DB writes must be idempotent.     |  |
|  |                                                                   |  |
|  |  Pattern A: UNIQUE CONSTRAINT                                     |  |
|  |    INSERT INTO notifications (notification_id, ...)               |  |
|  |    VALUES (?, ...)                                                |  |
|  |    ON CONFLICT (notification_id) DO NOTHING;                      |  |
|  |                                                                   |  |
|  |  Pattern B: CONDITIONAL UPDATE (state machine)                    |  |
|  |    UPDATE notifications                                           |  |
|  |    SET status = 'SENDING'                                         |  |
|  |    WHERE notification_id = ? AND status = 'QUEUED';               |  |
|  |    -- Only one worker can transition QUEUED -> SENDING            |  |
|  |    -- if rows_affected = 0: someone else got it; SKIP             |  |
|  |                                                                   |  |
|  |  Pattern C: SEEN-CACHE                                            |  |
|  |    Redis SET seen:{notification_id} EX 24h NX                     |  |
|  |    If NX fails: already processed, skip.                          |  |
|  |    (Cheap but loses safety if Redis flushes.)                     |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  IDEMPOTENCY LAYER 4: WORKER -> PROVIDER (APNs / FCM / etc.)            |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  APNs:                                                            |  |
|  |    Header `apns-collapse-id`: provider collapses multiple pushes  |  |
|  |    with the same id into ONE delivered push on the device.        |  |
|  |    Header `apns-id`: unique per attempt; helps debugging but does |  |
|  |    NOT dedup on Apple's side.                                     |  |
|  |                                                                   |  |
|  |  FCM:                                                             |  |
|  |    `collapse_key`: same as APNs, last-write-wins on the device    |  |
|  |    `message_id`: provider-assigned; can be used to query status   |  |
|  |    FCM itself does NOT dedup retried sends.                       |  |
|  |                                                                   |  |
|  |  IMPLICATION:                                                     |  |
|  |    Retrying the same notification = a SECOND push to the device   |  |
|  |    unless collapse_id matches AND the first push wasn't displayed |  |
|  |    yet. Collapse only helps for unread updates.                   |  |
|  |                                                                   |  |
|  |  Therefore: do NOT retry naively after a 200 OK. The provider     |  |
|  |  succeeded; treat it as done even if your DB update failed.       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  IDEMPOTENCY LAYER 5: CLIENT-SIDE                                       |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Mobile / web client dedups by notification_id in the payload:    |  |
|  |    if seen.contains(payload.notification_id): suppress            |  |
|  |    else: display + add to seen (LRU of last 1000)                 |  |
|  |                                                                   |  |
|  |  In-app inbox: notification_id is PRIMARY KEY -- duplicate writes |  |
|  |  are absorbed by INSERT ... ON CONFLICT DO NOTHING.               |  |
|  |                                                                   |  |
|  |  This is the FINAL safety net. With it, the at-least-once         |  |
|  |  pipeline becomes "effectively-once" to the user.                 |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  THE "STUCK-IN-SENDING" SCENARIO  (mirror of the payments bug)          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  What if the worker calls FCM (success), then dies before         |  |
|  |  updating DB status from SENDING -> DELIVERED?                    |  |
|  |                                                                   |  |
|  |  On restart, the Kafka message is redelivered. The worker would   |  |
|  |  re-send to FCM -> the user gets TWO pushes.                      |  |
|  |                                                                   |  |
|  |  SOLUTION (multi-layer):                                          |  |
|  |   1. Conditional UPDATE before provider call:                     |  |
|  |        UPDATE status='SENDING' WHERE status='QUEUED'.             |  |
|  |      Only one worker wins; others SKIP.                           |  |
|  |   2. Reconciliation job: scan SENDING > 5 min old. If stuck,      |  |
|  |      query provider by message_id (if supported) or assume        |  |
|  |      success and mark DELIVERED (idempotent on client).           |  |
|  |   3. Client-side dedup by notification_id is the final guard.     |  |
|  |                                                                   |  |
|  |  Compare to PAYMENT SCENARIO 2: same shape (provider succeeded,   |  |
|  |  DB failed). The difference: a duplicate push is annoying; a      |  |
|  |  duplicate charge is dangerous. Notifications can tolerate more.  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  RECOMMENDED DEFAULTS                                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  - Pipeline guarantee:    AT-LEAST-ONCE                           |  |
|  |  - User-visible behavior: EFFECTIVELY-ONCE                        |  |
|  |  - Mechanisms:                                                    |  |
|  |     * Idempotency-Key at API (Redis SETNX, 24h TTL)               |  |
|  |     * Kafka idempotent producer (enable.idempotence=true)         |  |
|  |     * Conditional UPDATE for state transitions (QUEUED->SENDING)  |  |
|  |     * notification_id UNIQUE constraint on in-app inbox           |  |
|  |     * Client-side dedup by notification_id (LRU cache)            |  |
|  |     * Reconciliation sweeper for stuck SENDING rows               |  |
|  |                                                                   |  |
|  |  GOLDEN RULE                                                      |  |
|  |    Don't chase exactly-once. Make every step idempotent and       |  |
|  |    the user will perceive exactly-once delivery in practice.      |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

*+-------------------------------------------------------------------------+*

## SECTION 18: WRAP-UP

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SUMMARY OF KEY DESIGN DECISIONS:                                       |
|                                                                         |
|  1. CHANNEL-AGNOSTIC ARCHITECTURE                                       |
|     Notification request is channel-independent. A router decides       |
|     which channel(s) to use based on user preferences, priority,        |
|     and channel availability. Adding a new channel requires only        |
|     a new provider adapter, not core system changes.                    |
|                                                                         |
|  2. PRIORITY QUEUE WITH MULTIPLE TIERS                                  |
|     Critical (payments, security) goes to high-priority queue with      |
|     dedicated workers. Normal (social, marketing) goes to standard      |
|     queue. Prevents marketing blasts from delaying payment alerts.      |
|                                                                         |
|  3. RATE LIMITING PER USER PER CHANNEL                                  |
|     Redis sliding window: max N notifications per user per hour per     |
|     channel. Prevents notification fatigue and respects user            |
|     experience. Exceeded notifications are dropped or deferred.         |
|                                                                         |
|  4. TEMPLATE ENGINE FOR MESSAGE RENDERING                               |
|     Upstream services send template_id + params. Notification           |
|     system renders the final message per channel (push is short,        |
|     email is rich HTML). Supports i18n and A/B testing.                 |
|                                                                         |
|  5. DELIVERY TRACKING WITH FEEDBACK LOOP                                |
|     Every notification gets a unique ID tracked through send ->         |
|     delivered -> opened. Provider callbacks (APNs, SendGrid) update     |
|     status. Analytics pipeline consumes events for dashboards.          |
|                                                                         |
|  -----------------------------------------------------------------      |
|                                                                         |
|  KEY TRADE-OFFS:                                                        |
|                                                                         |
|  * AT-LEAST-ONCE vs EXACTLY-ONCE: At-least-once is simpler and          |
|    sufficient with client-side dedup. Exactly-once requires             |
|    distributed transactions with third-party providers (impossible      |
|    in practice since APNs/FCM don't support transactions).              |
|                                                                         |
|  * PUSH LATENCY vs BATCHING EFFICIENCY: Immediate push for every        |
|    notification wastes resources. Batching (digest every 15 min)        |
|    saves cost but delays delivery. Priority tiers solve this:           |
|    urgent = immediate, normal = batchable.                              |
|                                                                         |
|  * SMS COST vs REACH: SMS costs $0.01-0.05 per message. Push is         |
|    free. We use SMS only for critical notifications (OTP, payment)      |
|    where push delivery is uncertain (app not installed).                |
|                                                                         |
|  * USER PREFERENCE COMPLEXITY: Fine-grained preferences (per            |
|    category, per channel, per time-of-day) improve UX but add           |
|    query complexity. We cache preferences in Redis with event-          |
|    driven invalidation on preference changes.                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 19: INTERVIEW QUICK REFERENCE
```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY TALKING POINTS                                                     |
|                                                                         |
|  1. MULTI-CHANNEL                                                       |
|     * Push (APNs/FCM), SMS, Email, In-App                               |
|     * Different SLAs and costs per channel                              |
|                                                                         |
|  2. ARCHITECTURE                                                        |
|     * API > Kafka (priority queues) > Channel Workers > Providers       |
|     * Separate topics by priority and channel                           |
|                                                                         |
|  3. RELIABILITY                                                         |
|     * At-least-once delivery via Kafka                                  |
|     * Retry with exponential backoff                                    |
|     * Dead Letter Queue for failed messages                             |
|     * Provider fallback (Twilio > Nexmo > SNS)                          |
|                                                                         |
|  4. USER PREFERENCES                                                    |
|     * Opt-in/out per channel and category                               |
|     * Quiet hours with timezone support                                 |
|                                                                         |
|  5. RATE LIMITING                                                       |
|     * Per-user, per-service, global, provider limits                    |
|     * Notification batching to prevent spam                             |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  COMMON INTERVIEW QUESTIONS                                             |
|                                                                         |
|  Q: How do you ensure notifications are delivered?                      |
|  A: At-least-once via Kafka + retries. Exponential backoff for          |
|     transient failures. Invalid tokens removed, not retried.            |
|     Provider fallback for SMS/email.                                    |
|                                                                         |
|  Q: How do you handle millions of notifications per second?             |
|  A: Kafka partitioned by user_id for ordering. Separate topics by       |
|     priority (critical processes first). Scale workers horizontally.    |
|     Batch notifications to providers (FCM supports 500/request).        |
|                                                                         |
|  Q: How do you prevent notification spam?                               |
|  A: Rate limiting per user. Batching similar notifications.             |
|     User preferences for opt-out. Smart frequency capping via ML.       |
|                                                                         |
|  Q: How do you handle user preferences like quiet hours?                |
|  A: Store timezone in user profile. On notification, calculate          |
|     user's local time. If quiet hours, schedule for after.              |
|     Critical notifications bypass quiet hours.                          |
|                                                                         |
|  Q: How do you track if notification was opened?                        |
|  A: Email: tracking pixel (1x1 image with unique URL).                  |
|     Push: App reports open event to server.                             |
|     Links: URL rewriting through redirect service.                      |
|                                                                         |
|  Q: What happens if APNs/FCM is down?                                   |
|  A: Retry with backoff. Kafka retains messages. Once provider           |
|     recovers, backlog processes. Monitor latency, alert if stuck.       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ARCHITECTURE SUMMARY                                                   |
|                                                                         |
|  Internal Services > Notification API > Kafka (priority queues)         |
|      > Channel Workers > External Providers (APNs, FCM, Twilio)         |
|                                                                         |
|  Key Components:                                                        |
|  * Notification API: Validation, preferences, templates, enqueue        |
|  * Kafka: Priority topics, partitioned by user_id                       |
|  * Workers: Channel-specific, batch to providers, handle retries        |
|  * Providers: APNs, FCM, Twilio, SendGrid                               |
|                                                                         |
|  Key Numbers:                                                           |
|  * 1.6B notifications/day                                               |
|  * 18K/second average, 185K/second peak                                 |
|  * Push 4KB payload limit                                               |
|  * Email: Track open/click rates                                        |
|                                                                         |
```

*+-------------------------------------------------------------------------+*

ARCHITECTURE DIAGRAM
```
+-------------------------------------------------------------------------+
|                                                                         |
|          +------------------------------------------------------+       |
|          |              INTERNAL SERVICES                       |       |
|          |    (Order, User, Marketing, Payment, etc.)          |        |
|          +--------------------------+---------------------------+       |
|                                     |                                   |
|                                     v                                   |
|                    +--------------------------------+                   |
|                    |      NOTIFICATION API          |                   |
|                    |                                |                   |
|                    |  * Validate request            |                   |
|                    |  * Check user preferences      |                   |
|                    |  * Render template             |                   |
|                    |  * Rate limit                  |                   |
|                    |  * Enqueue to Kafka            |                   |
|                    +----------------+---------------+                   |
|                                     |                                   |
|                                     v                                   |
|     +----------------------------------------------------------------+  |
|     |                         KAFKA                                  |  |
|     |                                                                |  |
|     |  +--------------+  +--------------+  +--------------+          |  |
|     |  |push.critical |  | sms.critical |  |email.high    |          |  |
|     |  |push.high     |  | sms.high     |  |email.normal  |          |  |
|     |  |push.normal   |  +--------------+  |email.low     |          |  |
|     |  |push.low      |                    +--------------+          |  |
|     |  +--------------+                                              |  |
|     |                       +--------------+                         |  |
|     |                       |   in_app     |                         |  |
|     |                       +--------------+                         |  |
|     +-------------------------------+--------------------------------+  |
|                                     |                                   |
|          +--------------------------+--------------------------+        |
|          |                          |                          |        |
|          v                          v                          v        |
|   +------------+            +------------+            +--------------+  |
|   |   PUSH     |            |    SMS     |            |   EMAIL      |  |
|   |  WORKERS   |            |  WORKERS   |            |  WORKERS     |  |
|   +-----+------+            +-----+------+            +-----+--------+  |
|         |                         |                         |           |
|    +----+----+              +-----+-----+             +-----+--------+  |
|    |         |              |           |             |              |  |
|    v         v              v           v             v           v     |
| +------+ +------+      +--------+ +--------+   +---------+ +---------+  |
| | APNs | | FCM  |      | Twilio | | Nexmo  |   |SendGrid | | SES     |  |
| |(iOS) | |(Andr)|      |        | |(backup)|   |         | |         |  |
| +------+ +------+      +--------+ +--------+   +---------+ +---------+  |
|                                                                         |
|                    +--------------------------------+                   |
|                    |         IN-APP WORKER          |                   |
|                    +----------------+---------------+                   |
|                                     |                                   |
|                    +----------------+---------------+                   |
|                    |            REDIS               |                   |
|                    |    (In-app notification DB)    |                   |
|                    +----------------+---------------+                   |
|                                     |                                   |
|                                     | WebSocket                         |
|                                     v                                   |
|                    +--------------------------------+                   |
|                    |        CLIENT APPS             |                   |
|                    +--------------------------------+                   |
|                                                                         |
```

*+-------------------------------------------------------------------------+*

END OF NOTIFICATION SYSTEM DESIGN
