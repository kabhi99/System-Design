================================================================================
                    KUBERNETES JOBS & CRONJOBS
                    Chapter 10: Batch and Scheduled Workloads
================================================================================

Jobs run tasks to completion. CronJobs run Jobs on a schedule.


================================================================================
SECTION 10.1: WHY JOBS? (Deployment vs Job)
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  THE PROBLEM: NOT ALL WORKLOADS RUN FOREVER                           │
    │  ════════════════════════════════════════════                           │
    │                                                                         │
    │  Deployments are designed for LONG-RUNNING services:                  │
    │  • Web servers (run forever, handle requests)                         │
    │  • APIs (always listening)                                            │
    │  • Databases (always available)                                       │
    │                                                                         │
    │  But some tasks should RUN ONCE AND EXIT:                             │
    │  • Database migration                                                  │
    │  • Batch data processing                                               │
    │  • Sending email campaign                                              │
    │  • Generating reports                                                  │
    │  • Cleanup old data                                                    │
    │                                                                         │
    │  ─────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  WHAT HAPPENS IF YOU USE DEPLOYMENT FOR BATCH TASK?                   │
    │                                                                         │
    │  kind: Deployment                  # WRONG for batch tasks!           │
    │  spec:                                                                 │
    │    replicas: 1                                                        │
    │    template:                                                           │
    │      spec:                                                             │
    │        containers:                                                     │
    │          - name: migrate                                              │
    │            command: ["python", "migrate.py"]                         │
    │            # Script finishes → container exits → pod "completes"     │
    │                                                                         │
    │  PROBLEM: Deployment sees pod "failed" and RESTARTS IT!              │
    │                                                                         │
    │  migrate.py finishes → pod exits → Deployment: "Pod died! Restart!"  │
    │  migrate.py runs AGAIN → exits → "Pod died! Restart!"                │
    │  ... INFINITE LOOP!                                                    │
    │                                                                         │
    │  SOLUTION: Use Job!                                                    │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  DEPLOYMENT vs JOB vs CRONJOB                                          │
    │  ═════════════════════════════                                          │
    │                                                                         │
    │  ┌────────────────┬────────────────────┬────────────────────────────┐  │
    │  │ Workload       │ Use For            │ Behavior                   │  │
    │  ├────────────────┼────────────────────┼────────────────────────────┤  │
    │  │ Deployment     │ Long-running       │ Keeps pods RUNNING         │  │
    │  │                │ services           │ Restarts if they exit      │  │
    │  │                │ (web, API, DB)     │                            │  │
    │  ├────────────────┼────────────────────┼────────────────────────────┤  │
    │  │ Job            │ Run-to-completion  │ Runs until SUCCESS         │  │
    │  │                │ tasks              │ Does NOT restart on        │  │
    │  │                │ (migration, batch) │ successful exit            │  │
    │  ├────────────────┼────────────────────┼────────────────────────────┤  │
    │  │ CronJob        │ Scheduled tasks    │ Creates Jobs on schedule   │  │
    │  │                │ (daily backup,     │ Like cron on Linux         │  │
    │  │                │  hourly cleanup)   │                            │  │
    │  └────────────────┴────────────────────┴────────────────────────────┘  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  REAL-WORLD JOB USE CASES                                             │
    │  ═════════════════════════                                              │
    │                                                                         │
    │  1. DATABASE MIGRATIONS                                                │
    │     • Run before deploying new app version                            │
    │     • ALTER TABLE, CREATE INDEX                                       │
    │     • Must complete successfully before app starts                    │
    │                                                                         │
    │  2. BATCH DATA PROCESSING                                             │
    │     • Process CSV file uploaded by user                              │
    │     • ETL (Extract, Transform, Load)                                 │
    │     • Generate reports from database                                  │
    │                                                                         │
    │  3. MACHINE LEARNING TRAINING                                         │
    │     • Train model on dataset                                          │
    │     • Long-running but finite task                                   │
    │     • Needs retries on failure                                       │
    │                                                                         │
    │  4. SENDING NOTIFICATIONS                                             │
    │     • Send email to all users                                        │
    │     • Push notification campaign                                     │
    │     • Can be parallelized                                            │
    │                                                                         │
    │  5. CLEANUP TASKS                                                      │
    │     • Delete old records                                              │
    │     • Archive logs                                                    │
    │     • Purge temp files                                               │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CRONJOB USE CASES                                                     │
    │  ══════════════════                                                    │
    │                                                                         │
    │  1. SCHEDULED BACKUPS                                                  │
    │     • Daily database backup at 2 AM                                  │
    │     • Weekly full backup                                             │
    │                                                                         │
    │  2. PERIODIC CLEANUP                                                   │
    │     • Delete old sessions every hour                                 │
    │     • Clean temp files daily                                         │
    │     • Archive old logs weekly                                        │
    │                                                                         │
    │  3. REPORT GENERATION                                                  │
    │     • Daily sales report at 6 AM                                     │
    │     • Monthly analytics report                                       │
    │                                                                         │
    │  4. DATA SYNC                                                          │
    │     • Sync data from external API every 15 min                       │
    │     • Update cache periodically                                      │
    │                                                                         │
    │  5. HEALTH CHECKS / MONITORING                                        │
    │     • Check external services every 5 min                            │
    │     • Alert if something is down                                     │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 10.2: JOB BASICS
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  BASIC JOB                                                             │
    │  ═════════                                                              │
    │                                                                         │
    │  apiVersion: batch/v1                                                  │
    │  kind: Job                                                              │
    │  metadata:                                                              │
    │    name: process-data                                                  │
    │  spec:                                                                  │
    │    template:                                                            │
    │      spec:                                                              │
    │        containers:                                                      │
    │          - name: processor                                             │
    │            image: my-processor:latest                                 │
    │            command: ["python", "process.py"]                          │
    │        restartPolicy: Never   # or OnFailure                         │
    │    backoffLimit: 4            # Max retries                          │
    │                                                                         │
    │  ─────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  PARALLEL JOBS                                                         │
    │  ══════════════                                                        │
    │                                                                         │
    │  spec:                                                                  │
    │    completions: 10     # Total successful completions needed         │
    │    parallelism: 3      # Run 3 pods at a time                        │
    │    template:                                                            │
    │      spec:                                                              │
    │        containers:                                                      │
    │          - name: worker                                                │
    │            image: my-worker                                            │
    │        restartPolicy: Never                                            │
    │                                                                         │
    │  ─────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  JOB PARAMETERS                                                        │
    │                                                                         │
    │  • completions: How many pods must succeed                           │
    │  • parallelism: Max concurrent pods                                  │
    │  • backoffLimit: Max retries before giving up                       │
    │  • activeDeadlineSeconds: Timeout                                    │
    │  • ttlSecondsAfterFinished: Auto-cleanup                            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 10.2: CRONJOBS
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CRONJOB DEFINITION                                                    │
    │  ═══════════════════                                                    │
    │                                                                         │
    │  apiVersion: batch/v1                                                  │
    │  kind: CronJob                                                          │
    │  metadata:                                                              │
    │    name: daily-backup                                                  │
    │  spec:                                                                  │
    │    schedule: "0 2 * * *"     # 2 AM daily                            │
    │    jobTemplate:                                                         │
    │      spec:                                                              │
    │        template:                                                        │
    │          spec:                                                          │
    │            containers:                                                  │
    │              - name: backup                                            │
    │                image: backup-tool                                     │
    │                command: ["./backup.sh"]                               │
    │            restartPolicy: OnFailure                                   │
    │    successfulJobsHistoryLimit: 3                                      │
    │    failedJobsHistoryLimit: 1                                          │
    │    concurrencyPolicy: Forbid                                          │
    │                                                                         │
    │  ─────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  CRON SCHEDULE FORMAT                                                  │
    │  ═════════════════════                                                  │
    │                                                                         │
    │  ┌───────────── minute (0-59)                                         │
    │  │ ┌───────────── hour (0-23)                                        │
    │  │ │ ┌───────────── day of month (1-31)                             │
    │  │ │ │ ┌───────────── month (1-12)                                  │
    │  │ │ │ │ ┌───────────── day of week (0-6, Sun=0)                   │
    │  │ │ │ │ │                                                           │
    │  * * * * *                                                             │
    │                                                                         │
    │  EXAMPLES:                                                             │
    │  "*/15 * * * *"    Every 15 minutes                                  │
    │  "0 * * * *"       Every hour                                        │
    │  "0 2 * * *"       Daily at 2 AM                                     │
    │  "0 0 * * 0"       Weekly on Sunday                                  │
    │  "0 0 1 * *"       Monthly on 1st                                    │
    │                                                                         │
    │  ─────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  CONCURRENCY POLICY                                                    │
    │  ═══════════════════                                                    │
    │                                                                         │
    │  • Allow: Multiple jobs can run concurrently                         │
    │  • Forbid: Skip new job if previous still running                   │
    │  • Replace: Cancel running job, start new                           │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 10.3: COMMANDS
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  # List jobs                                                           │
    │  kubectl get jobs                                                       │
    │  kubectl get cronjobs                                                   │
    │                                                                         │
    │  # Watch job progress                                                  │
    │  kubectl get jobs -w                                                   │
    │                                                                         │
    │  # View job logs                                                       │
    │  kubectl logs job/process-data                                        │
    │                                                                         │
    │  # Manually trigger CronJob                                           │
    │  kubectl create job --from=cronjob/daily-backup manual-backup        │
    │                                                                         │
    │  # Delete job                                                          │
    │  kubectl delete job process-data                                      │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
CHAPTER SUMMARY
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  JOBS & CRONJOBS - KEY TAKEAWAYS                                      │
    │                                                                         │
    │  JOBS                                                                  │
    │  ────                                                                  │
    │  • Run to completion (not continuously)                              │
    │  • Can run parallel pods                                             │
    │  • Retry on failure (backoffLimit)                                  │
    │                                                                         │
    │  CRONJOBS                                                              │
    │  ────────                                                              │
    │  • Scheduled Jobs                                                     │
    │  • Cron syntax (min hour day month weekday)                         │
    │  • concurrencyPolicy controls overlap                                │
    │                                                                         │
    │  USE CASES                                                             │
    │  ─────────                                                             │
    │  • Data processing                                                    │
    │  • Backups                                                            │
    │  • Reports                                                            │
    │  • Cleanup tasks                                                      │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
                              END OF CHAPTER 10
================================================================================

