# NOTIFICATION SYSTEM - HIGH LEVEL DESIGN

A COMPLETE CONCEPTUAL GUIDE
SECTION 1: UNDERSTANDING THE PROBLEM
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHAT IS A NOTIFICATION SYSTEM?                                        |*
*|                                                                         |*
*|  A service that sends timely, relevant messages to users across        |*
*|  multiple channels (push, SMS, email, in-app).                         |*
*|                                                                         |*
*|  Examples:                                                              |*
*|  * "Your order has been shipped" (Push + Email)                       |*
*|  * "John liked your photo" (Push + In-app)                            |*
*|  * "Your OTP is 123456" (SMS)                                         |*
*|  * "Weekly digest: 5 new connections" (Email)                         |*
*|  * "Price drop alert!" (Push)                                         |*
*|                                                                         |*
*|  Real-world systems:                                                   |*
*|  * AWS SNS, Firebase Cloud Messaging                                   |*
*|  * Twilio (SMS), SendGrid (Email)                                     |*
*|  * Custom systems at Twitter, Facebook, Uber                          |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  NOTIFICATION CHANNELS                                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. PUSH NOTIFICATIONS                                         |  |*
*|  |     * Mobile (iOS APNs, Android FCM)                          |  |*
*|  |     * Web (Web Push API)                                       |  |*
*|  |     * Desktop (native apps)                                    |  |*
*|  |     * Instant delivery, requires device token                 |  |*
*|  |                                                                 |  |*
*|  |  2. SMS                                                         |  |*
*|  |     * Text messages via telecom carriers                      |  |*
*|  |     * High open rate (98%)                                    |  |*
*|  |     * Expensive, limited content                              |  |*
*|  |     * Best for: OTP, urgent alerts                           |  |*
*|  |                                                                 |  |*
*|  |  3. EMAIL                                                       |  |*
*|  |     * Rich content (HTML, attachments)                        |  |*
*|  |     * Cheap at scale                                          |  |*
*|  |     * Lower engagement, spam risk                             |  |*
*|  |     * Best for: Newsletters, receipts, detailed info         |  |*
*|  |                                                                 |  |*
*|  |  4. IN-APP NOTIFICATIONS                                       |  |*
*|  |     * Bell icon / notification center                         |  |*
*|  |     * Only visible when user is in app                        |  |*
*|  |     * No external delivery cost                               |  |*
*|  |     * Best for: Social interactions, updates                 |  |*
*|  |                                                                 |  |*
*|  |  5. WEBHOOK                                                     |  |*
*|  |     * HTTP callback to external systems                       |  |*
*|  |     * For B2B integrations                                    |  |*
*|  |     * Best for: Developer notifications, integrations        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  KEY CHALLENGES                                                        |*
*|                                                                         |*
*|  1. SCALE                                                              |*
*|     * Billions of notifications per day                               |*
*|     * Burst traffic (Black Friday, breaking news)                    |*
*|                                                                         |*
*|  2. RELIABILITY                                                        |*
*|     * Messages must not be lost                                       |*
*|     * At-least-once delivery guarantee                               |*
*|                                                                         |*
*|  3. LATENCY                                                            |*
*|     * Real-time for push/SMS (seconds)                               |*
*|     * Near real-time for email (minutes)                             |*
*|                                                                         |*
*|  4. USER PREFERENCES                                                   |*
*|     * Respect opt-out per channel/category                           |*
*|     * Don't spam users                                                |*
*|                                                                         |*
*|  5. RATE LIMITING                                                      |*
*|     * Provider limits (APNs, FCM, SMS carriers)                      |*
*|     * Per-user limits (no notification bombing)                      |*
*|                                                                         |*
*|  6. DEDUPLICATION                                                      |*
*|     * Same notification shouldn't be sent twice                      |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2: REQUIREMENTS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  FUNCTIONAL REQUIREMENTS                                               |*
*|                                                                         |*
*|  1. MULTI-CHANNEL DELIVERY                                            |*
*|     * Send push, SMS, email, in-app notifications                    |*
*|     * Support for multiple channels per notification                 |*
*|                                                                         |*
*|  2. TEMPLATE MANAGEMENT                                                |*
*|     * Create/update notification templates                           |*
*|     * Variable substitution (Hi {{name}}, your order {{order_id}})  |*
*|     * Localization (multi-language)                                  |*
*|                                                                         |*
*|  3. USER PREFERENCES                                                   |*
*|     * Opt-in/opt-out per channel                                     |*
*|     * Opt-in/opt-out per notification category                      |*
*|     * Quiet hours (no notifications 10 PM - 8 AM)                   |*
*|                                                                         |*
*|  4. SCHEDULING                                                         |*
*|     * Send immediately                                                |*
*|     * Schedule for future time                                       |*
*|     * Recurring notifications                                        |*
*|                                                                         |*
*|  5. PRIORITY LEVELS                                                    |*
*|     * Critical (OTP, security alerts) - send immediately            |*
*|     * High (order updates) - send within seconds                    |*
*|     * Normal (social) - send within minutes                         |*
*|     * Low (marketing) - batch and send                              |*
*|                                                                         |*
*|  6. TRACKING & ANALYTICS                                              |*
*|     * Delivery status (sent, delivered, failed)                     |*
*|     * Open rates, click rates                                        |*
*|     * Unsubscribe tracking                                           |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  NON-FUNCTIONAL REQUIREMENTS                                           |*
*|                                                                         |*
*|  1. SCALE                                                              |*
*|     * 10 billion notifications/day                                   |*
*|     * 100K notifications/second peak                                 |*
*|                                                                         |*
*|  2. AVAILABILITY                                                       |*
*|     * 99.99% uptime                                                   |*
*|     * No single point of failure                                     |*
*|                                                                         |*
*|  3. LATENCY                                                            |*
*|     * Critical: < 1 second                                           |*
*|     * Normal: < 30 seconds                                           |*
*|                                                                         |*
*|  4. RELIABILITY                                                        |*
*|     * At-least-once delivery                                         |*
*|     * No message loss                                                 |*
*|                                                                         |*
*|  5. EXTENSIBILITY                                                      |*
*|     * Easy to add new channels                                       |*
*|     * Pluggable provider architecture                                |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3: SCALE ESTIMATION
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  USER BASE                                                              |*
*|                                                                         |*
*|  * 500 million registered users                                       |*
*|  * 100 million daily active users                                     |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  NOTIFICATION VOLUME                                                   |*
*|                                                                         |*
*|  Per user per day:                                                     |*
*|  * Push: 5 notifications                                              |*
*|  * Email: 1 notification                                              |*
*|  * SMS: 0.1 (occasional OTP)                                         |*
*|  * In-app: 10 notifications                                          |*
*|                                                                         |*
*|  Daily totals:                                                         |*
*|  * Push: 100M × 5 = 500 million/day                                  |*
*|  * Email: 100M × 1 = 100 million/day                                 |*
*|  * SMS: 100M × 0.1 = 10 million/day                                  |*
*|  * In-app: 100M × 10 = 1 billion/day                                 |*
*|  * TOTAL: ~1.6 billion/day                                           |*
*|                                                                         |*
*|  Per second (average):                                                 |*
*|  * 1.6B / 86400 ≈ 18,500 notifications/second                       |*
*|                                                                         |*
*|  Per second (peak 10x):                                                |*
*|  * 185,000 notifications/second                                       |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  STORAGE                                                               |*
*|                                                                         |*
*|  Notification record:                                                  |*
*|  * notification_id: 16 bytes                                          |*
*|  * user_id: 8 bytes                                                   |*
*|  * channel: 10 bytes                                                  |*
*|  * content: 500 bytes                                                 |*
*|  * metadata: 200 bytes                                                |*
*|  * Total: ~750 bytes                                                  |*
*|                                                                         |*
*|  Daily storage:                                                        |*
*|  * 1.6B × 750 bytes = 1.2 TB/day                                     |*
*|                                                                         |*
*|  Keep 30 days:                                                         |*
*|  * 1.2 TB × 30 = 36 TB                                               |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4: HIGH-LEVEL ARCHITECTURE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  ARCHITECTURE OVERVIEW                                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |                     INTERNAL SERVICES                          |  |*
*|  |         (Order Service, User Service, etc.)                    |  |*
*|  |                          |                                      |  |*
*|  |                          | Send notification request           |  |*
*|  |                          v                                      |  |*
*|  |               +----------------------+                         |  |*
*|  |               |   NOTIFICATION API   |                         |  |*
*|  |               |                      |                         |  |*
*|  |               |  * Validate request  |                         |  |*
*|  |               |  * Enrich with user  |                         |  |*
*|  |               |  * Check preferences |                         |  |*
*|  |               |  * Rate limit        |                         |  |*
*|  |               +----------+-----------+                         |  |*
*|  |                          |                                      |  |*
*|  |                          v                                      |  |*
*|  |               +----------------------+                         |  |*
*|  |               |    MESSAGE QUEUE     |                         |  |*
*|  |               |      (Kafka)         |                         |  |*
*|  |               |                      |                         |  |*
*|  |               |  Partitioned by      |                         |  |*
*|  |               |  priority + channel  |                         |  |*
*|  |               +----------+-----------+                         |  |*
*|  |                          |                                      |  |*
*|  |     +--------------------+--------------------+                |  |*
*|  |     |                    |                    |                |  |*
*|  |     v                    v                    v                |  |*
*|  |  +--------+        +----------+        +----------+           |  |*
*|  |  |  PUSH  |        |   SMS    |        |  EMAIL   |           |  |*
*|  |  | WORKER |        |  WORKER  |        |  WORKER  |           |  |*
*|  |  +---+----+        +----+-----+        +----+-----+           |  |*
*|  |      |                  |                   |                  |  |*
*|  |      v                  v                   v                  |  |*
*|  |  +--------+        +----------+        +----------+           |  |*
*|  |  |  APNs  |        |  Twilio  |        | SendGrid |           |  |*
*|  |  |  FCM   |        |          |        |   SES    |           |  |*
*|  |  +--------+        +----------+        +----------+           |  |*
*|  |                                                                 |  |*
*|  |                  +--------------+                              |  |*
*|  |                  |   IN-APP     |                              |  |*
*|  |                  |   WORKER     |                              |  |*
*|  |                  +------+-------+                              |  |*
*|  |                         |                                      |  |*
*|  |                         v                                      |  |*
*|  |                  +--------------+                              |  |*
*|  |                  |    Redis     | --> WebSocket to client     |  |*
*|  |                  |  (In-app DB) |                              |  |*
*|  |                  +--------------+                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 5: COMPONENT DEEP DIVE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  1. NOTIFICATION API SERVICE                                           |*
*|  ------------------------------                                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  RESPONSIBILITIES:                                              |  |*
*|  |                                                                 |  |*
*|  |  1. Request Validation                                         |  |*
*|  |     * Required fields present                                  |  |*
*|  |     * Valid user_id, channel, template_id                     |  |*
*|  |                                                                 |  |*
*|  |  2. User Enrichment                                            |  |*
*|  |     * Fetch user preferences                                   |  |*
*|  |     * Get device tokens (for push)                            |  |*
*|  |     * Get email address, phone number                         |  |*
*|  |                                                                 |  |*
*|  |  3. Preference Check                                           |  |*
*|  |     * Is user opted-in for this channel?                      |  |*
*|  |     * Is user opted-in for this category?                     |  |*
*|  |     * Is it quiet hours?                                       |  |*
*|  |                                                                 |  |*
*|  |  4. Rate Limiting                                              |  |*
*|  |     * Per-user limits (max 50 push/day)                       |  |*
*|  |     * Per-service limits (calling service quota)              |  |*
*|  |                                                                 |  |*
*|  |  5. Template Rendering                                         |  |*
*|  |     * Fetch template by ID                                    |  |*
*|  |     * Substitute variables                                    |  |*
*|  |     * Apply localization                                      |  |*
*|  |                                                                 |  |*
*|  |  6. Deduplication                                              |  |*
*|  |     * Check if same notification sent recently                |  |*
*|  |     * Idempotency key check                                   |  |*
*|  |                                                                 |  |*
*|  |  7. Enqueue                                                    |  |*
*|  |     * Put message on Kafka with priority                      |  |*
*|  |     * Return notification_id                                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  2. MESSAGE QUEUE (Kafka)                                             |*
*|  -------------------------                                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TOPIC STRUCTURE:                                              |  |*
*|  |                                                                 |  |*
*|  |  notifications.push.critical    (OTP, security)               |  |*
*|  |  notifications.push.high        (transactional)               |  |*
*|  |  notifications.push.normal      (social)                      |  |*
*|  |  notifications.push.low         (marketing)                   |  |*
*|  |                                                                 |  |*
*|  |  notifications.sms.critical     (OTP)                         |  |*
*|  |  notifications.sms.high         (alerts)                      |  |*
*|  |                                                                 |  |*
*|  |  notifications.email.high       (receipts, confirmations)    |  |*
*|  |  notifications.email.normal     (updates)                     |  |*
*|  |  notifications.email.low        (newsletters, marketing)     |  |*
*|  |                                                                 |  |*
*|  |  notifications.inapp            (all in-app)                  |  |*
*|  |                                                                 |  |*
*|  |  WHY SEPARATE TOPICS:                                          |  |*
*|  |  * Different SLAs per priority                                |  |*
*|  |  * Scale workers independently per channel                    |  |*
*|  |  * Isolate failures (SMS down doesn't affect push)           |  |*
*|  |                                                                 |  |*
*|  |  PARTITIONING:                                                 |  |*
*|  |  * By user_id hash (for ordering per user)                   |  |*
*|  |  * Ensures same user's notifications processed in order      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  3. CHANNEL WORKERS                                                    |*
*|  -------------------                                                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  PUSH WORKER:                                                  |  |*
*|  |                                                                 |  |*
*|  |  1. Consume from Kafka                                        |  |*
*|  |  2. Batch notifications by platform (iOS/Android)            |  |*
*|  |  3. Send to APNs (iOS) or FCM (Android)                      |  |*
*|  |  4. Handle responses:                                         |  |*
*|  |     * Success > Update status                                |  |*
*|  |     * Invalid token > Remove token from user profile        |  |*
*|  |     * Rate limited > Retry with backoff                     |  |*
*|  |     * Server error > Retry with backoff                     |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  SMS WORKER:                                                   |  |*
*|  |                                                                 |  |*
*|  |  1. Consume from Kafka                                        |  |*
*|  |  2. Format message (160 char limit)                          |  |*
*|  |  3. Select SMS provider (Twilio, Nexmo, etc.)               |  |*
*|  |     * Primary provider                                       |  |*
*|  |     * Fallback if primary fails                             |  |*
*|  |  4. Handle country-specific routing                          |  |*
*|  |  5. Track delivery status via webhooks                       |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  EMAIL WORKER:                                                 |  |*
*|  |                                                                 |  |*
*|  |  1. Consume from Kafka                                        |  |*
*|  |  2. Render HTML template                                      |  |*
*|  |  3. Generate text version (for plaintext clients)            |  |*
*|  |  4. Add tracking pixel (for open tracking)                   |  |*
*|  |  5. Rewrite links (for click tracking)                       |  |*
*|  |  6. Send via SendGrid/SES/Mailgun                           |  |*
*|  |  7. Handle bounces and complaints via webhooks               |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  IN-APP WORKER:                                                |  |*
*|  |                                                                 |  |*
*|  |  1. Consume from Kafka                                        |  |*
*|  |  2. Store in database (Cassandra/Redis)                      |  |*
*|  |  3. If user online > push via WebSocket                     |  |*
*|  |  4. Update unread count                                      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 6: DATA MODEL
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  CORE TABLES                                                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: notification_templates                                 |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | template_id     | VARCHAR (PK)  | "order_shipped"        | |  |*
*|  |  | channel         | ENUM          | PUSH, SMS, EMAIL       | |  |*
*|  |  | category        | VARCHAR       | "transactional"        | |  |*
*|  |  | title_template  | TEXT          | "Order {{order_id}}"   | |  |*
*|  |  | body_template   | TEXT          | "Your order shipped"   | |  |*
*|  |  | html_template   | TEXT          | For email HTML         | |  |*
*|  |  | language        | VARCHAR       | "en", "es", "fr"       | |  |*
*|  |  | created_at      | TIMESTAMP     |                        | |  |*
*|  |  | updated_at      | TIMESTAMP     |                        | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: user_preferences                                       |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | user_id         | BIGINT (PK)   | User identifier        | |  |*
*|  |  | push_enabled    | BOOLEAN       | Opt-in for push        | |  |*
*|  |  | sms_enabled     | BOOLEAN       | Opt-in for SMS         | |  |*
*|  |  | email_enabled   | BOOLEAN       | Opt-in for email       | |  |*
*|  |  | quiet_start     | TIME          | 22:00 (10 PM)          | |  |*
*|  |  | quiet_end       | TIME          | 08:00 (8 AM)           | |  |*
*|  |  | timezone        | VARCHAR       | "America/New_York"     | |  |*
*|  |  | language        | VARCHAR       | "en"                   | |  |*
*|  |  | categories      | JSON          | {"marketing": false}   | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: device_tokens                                          |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | token_id        | UUID (PK)     | Unique identifier      | |  |*
*|  |  | user_id         | BIGINT        | Owner                  | |  |*
*|  |  | token           | VARCHAR       | APNs/FCM token         | |  |*
*|  |  | platform        | ENUM          | IOS, ANDROID, WEB      | |  |*
*|  |  | device_id       | VARCHAR       | Device identifier      | |  |*
*|  |  | app_version     | VARCHAR       | "3.2.1"                | |  |*
*|  |  | created_at      | TIMESTAMP     |                        | |  |*
*|  |  | last_used_at    | TIMESTAMP     | Last notification sent | |  |*
*|  |  | is_valid        | BOOLEAN       | False if token expired | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  INDEX: (user_id, is_valid)                                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: notifications (Write-heavy, use Cassandra)            |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | notification_id | UUID (PK)     | Unique identifier      | |  |*
*|  |  | user_id         | BIGINT        | Recipient              | |  |*
*|  |  | channel         | ENUM          | PUSH, SMS, EMAIL       | |  |*
*|  |  | template_id     | VARCHAR       | Template used          | |  |*
*|  |  | title           | VARCHAR       | Rendered title         | |  |*
*|  |  | body            | TEXT          | Rendered content       | |  |*
*|  |  | status          | ENUM          | PENDING, SENT,         | |  |*
*|  |  |                 |               | DELIVERED, FAILED      | |  |*
*|  |  | priority        | ENUM          | CRITICAL, HIGH, etc.   | |  |*
*|  |  | created_at      | TIMESTAMP     | Request time           | |  |*
*|  |  | sent_at         | TIMESTAMP     | When sent to provider  | |  |*
*|  |  | delivered_at    | TIMESTAMP     | Provider confirmation  | |  |*
*|  |  | opened_at       | TIMESTAMP     | User opened (if track) | |  |*
*|  |  | clicked_at      | TIMESTAMP     | User clicked link      | |  |*
*|  |  | error_code      | VARCHAR       | If failed              | |  |*
*|  |  | error_message   | TEXT          | If failed              | |  |*
*|  |  | retry_count     | INT           | Retry attempts         | |  |*
*|  |  | metadata        | JSON          | Extra context          | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  Partition key: user_id (for "my notifications" query)        |  |*
*|  |  Clustering key: created_at DESC                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: in_app_notifications (For notification center)        |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | user_id         | BIGINT (PK)   | Recipient              | |  |*
*|  |  | notification_id | UUID (PK)     | Notification           | |  |*
*|  |  | title           | VARCHAR       | Display title          | |  |*
*|  |  | body            | TEXT          | Display text           | |  |*
*|  |  | icon_url        | VARCHAR       | Notification icon      | |  |*
*|  |  | action_url      | VARCHAR       | Deep link              | |  |*
*|  |  | is_read         | BOOLEAN       | User has seen          | |  |*
*|  |  | created_at      | TIMESTAMP     | When created           | |  |*
*|  |  | expires_at      | TIMESTAMP     | TTL for cleanup        | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  Query: Get unread notifications for user                     |  |*
*|  |  SELECT * FROM in_app_notifications                           |  |*
*|  |  WHERE user_id = ? AND is_read = false                       |  |*
*|  |  ORDER BY created_at DESC LIMIT 50;                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 7: API DESIGN
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SEND NOTIFICATION API                                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  POST /api/v1/notifications                                   |  |*
*|  |                                                                 |  |*
*|  |  Request:                                                       |  |*
*|  |  {                                                              |  |*
*|  |    "user_id": "12345",                                        |  |*
*|  |    "template_id": "order_shipped",                            |  |*
*|  |    "channels": ["push", "email"],                             |  |*
*|  |    "priority": "high",                                        |  |*
*|  |    "variables": {                                              |  |*
*|  |      "order_id": "ORD-789",                                   |  |*
*|  |      "tracking_url": "https://..."                           |  |*
*|  |    },                                                          |  |*
*|  |    "idempotency_key": "order-789-shipped",                    |  |*
*|  |    "scheduled_at": null,  // or ISO timestamp                |  |*
*|  |    "metadata": {                                               |  |*
*|  |      "source": "order-service",                              |  |*
*|  |      "order_id": "789"                                        |  |*
*|  |    }                                                           |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  Response:                                                      |  |*
*|  |  {                                                              |  |*
*|  |    "notification_id": "ntf-uuid-123",                         |  |*
*|  |    "status": "queued",                                        |  |*
*|  |    "channels_queued": ["push", "email"]                       |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  BATCH SEND (For bulk notifications)                          |  |*
*|  |                                                                 |  |*
*|  |  POST /api/v1/notifications/batch                             |  |*
*|  |                                                                 |  |*
*|  |  Request:                                                       |  |*
*|  |  {                                                              |  |*
*|  |    "template_id": "weekly_digest",                            |  |*
*|  |    "channel": "email",                                        |  |*
*|  |    "priority": "low",                                         |  |*
*|  |    "recipients": [                                            |  |*
*|  |      { "user_id": "123", "variables": {...} },               |  |*
*|  |      { "user_id": "456", "variables": {...} },               |  |*
*|  |      ...                                                       |  |*
*|  |    ]                                                           |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  Response:                                                      |  |*
*|  |  {                                                              |  |*
*|  |    "batch_id": "batch-uuid-789",                              |  |*
*|  |    "status": "processing",                                    |  |*
*|  |    "total_recipients": 10000,                                 |  |*
*|  |    "queued": 10000                                            |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  GET NOTIFICATION STATUS                                       |  |*
*|  |                                                                 |  |*
*|  |  GET /api/v1/notifications/{notification_id}                  |  |*
*|  |                                                                 |  |*
*|  |  Response:                                                      |  |*
*|  |  {                                                              |  |*
*|  |    "notification_id": "ntf-uuid-123",                         |  |*
*|  |    "user_id": "12345",                                        |  |*
*|  |    "channels": {                                               |  |*
*|  |      "push": {                                                |  |*
*|  |        "status": "delivered",                                 |  |*
*|  |        "sent_at": "2024-01-15T10:00:00Z",                    |  |*
*|  |        "delivered_at": "2024-01-15T10:00:01Z"                |  |*
*|  |      },                                                        |  |*
*|  |      "email": {                                               |  |*
*|  |        "status": "opened",                                    |  |*
*|  |        "sent_at": "2024-01-15T10:00:00Z",                    |  |*
*|  |        "opened_at": "2024-01-15T10:05:00Z"                   |  |*
*|  |      }                                                         |  |*
*|  |    }                                                           |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  USER PREFERENCES API                                          |  |*
*|  |                                                                 |  |*
*|  |  GET /api/v1/users/{user_id}/preferences                      |  |*
*|  |  PUT /api/v1/users/{user_id}/preferences                      |  |*
*|  |                                                                 |  |*
*|  |  {                                                              |  |*
*|  |    "push_enabled": true,                                      |  |*
*|  |    "email_enabled": true,                                     |  |*
*|  |    "sms_enabled": false,                                      |  |*
*|  |    "quiet_hours": {                                           |  |*
*|  |      "enabled": true,                                         |  |*
*|  |      "start": "22:00",                                        |  |*
*|  |      "end": "08:00"                                           |  |*
*|  |    },                                                          |  |*
*|  |    "categories": {                                            |  |*
*|  |      "marketing": false,                                      |  |*
*|  |      "social": true,                                          |  |*
*|  |      "transactional": true                                    |  |*
*|  |    }                                                           |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  IN-APP NOTIFICATIONS API (For client apps)                   |  |*
*|  |                                                                 |  |*
*|  |  GET /api/v1/users/{user_id}/notifications                    |  |*
*|  |  Query: ?unread_only=true&limit=20&cursor=xxx                |  |*
*|  |                                                                 |  |*
*|  |  POST /api/v1/users/{user_id}/notifications/mark-read        |  |*
*|  |  { "notification_ids": ["ntf-1", "ntf-2"] }                  |  |*
*|  |                                                                 |  |*
*|  |  POST /api/v1/users/{user_id}/notifications/mark-all-read    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 8: PUSH NOTIFICATION DEEP DIVE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  iOS (APNs) vs Android (FCM)                                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  APPLE PUSH NOTIFICATION SERVICE (APNs)                       |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  Your Server                                              ||  |*
*|  |  |      |                                                    ||  |*
*|  |  |      | HTTP/2 connection (keep-alive)                    ||  |*
*|  |  |      | JWT authentication                                ||  |*
*|  |  |      v                                                    ||  |*
*|  |  |  APNs Server (api.push.apple.com)                        ||  |*
*|  |  |      |                                                    ||  |*
*|  |  |      |                                                    ||  |*
*|  |  |      v                                                    ||  |*
*|  |  |  iPhone                                                   ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  Payload format:                                               |  |*
*|  |  {                                                              |  |*
*|  |    "aps": {                                                    |  |*
*|  |      "alert": {                                               |  |*
*|  |        "title": "Order Shipped",                             |  |*
*|  |        "body": "Your order is on its way!"                  |  |*
*|  |      },                                                        |  |*
*|  |      "badge": 5,                                              |  |*
*|  |      "sound": "default",                                      |  |*
*|  |      "content-available": 1  // silent push                  |  |*
*|  |    },                                                          |  |*
*|  |    "custom_data": {...}                                       |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  Limits:                                                       |  |*
*|  |  * Payload max: 4 KB                                          |  |*
*|  |  * No rate limit (but Apple may throttle if abusive)        |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  FIREBASE CLOUD MESSAGING (FCM)                               |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  Your Server                                              ||  |*
*|  |  |      |                                                    ||  |*
*|  |  |      | HTTP POST to fcm.googleapis.com                   ||  |*
*|  |  |      | OAuth 2.0 authentication                          ||  |*
*|  |  |      v                                                    ||  |*
*|  |  |  FCM Server                                               ||  |*
*|  |  |      |                                                    ||  |*
*|  |  |      v                                                    ||  |*
*|  |  |  Android Device                                           ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  Payload format:                                               |  |*
*|  |  {                                                              |  |*
*|  |    "message": {                                                |  |*
*|  |      "token": "device_token_here",                           |  |*
*|  |      "notification": {                                        |  |*
*|  |        "title": "Order Shipped",                             |  |*
*|  |        "body": "Your order is on its way!"                  |  |*
*|  |      },                                                        |  |*
*|  |      "data": {                                                |  |*
*|  |        "order_id": "123",                                    |  |*
*|  |        "deep_link": "myapp://orders/123"                    |  |*
*|  |      },                                                        |  |*
*|  |      "android": {                                             |  |*
*|  |        "priority": "high",                                   |  |*
*|  |        "notification": {                                     |  |*
*|  |          "channel_id": "orders"                              |  |*
*|  |        }                                                      |  |*
*|  |      }                                                         |  |*
*|  |    }                                                           |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  Limits:                                                       |  |*
*|  |  * Payload max: 4 KB                                          |  |*
*|  |  * Rate limit: ~240 messages/min per device                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DEVICE TOKEN MANAGEMENT                                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Token lifecycle:                                              |  |*
*|  |                                                                 |  |*
*|  |  1. App installed > Register token with APNs/FCM              |  |*
*|  |  2. Send token to your server                                 |  |*
*|  |  3. Store: (user_id, token, platform, timestamp)             |  |*
*|  |  4. Token can change! (app update, reinstall)                |  |*
*|  |  5. On push failure "invalid token" > delete from DB         |  |*
*|  |                                                                 |  |*
*|  |  Multiple devices per user:                                    |  |*
*|  |  * User may have iPhone + iPad + Android                     |  |*
*|  |  * Send to ALL valid tokens                                   |  |*
*|  |  * Dedupe on device_id to avoid multiple tokens per device  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 9: RELIABILITY & RETRY HANDLING
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  RETRY STRATEGY                                                        |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  NOT ALL FAILURES SHOULD RETRY:                                |  |*
*|  |                                                                 |  |*
*|  |  +-----------------+----------------+------------------------+|  |*
*|  |  | Error Type      | Retry?         | Action                 ||  |*
*|  |  +-----------------+----------------+------------------------+|  |*
*|  |  | Invalid token   | NO             | Delete token, don't   ||  |*
*|  |  |                 |                | retry                  ||  |*
*|  |  | User unsubscri. | NO             | Update preferences    ||  |*
*|  |  | Rate limited    | YES            | Retry with backoff    ||  |*
*|  |  | Server error    | YES            | Retry with backoff    ||  |*
*|  |  | Timeout         | YES            | Retry immediately     ||  |*
*|  |  | Malformed req   | NO             | Log, alert, fix bug   ||  |*
*|  |  +-----------------+----------------+------------------------+|  |*
*|  |                                                                 |  |*
*|  |  EXPONENTIAL BACKOFF:                                          |  |*
*|  |                                                                 |  |*
*|  |  Attempt 1: Immediate                                          |  |*
*|  |  Attempt 2: 1 second                                          |  |*
*|  |  Attempt 3: 2 seconds                                         |  |*
*|  |  Attempt 4: 4 seconds                                         |  |*
*|  |  Attempt 5: 8 seconds                                         |  |*
*|  |  Max attempts: 5                                               |  |*
*|  |                                                                 |  |*
*|  |  After max attempts: Move to Dead Letter Queue               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  DEAD LETTER QUEUE (DLQ)                                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Purpose: Store notifications that repeatedly failed          |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  Main Queue > Worker > [Fail] > Retry Queue              ||  |*
*|  |  |                                     |                     ||  |*
*|  |  |                                     | (after max retries) ||  |*
*|  |  |                                     v                     ||  |*
*|  |  |                              Dead Letter Queue            ||  |*
*|  |  |                                     |                     ||  |*
*|  |  |                                     v                     ||  |*
*|  |  |                              Manual Review / Alert        ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  Actions on DLQ:                                               |  |*
*|  |  * Alert on-call if critical notification                    |  |*
*|  |  * Batch retry after provider issue resolved                 |  |*
*|  |  * Analyze patterns (why so many failures?)                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  PROVIDER FALLBACK                                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  For SMS and Email, maintain multiple providers:              |  |*
*|  |                                                                 |  |*
*|  |  SMS:                                                          |  |*
*|  |  * Primary: Twilio                                            |  |*
*|  |  * Fallback: Nexmo                                            |  |*
*|  |  * Fallback 2: AWS SNS                                        |  |*
*|  |                                                                 |  |*
*|  |  Email:                                                        |  |*
*|  |  * Primary: SendGrid                                          |  |*
*|  |  * Fallback: AWS SES                                          |  |*
*|  |  * Fallback 2: Mailgun                                        |  |*
*|  |                                                                 |  |*
*|  |  Implementation:                                               |  |*
*|  |                                                                 |  |*
*|  |  def send_sms(phone, message):                                |  |*
*|  |      providers = [twilio, nexmo, aws_sns]                    |  |*
*|  |      for provider in providers:                               |  |*
*|  |          try:                                                  |  |*
*|  |              return provider.send(phone, message)            |  |*
*|  |          except ProviderError:                                |  |*
*|  |              log.warn(f"{provider} failed, trying next")    |  |*
*|  |              continue                                         |  |*
*|  |      raise AllProvidersFailed()                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 10: RATE LIMITING & THROTTLING
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  MULTIPLE LEVELS OF RATE LIMITING                                      |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. PER-USER LIMITS (Prevent spam)                            |  |*
*|  |     * Max 50 push notifications/day                          |  |*
*|  |     * Max 5 SMS/day                                           |  |*
*|  |     * Max 10 marketing emails/week                           |  |*
*|  |                                                                 |  |*
*|  |  2. PER-SERVICE LIMITS (Prevent runaway services)            |  |*
*|  |     * Order service: 10K notifications/minute                |  |*
*|  |     * Marketing service: 100K emails/hour                    |  |*
*|  |                                                                 |  |*
*|  |  3. GLOBAL LIMITS (Protect infrastructure)                   |  |*
*|  |     * Total push: 100K/second                                |  |*
*|  |     * Total SMS: 10K/second                                  |  |*
*|  |     * Total email: 50K/second                                |  |*
*|  |                                                                 |  |*
*|  |  4. PROVIDER LIMITS (External constraints)                   |  |*
*|  |     * APNs: Varies (throttles if too aggressive)            |  |*
*|  |     * FCM: 240 messages/minute per device                   |  |*
*|  |     * Twilio: Based on account tier                         |  |*
*|  |     * SendGrid: Based on plan                               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  QUIET HOURS IMPLEMENTATION                                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  def should_send_now(user_id, notification):                  |  |*
*|  |      # Critical always sends                                  |  |*
*|  |      if notification.priority == "critical":                 |  |*
*|  |          return True                                          |  |*
*|  |                                                                 |  |*
*|  |      prefs = get_user_preferences(user_id)                   |  |*
*|  |      if not prefs.quiet_hours_enabled:                       |  |*
*|  |          return True                                          |  |*
*|  |                                                                 |  |*
*|  |      user_local_time = get_local_time(prefs.timezone)        |  |*
*|  |      quiet_start = prefs.quiet_start  # 22:00               |  |*
*|  |      quiet_end = prefs.quiet_end      # 08:00               |  |*
*|  |                                                                 |  |*
*|  |      if is_within_quiet_hours(user_local_time,               |  |*
*|  |                               quiet_start, quiet_end):       |  |*
*|  |          # Queue for delivery after quiet hours             |  |*
*|  |          schedule_for(notification, quiet_end)               |  |*
*|  |          return False                                         |  |*
*|  |                                                                 |  |*
*|  |      return True                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  NOTIFICATION BATCHING                                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Problem: User gets 10 likes in 1 minute                     |  |*
*|  |           Don't send 10 separate push notifications!          |  |*
*|  |                                                                 |  |*
*|  |  Solution: Batch similar notifications                        |  |*
*|  |                                                                 |  |*
*|  |  Instead of:                                                   |  |*
*|  |  * "Alice liked your post"                                   |  |*
*|  |  * "Bob liked your post"                                     |  |*
*|  |  * "Carol liked your post"                                   |  |*
*|  |                                                                 |  |*
*|  |  Send:                                                         |  |*
*|  |  * "Alice, Bob, and 8 others liked your post"               |  |*
*|  |                                                                 |  |*
*|  |  Implementation:                                               |  |*
*|  |  * Window-based batching (collect for 30 seconds)            |  |*
*|  |  * Key: (user_id, notification_type, target_object)          |  |*
*|  |  * Aggregate count during window                             |  |*
*|  |  * Send summary after window closes                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 11: ANALYTICS & TRACKING
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  TRACKING PIPELINE                                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Notification Sent                                             |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |  EVENT: notification_sent                               |  |  |*
*|  |  |  { notification_id, user_id, channel, timestamp }       |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  Provider Webhook (Delivered)                                 |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |  EVENT: notification_delivered                          |  |  |*
*|  |  |  { notification_id, timestamp }                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  User Opens (Tracking pixel / app open)                       |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |  EVENT: notification_opened                             |  |  |*
*|  |  |  { notification_id, timestamp }                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  User Clicks Link                                             |  |*
*|  |       |                                                        |  |*
*|  |       v                                                        |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |  EVENT: notification_clicked                            |  |  |*
*|  |  |  { notification_id, link_url, timestamp }               |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  |  All events > Kafka > Analytics DB (ClickHouse/BigQuery)      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  METRICS DASHBOARD                                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  KEY METRICS:                                                  |  |*
*|  |                                                                 |  |*
*|  |  Delivery Metrics:                                             |  |*
*|  |  * Sent count (by channel, template, priority)               |  |*
*|  |  * Delivery rate = delivered / sent                          |  |*
*|  |  * Failure rate (by error code)                              |  |*
*|  |  * Average latency (sent to delivered)                       |  |*
*|  |                                                                 |  |*
*|  |  Engagement Metrics:                                           |  |*
*|  |  * Open rate = opened / delivered                            |  |*
*|  |  * Click rate = clicked / opened                             |  |*
*|  |  * Unsubscribe rate                                          |  |*
*|  |                                                                 |  |*
*|  |  System Metrics:                                               |  |*
*|  |  * Queue depth (by priority)                                 |  |*
*|  |  * Processing latency                                        |  |*
*|  |  * Worker throughput                                         |  |*
*|  |  * Provider availability                                     |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 12: ADVANCED TOPICS & REAL-WORLD PROBLEMS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  NOTIFICATION FATIGUE                                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Problem: Users disable all notifications because too many    |  |*
*|  |                                                                 |  |*
*|  |  Solutions:                                                    |  |*
*|  |                                                                 |  |*
*|  |  1. SMART FREQUENCY CAPPING                                   |  |*
*|  |     * ML model predicts optimal notification frequency       |  |*
*|  |     * Reduce for users who don't engage                      |  |*
*|  |     * "This user opens 10% of pushes, send max 2/day"       |  |*
*|  |                                                                 |  |*
*|  |  2. NOTIFICATION SCORING                                      |  |*
*|  |     * Score each notification by importance                  |  |*
*|  |     * Only send if score > user's threshold                 |  |*
*|  |     * Threshold adapts based on engagement                  |  |*
*|  |                                                                 |  |*
*|  |  3. DIGEST MODE                                               |  |*
*|  |     * Batch low-priority into daily/weekly digest           |  |*
*|  |     * User preference: real-time vs digest                  |  |*
*|  |                                                                 |  |*
*|  |  4. CATEGORY MANAGEMENT                                       |  |*
*|  |     * Let users control by category                         |  |*
*|  |     * "Turn off marketing but keep order updates"           |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  EMAIL DELIVERABILITY                                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Problem: Emails going to spam folder                         |  |*
*|  |                                                                 |  |*
*|  |  Solutions:                                                    |  |*
*|  |                                                                 |  |*
*|  |  1. AUTHENTICATION                                            |  |*
*|  |     * SPF (Sender Policy Framework)                          |  |*
*|  |     * DKIM (DomainKeys Identified Mail)                      |  |*
*|  |     * DMARC (Domain-based Message Authentication)            |  |*
*|  |                                                                 |  |*
*|  |  2. IP REPUTATION                                             |  |*
*|  |     * Use dedicated IPs for marketing vs transactional       |  |*
*|  |     * Warm up new IPs gradually                              |  |*
*|  |     * Monitor blacklists                                     |  |*
*|  |                                                                 |  |*
*|  |  3. LIST HYGIENE                                              |  |*
*|  |     * Remove bounced emails                                  |  |*
*|  |     * Remove unengaged users (no opens in 6 months)         |  |*
*|  |     * Double opt-in for marketing                           |  |*
*|  |                                                                 |  |*
*|  |  4. CONTENT BEST PRACTICES                                    |  |*
*|  |     * Avoid spam trigger words                               |  |*
*|  |     * Good text-to-image ratio                               |  |*
*|  |     * Working unsubscribe link (required by law)            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  MULTI-REGION DEPLOYMENT                                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  For global users, deploy in multiple regions:                |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  US Users          EU Users          APAC Users          ||  |*
*|  |  |      |                 |                 |                ||  |*
*|  |  |      v                 v                 v                ||  |*
*|  |  |  US Region         EU Region        APAC Region          ||  |*
*|  |  |  Workers           Workers           Workers              ||  |*
*|  |  |      |                 |                 |                ||  |*
*|  |  |      v                 v                 v                ||  |*
*|  |  |  APNs/FCM          APNs/FCM         APNs/FCM             ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  Benefits:                                                     |  |*
*|  |  * Lower latency to APNs/FCM (they have regional endpoints)  |  |*
*|  |  * Data residency compliance (GDPR)                          |  |*
*|  |  * Fault isolation                                           |  |*
*|  |                                                                 |  |*
*|  |  Routing:                                                      |  |*
*|  |  * Route by user's region (stored in profile)                |  |*
*|  |  * Or by device token prefix (FCM has regional hints)        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  A/B TESTING NOTIFICATIONS                                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Test different:                                               |  |*
*|  |  * Message copy                                               |  |*
*|  |  * Send time                                                   |  |*
*|  |  * Frequency                                                   |  |*
*|  |  * Channel combination                                        |  |*
*|  |                                                                 |  |*
*|  |  Implementation:                                               |  |*
*|  |                                                                 |  |*
*|  |  def select_template(user_id, template_id, experiment_id):   |  |*
*|  |      bucket = hash(user_id, experiment_id) % 100             |  |*
*|  |                                                                 |  |*
*|  |      if bucket < 50:  # Control                               |  |*
*|  |          return template_id + "_control"                     |  |*
*|  |      else:            # Variant                               |  |*
*|  |          return template_id + "_variant"                     |  |*
*|  |                                                                 |  |*
*|  |  Track: experiment_id with each notification                  |  |*
*|  |  Analyze: Compare open/click rates between variants          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  PERSONALIZATION / ML-POWERED NOTIFICATIONS                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. SEND TIME OPTIMIZATION                                    |  |*
*|  |     * ML predicts when user most likely to engage            |  |*
*|  |     * Based on historical open patterns                      |  |*
*|  |     * "User opens notifications around 8 AM and 6 PM"       |  |*
*|  |                                                                 |  |*
*|  |  2. CHANNEL SELECTION                                         |  |*
*|  |     * Some users prefer email, some prefer push              |  |*
*|  |     * ML selects optimal channel per user                   |  |*
*|  |                                                                 |  |*
*|  |  3. CONTENT PERSONALIZATION                                   |  |*
*|  |     * Dynamic subject lines based on user interests          |  |*
*|  |     * Product recommendations in notification                |  |*
*|  |                                                                 |  |*
*|  |  4. PREDICTIVE NOTIFICATIONS                                  |  |*
*|  |     * Predict user needs before they act                    |  |*
*|  |     * "Your usual order? Tap to reorder"                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 13: INTERVIEW QUICK REFERENCE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  KEY TALKING POINTS                                                    |*
*|                                                                         |*
*|  1. MULTI-CHANNEL                                                      |*
*|     * Push (APNs/FCM), SMS, Email, In-App                            |*
*|     * Different SLAs and costs per channel                           |*
*|                                                                         |*
*|  2. ARCHITECTURE                                                       |*
*|     * API > Kafka (priority queues) > Channel Workers > Providers   |*
*|     * Separate topics by priority and channel                        |*
*|                                                                         |*
*|  3. RELIABILITY                                                        |*
*|     * At-least-once delivery via Kafka                               |*
*|     * Retry with exponential backoff                                 |*
*|     * Dead Letter Queue for failed messages                          |*
*|     * Provider fallback (Twilio > Nexmo > SNS)                      |*
*|                                                                         |*
*|  4. USER PREFERENCES                                                   |*
*|     * Opt-in/out per channel and category                           |*
*|     * Quiet hours with timezone support                              |*
*|                                                                         |*
*|  5. RATE LIMITING                                                      |*
*|     * Per-user, per-service, global, provider limits                |*
*|     * Notification batching to prevent spam                         |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  COMMON INTERVIEW QUESTIONS                                           |*
*|                                                                         |*
*|  Q: How do you ensure notifications are delivered?                   |*
*|  A: At-least-once via Kafka + retries. Exponential backoff for      |*
*|     transient failures. Invalid tokens removed, not retried.        |*
*|     Provider fallback for SMS/email.                                 |*
*|                                                                         |*
*|  Q: How do you handle millions of notifications per second?         |*
*|  A: Kafka partitioned by user_id for ordering. Separate topics by   |*
*|     priority (critical processes first). Scale workers horizontally.|*
*|     Batch notifications to providers (FCM supports 500/request).    |*
*|                                                                         |*
*|  Q: How do you prevent notification spam?                            |*
*|  A: Rate limiting per user. Batching similar notifications.         |*
*|     User preferences for opt-out. Smart frequency capping via ML.   |*
*|                                                                         |*
*|  Q: How do you handle user preferences like quiet hours?            |*
*|  A: Store timezone in user profile. On notification, calculate      |*
*|     user's local time. If quiet hours, schedule for after.         |*
*|     Critical notifications bypass quiet hours.                       |*
*|                                                                         |*
*|  Q: How do you track if notification was opened?                    |*
*|  A: Email: tracking pixel (1x1 image with unique URL).             |*
*|     Push: App reports open event to server.                         |*
*|     Links: URL rewriting through redirect service.                  |*
*|                                                                         |*
*|  Q: What happens if APNs/FCM is down?                               |*
*|  A: Retry with backoff. Kafka retains messages. Once provider       |*
*|     recovers, backlog processes. Monitor latency, alert if stuck.  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  ARCHITECTURE SUMMARY                                                  |*
*|                                                                         |*
*|  Internal Services > Notification API > Kafka (priority queues)     |*
*|      > Channel Workers > External Providers (APNs, FCM, Twilio)    |*
*|                                                                         |*
*|  Key Components:                                                       |*
*|  * Notification API: Validation, preferences, templates, enqueue   |*
*|  * Kafka: Priority topics, partitioned by user_id                  |*
*|  * Workers: Channel-specific, batch to providers, handle retries   |*
*|  * Providers: APNs, FCM, Twilio, SendGrid                          |*
*|                                                                         |*
*|  Key Numbers:                                                          |*
*|  * 1.6B notifications/day                                            |*
*|  * 18K/second average, 185K/second peak                            |*
*|  * Push 4KB payload limit                                            |*
*|  * Email: Track open/click rates                                    |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

ARCHITECTURE DIAGRAM
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|          +------------------------------------------------------+      |*
*|          |              INTERNAL SERVICES                       |      |*
*|          |    (Order, User, Marketing, Payment, etc.)          |      |*
*|          +--------------------------+---------------------------+      |*
*|                                     |                                   |*
*|                                     v                                   |*
*|                    +--------------------------------+                  |*
*|                    |      NOTIFICATION API          |                  |*
*|                    |                                |                  |*
*|                    |  * Validate request            |                  |*
*|                    |  * Check user preferences      |                  |*
*|                    |  * Render template             |                  |*
*|                    |  * Rate limit                  |                  |*
*|                    |  * Enqueue to Kafka            |                  |*
*|                    +----------------+---------------+                  |*
*|                                     |                                   |*
*|                                     v                                   |*
*|     +---------------------------------------------------------------+  |*
*|     |                         KAFKA                                 |  |*
*|     |                                                               |  |*
*|     |  +--------------+  +--------------+  +--------------+       |  |*
*|     |  |push.critical |  | sms.critical |  |email.high    |       |  |*
*|     |  |push.high     |  | sms.high     |  |email.normal  |       |  |*
*|     |  |push.normal   |  +--------------+  |email.low     |       |  |*
*|     |  |push.low      |                    +--------------+       |  |*
*|     |  +--------------+                                           |  |*
*|     |                       +--------------+                       |  |*
*|     |                       |   in_app     |                       |  |*
*|     |                       +--------------+                       |  |*
*|     +-------------------------------+-------------------------------+  |*
*|                                     |                                   |*
*|          +--------------------------+--------------------------+       |*
*|          |                          |                          |       |*
*|          v                          v                          v       |*
*|   +------------+            +------------+            +------------+  |*
*|   |   PUSH     |            |    SMS     |            |   EMAIL    |  |*
*|   |  WORKERS   |            |  WORKERS   |            |  WORKERS   |  |*
*|   +-----+------+            +-----+------+            +-----+------+  |*
*|         |                         |                         |         |*
*|    +----+----+              +-----+-----+             +-----+-----+  |*
*|    |         |              |           |             |           |  |*
*|    v         v              v           v             v           v  |*
*| +------+ +------+      +--------+ +--------+   +---------+ +-----+  |*
*| | APNs | | FCM  |      | Twilio | | Nexmo  |   |SendGrid | | SES |  |*
*| |(iOS) | |(Andr)|      |        | |(backup)|   |         | |     |  |*
*| +------+ +------+      +--------+ +--------+   +---------+ +-----+  |*
*|                                                                         |*
*|                    +--------------------------------+                  |*
*|                    |         IN-APP WORKER          |                  |*
*|                    +----------------+---------------+                  |*
*|                                     |                                   |*
*|                    +----------------+---------------+                  |*
*|                    |            REDIS               |                  |*
*|                    |    (In-app notification DB)    |                  |*
*|                    +----------------+---------------+                  |*
*|                                     |                                   |*
*|                                     | WebSocket                        |*
*|                                     v                                   |*
*|                    +--------------------------------+                  |*
*|                    |        CLIENT APPS             |                  |*
*|                    +--------------------------------+                  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF NOTIFICATION SYSTEM DESIGN
