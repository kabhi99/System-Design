# DISTRIBUTED JOB SCHEDULER SYSTEM DESIGN

A COMPLETE CONCEPTUAL GUIDE
SECTION 1: UNDERSTANDING THE PROBLEM
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHAT IS A JOB SCHEDULER?                                              |*
*|                                                                         |*
*|  A system that executes tasks/jobs at specific times or intervals      |*
*|                                                                         |*
*|  Examples:                                                              |*
*|  * Send daily email digests at 9 AM                                   |*
*|  * Generate monthly reports on 1st of each month                      |*
*|  * Process payment retries every 30 minutes                           |*
*|  * Clean up expired sessions hourly                                   |*
*|  * Execute one-time delayed tasks (send email in 24 hours)           |*
*|                                                                         |*
*|  Real-world systems:                                                   |*
*|  * Airflow (Apache) - Data pipeline orchestration                     |*
*|  * Celery Beat - Python distributed task queue                        |*
*|  * Quartz - Java scheduling framework                                 |*
*|  * Kubernetes CronJobs                                                 |*
*|  * AWS CloudWatch Events / EventBridge                                |*
*|  * Sidekiq (Ruby)                                                     |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  WHY DISTRIBUTED?                                                      |*
*|                                                                         |*
*|  Single-node scheduler problems:                                       |*
*|  * Single point of failure                                            |*
*|  * Limited throughput                                                 |*
*|  * Can't scale with job volume                                       |*
*|  * Node restart = missed jobs                                        |*
*|                                                                         |*
*|  Distributed scheduler provides:                                       |*
*|  * High availability (no single point of failure)                    |*
*|  * Horizontal scalability                                             |*
*|  * Fault tolerance                                                    |*
*|  * Load balancing across workers                                     |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  KEY CHALLENGES                                                        |*
*|                                                                         |*
*|  1. EXACTLY-ONCE EXECUTION                                            |*
*|     * Job should run exactly once, not multiple times                |*
*|     * Tricky in distributed systems!                                 |*
*|                                                                         |*
*|  2. HIGH AVAILABILITY                                                  |*
*|     * Scheduler node failure shouldn't stop jobs                     |*
*|     * Jobs must be picked up by another node                        |*
*|                                                                         |*
*|  3. TIME ACCURACY                                                      |*
*|     * Jobs should run at the specified time (not late)               |*
*|     * Clock synchronization across nodes                             |*
*|                                                                         |*
*|  4. SCALABILITY                                                        |*
*|     * Handle millions of scheduled jobs                              |*
*|     * Efficient lookup of "jobs due now"                            |*
*|                                                                         |*
*|  5. ORDERING & PRIORITIES                                             |*
*|     * High-priority jobs should run first                            |*
*|     * Dependencies between jobs                                      |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2: TYPES OF JOBS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  JOB TYPES                                                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. ONE-TIME JOBS (Delayed Jobs)                               |  |*
*|  |     -----------------------------                               |  |*
*|  |     Execute once at a specific future time                     |  |*
*|  |                                                                 |  |*
*|  |     Examples:                                                   |  |*
*|  |     * "Send reminder email in 24 hours"                       |  |*
*|  |     * "Expire promotion on Jan 15, 2024 at midnight"          |  |*
*|  |     * "Retry payment in 30 minutes"                           |  |*
*|  |                                                                 |  |*
*|  |     Input: { job_type, payload, execute_at: timestamp }       |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  2. RECURRING JOBS (Cron Jobs)                                 |  |*
*|  |     ------------------------------                              |  |*
*|  |     Execute repeatedly based on a schedule                    |  |*
*|  |                                                                 |  |*
*|  |     Examples:                                                   |  |*
*|  |     * "Every day at 9 AM"                                     |  |*
*|  |     * "Every Monday at 6 PM"                                  |  |*
*|  |     * "Every 5 minutes"                                       |  |*
*|  |     * "1st of every month at midnight"                        |  |*
*|  |                                                                 |  |*
*|  |     Input: { job_type, payload, cron_expression }             |  |*
*|  |                                                                 |  |*
*|  |     Cron expression: "0 9 * * *" (9 AM daily)                 |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  3. IMMEDIATE JOBS (Background Jobs)                           |  |*
*|  |     --------------------------------                            |  |*
*|  |     Execute as soon as possible (async processing)            |  |*
*|  |                                                                 |  |*
*|  |     Examples:                                                   |  |*
*|  |     * "Process this uploaded video now"                       |  |*
*|  |     * "Send welcome email immediately"                        |  |*
*|  |                                                                 |  |*
*|  |     (This is more like a task queue than scheduler)           |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  CRON EXPRESSION FORMAT                                                |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |   +------------- minute (0 - 59)                              |  |*
*|  |   | +------------- hour (0 - 23)                              |  |*
*|  |   | | +------------- day of month (1 - 31)                    |  |*
*|  |   | | | +------------- month (1 - 12)                         |  |*
*|  |   | | | | +------------- day of week (0 - 6) (Sunday = 0)    |  |*
*|  |   | | | | |                                                    |  |*
*|  |   * * * * *                                                    |  |*
*|  |                                                                 |  |*
*|  |   Examples:                                                    |  |*
*|  |   "0 9 * * *"     = Every day at 9:00 AM                      |  |*
*|  |   "*/5 * * * *"   = Every 5 minutes                           |  |*
*|  |   "0 0 1 * *"     = 1st of every month at midnight            |  |*
*|  |   "0 18 * * 1"    = Every Monday at 6 PM                      |  |*
*|  |   "30 8 * * 1-5"  = Mon-Fri at 8:30 AM                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3: REQUIREMENTS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  FUNCTIONAL REQUIREMENTS                                               |*
*|                                                                         |*
*|  1. JOB MANAGEMENT                                                     |*
*|     * Create one-time scheduled jobs                                  |*
*|     * Create recurring jobs (cron-based)                              |*
*|     * Cancel/pause/resume jobs                                        |*
*|     * Update job schedule                                             |*
*|     * Delete jobs                                                      |*
*|                                                                         |*
*|  2. JOB EXECUTION                                                      |*
*|     * Execute jobs at specified time                                  |*
*|     * Support job priorities                                          |*
*|     * Retry failed jobs with backoff                                  |*
*|     * Timeout handling                                                 |*
*|                                                                         |*
*|  3. OBSERVABILITY                                                      |*
*|     * View job status (pending, running, completed, failed)          |*
*|     * View execution history                                          |*
*|     * Get job logs                                                    |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  NON-FUNCTIONAL REQUIREMENTS                                           |*
*|                                                                         |*
*|  1. RELIABILITY                                                        |*
*|     * Jobs should never be lost                                       |*
*|     * At-least-once execution guarantee                              |*
*|     * Exactly-once semantics (ideally)                               |*
*|                                                                         |*
*|  2. AVAILABILITY                                                       |*
*|     * 99.99% uptime                                                   |*
*|     * No single point of failure                                     |*
*|                                                                         |*
*|  3. SCALABILITY                                                        |*
*|     * Support millions of jobs                                       |*
*|     * Handle 10,000+ job executions per second                       |*
*|                                                                         |*
*|  4. TIMELINESS                                                         |*
*|     * Jobs execute within 1-5 seconds of scheduled time              |*
*|     * Clock skew tolerance                                           |*
*|                                                                         |*
*|  5. CONSISTENCY                                                        |*
*|     * Same job should NOT run twice simultaneously                   |*
*|     * Job state should be consistent                                 |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4: SCALE ESTIMATION
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  EXAMPLE SCALE (Large Enterprise)                                      |*
*|                                                                         |*
*|  Jobs:                                                                  |*
*|  * 100 million total scheduled jobs                                   |*
*|  * 10 million recurring jobs                                          |*
*|  * 90 million one-time delayed jobs                                   |*
*|                                                                         |*
*|  Execution rate:                                                        |*
*|  * Average: 10,000 jobs/second                                        |*
*|  * Peak: 50,000 jobs/second                                           |*
*|  * 864 million job executions/day                                     |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  STORAGE                                                               |*
*|                                                                         |*
*|  Job record size:                                                       |*
*|  * job_id: 16 bytes (UUID)                                            |*
*|  * job_type: 50 bytes                                                 |*
*|  * payload: 1 KB average                                              |*
*|  * metadata: 200 bytes                                                |*
*|  * Total: ~1.3 KB per job                                            |*
*|                                                                         |*
*|  Storage needed:                                                        |*
*|  * 100M jobs × 1.3 KB = 130 GB (active jobs)                         |*
*|  * Execution history: 10× more = 1.3 TB                              |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  KEY INSIGHT                                                           |*
*|                                                                         |*
*|  The hard problem is NOT storage or compute.                          |*
*|  The hard problem is:                                                  |*
*|  1. Finding "jobs due now" efficiently (from 100M jobs)              |*
*|  2. Ensuring exactly-once execution                                   |*
*|  3. High availability without duplicate execution                    |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 5: HIGH-LEVEL ARCHITECTURE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  ARCHITECTURE OVERVIEW                                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |                        CLIENTS                                 |  |*
*|  |              (Create/Manage Jobs via API)                      |  |*
*|  |                          |                                      |  |*
*|  |                          v                                      |  |*
*|  |               +----------------------+                         |  |*
*|  |               |      API SERVICE     |                         |  |*
*|  |               |                      |                         |  |*
*|  |               |  * Create job        |                         |  |*
*|  |               |  * Cancel job        |                         |  |*
*|  |               |  * Get job status    |                         |  |*
*|  |               +----------+-----------+                         |  |*
*|  |                          |                                      |  |*
*|  |                          v                                      |  |*
*|  |               +----------------------+                         |  |*
*|  |               |     JOB STORE        |                         |  |*
*|  |               |      (MySQL)         |                         |  |*
*|  |               |                      |                         |  |*
*|  |               |  All job definitions |                         |  |*
*|  |               |  and metadata        |                         |  |*
*|  |               +----------+-----------+                         |  |*
*|  |                          |                                      |  |*
*|  |     +--------------------+--------------------+                |  |*
*|  |     |                    |                    |                |  |*
*|  |     v                    v                    v                |  |*
*|  |  +------------+   +------------+   +------------+             |  |*
*|  |  | SCHEDULER  |   | SCHEDULER  |   | SCHEDULER  |             |  |*
*|  |  |   NODE 1   |   |   NODE 2   |   |   NODE 3   |             |  |*
*|  |  |  (Leader)  |   | (Standby)  |   | (Standby)  |             |  |*
*|  |  +-----+------+   +------------+   +------------+             |  |*
*|  |        |                                                       |  |*
*|  |        | Leader finds due jobs,                               |  |*
*|  |        | enqueues to ready queue                              |  |*
*|  |        |                                                       |  |*
*|  |        v                                                       |  |*
*|  |  +----------------------------------------------------------+ |  |*
*|  |  |                    READY QUEUE                           | |  |*
*|  |  |                 (Redis / Kafka)                          | |  |*
*|  |  |                                                          | |  |*
*|  |  |  Jobs ready to be executed NOW                          | |  |*
*|  |  +-------------------------+--------------------------------+ |  |*
*|  |                            |                                  |  |*
*|  |       +--------------------+--------------------+            |  |*
*|  |       |                    |                    |            |  |*
*|  |       v                    v                    v            |  |*
*|  |  +----------+        +----------+        +----------+       |  |*
*|  |  |  WORKER  |        |  WORKER  |        |  WORKER  |       |  |*
*|  |  |  NODE 1  |        |  NODE 2  |        |  NODE N  |       |  |*
*|  |  |          |        |          |        |          |       |  |*
*|  |  | Execute  |        | Execute  |        | Execute  |       |  |*
*|  |  |  jobs    |        |  jobs    |        |  jobs    |       |  |*
*|  |  +----------+        +----------+        +----------+       |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  KEY COMPONENTS                                                        |*
*|                                                                         |*
*|  1. API SERVICE                                                        |*
*|     * Stateless, horizontally scalable                               |*
*|     * CRUD operations on jobs                                        |*
*|     * Input validation                                                |*
*|                                                                         |*
*|  2. JOB STORE (Database)                                              |*
*|     * Persistent storage of all jobs                                 |*
*|     * Source of truth for job definitions                           |*
*|     * MySQL/PostgreSQL with proper indexing                         |*
*|                                                                         |*
*|  3. SCHEDULER NODES                                                    |*
*|     * Find jobs that are due for execution                          |*
*|     * Leader election for coordination                               |*
*|     * Push ready jobs to queue                                       |*
*|                                                                         |*
*|  4. READY QUEUE                                                        |*
*|     * Hold jobs ready to execute                                     |*
*|     * Decouple scheduling from execution                            |*
*|     * Enable work distribution                                       |*
*|                                                                         |*
*|  5. WORKER NODES                                                       |*
*|     * Pull jobs from queue                                           |*
*|     * Execute job logic                                               |*
*|     * Report success/failure                                         |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 6: DATABASE DESIGN
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  CORE TABLES                                                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: jobs                                                   |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | Column          | Type          | Description            | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | job_id          | UUID (PK)     | Unique identifier      | |  |*
*|  |  | job_name        | VARCHAR(200)  | Human readable name    | |  |*
*|  |  | job_type        | VARCHAR(100)  | Handler to execute     | |  |*
*|  |  | payload         | JSON/BLOB     | Job parameters         | |  |*
*|  |  | schedule_type   | ENUM          | ONE_TIME, RECURRING    | |  |*
*|  |  | cron_expression | VARCHAR(100)  | For recurring jobs     | |  |*
*|  |  | next_run_time   | TIMESTAMP     | When to run next ⭐    | |  |*
*|  |  | status          | ENUM          | ACTIVE, PAUSED, DONE   | |  |*
*|  |  | priority        | INT           | 1-10 (higher = first)  | |  |*
*|  |  | max_retries     | INT           | Retry limit            | |  |*
*|  |  | timeout_secs    | INT           | Execution timeout      | |  |*
*|  |  | owner_id        | VARCHAR(100)  | Who created this job   | |  |*
*|  |  | created_at      | TIMESTAMP     | Creation time          | |  |*
*|  |  | updated_at      | TIMESTAMP     | Last modified          | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  CRITICAL INDEX:                                               |  |*
*|  |  CREATE INDEX idx_due_jobs ON jobs                            |  |*
*|  |      (status, next_run_time)                                  |  |*
*|  |      WHERE status = 'ACTIVE';                                 |  |*
*|  |                                                                 |  |*
*|  |  This index is CRUCIAL for "find jobs due now" query!        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: job_executions                                         |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | execution_id    | UUID (PK)     | Unique execution ID    | |  |*
*|  |  | job_id          | UUID (FK)     | Parent job             | |  |*
*|  |  | status          | ENUM          | PENDING, RUNNING,      | |  |*
*|  |  |                 |               | SUCCESS, FAILED        | |  |*
*|  |  | scheduled_time  | TIMESTAMP     | When it was supposed   | |  |*
*|  |  | started_at      | TIMESTAMP     | When execution began   | |  |*
*|  |  | completed_at    | TIMESTAMP     | When it finished       | |  |*
*|  |  | worker_id       | VARCHAR(100)  | Which worker ran it    | |  |*
*|  |  | attempt_number  | INT           | Retry attempt          | |  |*
*|  |  | error_message   | TEXT          | If failed              | |  |*
*|  |  | result          | JSON          | Output/result          | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  |  INDEXES:                                                      |  |*
*|  |  * (job_id, scheduled_time DESC) - Job history                |  |*
*|  |  * (status, started_at) - Find stuck jobs                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TABLE: job_locks (For exactly-once execution)                |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |  | job_id          | UUID (PK)     | Job being executed     | |  |*
*|  |  | execution_id    | UUID          | Current execution      | |  |*
*|  |  | locked_by       | VARCHAR(100)  | Worker holding lock    | |  |*
*|  |  | locked_at       | TIMESTAMP     | When locked            | |  |*
*|  |  | expires_at      | TIMESTAMP     | Lock expiration        | |  |*
*|  |  +-----------------+---------------+------------------------+ |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 7: FINDING DUE JOBS (The Core Problem)
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  THE CHALLENGE                                                         |*
*|                                                                         |*
*|  You have 100 million jobs. Every second, you need to find jobs       |*
*|  where next_run_time <= NOW()                                          |*
*|                                                                         |*
*|  Naive approach: SELECT * FROM jobs WHERE next_run_time <= NOW()      |*
*|  Problem: Table scan on 100M rows every second = DISASTER             |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SOLUTION 1: DATABASE POLLING WITH INDEX                              |*
*|  ------------------------------------------                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Scheduler polls database every second:                        |  |*
*|  |                                                                 |  |*
*|  |  SELECT * FROM jobs                                            |  |*
*|  |  WHERE status = 'ACTIVE'                                       |  |*
*|  |    AND next_run_time <= NOW()                                  |  |*
*|  |  ORDER BY priority DESC, next_run_time ASC                    |  |*
*|  |  LIMIT 1000                                                    |  |*
*|  |  FOR UPDATE SKIP LOCKED;  -- Critical for concurrency!        |  |*
*|  |                                                                 |  |*
*|  |  With index on (status, next_run_time), this is O(log N)      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  Pros: Simple, works well up to millions of jobs                     |*
*|  Cons: Polling overhead, database load                               |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SOLUTION 2: TIME-BUCKETED QUEUES                                     |*
*|  ------------------------------------                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Instead of one big table, partition by time:                 |  |*
*|  |                                                                 |  |*
*|  |  Redis Sorted Sets (score = execution timestamp):             |  |*
*|  |                                                                 |  |*
*|  |  jobs:bucket:2024-01-15-14  (jobs due at 2 PM hour)          |  |*
*|  |  jobs:bucket:2024-01-15-15  (jobs due at 3 PM hour)          |  |*
*|  |  jobs:bucket:2024-01-15-16  (jobs due at 4 PM hour)          |  |*
*|  |                                                                 |  |*
*|  |  To find due jobs:                                             |  |*
*|  |  ZRANGEBYSCORE jobs:bucket:2024-01-15-14 0 {now} LIMIT 100   |  |*
*|  |                                                                 |  |*
*|  |  Only query current hour's bucket = much smaller set!         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  REDIS SORTED SET STRUCTURE                                    |  |*
*|  |                                                                 |  |*
*|  |  Key: jobs:due:{bucket_id}                                    |  |*
*|  |  Score: Unix timestamp (execution time)                       |  |*
*|  |  Member: job_id                                                |  |*
*|  |                                                                 |  |*
*|  |  ZADD jobs:due:2024-01-15-14 1705320000 "job-uuid-123"       |  |*
*|  |  ZADD jobs:due:2024-01-15-14 1705320030 "job-uuid-456"       |  |*
*|  |                                                                 |  |*
*|  |  Finding due jobs (O(log N) + M where M = results):           |  |*
*|  |  ZRANGEBYSCORE jobs:due:2024-01-15-14 0 {now} LIMIT 100      |  |*
*|  |                                                                 |  |*
*|  |  Remove after processing:                                      |  |*
*|  |  ZREM jobs:due:2024-01-15-14 "job-uuid-123"                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SOLUTION 3: DELAY QUEUE (For Delayed Jobs)                          |*
*|  ------------------------------------------                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Hierarchical Timing Wheels (Used by Kafka, Netty)            |  |*
*|  |                                                                 |  |*
*|  |  Imagine a clock with buckets:                                |  |*
*|  |                                                                 |  |*
*|  |       [0] [1] [2] [3] [4] [5] ... [59]   < Seconds wheel      |  |*
*|  |              ^                                                 |  |*
*|  |           pointer                                              |  |*
*|  |                                                                 |  |*
*|  |  * Each bucket holds jobs for that second                     |  |*
*|  |  * Pointer advances every second                              |  |*
*|  |  * Jobs in current bucket are fired                           |  |*
*|  |                                                                 |  |*
*|  |  For longer delays, use multiple wheels:                      |  |*
*|  |  * Seconds wheel (60 buckets)                                 |  |*
*|  |  * Minutes wheel (60 buckets)                                 |  |*
*|  |  * Hours wheel (24 buckets)                                   |  |*
*|  |                                                                 |  |*
*|  |  Job "run in 90 minutes" goes to minutes wheel bucket 30,     |  |*
*|  |  then cascades down to seconds wheel.                         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 8: EXACTLY-ONCE EXECUTION
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  THE PROBLEM                                                           |*
*|                                                                         |*
*|  In distributed systems, failures can cause:                          |*
*|  * Job executed ZERO times (missed)                                   |*
*|  * Job executed MULTIPLE times (duplicate)                            |*
*|                                                                         |*
*|  We want: Job executed EXACTLY ONCE                                   |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SCENARIO: DUPLICATE EXECUTION                                        |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. Scheduler finds job due                                    |  |*
*|  |  2. Scheduler enqueues job to ready queue                      |  |*
*|  |  3. Scheduler CRASHES before updating next_run_time            |  |*
*|  |  4. New scheduler leader takes over                           |  |*
*|  |  5. New scheduler finds SAME job due (not updated!)           |  |*
*|  |  6. Same job enqueued AGAIN > DUPLICATE!                      |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SOLUTION: DISTRIBUTED LOCKING + IDEMPOTENCY                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  APPROACH 1: OPTIMISTIC LOCKING (Database)                    |  |*
*|  |  -------------------------------------------                    |  |*
*|  |                                                                 |  |*
*|  |  -- Atomic update with version check                          |  |*
*|  |  UPDATE jobs                                                   |  |*
*|  |  SET status = 'RUNNING',                                       |  |*
*|  |      next_run_time = {next_time},                             |  |*
*|  |      version = version + 1                                    |  |*
*|  |  WHERE job_id = 'xxx'                                          |  |*
*|  |    AND status = 'ACTIVE'                                       |  |*
*|  |    AND next_run_time <= NOW()                                 |  |*
*|  |    AND version = {current_version};                           |  |*
*|  |                                                                 |  |*
*|  |  -- If 0 rows affected > someone else got it                  |  |*
*|  |  -- If 1 row affected > we got the lock, proceed             |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  APPROACH 2: REDIS DISTRIBUTED LOCK                           |  |*
*|  |  ---------------------------------------                        |  |*
*|  |                                                                 |  |*
*|  |  Before executing job:                                         |  |*
*|  |                                                                 |  |*
*|  |  SET job_lock:{job_id}:{execution_time} {worker_id}           |  |*
*|  |      NX                    -- Only if not exists              |  |*
*|  |      EX 300                -- Expire in 5 minutes             |  |*
*|  |                                                                 |  |*
*|  |  If SET returns OK > we got the lock, execute                 |  |*
*|  |  If SET returns nil > another worker has it, skip             |  |*
*|  |                                                                 |  |*
*|  |  Key includes execution_time to allow re-execution            |  |*
*|  |  if same job is due again later.                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  APPROACH 3: DATABASE SELECT FOR UPDATE SKIP LOCKED           |  |*
*|  |  --------------------------------------------------             |  |*
*|  |                                                                 |  |*
*|  |  Multiple schedulers can poll concurrently:                   |  |*
*|  |                                                                 |  |*
*|  |  BEGIN;                                                        |  |*
*|  |                                                                 |  |*
*|  |  SELECT * FROM jobs                                            |  |*
*|  |  WHERE status = 'ACTIVE'                                       |  |*
*|  |    AND next_run_time <= NOW()                                 |  |*
*|  |  ORDER BY priority DESC                                       |  |*
*|  |  LIMIT 100                                                     |  |*
*|  |  FOR UPDATE SKIP LOCKED;  -- ⭐ Key feature!                  |  |*
*|  |                                                                 |  |*
*|  |  -- Process jobs...                                            |  |*
*|  |  UPDATE jobs SET next_run_time = ... WHERE job_id IN (...);  |  |*
*|  |                                                                 |  |*
*|  |  COMMIT;                                                       |  |*
*|  |                                                                 |  |*
*|  |  SKIP LOCKED: If a row is locked by another transaction,      |  |*
*|  |  skip it instead of waiting. Perfect for job distribution!   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  IDEMPOTENCY (Defense in Depth)                                       |*
*|                                                                         |*
*|  Even with locks, always design jobs to be IDEMPOTENT:               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  IDEMPOTENT JOB EXAMPLE:                                       |  |*
*|  |                                                                 |  |*
*|  |  // BAD: Not idempotent                                       |  |*
*|  |  def send_email_job(user_id):                                 |  |*
*|  |      send_email(user_id, "Daily digest")                     |  |*
*|  |      // If run twice, user gets 2 emails!                    |  |*
*|  |                                                                 |  |*
*|  |  // GOOD: Idempotent                                          |  |*
*|  |  def send_email_job(user_id, execution_date):                |  |*
*|  |      key = f"email_sent:{user_id}:{execution_date}"          |  |*
*|  |      if redis.get(key):                                       |  |*
*|  |          return  // Already sent, skip                        |  |*
*|  |      send_email(user_id, "Daily digest")                     |  |*
*|  |      redis.set(key, "1", ex=86400)                           |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 9: LEADER ELECTION FOR SCHEDULER
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHY LEADER ELECTION?                                                  |*
*|                                                                         |*
*|  We need multiple scheduler nodes for HA, but only ONE should         |*
*|  be actively scheduling at a time to avoid duplicates.                |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  +-----------+   +-----------+   +-----------+                |  |*
*|  |  | Scheduler |   | Scheduler |   | Scheduler |                |  |*
*|  |  |  Node 1   |   |  Node 2   |   |  Node 3   |                |  |*
*|  |  |  LEADER Y |   |  Standby  |   |  Standby  |                |  |*
*|  |  +-----+-----+   +-----+-----+   +-----+-----+                |  |*
*|  |        |               |               |                       |  |*
*|  |        +---------------+---------------+                       |  |*
*|  |                        |                                        |  |*
*|  |                        v                                        |  |*
*|  |               +-----------------+                              |  |*
*|  |               |   ZooKeeper /   |                              |  |*
*|  |               |     etcd        |                              |  |*
*|  |               |                 |                              |  |*
*|  |               | Leader election |                              |  |*
*|  |               | coordination    |                              |  |*
*|  |               +-----------------+                              |  |*
*|  |                                                                 |  |*
*|  |  If Leader crashes:                                            |  |*
*|  |  1. ZooKeeper detects (heartbeat timeout)                     |  |*
*|  |  2. Node 2 or 3 becomes new leader                            |  |*
*|  |  3. New leader starts scheduling                              |  |*
*|  |  4. Failover in ~10 seconds                                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  IMPLEMENTATION OPTIONS                                                |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  OPTION 1: ZooKeeper                                           |  |*
*|  |  ---------------------                                          |  |*
*|  |  * Create ephemeral sequential nodes                          |  |*
*|  |  * Lowest sequence number is leader                           |  |*
*|  |  * When leader dies, node disappears, next becomes leader     |  |*
*|  |                                                                 |  |*
*|  |  OPTION 2: etcd (Kubernetes uses this)                        |  |*
*|  |  -------------------------------------                          |  |*
*|  |  * Lease-based leader election                                |  |*
*|  |  * Leader holds lease, must renew periodically               |  |*
*|  |  * If lease expires, others can claim leadership             |  |*
*|  |                                                                 |  |*
*|  |  OPTION 3: Redis (Simpler but less robust)                    |  |*
*|  |  -----------------------------------------                      |  |*
*|  |  SET scheduler_leader {node_id} NX EX 30                      |  |*
*|  |  * Leader must refresh every 10 seconds                       |  |*
*|  |  * If leader dies, lock expires, another takes over          |  |*
*|  |                                                                 |  |*
*|  |  OPTION 4: Database (Simplest)                                |  |*
*|  |  -----------------------------                                  |  |*
*|  |  * Single row in "leader" table                               |  |*
*|  |  * Leader updates heartbeat every 5 seconds                   |  |*
*|  |  * If heartbeat stale > 15s, others can claim                |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  ALTERNATIVE: PARTITIONED SCHEDULING (No Leader Needed)              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Instead of leader election, partition jobs:                  |  |*
*|  |                                                                 |  |*
*|  |  Scheduler 1: Handles job_id % 3 == 0                         |  |*
*|  |  Scheduler 2: Handles job_id % 3 == 1                         |  |*
*|  |  Scheduler 3: Handles job_id % 3 == 2                         |  |*
*|  |                                                                 |  |*
*|  |  Or partition by tenant/owner:                                |  |*
*|  |  Scheduler 1: Tenant A, B                                     |  |*
*|  |  Scheduler 2: Tenant C, D                                     |  |*
*|  |  Scheduler 3: Tenant E, F                                     |  |*
*|  |                                                                 |  |*
*|  |  Benefits:                                                     |  |*
*|  |  * True parallel scheduling                                   |  |*
*|  |  * Better throughput                                          |  |*
*|  |                                                                 |  |*
*|  |  Complexity:                                                   |  |*
*|  |  * Need consistent hashing for rebalancing                   |  |*
*|  |  * Node failure requires reassignment                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 10: WORKER DESIGN
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WORKER RESPONSIBILITIES                                               |*
*|                                                                         |*
*|  1. Poll jobs from ready queue                                        |*
*|  2. Execute job logic                                                  |*
*|  3. Handle timeouts                                                    |*
*|  4. Report results (success/failure)                                  |*
*|  5. Trigger retries if needed                                         |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  WORKER FLOW                                                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  while True:                                                   |  |*
*|  |      # 1. Fetch job from queue (blocking)                     |  |*
*|  |      job = queue.pop(timeout=30)                              |  |*
*|  |      if not job:                                               |  |*
*|  |          continue                                              |  |*
*|  |                                                                 |  |*
*|  |      # 2. Acquire execution lock                              |  |*
*|  |      lock_key = f"lock:{job.id}:{job.scheduled_time}"        |  |*
*|  |      if not redis.set(lock_key, worker_id, nx=True, ex=300): |  |*
*|  |          continue  # Another worker has it                    |  |*
*|  |                                                                 |  |*
*|  |      # 3. Record execution start                              |  |*
*|  |      execution_id = create_execution_record(job, "RUNNING")  |  |*
*|  |      send_heartbeat(execution_id)  # Start heartbeat thread  |  |*
*|  |                                                                 |  |*
*|  |      try:                                                      |  |*
*|  |          # 4. Execute with timeout                            |  |*
*|  |          with timeout(job.timeout_secs):                      |  |*
*|  |              result = execute_job(job)                        |  |*
*|  |                                                                 |  |*
*|  |          # 5. Mark success                                    |  |*
*|  |          update_execution(execution_id, "SUCCESS", result)   |  |*
*|  |                                                                 |  |*
*|  |      except TimeoutError:                                      |  |*
*|  |          update_execution(execution_id, "TIMEOUT")           |  |*
*|  |          maybe_retry(job)                                     |  |*
*|  |                                                                 |  |*
*|  |      except Exception as e:                                   |  |*
*|  |          update_execution(execution_id, "FAILED", error=e)   |  |*
*|  |          maybe_retry(job)                                     |  |*
*|  |                                                                 |  |*
*|  |      finally:                                                  |  |*
*|  |          redis.delete(lock_key)                               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  HEARTBEAT MECHANISM                                                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Problem: Worker crashes mid-execution. Job stuck as RUNNING. |  |*
*|  |                                                                 |  |*
*|  |  Solution: Heartbeat + timeout detection                      |  |*
*|  |                                                                 |  |*
*|  |  Worker:                                                       |  |*
*|  |  * Update execution heartbeat every 10 seconds               |  |*
*|  |  * Redis: SET worker_heartbeat:{execution_id} {timestamp}    |  |*
*|  |                                                                 |  |*
*|  |  Monitor process:                                              |  |*
*|  |  * Check for stuck executions:                                |  |*
*|  |    SELECT * FROM job_executions                               |  |*
*|  |    WHERE status = 'RUNNING'                                   |  |*
*|  |      AND heartbeat < NOW() - INTERVAL 30 SECONDS;            |  |*
*|  |                                                                 |  |*
*|  |  * Mark as FAILED, trigger retry                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  RETRY STRATEGY                                                        |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Exponential backoff with jitter:                              |  |*
*|  |                                                                 |  |*
*|  |  def calculate_retry_delay(attempt):                          |  |*
*|  |      base_delay = 60  # 1 minute                              |  |*
*|  |      max_delay = 3600  # 1 hour                               |  |*
*|  |                                                                 |  |*
*|  |      delay = min(base_delay * (2 ** attempt), max_delay)     |  |*
*|  |      jitter = random.uniform(0, delay * 0.1)                  |  |*
*|  |      return delay + jitter                                    |  |*
*|  |                                                                 |  |*
*|  |  Attempt 1: ~1 min                                            |  |*
*|  |  Attempt 2: ~2 min                                            |  |*
*|  |  Attempt 3: ~4 min                                            |  |*
*|  |  Attempt 4: ~8 min                                            |  |*
*|  |  ...                                                           |  |*
*|  |  Attempt N: capped at 1 hour                                  |  |*
*|  |                                                                 |  |*
*|  |  After max_retries: Mark job as FAILED_PERMANENT              |  |*
*|  |  > Alert, move to dead letter queue                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  CONCURRENT TASK PROCESSING                                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  WORKER ARCHITECTURE                                           |  |*
*|  |                                                                 |  |*
*|  |  Each worker node runs MULTIPLE threads/goroutines/processes  |  |*
*|  |  to process jobs concurrently:                                |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                     WORKER NODE                           ||  |*
*|  |  |                                                           ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |  |              THREAD POOL (N threads)                | ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  |  +---------+ +---------+ +---------+ +---------+  | ||  |*
*|  |  |  |  |Thread 1 | |Thread 2 | |Thread 3 | |Thread N |  | ||  |*
*|  |  |  |  |         | |         | |         | |         |  | ||  |*
*|  |  |  |  | Job A   | | Job B   | | Job C   | |  Idle   |  | ||  |*
*|  |  |  |  |(running)| |(running)| |(running)| |(waiting)|  | ||  |*
*|  |  |  |  +---------+ +---------+ +---------+ +---------+  | ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |                          ^                                ||  |*
*|  |  |                          | fetch jobs                    ||  |*
*|  |  |                          |                                ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |  |           LOCAL JOB QUEUE (bounded)                 | ||  |*
*|  |  |  |           [job_x] [job_y] [job_z] ...               | ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |                          ^                                ||  |*
*|  |  |                          | batch fetch                   ||  |*
*|  |  |                          |                                ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                             |                                  |  |*
*|  |                             |                                  |  |*
*|  |             +---------------+---------------+                 |  |*
*|  |             |        READY QUEUE            |                 |  |*
*|  |             |     (Redis / Kafka)           |                 |  |*
*|  |             +-------------------------------+                 |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CONCURRENCY CONFIGURATION                                     |  |*
*|  |                                                                 |  |*
*|  |  class WorkerConfig:                                           |  |*
*|  |      concurrency = 10        # Threads per worker node        |  |*
*|  |      prefetch_count = 20     # Jobs to buffer locally         |  |*
*|  |      poll_interval = 100     # ms between queue polls         |  |*
*|  |                                                                 |  |*
*|  |  Tuning:                                                       |  |*
*|  |  * CPU-bound jobs: concurrency = num_cores                    |  |*
*|  |  * I/O-bound jobs: concurrency = num_cores × 2-4              |  |*
*|  |  * Mixed workload: concurrency = num_cores × 2                |  |*
*|  |                                                                 |  |*
*|  |  Example:                                                       |  |*
*|  |  * 8-core machine with I/O-bound jobs                        |  |*
*|  |  * concurrency = 8 × 4 = 32 concurrent jobs                  |  |*
*|  |  * 10 worker nodes = 320 concurrent jobs cluster-wide        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CONCURRENT WORKER PSEUDOCODE                                  |  |*
*|  |                                                                 |  |*
*|  |  class Worker:                                                 |  |*
*|  |      def __init__(self, concurrency=10):                      |  |*
*|  |          self.concurrency = concurrency                       |  |*
*|  |          self.semaphore = Semaphore(concurrency)             |  |*
*|  |          self.executor = ThreadPoolExecutor(concurrency)     |  |*
*|  |                                                                 |  |*
*|  |      def run(self):                                           |  |*
*|  |          while True:                                          |  |*
*|  |              # Wait for available slot                        |  |*
*|  |              self.semaphore.acquire()                        |  |*
*|  |                                                                 |  |*
*|  |              # Fetch job (blocking)                           |  |*
*|  |              job = self.queue.pop(timeout=30)                |  |*
*|  |              if not job:                                      |  |*
*|  |                  self.semaphore.release()                    |  |*
*|  |                  continue                                     |  |*
*|  |                                                                 |  |*
*|  |              # Process in thread pool                         |  |*
*|  |              self.executor.submit(                           |  |*
*|  |                  self.process_job,                           |  |*
*|  |                  job,                                         |  |*
*|  |                  callback=self.on_complete                   |  |*
*|  |              )                                                 |  |*
*|  |                                                                 |  |*
*|  |      def process_job(self, job):                              |  |*
*|  |          try:                                                  |  |*
*|  |              with timeout(job.timeout):                       |  |*
*|  |                  handler = get_handler(job.job_type)         |  |*
*|  |                  result = handler.execute(job.payload)       |  |*
*|  |              return ("SUCCESS", result)                       |  |*
*|  |          except Exception as e:                               |  |*
*|  |              return ("FAILED", str(e))                       |  |*
*|  |                                                                 |  |*
*|  |      def on_complete(self, future):                          |  |*
*|  |          status, result = future.result()                    |  |*
*|  |          # Update execution record...                        |  |*
*|  |          self.semaphore.release()  # Free slot for next job |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  WORK DISTRIBUTION ACROSS WORKERS                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Multiple worker nodes compete for jobs from shared queue:    |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                     READY QUEUE                           ||  |*
*|  |  |  [J1] [J2] [J3] [J4] [J5] [J6] [J7] [J8] [J9] [J10]...   ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |            |              |              |                     |  |*
*|  |            | pop          | pop          | pop                 |  |*
*|  |            v              v              v                     |  |*
*|  |       +---------+   +---------+   +---------+                 |  |*
*|  |       |Worker 1 |   |Worker 2 |   |Worker 3 |                 |  |*
*|  |       |         |   |         |   |         |                 |  |*
*|  |       | J1, J4  |   | J2, J5  |   | J3, J6  |                 |  |*
*|  |       |(10 slots|   |(10 slots|   |(10 slots|                 |  |*
*|  |       | 2 used) |   | 2 used) |   | 2 used) |                 |  |*
*|  |       +---------+   +---------+   +---------+                 |  |*
*|  |                                                                 |  |*
*|  |  Naturally load-balanced:                                     |  |*
*|  |  * Faster workers finish jobs > fetch more jobs              |  |*
*|  |  * Slower/busier workers naturally get fewer jobs            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  BACK PRESSURE HANDLING                                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Problem: Queue fills up faster than workers can process      |  |*
*|  |                                                                 |  |*
*|  |  Solutions:                                                    |  |*
*|  |                                                                 |  |*
*|  |  1. BOUNDED QUEUES                                            |  |*
*|  |     * Set max queue size (e.g., 100,000 jobs)                |  |*
*|  |     * Reject new jobs with HTTP 429 when full               |  |*
*|  |     * Client retries with backoff                            |  |*
*|  |                                                                 |  |*
*|  |  2. AUTO-SCALING WORKERS                                      |  |*
*|  |     * Monitor queue depth                                     |  |*
*|  |     * If depth > threshold > spin up more workers           |  |*
*|  |     * If depth < threshold > scale down                     |  |*
*|  |                                                                 |  |*
*|  |     if queue_depth > 10000 and workers < max_workers:        |  |*
*|  |         scale_up_workers(count=2)                            |  |*
*|  |     if queue_depth < 100 and workers > min_workers:          |  |*
*|  |         scale_down_workers(count=1)                          |  |*
*|  |                                                                 |  |*
*|  |  3. PRIORITY QUEUES                                           |  |*
*|  |     * High priority jobs processed first                     |  |*
*|  |     * Low priority jobs may be delayed during load          |  |*
*|  |                                                                 |  |*
*|  |  4. RATE LIMITING JOB SUBMISSION                              |  |*
*|  |     * Limit jobs/second per client                           |  |*
*|  |     * Prevents single client from flooding queue            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  WORK STEALING (Advanced)                                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Problem: Some workers finish fast, sit idle while others    |  |*
*|  |           are overloaded (especially with local queues)       |  |*
*|  |                                                                 |  |*
*|  |  Solution: Idle workers "steal" jobs from busy workers       |  |*
*|  |                                                                 |  |*
*|  |  +---------+           +---------+           +---------+     |  |*
*|  |  |Worker 1 |           |Worker 2 |           |Worker 3 |     |  |*
*|  |  |         |           |         |           |         |     |  |*
*|  |  | Local Q |  steal    | Local Q |           | Local Q |     |  |*
*|  |  | [    ]  | <-------- | [J J J] |           | [J    ] |     |  |*
*|  |  | (empty) |           | (busy)  |           |         |     |  |*
*|  |  +---------+           +---------+           +---------+     |  |*
*|  |                                                                 |  |*
*|  |  Worker 1 is idle > looks at other workers' queues           |  |*
*|  |  Worker 2 has jobs > Worker 1 steals one                     |  |*
*|  |                                                                 |  |*
*|  |  Implementation:                                               |  |*
*|  |  * Each worker exposes local queue via RPC/Redis             |  |*
*|  |  * Idle worker randomly picks another worker                 |  |*
*|  |  * Tries to steal from back of their queue                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  JOB ISOLATION                                                         |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Problem: One bad job shouldn't affect others                 |  |*
*|  |                                                                 |  |*
*|  |  Solutions:                                                    |  |*
*|  |                                                                 |  |*
*|  |  1. PROCESS-BASED ISOLATION                                   |  |*
*|  |     * Each job runs in separate process                      |  |*
*|  |     * Process crash doesn't affect worker                    |  |*
*|  |     * Higher overhead but safer                               |  |*
*|  |                                                                 |  |*
*|  |  2. THREAD-BASED (Less isolated, more efficient)             |  |*
*|  |     * Jobs share process memory                              |  |*
*|  |     * One crash can affect others                            |  |*
*|  |     * Use for trusted job code                                |  |*
*|  |                                                                 |  |*
*|  |  3. CONTAINER-BASED (Maximum isolation)                       |  |*
*|  |     * Each job in separate container                         |  |*
*|  |     * Full resource isolation                                 |  |*
*|  |     * Used by Kubernetes Jobs                                |  |*
*|  |                                                                 |  |*
*|  |  4. RESOURCE LIMITS                                           |  |*
*|  |     * CPU limit per job                                       |  |*
*|  |     * Memory limit per job                                   |  |*
*|  |     * Timeout enforcement                                     |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 11: RECURRING JOB HANDLING
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  CRON JOB EXECUTION CYCLE                                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Job: "Send daily report at 9 AM"                             |  |*
*|  |  Cron: "0 9 * * *"                                             |  |*
*|  |                                                                 |  |*
*|  |  1. Job created with next_run_time = Jan 15, 9:00 AM          |  |*
*|  |                                                                 |  |*
*|  |  2. Jan 15, 9:00 AM: Scheduler finds job due                  |  |*
*|  |     * Enqueues to ready queue                                 |  |*
*|  |     * Calculates NEXT run time from cron expression          |  |*
*|  |     * Updates next_run_time = Jan 16, 9:00 AM                |  |*
*|  |                                                                 |  |*
*|  |  3. Worker executes job                                        |  |*
*|  |                                                                 |  |*
*|  |  4. Jan 16, 9:00 AM: Same cycle repeats                       |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  CRON NEXT TIME CALCULATION:                                  |  |*
*|  |                                                                 |  |*
*|  |  def get_next_run_time(cron_expr, from_time):                 |  |*
*|  |      # Use library like croniter (Python)                     |  |*
*|  |      cron = croniter(cron_expr, from_time)                   |  |*
*|  |      return cron.get_next(datetime)                          |  |*
*|  |                                                                 |  |*
*|  |  # Example                                                     |  |*
*|  |  get_next_run_time("0 9 * * *", datetime(2024, 1, 15, 9, 0)) |  |*
*|  |  # Returns: datetime(2024, 1, 16, 9, 0)                       |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  HANDLING MISSED EXECUTIONS                                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Scenario: Scheduler was down from 8 AM to 11 AM               |  |*
*|  |  Job was due at 9 AM but missed                               |  |*
*|  |                                                                 |  |*
*|  |  Options (configurable per job):                               |  |*
*|  |                                                                 |  |*
*|  |  1. SKIP_MISSED (default)                                     |  |*
*|  |     * Don't run missed executions                             |  |*
*|  |     * Just schedule next future run                           |  |*
*|  |     * Good for: Reports where latest is enough               |  |*
*|  |                                                                 |  |*
*|  |  2. RUN_ONCE                                                   |  |*
*|  |     * Run once immediately for all missed                     |  |*
*|  |     * Then schedule next future run                           |  |*
*|  |     * Good for: Critical jobs that must run                  |  |*
*|  |                                                                 |  |*
*|  |  3. RUN_ALL                                                    |  |*
*|  |     * Run once for each missed occurrence                     |  |*
*|  |     * Good for: Time-series data collection                  |  |*
*|  |     * Dangerous: Could flood system after outage             |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 12: API DESIGN
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  REST API                                                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CREATE ONE-TIME JOB                                           |  |*
*|  |  ----------------------                                         |  |*
*|  |  POST /api/jobs                                                 |  |*
*|  |  {                                                              |  |*
*|  |    "name": "send-reminder-email",                              |  |*
*|  |    "job_type": "EMAIL_SENDER",                                 |  |*
*|  |    "schedule_type": "ONE_TIME",                                |  |*
*|  |    "execute_at": "2024-01-16T09:00:00Z",                      |  |*
*|  |    "payload": {                                                 |  |*
*|  |      "user_id": "123",                                        |  |*
*|  |      "template": "reminder"                                   |  |*
*|  |    },                                                           |  |*
*|  |    "priority": 5,                                              |  |*
*|  |    "max_retries": 3,                                           |  |*
*|  |    "timeout_secs": 60                                          |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  Response: { "job_id": "uuid-xxx", "status": "ACTIVE" }       |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  CREATE RECURRING JOB                                          |  |*
*|  |  ------------------------                                       |  |*
*|  |  POST /api/jobs                                                 |  |*
*|  |  {                                                              |  |*
*|  |    "name": "daily-report",                                     |  |*
*|  |    "job_type": "REPORT_GENERATOR",                            |  |*
*|  |    "schedule_type": "RECURRING",                               |  |*
*|  |    "cron_expression": "0 9 * * *",                            |  |*
*|  |    "timezone": "America/New_York",                            |  |*
*|  |    "payload": { "report_type": "daily_summary" },             |  |*
*|  |    "priority": 7                                               |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  GET JOB STATUS                                                |  |*
*|  |  ----------------                                               |  |*
*|  |  GET /api/jobs/{job_id}                                        |  |*
*|  |                                                                 |  |*
*|  |  Response:                                                      |  |*
*|  |  {                                                              |  |*
*|  |    "job_id": "uuid-xxx",                                       |  |*
*|  |    "name": "daily-report",                                     |  |*
*|  |    "status": "ACTIVE",                                         |  |*
*|  |    "next_run_time": "2024-01-16T09:00:00Z",                   |  |*
*|  |    "last_execution": {                                        |  |*
*|  |      "execution_id": "exec-yyy",                              |  |*
*|  |      "status": "SUCCESS",                                     |  |*
*|  |      "completed_at": "2024-01-15T09:00:05Z"                  |  |*
*|  |    }                                                           |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  GET EXECUTION HISTORY                                         |  |*
*|  |  ------------------------                                       |  |*
*|  |  GET /api/jobs/{job_id}/executions?limit=10                   |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  PAUSE/RESUME JOB                                              |  |*
*|  |  -----------------                                              |  |*
*|  |  POST /api/jobs/{job_id}/pause                                |  |*
*|  |  POST /api/jobs/{job_id}/resume                               |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  DELETE JOB                                                    |  |*
*|  |  ------------                                                   |  |*
*|  |  DELETE /api/jobs/{job_id}                                    |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  TRIGGER JOB MANUALLY                                          |  |*
*|  |  ---------------------                                          |  |*
*|  |  POST /api/jobs/{job_id}/trigger                              |  |*
*|  |  (Execute immediately regardless of schedule)                 |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 13: INTERVIEW QUICK REFERENCE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  KEY TALKING POINTS                                                    |*
*|                                                                         |*
*|  1. JOB TYPES                                                          |*
*|     * One-time (delayed): Execute once at future time                |*
*|     * Recurring (cron): Execute on schedule repeatedly               |*
*|                                                                         |*
*|  2. FINDING DUE JOBS                                                   |*
*|     * Database with index on (status, next_run_time)                 |*
*|     * Redis sorted sets with timestamp as score                      |*
*|     * Time-bucketed queues for partitioning                          |*
*|                                                                         |*
*|  3. EXACTLY-ONCE EXECUTION                                            |*
*|     * Distributed locks (Redis SETNX or database row lock)           |*
*|     * SELECT FOR UPDATE SKIP LOCKED                                  |*
*|     * Idempotency in job handlers as defense                         |*
*|                                                                         |*
*|  4. HIGH AVAILABILITY                                                  |*
*|     * Multiple scheduler nodes with leader election                  |*
*|     * Or partitioned scheduling (no leader needed)                   |*
*|     * Workers are stateless, easily replaceable                     |*
*|                                                                         |*
*|  5. RELIABILITY                                                        |*
*|     * Heartbeat + stuck job detection                                |*
*|     * Retry with exponential backoff                                 |*
*|     * Dead letter queue for permanently failed                       |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  COMMON INTERVIEW QUESTIONS                                           |*
*|                                                                         |*
*|  Q: How do you ensure a job runs exactly once?                       |*
*|  A: Distributed lock before execution (Redis SET NX or DB lock).     |*
*|     Lock key includes job_id AND scheduled_time. If lock fails,     |*
*|     skip (another worker has it). Jobs should also be idempotent.   |*
*|                                                                         |*
*|  Q: How do you handle scheduler node failure?                        |*
*|  A: Leader election with ZooKeeper/etcd/Redis. Standby nodes        |*
*|     detect leader failure and elect new leader. Jobs continue       |*
*|     after brief failover (~10 seconds).                              |*
*|                                                                         |*
*|  Q: How do you scale to millions of jobs?                            |*
*|  A: Efficient indexing (B-tree on next_run_time). Time-bucketed     |*
*|     queues to partition by time. Partitioned scheduling where       |*
*|     different schedulers handle different job subsets.               |*
*|                                                                         |*
*|  Q: What if a worker crashes during execution?                       |*
*|  A: Heartbeat mechanism. Worker updates heartbeat every 10s.        |*
*|     Monitor process detects stale heartbeats, marks job FAILED,     |*
*|     and triggers retry.                                               |*
*|                                                                         |*
*|  Q: How do you handle jobs that take too long?                       |*
*|  A: Per-job timeout configuration. Worker kills job after timeout.  |*
*|     Mark as TIMEOUT, trigger retry with longer timeout if needed.   |*
*|                                                                         |*
*|  Q: How do you prioritize jobs?                                      |*
*|  A: Priority field on job. Ready queue uses priority queue          |*
*|     (Redis sorted set with priority+timestamp as score).            |*
*|     Higher priority jobs dequeued first.                             |*
*|                                                                         |*
*|  Q: What happens if scheduler is down for an hour?                   |*
*|  A: Configurable per job: SKIP_MISSED (just schedule next),         |*
*|     RUN_ONCE (run immediately once), RUN_ALL (run all missed).     |*
*|     Default: SKIP_MISSED.                                            |*
*|                                                                         |*
*|  Q: How do you handle timezone for cron jobs?                        |*
*|  A: Store timezone with job. Convert cron to UTC for storage.       |*
*|     next_run_time always in UTC. Handle DST transitions.            |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  ARCHITECTURE SUMMARY                                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Client > API > Job Store (MySQL)                             |  |*
*|  |                      v                                         |  |*
*|  |            Scheduler (Leader Election)                        |  |*
*|  |                      v                                         |  |*
*|  |            Ready Queue (Redis/Kafka)                          |  |*
*|  |                      v                                         |  |*
*|  |            Workers (Execute + Report)                         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  Key Components:                                                       |*
*|  * Job Store: MySQL with proper indexes                              |*
*|  * Scheduler: Leader-elected or partitioned                         |*
*|  * Ready Queue: Redis sorted set or Kafka                           |*
*|  * Workers: Stateless, horizontally scalable                        |*
*|  * Coordination: ZooKeeper/etcd for leader election                 |*
*|                                                                         |*
*|  Key Numbers:                                                          |*
*|  * 100M jobs, 10K executions/second                                  |*
*|  * Index lookup: O(log N)                                            |*
*|  * Lock acquisition: O(1)                                            |*
*|  * Failover time: ~10 seconds                                        |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

ARCHITECTURE DIAGRAM
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|                          +-------------+                               |*
*|                          |   CLIENTS   |                               |*
*|                          +------+------+                               |*
*|                                 |                                       |*
*|                                 v                                       |*
*|                          +-------------+                               |*
*|                          | API SERVICE |                               |*
*|                          +------+------+                               |*
*|                                 |                                       |*
*|                                 v                                       |*
*|                          +-------------+                               |*
*|                          |  JOB STORE  |                               |*
*|                          |   (MySQL)   |                               |*
*|                          +------+------+                               |*
*|                                 |                                       |*
*|            +--------------------+--------------------+                 |*
*|            v                    v                    v                 |*
*|     +------------+       +------------+       +------------+         |*
*|     | SCHEDULER  |       | SCHEDULER  |       | SCHEDULER  |         |*
*|     |   NODE 1   |       |   NODE 2   |       |   NODE 3   |         |*
*|     |  (Leader)  |       | (Standby)  |       | (Standby)  |         |*
*|     +-----+------+       +------------+       +------------+         |*
*|           |                                                           |*
*|           |   Leader Election via                                    |*
*|           |   +-----------------+                                    |*
*|           |   | ZooKeeper/etcd  |                                    |*
*|           |   +-----------------+                                    |*
*|           |                                                           |*
*|           v                                                           |*
*|     +----------------------------------------------------------+    |*
*|     |                    READY QUEUE                           |    |*
*|     |                   (Redis / Kafka)                        |    |*
*|     +-------------------------+--------------------------------+    |*
*|                               |                                      |*
*|          +--------------------+--------------------+                |*
*|          v                    v                    v                |*
*|    +----------+        +----------+        +----------+            |*
*|    |  WORKER  |        |  WORKER  |        |  WORKER  |            |*
*|    |  NODE 1  |        |  NODE 2  |        |  NODE N  |            |*
*|    +----------+        +----------+        +----------+            |*
*|                                                                      |*
*+-------------------------------------------------------------------------+*

END OF DISTRIBUTED JOB SCHEDULER SYSTEM DESIGN
