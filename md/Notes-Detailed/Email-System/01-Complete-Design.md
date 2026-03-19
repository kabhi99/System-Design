# EMAIL SYSTEM DESIGN (GMAIL)
*Complete Design: Requirements, Architecture, and Interview Guide*

An email system is one of the oldest and most critical internet services. At
Gmail's scale (1.8B+ users), the system must handle billions of emails daily,
store petabytes of data, provide sub-second search across years of mail, filter
spam with near-perfect accuracy, and support massive attachments - all while
guaranteeing that no legitimate email is ever lost.

## SECTION 1: UNDERSTANDING THE PROBLEM

### WHAT IS AN EMAIL SYSTEM?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  An email system enables asynchronous messaging between users           |
|  across the internet using standardized protocols.                      |
|                                                                         |
|  USER EXPERIENCE:                                                       |
|  1. Compose an email (to, cc, bcc, subject, body, attachments)          |
|  2. Click "Send" - email travels through SMTP servers                   |
|  3. Recipient sees email in their inbox within seconds                  |
|  4. Recipient can reply, forward, organize into folders/labels          |
|  5. Search through years of email history instantly                     |
|  6. Access from any device (web, mobile, desktop client)                |
|                                                                         |
|  REAL-WORLD EXAMPLES:                                                   |
|  * Gmail           - 1.8B users, Google's email service                 |
|  * Outlook         - Microsoft's enterprise and consumer email          |
|  * Yahoo Mail      - one of the original web mail services              |
|  * ProtonMail      - end-to-end encrypted email                         |
|  * Apple Mail      - Apple's native email client + iCloud Mail          |
|                                                                         |
|  KEY PROTOCOLS:                                                         |
|  * SMTP - Simple Mail Transfer Protocol (sending)                       |
|  * IMAP - Internet Message Access Protocol (reading, server-side)       |
|  * POP3 - Post Office Protocol (reading, client-side download)          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY IS THIS HARD TO BUILD?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY CHALLENGES:                                                        |
|                                                                         |
|  1. RELIABILITY - ZERO EMAIL LOSS                                       |
|  ---------------------------------                                      |
|  Email is a "store-and-forward" system - unlike chat, users             |
|  expect that once sent, an email WILL arrive. Losing an email           |
|  is unacceptable - could be a job offer, legal document, or             |
|  financial statement.                                                   |
|                                                                         |
|  2. MASSIVE SCALE                                                       |
|  ----------------                                                       |
|  1B+ users, each with potentially GBs of stored email.                  |
|  Billions of emails sent and received daily.                            |
|  Must store, index, and search across petabytes.                        |
|                                                                         |
|  3. SPAM AND SECURITY                                                   |
|  ---------------------                                                  |
|  Over 45% of all email is spam. Must filter with high precision         |
|  (don't lose legitimate email) and high recall (catch most spam).       |
|  Phishing, malware, impersonation attacks are constant threats.         |
|                                                                         |
|  4. PROTOCOL COMPLEXITY                                                 |
|  -----------------------                                                |
|  SMTP was designed in 1982. Extensions like MIME, DKIM, SPF,            |
|  DMARC have been bolted on over decades. Supporting all of these        |
|  correctly is complex and error-prone.                                  |
|                                                                         |
|  5. LARGE ATTACHMENTS                                                   |
|  ---------------------                                                  |
|  Users send 25MB+ attachments. Must store, virus-scan, and serve        |
|  them efficiently. Deduplication across millions of copies of           |
|  the same PDF forward chain is critical.                                |
|                                                                         |
|  6. SEARCH AT SCALE                                                     |
|  -------------------                                                    |
|  Users search "that email from John about the Q3 report from            |
|  last year." Must full-text search across years of email,               |
|  billions of messages, in under a second.                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: REQUIREMENTS

### FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CORE FEATURES:                                                         |
|                                                                         |
|  1. SEND EMAIL                                                          |
|     * Compose with to, cc, bcc, subject, body (rich text)               |
|     * Attach files (up to 25 MB per email)                              |
|     * Schedule send (deliver at a future time)                          |
|     * Reply, reply-all, forward                                         |
|                                                                         |
|  2. RECEIVE EMAIL                                                       |
|     * Receive from any SMTP-compliant sender                            |
|     * Real-time or near-real-time delivery to inbox                     |
|     * Push notifications on new mail                                    |
|                                                                         |
|  3. INBOX AND FOLDERS                                                   |
|     * Inbox, Sent, Drafts, Trash, Spam, Archive                         |
|     * Custom labels / folders                                           |
|     * Star / flag important emails                                      |
|     * Read / unread status                                              |
|     * Threaded conversations (group by subject + participants)          |
|                                                                         |
|  4. SEARCH                                                              |
|     * Full-text search across all emails                                |
|     * Filter by sender, date, has-attachment, label                     |
|     * Search within specific folders                                    |
|     * Autocomplete suggestions                                          |
|                                                                         |
|  5. ATTACHMENTS                                                         |
|     * Upload and download files                                         |
|     * Preview common formats (PDF, images, docs)                        |
|     * Virus scanning before delivery                                    |
|                                                                         |
|  6. LABELS AND FILTERS                                                  |
|     * Auto-categorize (Primary, Social, Promotions, Updates)            |
|     * User-defined rules (from X > apply label Y, archive)              |
|     * Automatic priority / importance detection                         |
|                                                                         |
|  7. CONTACTS                                                            |
|     * Address book with auto-complete                                   |
|     * Contact groups / distribution lists                               |
|     * Import/export contacts                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### NON-FUNCTIONAL REQUIREMENTS

```
+--------------------------------------------------------------------------+
|                                                                          |
|  AVAILABILITY:                                                           |
|  * 99.99% uptime (< 52 minutes downtime/year)                            |
|  * Email delivery must work even during partial outages                  |
|  * Graceful degradation: search may slow but email must deliver          |
|                                                                          |
|  RELIABILITY:                                                            |
|  * ZERO email loss - this is the #1 non-negotiable requirement           |
|  * At-least-once delivery (duplicates are preferable to loss)            |
|  * Durable storage with replication                                      |
|                                                                          |
|  SCALE:                                                                  |
|  * 1 billion+ users                                                      |
|  * Average 40 emails received per user per day                           |
|  * 15 GB storage per user (free tier)                                    |
|  * Support 25 MB attachments                                             |
|                                                                          |
|  PERFORMANCE:                                                            |
|  * Inbox load: < 1 second                                                |
|  * Send email: < 2 seconds to acknowledge                                |
|  * Search: < 1 second for most queries                                   |
|  * Email delivery: < 30 seconds for most emails                          |
|                                                                          |
|  SECURITY:                                                               |
|  * TLS for all connections (in transit)                                  |
|  * Encryption at rest for stored emails                                  |
|  * Spam filtering: > 99.9% catch rate, < 0.01% false positive            |
|  * DKIM, SPF, DMARC for sender authentication                            |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 3: BACK-OF-ENVELOPE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  EMAIL VOLUME:                                                          |
|  * 1B users, average 40 emails received/day                             |
|  * Total received: 1B x 40 = 40B emails/day                             |
|  * Emails/second: 40B / 86,400 ~ 460,000 emails/sec                     |
|  * Peak (3x): ~1.4M emails/sec                                          |
|  * Average 10 emails sent per user per day                              |
|  * Total sent: 1B x 10 = 10B emails/day                                 |
|                                                                         |
|  EMAIL SIZE:                                                            |
|  * Average email body: ~50 KB (with HTML formatting)                    |
|  * Average attachment: ~500 KB (when present)                           |
|  * ~30% of emails have attachments                                      |
|  * Effective average email: 50 KB + (0.3 x 500 KB) = 200 KB             |
|                                                                         |
|  STORAGE PER USER:                                                      |
|  * 40 emails/day x 200 KB = 8 MB/day                                    |
|  * 8 MB x 365 = ~2.9 GB/year                                            |
|  * With 5 years of history: ~15 GB (matches Gmail free tier)            |
|                                                                         |
|  TOTAL STORAGE:                                                         |
|  * 1B users x 15 GB = 15 exabytes (EB)                                  |
|  * Not all users are active - assume 500M active: 7.5 EB                |
|  * With 3x replication: 22.5 EB                                         |
|  * This is why email companies build their own storage infra            |
|                                                                         |
|  DAILY INGESTION:                                                       |
|  * 40B emails x 200 KB = 8 PB/day ingested                              |
|  * With replication: ~24 PB/day written                                 |
|                                                                         |
|  BANDWIDTH:                                                             |
|  * Inbound SMTP: 460K emails/sec x 200 KB = ~92 GB/sec                  |
|  * User reads (IMAP/web): assume 20% of daily email read                |
|  * Read bandwidth: 40B x 0.2 x 200 KB / 86400 ~ 18.5 GB/sec             |
|                                                                         |
|  SEARCH INDEX:                                                          |
|  * Full-text index is typically 30-50% of raw data size                 |
|  * 7.5 EB x 0.4 = 3 EB of search index                                  |
|  * Partitioned per user - each user's index is ~6 GB                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                       HIGH-LEVEL ARCHITECTURE                           |
+-------------------------------------------------------------------------+
|                                                                         |
|  SENDING SIDE:                                                          |
|                                                                         |
|  +--------+    +-------------+    +-------------+    +-----------+      |
|  | Web /  |    | API Gateway |    | Outbound    |    | DNS MX    |      |
|  | Mobile | -> |             | -> | SMTP Server | -> | Lookup +  |      |
|  | Client |    |             |    |             |    | Relay     |      |
|  +--------+    +-------------+    +-------------+    +-----------+      |
|                                                           |             |
|                                                           v             |
|                                                   +-----------+         |
|                                                   | Recipient |         |
|                                                   | SMTP (ext)|         |
|                                                   +-----------+         |
|                                                                         |
|  RECEIVING SIDE:                                                        |
|                                                                         |
|  +-----------+    +-----------+    +----------+    +------------+       |
|  | Inbound   |    | Spam &    |    | Rule     |    | Mailbox    |       |
|  | SMTP      | -> | Virus     | -> | Engine   | -> | Storage    |       |
|  | Server    |    | Filter    |    | (labels, |    | (per-user) |       |
|  +-----------+    +-----------+    | filters) |    +------------+       |
|                                    +----------+         |               |
|                                                         v               |
|                                                   +------------+        |
|                                                   | Search     |        |
|                                                   | Indexer    |        |
|                                                   +------------+        |
|                                                         |               |
|                                                         v               |
|                                                   +------------+        |
|                                                   | Push       |        |
|                                                   | Notification|       |
|                                                   +------------+        |
|                                                                         |
|  READING SIDE:                                                          |
|                                                                         |
|  +--------+    +-------------+    +------------+    +------------+      |
|  | Web /  |    | API Gateway |    | Mailbox    |    | Search     |      |
|  | Mobile | -> |             | -> | Service    | -> | Service    |      |
|  | Client |    | / IMAP      |    |            |    | (ES/Lucene)|      |
|  +--------+    +-------------+    +------------+    +------------+      |
|                                        |                                |
|                                        v                                |
|                                   +------------+                        |
|                                   | Attachment  |                       |
|                                   | Service     |                       |
|                                   | (Blob Store)|                       |
|                                   +------------+                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMPONENT OVERVIEW

```
+--------------------------------------------------------------------------+
|                                                                          |
|  +-------------------+------------------------------------------------+  |
|  | Component         | Responsibility                                 |  |
|  +-------------------+------------------------------------------------+  |
|  | API Gateway       | Auth, rate limiting, route to services         |  |
|  | Outbound SMTP     | Compose > send via SMTP to recipients          |  |
|  | Inbound SMTP      | Accept incoming email from external senders    |  |
|  | Spam/Virus Filter | ML spam detection + virus scanning             |  |
|  | Rule Engine       | Apply user rules: labels, filters, forwards    |  |
|  | Mailbox Service   | CRUD on emails, folders, labels, threads       |  |
|  | Mailbox Storage   | Persistent storage (Bigtable/Cassandra)        |  |
|  | Search Service    | Full-text search (Elasticsearch/Lucene)        |  |
|  | Search Indexer    | Real-time indexing of new emails               |  |
|  | Attachment Service| Upload, download, dedup, virus scan            |  |
|  | Blob Storage      | Store large attachments (GCS/S3)               |  |
|  | Push Service      | Send push notifications on new mail            |  |
|  | Contact Service   | Address book, autocomplete                     |  |
|  +-------------------+------------------------------------------------+  |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 5: DEEP DIVE - EMAIL PROTOCOLS

### SMTP (SIMPLE MAIL TRANSFER PROTOCOL)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PURPOSE: Sending and relaying email between mail servers.              |
|  PORT: 25 (server-to-server), 587 (client submission with auth)         |
|  SECURITY: STARTTLS upgrades plaintext to encrypted                     |
|                                                                         |
|  SMTP CONVERSATION:                                                     |
|                                                                         |
|  Client                        Server                                   |
|  ------                        ------                                   |
|                            <-- 220 mail.example.com ESMTP ready         |
|  EHLO sender.com           -->                                          |
|                            <-- 250 Hello sender.com                     |
|  MAIL FROM:<a@sender.com>  -->                                          |
|                            <-- 250 OK                                   |
|  RCPT TO:<b@example.com>   -->                                          |
|                            <-- 250 OK                                   |
|  DATA                      -->                                          |
|                            <-- 354 Start mail input                     |
|  Subject: Hello            -->                                          |
|  (email body)              -->                                          |
|  .                         -->                                          |
|                            <-- 250 Message accepted                     |
|  QUIT                      -->                                          |
|                            <-- 221 Bye                                  |
|                                                                         |
|  MX RECORD DNS LOOKUP:                                                  |
|  When sending to b@example.com:                                         |
|  1. Query DNS for MX record of example.com                              |
|  2. DNS returns: mail.example.com (priority 10)                         |
|  3. Connect to mail.example.com on port 25                              |
|  4. Deliver the email via SMTP conversation                             |
|                                                                         |
|  +----------+  DNS MX query  +----------+  priority  +-----------+      |
|  | Sender   | ------------> | DNS      | ---------> | mail.     |       |
|  | SMTP     | example.com?  | Server   |  10:mail.  | example   |       |
|  | Server   |               |          |  example.  | .com:25   |       |
|  +----------+               +----------+  com       +-----------+       |
|       |                                                  ^              |
|       |             SMTP relay                           |              |
|       +--------------------------------------------------+              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### IMAP (INTERNET MESSAGE ACCESS PROTOCOL)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PURPOSE: Reading email while keeping messages on the server.           |
|  PORT: 993 (IMAP over TLS)                                              |
|                                                                         |
|  KEY FEATURES:                                                          |
|  * Folder management (create, rename, delete folders)                   |
|  * Partial fetch (download headers without body - saves bandwidth)      |
|  * Flags: \Seen, \Flagged, \Deleted, \Draft                             |
|  * Server-side search                                                   |
|  * Multiple device sync (read on phone > marked read on desktop)        |
|                                                                         |
|  IMAP vs POP3:                                                          |
|  +-------------------+-------------------+--------------------+         |
|  | Feature           | IMAP              | POP3               |         |
|  +-------------------+-------------------+--------------------+         |
|  | Message storage   | On server         | Downloaded to      |         |
|  |                   |                   | client, deleted    |         |
|  |                   |                   | from server        |         |
|  +-------------------+-------------------+--------------------+         |
|  | Multi-device sync | Yes               | No                 |         |
|  +-------------------+-------------------+--------------------+         |
|  | Folder support    | Yes               | No (inbox only)    |         |
|  +-------------------+-------------------+--------------------+         |
|  | Partial fetch     | Yes (headers only)| No (full download) |         |
|  +-------------------+-------------------+--------------------+         |
|  | Offline access    | Cached locally    | Full local copy    |         |
|  +-------------------+-------------------+--------------------+         |
|  | Complexity        | Higher            | Simple             |         |
|  +-------------------+-------------------+--------------------+         |
|  | Modern usage      | Standard          | Legacy / niche     |         |
|  +-------------------+-------------------+--------------------+         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### EMAIL AUTHENTICATION: DKIM, SPF, DMARC

```
+---------------------------------------------------------------------------+
|                                                                           |
|  PROBLEM: Anyone can forge the "From" address in email.                   |
|  SOLUTION: Authentication mechanisms to verify sender identity.           |
|                                                                           |
|  SPF (Sender Policy Framework):                                           |
|  +-----------------------------------------------------------+            |
|  | DNS TXT record listing authorized sending IPs for a domain |           |
|  | example.com TXT "v=spf1 ip4:203.0.113.0/24 -all"          |            |
|  | Receiving server checks: did this email come from an        |          |
|  | authorized IP? If not, reject or flag.                      |          |
|  +-----------------------------------------------------------+            |
|                                                                           |
|  DKIM (DomainKeys Identified Mail):                                       |
|  +-----------------------------------------------------------+            |
|  | Sending server signs email headers + body with private key. |          |
|  | Public key published in DNS.                                |          |
|  | Receiving server verifies signature using public key.        |         |
|  | Proves: email was not tampered with in transit.              |         |
|  +-----------------------------------------------------------+            |
|                                                                           |
|  DMARC (Domain-based Message Auth, Reporting, Conformance):               |
|  +-----------------------------------------------------------+            |
|  | Policy layer on top of SPF + DKIM.                          |          |
|  | Tells receivers: if SPF and DKIM both fail, do THIS:        |          |
|  |   - none: do nothing (monitoring mode)                      |          |
|  |   - quarantine: put in spam                                 |          |
|  |   - reject: bounce the email                                |          |
|  | Also sends aggregate reports back to the domain owner.       |         |
|  +-----------------------------------------------------------+            |
|                                                                           |
|  AUTHENTICATION FLOW:                                                     |
|                                                                           |
|  +--------+  email with  +----------+  check SPF  +--------+              |
|  | Sender | -----------> | Receiver | ----------> | DNS    |              |
|  | SMTP   |  DKIM header | SMTP     |  check DKIM | Server |              |
|  +--------+              +----------+  check DMARC+--------+              |
|                               |                                           |
|                               v                                           |
|                          PASS / FAIL                                      |
|                          > deliver / spam / reject                        |
|                                                                           |
+---------------------------------------------------------------------------+
```

## SECTION 6: DEEP DIVE - SEND FLOW

```
+--------------------------------------------------------------------------+
|                                                                          |
|  END-TO-END SEND FLOW:                                                   |
|                                                                          |
|  +--------+    +----------+    +----------+    +-----------+             |
|  | User   |    | API      |    | Outbound |    | Queue     |             |
|  | clicks |    | Gateway  |    | SMTP     |    | (retry    |             |
|  | Send   | -> | (auth,   | -> | Server   | -> | buffer)   |             |
|  |        |    |  validate)|    |          |    |           |            |
|  +--------+    +----------+    +----------+    +-----------+             |
|                                                      |                   |
|                                                      v                   |
|                                               +------------+             |
|                                               | DNS MX     |             |
|                                               | Lookup     |             |
|                                               +------------+             |
|                                                      |                   |
|                                                      v                   |
|                                               +------------+             |
|                                               | Relay to   |             |
|                                               | Recipient  |             |
|                                               | SMTP       |             |
|                                               +------------+             |
|                                                      |                   |
|                                                      v                   |
|                                               +------------+             |
|                                               | Recipient  |             |
|                                               | Delivery   |             |
|                                               | Pipeline   |             |
|                                               +------------+             |
|                                                      |                   |
|                                                      v                   |
|                                               +------------+             |
|                                               | Recipient  |             |
|                                               | Mailbox    |             |
|                                               +------------+             |
|                                                                          |
|  DETAILED STEPS:                                                         |
|                                                                          |
|  1. COMPOSE: User writes email in web/mobile client                      |
|  2. SUBMIT: Client sends to API Gateway via HTTPS                        |
|  3. VALIDATE: Check recipients exist, attachment sizes, rate limits      |
|  4. STORE DRAFT: Save to Sent folder (for sender's records)              |
|  5. ENQUEUE: Put email in outbound queue (durability guarantee)          |
|  6. SMTP SEND: Outbound SMTP picks up from queue                         |
|  7. DNS LOOKUP: Query MX record for recipient domain                     |
|  8. RELAY: Connect to recipient's SMTP server, deliver                   |
|  9. ACK: If accepted, mark as delivered. If rejected, handle error.      |
|                                                                          |
+--------------------------------------------------------------------------+
```

### RETRY AND BOUNCE HANDLING

```
+---------------------------------------------------------------------------+
|                                                                           |
|  RETRY WITH EXPONENTIAL BACKOFF:                                          |
|                                                                           |
|  If recipient SMTP server is temporarily unavailable:                     |
|                                                                           |
|  Attempt 1: immediate                                                     |
|  Attempt 2: wait 1 minute                                                 |
|  Attempt 3: wait 5 minutes                                                |
|  Attempt 4: wait 30 minutes                                               |
|  Attempt 5: wait 2 hours                                                  |
|  Attempt 6: wait 8 hours                                                  |
|  Attempt 7: wait 24 hours                                                 |
|  ... up to 72 hours total retry window                                    |
|                                                                           |
|  After 72 hours: generate bounce email to sender                          |
|                                                                           |
|  BOUNCE TYPES:                                                            |
|  +--------------+-------------------------------------------+             |
|  | Type         | Cause                                     |             |
|  +--------------+-------------------------------------------+             |
|  | Hard bounce  | Invalid address, domain doesn't exist      |            |
|  |              | > Stop retrying immediately                |            |
|  +--------------+-------------------------------------------+             |
|  | Soft bounce  | Mailbox full, server temp unavailable       |           |
|  |              | > Keep retrying with backoff               |            |
|  +--------------+-------------------------------------------+             |
|  | Policy block | Blocked by spam filter or policy            |           |
|  |              | > Notify sender, may need action            |           |
|  +--------------+-------------------------------------------+             |
|                                                                           |
|  BOUNCE EMAIL TO SENDER:                                                  |
|  +----------------------------------------------------------+             |
|  | From: MAILER-DAEMON@gmail.com                             |            |
|  | Subject: Delivery Status Notification (Failure)           |            |
|  | Body: Your message to X was not delivered because:        |            |
|  |       "550 User not found"                                |            |
|  +----------------------------------------------------------+             |
|                                                                           |
+---------------------------------------------------------------------------+
```

## SECTION 7: DEEP DIVE - RECEIVE FLOW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INBOUND EMAIL PIPELINE:                                                |
|                                                                         |
|  +----------+                                                           |
|  | External |                                                           |
|  | SMTP     |                                                           |
|  | Server   |                                                           |
|  +----------+                                                           |
|       |                                                                 |
|       v                                                                 |
|  +-------------------+                                                  |
|  | 1. INBOUND SMTP   |  Accept connection, authenticate sender          |
|  |    SERVER          |  Check SPF, DKIM, DMARC                         |
|  +-------------------+                                                  |
|       |                                                                 |
|       v                                                                 |
|  +-------------------+                                                  |
|  | 2. SPAM FILTER    |  ML-based content analysis                       |
|  |                   |  Reputation check (IP, domain, sender)           |
|  |                   |  > PASS: continue / SPAM: move to spam folder    |
|  +-------------------+                                                  |
|       |                                                                 |
|       v                                                                 |
|  +-------------------+                                                  |
|  | 3. VIRUS SCAN     |  Scan attachments for malware                    |
|  |                   |  Check URLs for phishing                         |
|  |                   |  > CLEAN: continue / INFECTED: quarantine        |
|  +-------------------+                                                  |
|       |                                                                 |
|       v                                                                 |
|  +-------------------+                                                  |
|  | 4. RULE ENGINE    |  Apply user-defined filters:                     |
|  |                   |  - Auto-label (from boss > "Important")          |
|  |                   |  - Auto-forward (CC me on all from X)            |
|  |                   |  - Auto-archive (newsletters > archive)          |
|  |                   |  Apply system categorization:                    |
|  |                   |  - Primary / Social / Promotions / Updates       |
|  +-------------------+                                                  |
|       |                                                                 |
|       v                                                                 |
|  +-------------------+                                                  |
|  | 5. STORE IN       |  Write email to user's mailbox storage           |
|  |    MAILBOX        |  Assign thread ID (conversation threading)       |
|  |                   |  Set initial flags: \Recent, category label      |
|  +-------------------+                                                  |
|       |                                                                 |
|       v                                                                 |
|  +-------------------+                                                  |
|  | 6. INDEX FOR      |  Extract text from body + attachments            |
|  |    SEARCH         |  Index: sender, subject, body, date, labels      |
|  |                   |  Near-real-time (< 30 seconds to searchable)     |
|  +-------------------+                                                  |
|       |                                                                 |
|       v                                                                 |
|  +-------------------+                                                  |
|  | 7. PUSH           |  Notify user's devices:                          |
|  |    NOTIFICATION   |  - Mobile push (FCM / APNs)                      |
|  |                   |  - Desktop notification                          |
|  |                   |  - Badge count update                            |
|  +-------------------+                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8: DEEP DIVE - MAILBOX STORAGE

### EMAIL AS IMMUTABLE OBJECTS

```
+--------------------------------------------------------------------------+
|                                                                          |
|  DESIGN PRINCIPLE: Emails are immutable once received.                   |
|  They are never modified - only metadata changes (read, labels, etc.)    |
|                                                                          |
|  EMAIL OBJECT:                                                           |
|  +-----------------------------------------------------------+           |
|  | email_id:     "e_abc123"         (globally unique)         |          |
|  | user_id:      "u_xyz789"         (mailbox owner)           |          |
|  | thread_id:    "t_def456"         (conversation grouping)   |          |
|  | from:         "alice@example.com"                          |          |
|  | to:           ["bob@gmail.com"]                             |         |
|  | cc:           ["carol@gmail.com"]                           |         |
|  | subject:      "Q3 Report"                                  |          |
|  | body_ref:     "blob://body/e_abc123"  (pointer to body)    |          |
|  | attachments:  ["blob://att/hash1", "blob://att/hash2"]     |          |
|  | timestamp:    1709312400                                   |          |
|  | size_bytes:   52480                                        |          |
|  | headers:      { ... raw SMTP headers ... }                 |          |
|  +-----------------------------------------------------------+           |
|                                                                          |
|  METADATA (mutable):                                                     |
|  +-----------------------------------------------------------+           |
|  | email_id:     "e_abc123"                                   |          |
|  | is_read:      true                                         |          |
|  | is_starred:   false                                        |          |
|  | labels:       ["inbox", "important", "work"]               |          |
|  | is_deleted:   false                                        |          |
|  | snoozed_until: null                                        |          |
|  +-----------------------------------------------------------+           |
|                                                                          |
|  SEPARATION OF CONCERNS:                                                 |
|  * Immutable email data > write once to blob storage                     |
|  * Mutable metadata > lightweight row in metadata store                  |
|  * Enables: label changes without copying the entire email               |
|                                                                          |
+--------------------------------------------------------------------------+
```

### FOLDERS AS VIEWS (NOT PHYSICAL COPIES)

```
+--------------------------------------------------------------------------+
|                                                                          |
|  A "folder" or "label" is NOT a physical copy of the email.              |
|  It is a VIEW - a tag on the email's metadata.                           |
|                                                                          |
|  EXAMPLE:                                                                |
|  Email e_abc123 has labels: ["inbox", "important", "work"]               |
|                                                                          |
|  When user views "Inbox":                                                |
|    > Query: SELECT * WHERE labels CONTAINS "inbox"                       |
|  When user views "Important":                                            |
|    > Query: SELECT * WHERE labels CONTAINS "important"                   |
|  When user views "Work":                                                 |
|    > Query: SELECT * WHERE labels CONTAINS "work"                        |
|                                                                          |
|  ALL three views point to the SAME email object.                         |
|  No duplication. Moving to Trash = remove "inbox", add "trash".          |
|                                                                          |
|  +------------------+                                                    |
|  |  Email Object    |                                                    |
|  |  e_abc123        |<-------+-------+-------+                           |
|  +------------------+        |       |       |                           |
|                              |       |       |                           |
|                     +--------+  +----+--+  +-+-------+                   |
|                     | Inbox  |  | Work  |  |Important|                   |
|                     | View   |  | View  |  | View    |                   |
|                     +--------+  +-------+  +---------+                   |
|                                                                          |
|  STORAGE BACKEND OPTIONS:                                                |
|                                                                          |
|  +-------------------+------------------------------------------+        |
|  | Option            | Characteristics                          |        |
|  +-------------------+------------------------------------------+        |
|  | Bigtable          | Google's choice. Wide-column, per-user   |        |
|  |                   | row key, sorted by timestamp. Scales     |        |
|  |                   | horizontally. Excellent for sequential   |        |
|  |                   | reads (inbox listing).                   |        |
|  +-------------------+------------------------------------------+        |
|  | Cassandra         | Similar wide-column model. Good write    |        |
|  |                   | throughput. Tunable consistency.          |       |
|  +-------------------+------------------------------------------+        |
|  | Custom (Gmail)    | Gmail uses a custom storage layer        |        |
|  |                   | built on GFS/Colossus. Optimized for     |        |
|  |                   | email-specific access patterns.          |        |
|  +-------------------+------------------------------------------+        |
|                                                                          |
+--------------------------------------------------------------------------+
```

### ATTACHMENT STORAGE AND DEDUPLICATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROBLEM: The same 5 MB PDF gets forwarded 10,000 times.                |
|  Storing 10,000 copies = 50 GB wasted. Must deduplicate.                |
|                                                                         |
|  DEDUPLICATION STRATEGY:                                                |
|                                                                         |
|  1. On attachment upload, compute SHA-256 hash of content               |
|  2. Check if hash already exists in blob storage                        |
|  3. If YES: store a pointer (reference) to existing blob                |
|  4. If NO: store the blob, index by hash                                |
|                                                                         |
|  +----------+  hash = SHA256(file)  +----------+                        |
|  | Incoming | --------------------> | Lookup   |                        |
|  | attach.  |                       | Hash DB  |                        |
|  +----------+                       +----------+                        |
|                                       |      |                          |
|                                EXISTS |      | NEW                      |
|                                       v      v                          |
|                              +----------+ +----------+                  |
|                              | Store    | | Store    |                  |
|                              | pointer  | | blob +   |                  |
|                              | only     | | record   |                  |
|                              | (8 bytes)| | hash     |                  |
|                              +----------+ +----------+                  |
|                                                                         |
|  STORAGE TIERS:                                                         |
|  +-------------------+------------------------------------------+       |
|  | Tier              | Usage                                    |       |
|  +-------------------+------------------------------------------+       |
|  | Hot (SSD)         | Attachments < 30 days old                |       |
|  | Warm (HDD)        | Attachments 30 days - 1 year             |       |
|  | Cold (archive)    | Attachments > 1 year (rarely accessed)   |       |
|  +-------------------+------------------------------------------+       |
|                                                                         |
|  BLOB STORAGE:                                                          |
|  * Google Cloud Storage / S3 for large files                            |
|  * CDN for frequently accessed attachments                              |
|  * Virus-scanned before storage                                         |
|  * Encrypted at rest (AES-256)                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: DEEP DIVE - SEARCH

### FULL-TEXT SEARCH ARCHITECTURE

```
+--------------------------------------------------------------------------+
|                                                                          |
|  SEARCH ENGINE: Elasticsearch / Lucene (or custom equivalent)            |
|  WHY ES/LUCENE? Email search requires full-text matching across          |
|  subject+body+attachments, keyword filters (from:, to:, has:),           |
|  date range queries, and boolean combinations - all in <100ms.           |
|  Inverted index is purpose-built for this. SQL LIKE or MongoDB           |
|  text search can't handle this query complexity at scale.                |
|                                                                          |
|  INDEX STRUCTURE PER USER:                                               |
|  +-----------------------------------------------------------+           |
|  | Field          | Index Type    | Example                   |          |
|  +-----------------------------------------------------------+           |
|  | from           | Keyword       | "alice@example.com"       |          |
|  | to             | Keyword       | "bob@gmail.com"           |          |
|  | subject        | Full-text     | "Q3 quarterly report"     |          |
|  | body           | Full-text     | "Please find attached..." |          |
|  | date           | Date range    | 2024-03-01                |          |
|  | labels         | Keyword array | ["inbox", "work"]         |          |
|  | has_attachment  | Boolean       | true                      |         |
|  | attachment_name| Full-text     | "report.pdf"              |          |
|  | is_read        | Boolean       | false                     |          |
|  | thread_id      | Keyword       | "t_def456"                |          |
|  +-----------------------------------------------------------+           |
|                                                                          |
|  QUERY EXAMPLES:                                                         |
|                                                                          |
|  User types: "from:alice report Q3"                                      |
|  Parsed as:                                                              |
|    from = "alice*" AND (subject OR body) CONTAINS "report Q3"            |
|                                                                          |
|  User types: "has:attachment before:2024-01-01"                          |
|  Parsed as:                                                              |
|    has_attachment = true AND date < 2024-01-01                           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### REAL-TIME INDEXING

```
+--------------------------------------------------------------------------+
|                                                                          |
|  EMAIL ARRIVES > INDEX WITHIN SECONDS                                    |
|                                                                          |
|  +----------+    +-----------+    +-----------+    +------------+        |
|  | Mailbox  |    | Indexing  |    | Text      |    | Search     |        |
|  | Storage  | -> | Queue     | -> | Extractor | -> | Index      |        |
|  | (write)  |    | (Kafka)   |    | (parse    |    | (ES/Lucene)|        |
|  +----------+    +-----------+    | HTML,     |    +------------+        |
|                                   | extract   |                          |
|                                   | text from |                          |
|                                   | PDF, etc.)|                          |
|                                   +-----------+                          |
|                                                                          |
|  PIPELINE STEPS:                                                         |
|                                                                          |
|  1. Email stored in mailbox > event published to indexing queue          |
|  2. Text extractor:                                                      |
|     * Strip HTML tags from body                                          |
|     * Extract text from PDF/DOC attachments                              |
|     * Normalize unicode, handle multiple languages                       |
|  3. Tokenize and analyze (stemming, stop words, synonyms)                |
|  4. Write to per-user search index shard                                 |
|  5. Available for search within ~5-30 seconds                            |
|                                                                          |
|  QUERY PROCESSING:                                                       |
|                                                                          |
|  +--------+   query    +----------+   route to   +----------+            |
|  | User   | ---------> | Query    | -----------> | User's   |            |
|  | types  |            | Parser   |   user shard  | Index    |           |
|  | search |            +----------+              | Shard    |            |
|  +--------+                                      +----------+            |
|                                                       |                  |
|                                                       v                  |
|                                                  +----------+            |
|                                                  | Rank by  |            |
|                                                  | relevance|            |
|                                                  | + recency|            |
|                                                  +----------+            |
|                                                       |                  |
|                                                       v                  |
|                                                  Return top 20           |
|                                                  results                 |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 10: DEEP DIVE - SPAM AND SECURITY

### SPAM FILTERING PIPELINE

```
+--------------------------------------------------------------------------+
|                                                                          |
|  MULTI-LAYER SPAM DEFENSE:                                               |
|                                                                          |
|  LAYER 1: CONNECTION-LEVEL                                               |
|  +-----------------------------------------------------------+           |
|  | - IP reputation check (known spam IPs > reject)            |          |
|  | - Rate limiting per sender IP                               |         |
|  | - Reverse DNS check (sender IP must resolve)                |         |
|  | - DNSBL (DNS Block List) lookup                             |         |
|  | Filter: ~60% of spam blocked here (never even accepted)     |         |
|  +-----------------------------------------------------------+           |
|                                                                          |
|  LAYER 2: PROTOCOL-LEVEL                                                 |
|  +-----------------------------------------------------------+           |
|  | - SPF check (sender authorized for domain?)                 |         |
|  | - DKIM check (signature valid?)                             |         |
|  | - DMARC check (policy alignment?)                           |         |
|  | Filter: ~15% more spam blocked (forged sender addresses)    |         |
|  +-----------------------------------------------------------+           |
|                                                                          |
|  LAYER 3: CONTENT-LEVEL (ML)                                             |
|  +-----------------------------------------------------------+           |
|  | - Naive Bayes classifier on email text                      |         |
|  | - Deep learning model on email structure + content          |         |
|  | - URL reputation (is any link known-malicious?)             |         |
|  | - Image analysis (spam images, invisible text)              |         |
|  | - Header analysis (forged headers, unusual routing)         |         |
|  | Filter: ~20% more spam caught (sophisticated spam)          |         |
|  +-----------------------------------------------------------+           |
|                                                                          |
|  LAYER 4: USER BEHAVIOR                                                  |
|  +-----------------------------------------------------------+           |
|  | - User marks as spam > feedback to ML model                 |         |
|  | - If 100+ users mark same sender as spam > auto-block       |         |
|  | - Unsubscribe signals                                       |         |
|  | - Engagement metrics (never opened > likely spam)           |         |
|  +-----------------------------------------------------------+           |
|                                                                          |
|  COMBINED: > 99.9% spam caught, < 0.01% false positives                  |
|                                                                          |
+--------------------------------------------------------------------------+
```

### PHISHING AND SECURITY

```
+--------------------------------------------------------------------------+
|                                                                          |
|  PHISHING DETECTION:                                                     |
|  +-----------------------------------------------------------+           |
|  | - Check URLs against known phishing databases               |         |
|  | - Detect lookalike domains (goog1e.com, paypa1.com)         |         |
|  | - Analyze page content behind links (Safe Browsing API)     |         |
|  | - Flag emails claiming to be from banks, Google, etc.       |         |
|  |   but coming from unauthorized domains                      |         |
|  | - Display warning banners: "This may be a phishing email"   |         |
|  +-----------------------------------------------------------+           |
|                                                                          |
|  LINK SCANNING:                                                          |
|  +-----------------------------------------------------------+           |
|  | Every URL in every email is:                                |         |
|  | 1. Checked against Safe Browsing database at receive time   |         |
|  | 2. Optionally rewritten to pass through a redirect scanner  |         |
|  | 3. Re-checked at CLICK time (URL may become malicious later)|         |
|  +-----------------------------------------------------------+           |
|                                                                          |
|  ENCRYPTION:                                                             |
|  +-----------------------------------------------------------+           |
|  | In Transit:                                                 |         |
|  | - TLS 1.3 for all SMTP connections (opportunistic)          |         |
|  | - HTTPS for all web/mobile API access                       |         |
|  |                                                             |         |
|  | At Rest:                                                    |         |
|  | - AES-256 encryption for all stored email content           |         |
|  | - Per-user encryption keys (managed by KMS)                 |         |
|  | - Attachment blobs encrypted independently                  |         |
|  |                                                             |         |
|  | End-to-End (optional, like ProtonMail):                     |         |
|  | - Client-side encryption with user's key pair               |         |
|  | - Server never sees plaintext                               |         |
|  | - Breaks server-side search and spam filtering              |         |
|  +-----------------------------------------------------------+           |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 11: SCALING

### MAILBOX SHARDING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SHARD BY USER_ID:                                                      |
|  Each user's entire mailbox lives on one shard.                         |
|  Shard = hash(user_id) % N                                              |
|                                                                         |
|  +-------------------+     +-------------------+                        |
|  | Shard 0           |     | Shard 1           |                        |
|  | Users: A, D, G... |     | Users: B, E, H... |                        |
|  | 166M users        |     | 166M users        |                        |
|  | ~2.5 EB storage   |     | ~2.5 EB storage   |                        |
|  +-------------------+     +-------------------+                        |
|       |                         |                                       |
|       v                         v                                       |
|  +-------------------+     +-------------------+                        |
|  | Replica (DR)      |     | Replica (DR)      |                        |
|  +-------------------+     +-------------------+                        |
|                                                                         |
|  WHY SHARD BY USER:                                                     |
|  * All operations are scoped to ONE user (read inbox, search, etc.)     |
|  * No cross-user joins or queries needed                                |
|  * Each shard is independently scalable                                 |
|  * User's data locality > cache-friendly                                |
|                                                                         |
|  REBALANCING:                                                           |
|  * Consistent hashing for minimal data movement on shard add/remove     |
|  * Background migration: copy user data, switch routing, delete old     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SMTP SERVER FARM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INBOUND SMTP:                                                          |
|                                                                         |
|  +---------+     +----------------+     +------------------+            |
|  | Internet| --> | DNS MX points  | --> | L4 Load Balancer |            |
|  | senders |     | to multiple IPs|     | (round-robin)    |            |
|  +---------+     +----------------+     +------------------+            |
|                                              |  |  |  |                 |
|                                              v  v  v  v                 |
|                                         +-----------------+             |
|                                         | SMTP Server     |             |
|                                         | Fleet           |             |
|                                         | (100+ servers)  |             |
|                                         | Stateless       |             |
|                                         +-----------------+             |
|                                                                         |
|  OUTBOUND SMTP:                                                         |
|                                                                         |
|  +----------+     +-------------------+     +-----------------+         |
|  | Outbound | --> | IP Pool Manager   | --> | Send via        |         |
|  | Queue    |     | (rotate IPs to    |     | different IPs   |         |
|  |          |     |  maintain good    |     | per domain      |         |
|  +----------+     |  reputation)      |     +-----------------+         |
|                   +-------------------+                                 |
|                                                                         |
|  IP REPUTATION MANAGEMENT:                                              |
|  * Maintain pools of sending IPs with good reputation                   |
|  * Warm up new IPs gradually (start with low volume)                    |
|  * Monitor bounce rates per IP - rotate out degraded IPs                |
|  * Separate IP pools for transactional vs marketing email               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ASYNC PROCESSING PIPELINE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  The entire receive flow is an asynchronous pipeline:                   |
|                                                                         |
|  +--------+    +---------+    +--------+    +---------+    +---------+  |
|  | Accept | -> | Queue 1 | -> | Spam   | -> | Queue 2 | -> | Store   |  |
|  | SMTP   |    | (raw    |    | Filter |    | (clean  |    | in      |  |
|  | conn.  |    |  email) |    |        |    |  email) |    | mbox    |  |
|  +--------+    +---------+    +--------+    +---------+    +---------+  |
|                                                                 |       |
|                                                                 v       |
|                                                          +----------+   |
|                                                          | Queue 3  |   |
|                                                          | (index   |   |
|                                                          |  + push) |   |
|                                                          +----------+   |
|                                                            |     |      |
|                                                            v     v      |
|                                                      +------+ +-------+ |
|                                                      |Search| |Push   | |
|                                                      |Index | |Notif  | |
|                                                      +------+ +-------+ |
|                                                                         |
|  WHY QUEUES BETWEEN EACH STAGE:                                         |
|  * Decouple stages: spam filter down ! email acceptance down            |
|  * Buffer for traffic spikes (Black Friday email blasts)                |
|  * Each stage scales independently                                      |
|  * Guaranteed delivery: message persisted in queue before ACK           |
|  * Retry failed stages without re-accepting the email                   |
|                                                                         |
|  QUEUE TECHNOLOGY: Kafka or Pulsar                                      |
|  * Durable (replicated across brokers)                                  |
|  * Ordered per partition (emails from same sender stay ordered)         |
|  * Consumer groups for parallel processing                              |
|  * Retention for replay if a stage needs reprocessing                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SEARCH INDEX PARTITIONING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PARTITION STRATEGY: Per-user index shards                              |
|                                                                         |
|  Each user's search index is co-located with their mailbox shard.       |
|  A search query only hits ONE shard (the user's shard).                 |
|                                                                         |
|  +-------------------+   +-------------------+                          |
|  | Mailbox Shard 0   |   | Mailbox Shard 1   |                          |
|  | +---------------+ |   | +---------------+ |                          |
|  | | Search Index  | |   | | Search Index  | |                          |
|  | | for users     | |   | | for users     | |                          |
|  | | A, D, G...    | |   | | B, E, H...    | |                          |
|  | +---------------+ |   | +---------------+ |                          |
|  +-------------------+   +-------------------+                          |
|                                                                         |
|  ADVANTAGES:                                                            |
|  * No scatter-gather: one shard answers the full query                  |
|  * Index size per user: ~6 GB (manageable)                              |
|  * Index builds and repairs are per-user (isolated)                     |
|                                                                         |
|  INDEX MAINTENANCE:                                                     |
|  * Incremental: new emails indexed in real-time                         |
|  * Bulk rebuild: if index corrupts, rebuild from mailbox data           |
|  * Compaction: merge small segments periodically (Lucene merge)         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MULTI-REGION DEPLOYMENT

```
+--------------------------------------------------------------------------+
|                                                                          |
|                    +-------------------+                                 |
|                    | Global DNS        |                                 |
|                    | (GeoDNS routing)  |                                 |
|                    +-------------------+                                 |
|                     /        |        \                                  |
|                    v         v         v                                 |
|  +---------------+ +---------------+ +---------------+                   |
|  | US Region     | | EU Region     | | ASIA Region   |                   |
|  |               | |               | |               |                   |
|  | SMTP servers  | | SMTP servers  | | SMTP servers  |                   |
|  | Spam filter   | | Spam filter   | | Spam filter   |                   |
|  | Mailbox store | | Mailbox store | | Mailbox store |                   |
|  | Search index  | | Search index  | | Search index  |                   |
|  | Blob storage  | | Blob storage  | | Blob storage  |                   |
|  +---------------+ +---------------+ +---------------+                   |
|                                                                          |
|  USER DATA PLACEMENT:                                                    |
|  * User's mailbox stored in their primary region                         |
|  * GDPR: EU user data MUST stay in EU region                             |
|  * Cross-region email: sender's outbound SMTP relays to                  |
|    recipient's region SMTP inbound                                       |
|                                                                          |
|  ATTACHMENT CDN:                                                         |
|  * Frequently accessed attachments cached at edge                        |
|  * User opens attachment > served from nearest CDN node                  |
|  * Reduces cross-region blob fetches                                     |
|                                                                          |
|  DISASTER RECOVERY:                                                      |
|  * Async replication of mailbox data to secondary region                 |
|  * If primary region fails, failover to secondary                        |
|  * RPO (Recovery Point Objective): < 1 minute of data                    |
|  * RTO (Recovery Time Objective): < 5 minutes                            |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 12: INTERVIEW Q&A

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Q1: How do you guarantee zero email loss?                              |
|  ------------------------------------------                             |
|  A: Multiple layers of durability:                                      |
|  1. SMTP protocol itself: server sends 250 OK only AFTER writing        |
|     the email to durable storage (disk or queue). If crash before       |
|     ACK, sender retries.                                                |
|  2. Queues between pipeline stages are persistent (Kafka with           |
|     replication). Email is in queue until next stage ACKs.              |
|  3. Mailbox storage uses 3x replication across data centers.            |
|  4. At-least-once semantics: duplicates possible but no loss.           |
|  5. Deduplication at mailbox level using message-ID header.             |
|                                                                         |
|  Q2: Why use labels instead of physical folders?                        |
|  ------------------------------------------------                       |
|  A: Labels are more flexible and storage-efficient:                     |
|  * One email can have multiple labels (inbox + work + important)        |
|  * With physical folders, you'd need to copy the email to each one      |
|  * Label change = update one metadata field vs copy entire email        |
|  * Gmail pioneered this approach; it maps naturally to tags and         |
|    search-based email organization                                      |
|                                                                         |
|  Q3: How do you handle a 25 MB attachment?                              |
|  ------------------------------------------                             |
|  A: Attachments are separated from email body:                          |
|  1. Client uploads attachment to blob storage (direct upload URL)       |
|  2. Blob storage returns a content-hash reference                       |
|  3. Email metadata stores the reference, not the binary                 |
|  4. Deduplication: if hash exists, just store a pointer                 |
|  5. For SMTP delivery to external servers, attachment is inlined        |
|     in MIME format. For internal delivery, just the reference.          |
|  6. Virus-scanned asynchronously; quarantined if infected               |
|                                                                         |
|  Q4: How does search work across years of email?                        |
|  ------------------------------------------------                       |
|  A: Per-user inverted index (Lucene-based):                             |
|  * Each user's emails indexed in their own shard                        |
|  * Index covers all fields: from, to, subject, body, labels, date       |
|  * New emails indexed in near-real-time (< 30 sec)                      |
|  * Query hits only ONE shard (the user's shard) - no scatter-gather     |
|  * Index size ~6 GB per user (fits in memory for active users)          |
|  * Ranking: relevance score + recency boost                             |
|                                                                         |
|  Q5: How do you prevent your SMTP server from being flagged as spam?    |
|  -------------------------------------------------------------------    |
|  A: Sender reputation management:                                       |
|  * Maintain pools of IPs with established good reputation               |
|  * Warm up new IPs gradually (send small volume first)                  |
|  * Implement SPF, DKIM, DMARC for all outbound email                    |
|  * Monitor bounce rates and spam complaints per IP                      |
|  * Separate IP pools for different email types (transactional vs bulk)  |
|  * Rate limit per-user sending to prevent abuse                         |
|  * Scan outbound email for spam/malware before sending                  |
|                                                                         |
|  Q6: How do you handle email threading (conversations)?                 |
|  -------------------------------------------------------                |
|  A: Threading uses the References and In-Reply-To headers:              |
|  * Each email has a unique Message-ID header                            |
|  * Reply includes In-Reply-To: <original message-id>                    |
|  * References header chains all message-ids in the thread               |
|  * Server groups emails with matching References into a thread_id       |
|  * Fallback: group by normalized subject line (strip Re:/Fwd:)          |
|  * Thread view shows emails in chronological order with indentation     |
|                                                                         |
|  Q7: How would you build the "Promotions" tab categorization?           |
|  ------------------------------------------------------------           |
|  A: Multi-class ML classifier:                                          |
|  * Categories: Primary, Social, Promotions, Updates, Forums             |
|  * Features: sender domain, subject keywords, HTML structure,           |
|    unsubscribe headers, sender frequency, past user actions             |
|  * Training data: millions of user-categorized emails                   |
|  * Inference at receive time (add to pipeline after spam filter)        |
|  * User corrections (move to different tab) fed back to model           |
|  * Per-user personalization layer on top of global model                |
|                                                                         |
|  Q8: What happens during a region-wide outage?                          |
|  ----------------------------------------------                         |
|  A: Failover strategy:                                                  |
|  * SMTP inbound: MX records have multiple entries with priorities       |
|    > external senders automatically try the next MX server              |
|  * User access: DNS failover routes to secondary region                 |
|  * Mailbox: async-replicated to secondary region. May lose              |
|    up to ~1 minute of the most recent emails (RPO).                     |
|  * Search index: rebuilt from mailbox data if secondary index           |
|    is stale (can take minutes, degraded search in the interim)          |
|  * SMTP sending: queued emails retried from healthy region              |
|                                                                         |
|  Q9: How does email differ from a chat system architecturally?          |
|  -------------------------------------------------------------          |
|  A: Key differences:                                                    |
|  * Email is store-and-forward (async); chat is real-time                |
|  * Email has no presence/typing indicators                              |
|  * Email uses standard protocols (SMTP/IMAP) across providers;          |
|    chat is usually proprietary                                          |
|  * Email messages are much larger (attachments, HTML)                   |
|  * Email requires spam filtering (open system); chat doesn't            |
|    (closed system - you must accept a connection request)               |
|  * Email storage is long-term (years); chat can be ephemeral            |
|  * Email fan-out is lower (one email to few recipients);                |
|    chat groups can have thousands of members                            |
|                                                                         |
|  Q10: How would you implement "Undo Send"?                              |
|  ------------------------------------------                             |
|  A: Delayed sending:                                                    |
|  * When user clicks Send, email goes to a "pending" queue               |
|  * A configurable delay (5, 10, or 30 seconds) before actual send       |
|  * During this window, user can cancel > delete from queue              |
|  * After the window: email is sent via normal SMTP flow                 |
|  * Server stores the email in Sent folder immediately (with             |
|    "pending" status) so the user sees it as sent                        |
|  * If cancelled: remove from Sent folder, restore to Drafts             |
|  * This is NOT a recall - once sent via SMTP, it cannot be undone       |
|                                                                         |
+-------------------------------------------------------------------------+
```

*End of Email System Design*
