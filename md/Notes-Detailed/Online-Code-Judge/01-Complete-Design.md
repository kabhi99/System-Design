# ONLINE CODE JUDGE SYSTEM DESIGN (LEETCODE / HACKERRANK)

*Complete Design: Requirements, Architecture, and Interview Guide*

## SECTION 1: UNDERSTANDING THE PROBLEM

### WHAT IS AN ONLINE CODE JUDGE

```
+-------------------------------------------------------------------------+
| an online code judge (OJ) is a platform that allows users to write      |
| code solutions to programming problems, submit them, and receive        |
| automated verdicts on correctness and efficiency.                       |
|                                                                         |
| core workflow:                                                          |
|                                                                         |
| 1. user reads a problem statement with constraints                      |
| 2. user writes code in their preferred language                         |
| 3. user submits the solution                                            |
| 4. system compiles the code (if applicable)                             |
| 5. system runs the code against hidden test cases                       |
| 6. system compares output against expected answers                      |
| 7. system returns a verdict (accepted, wrong answer, etc.)              |
|                                                                         |
| the critical challenge is executing untrusted user code safely          |
| and efficiently while providing fast, accurate feedback.                |
+-------------------------------------------------------------------------+
```

### KEY CONCEPTS

```
+-------------------------------------------------------------------------+
| verdicts returned by the judge:                                         |
|                                                                         |
| * AC  (accepted): output matches expected for all test cases            |
| * WA  (wrong answer): output differs from expected on some case         |
| * TLE (time limit exceeded): code ran longer than allowed time          |
| * MLE (memory limit exceeded): code used more memory than allowed       |
| * RE  (runtime error): code crashed (segfault, exception, etc.)         |
| * CE  (compilation error): code failed to compile                       |
|                                                                         |
| problem difficulty tiers:                                               |
|                                                                         |
| * easy: basic data structures, simple algorithms                        |
| * medium: combinations of algorithms, optimization required             |
| * hard: complex algorithms, advanced data structures, math              |
|                                                                         |
| execution model:                                                        |
|                                                                         |
| * each submission is compiled and run in an isolated sandbox            |
| * stdin provides input, stdout captures output                          |
| * resource limits (CPU time, memory, processes) are enforced            |
| * no network access, no filesystem access beyond working directory      |
+-------------------------------------------------------------------------+
```

## SECTION 2: REQUIREMENTS

### FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
| core features:                                                          |
|                                                                         |
| * problem management: create, edit, tag, categorize problems            |
|   with markdown descriptions, constraints, sample I/O, hints            |
|                                                                         |
| * multi-language support: C, C++, java, python, javascript,             |
|   go, rust, and more. language-specific time/memory multipliers.        |
|                                                                         |
| * code submission: submit solution code, track submission history       |
|   per problem, view past attempts and verdicts                          |
|                                                                         |
| * automated judging: compile, execute against test cases, compare       |
|   output, return verdict with runtime/memory statistics                 |
|                                                                         |
| * test cases: hidden (for judging) and sample (visible to users).       |
|   support for special judges (multiple valid answers).                  |
|                                                                         |
| * leaderboard: global rankings by problems solved, rating, streak.      |
|   per-problem statistics (acceptance rate, avg runtime).                |
|                                                                         |
| * contests: timed competitions with real-time standings.                |
|   ICPC-style and codeforces-style scoring systems.                      |
|                                                                         |
| * editorial and discussion: problem solutions, approach explanations,   |
|   user discussions and comments per problem.                            |
|                                                                         |
| * user profiles: submission history, badges, activity heatmap,          |
|   problem-solving statistics by category and difficulty.                |
+-------------------------------------------------------------------------+
```

### NON-FUNCTIONAL REQUIREMENTS

```
+--------------------------------------------------------------------------+
| * sandboxed execution: user code must run in complete isolation.         |
|   no access to host system, network, or other submissions.               |
|   prevent all forms of escape, fork bombs, and resource abuse.           |
|                                                                          |
| * low latency judging: verdict returned within 5 seconds for most        |
|   submissions. compilation timeout: 10 seconds. execution timeout:       |
|   per-problem (typically 1-5 seconds per test case).                     |
|                                                                          |
| * high concurrency: support 10,000+ concurrent submissions during        |
|   contests. normal load: 500-1000 submissions per minute.                |
|                                                                          |
| * high availability: 99.9% uptime. contest mode requires even            |
|   higher reliability since downtime affects rankings.                    |
|                                                                          |
| * correctness: verdicts must be deterministic and reproducible.          |
|   same code + same test cases = same verdict every time.                 |
|                                                                          |
| * security: prevent code injection, host escape, information             |
|   leakage between submissions, and cheating during contests.             |
|                                                                          |
| * scalability: auto-scale judge workers based on submission queue        |
|   depth. handle 10x traffic spikes during popular contests.              |
+--------------------------------------------------------------------------+
```

## SECTION 3: BACK-OF-ENVELOPE ESTIMATION

### TRAFFIC ESTIMATES

```
+-------------------------------------------------------------------------+
| assumptions:                                                            |
|                                                                         |
| * 5 million registered users                                            |
| * 500,000 daily active users (DAU)                                      |
| * average 3 submissions per DAU per day                                 |
|                                                                         |
| daily submissions  = 500K * 3 = 1.5 million/day                         |
| average rate       = 1.5M / 86400 = ~17 submissions/second              |
| peak rate (5x)     = ~85 submissions/second                             |
| contest peak (20x) = ~350 submissions/second                            |
|                                                                         |
| read traffic (much higher):                                             |
| * problem page views: 10x submissions = ~170 req/sec avg                |
| * leaderboard views: 5x submissions = ~85 req/sec avg                   |
| * profile/history views: 3x submissions = ~50 req/sec avg               |
| * total read API: ~500 req/sec avg, ~5000 req/sec peak                  |
+-------------------------------------------------------------------------+
```

### STORAGE ESTIMATES

```
+-------------------------------------------------------------------------+
| submission storage:                                                     |
| * average code size: 2 KB                                               |
| * metadata per submission: 500 bytes                                    |
| * daily: 1.5M * 2.5 KB = ~3.75 GB/day                                   |
| * yearly: 3.75 GB * 365 = ~1.37 TB/year                                 |
|                                                                         |
| test case storage:                                                      |
| * 5000 problems, avg 20 test cases per problem                          |
| * avg input file: 50 KB, avg output file: 10 KB                         |
| * total: 5000 * 20 * 60 KB = ~6 GB                                      |
| * stored in object storage (S3) with CDN caching                        |
|                                                                         |
| problem content:                                                        |
| * 5000 problems * 10 KB each (markdown + images) = ~50 MB               |
|                                                                         |
| judge output (execution logs):                                          |
| * per submission: ~5 KB (stdout, stderr, verdict per test case)         |
| * daily: 1.5M * 5 KB = ~7.5 GB/day                                      |
| * retention: 90 days = ~675 GB                                          |
|                                                                         |
| total storage: ~5 TB for 3 years of operation                           |
+-------------------------------------------------------------------------+
```

### COMPUTE ESTIMATES

```
+--------------------------------------------------------------------------+
| judge worker computation:                                                |
|                                                                          |
| * average execution time per submission:                                 |
|   compilation: ~2 seconds                                                |
|   execution across all test cases: ~5 seconds                            |
|   total: ~7 seconds of compute per submission                            |
|                                                                          |
| * at peak (350 submissions/sec):                                         |
|   concurrent compute needed: 350 * 7 = 2,450 CPU-seconds/sec             |
|   = ~2,450 CPU cores needed at peak                                      |
|                                                                          |
| * at normal load (17 submissions/sec):                                   |
|   concurrent compute: 17 * 7 = ~120 CPU cores                            |
|                                                                          |
| * worker sizing: each worker VM has 4 cores, runs 2 concurrent           |
|   submissions. need ~600 workers at peak, ~30 workers at normal.         |
|                                                                          |
| * auto-scaling: scale based on queue depth and average wait time.        |
|   target: < 5 second queue wait time.                                    |
+--------------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

### COMPONENT OVERVIEW

```
+-------------------------------------------------------------------------+
|                                                                         |
|                      +-------------------+                              |
|                      |   web / mobile    |                              |
|                      |     client        |                              |
|                      +--------+----------+                              |
|                               |                                         |
|                      +--------v----------+                              |
|                      |    API gateway    |                              |
|                      | (auth, rate limit)|                              |
|                      +--------+----------+                              |
|                               |                                         |
|        +----------+-----------+-----------+----------+                  |
|        |          |           |           |          |                  |
|  +-----v---+ +----v----+ +---v----+ +----v---+ +----v-----+             |
|  | problem | |  submit | | result | | leader | | contest  |             |
|  | service | | service | |service | | board  | | service  |             |
|  +---------+ +----+----+ +---+----+ +----+---+ +----+-----+             |
|                   |          ^            |          |                  |
|              +----v----+     |       +----v---+     |                   |
|              |  judge  |     |       |  redis  |     |                  |
|              |  queue  |     |       |  cache  |     |                  |
|              | (kafka) |     |       +--------+     |                   |
|              +----+----+     |                      |                   |
|                   |          |                      |                   |
|        +----------v----------+-------+              |                   |
|        |     judge worker pool       |              |                   |
|        | (sandboxed execution env)   |              |                   |
|        +----+-----+-----+-----+-----+              |                    |
|             |     |     |     |                     |                   |
|           +--v--+--v--+--v--+--v--+                 |                   |
|           | w1  | w2  | w3  | wN  |                 |                   |
|           +-----+-----+-----+-----+                 |                   |
|                                                      |                  |
|        +-------------------------------------------+ |                  |
|        |               databases                   | |                  |
|        | +----------+ +-----------+ +------------+ | |                  |
|        | | problems | |submissions| | test cases | | |                  |
|        | |    DB    | |    DB     | |  (S3/blob) | | |                  |
|        | +----------+ +-----------+ +------------+ | |                  |
|        +-------------------------------------------+ |                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMPONENT RESPONSIBILITIES

```
+--------------------------------------------------------------------------+
| * problem service: CRUD for problems, tags, difficulty. serves           |
|   problem descriptions, constraints, and sample test cases.              |
|   caches popular problems in redis for fast retrieval.                   |
|                                                                          |
| * submission service: accepts code submissions, validates input,         |
|   stores code in DB, publishes judge request to kafka queue.             |
|   handles idempotent resubmission and rate limiting per user.            |
|                                                                          |
| * judge queue (kafka): decouples submission acceptance from judging.     |
|   provides buffering during traffic spikes, ensures no submission        |
|   is lost. supports priority queues for contests vs practice.            |
|                                                                          |
| * judge worker pool: pool of isolated execution environments.            |
|   each worker picks a submission, compiles, runs against test            |
|   cases, and publishes verdict. auto-scales based on queue depth.        |
|                                                                          |
| * result service: stores and serves judging results. updates             |
|   submission status. pushes real-time verdict via websocket.             |
|                                                                          |
| * leaderboard service: computes and caches global/per-contest            |
|   rankings. uses redis sorted sets for O(log N) rank operations.         |
|                                                                          |
| * contest service: manages contest lifecycle (create, start, end,        |
|   freeze). enforces contest rules, timing, and scoring logic.            |
+--------------------------------------------------------------------------+
```

## SECTION 5: SUBMISSION FLOW

### END-TO-END SUBMISSION PIPELINE

```
+--------------------------------------------------------------------------+
| detailed flow from code submission to verdict:                           |
|                                                                          |
|   +------+    +--------+    +-------+    +-------+    +--------+         |
|   |submit|--->|validate|--->| store |--->|enqueue|--->|  judge  |        |
|   +------+    +--------+    +-------+    +-------+    +---+----+         |
|                                                           |              |
|              +--------+    +--------+    +-------+   +----v----+         |
|              | notify |<---| update |<---|compare|<--| execute |         |
|              +--------+    +--------+    +-------+   +---------+         |
|                                                                          |
| step 1 - SUBMIT:                                                         |
|   * user submits code + problem_id + language via API                    |
|   * client sends POST /api/v1/submissions                                |
|                                                                          |
| step 2 - VALIDATE:                                                       |
|   * check authentication and rate limits (max 10 per minute)             |
|   * validate language is supported for this problem                      |
|   * check code size limit (50 KB max)                                    |
|   * sanitize input (no null bytes, valid encoding)                       |
|                                                                          |
| step 3 - STORE:                                                          |
|   * save submission record to DB with status QUEUED                      |
|   * store code blob (DB or object storage for large files)               |
|   * assign unique submission_id, record timestamp                        |
|                                                                          |
| step 4 - ENQUEUE:                                                        |
|   * publish judge request to kafka topic                                 |
|   * message: { submission_id, problem_id, language, code_ref }           |
|   * contest submissions get higher priority partition                    |
|                                                                          |
| step 5 - JUDGE (worker picks up from queue):                             |
|   * download code and test cases                                         |
|   * create sandboxed environment (container/microVM)                     |
|   * compile code (language-specific compiler)                            |
|   * if compilation error: return CE verdict immediately                  |
+--------------------------------------------------------------------------+
```

### EXECUTION AND VERDICT

```
+-------------------------------------------------------------------------+
| step 6 - EXECUTE (for each test case):                                  |
|                                                                         |
|   for test_case in problem.test_cases:                                  |
|       write test_case.input to sandbox stdin                            |
|       start process with resource limits:                               |
|           time_limit: problem.time_limit (e.g., 2 seconds)              |
|           memory_limit: problem.memory_limit (e.g., 256 MB)             |
|           process_limit: 1 (prevent fork bombs)                         |
|           network: disabled                                             |
|       wait for process to finish or hit limits                          |
|       capture stdout, stderr, exit_code                                 |
|       record actual_time and actual_memory                              |
|                                                                         |
|       if exit_code != 0:                      -> RE                     |
|       if actual_time > time_limit:            -> TLE                    |
|       if actual_memory > memory_limit:        -> MLE                    |
|                                                                         |
| step 7 - COMPARE:                                                       |
|   * standard judge: exact match after trimming trailing whitespace      |
|   * special judge: run custom checker program that validates output     |
|   * floating-point: compare with epsilon tolerance (1e-6 typical)       |
|                                                                         |
|   if output matches expected:     -> AC (for this test case)            |
|   else:                           -> WA                                 |
|                                                                         |
|   overall verdict:                                                      |
|   * if all test cases pass:       -> AC                                 |
|   * else: return first failing test case verdict                        |
|                                                                         |
| step 8 - UPDATE:                                                        |
|   * update submission record with verdict, runtime, memory              |
|   * update problem statistics (acceptance rate)                         |
|   * update user statistics (problems solved count)                      |
|   * if contest: update leaderboard scores                               |
|                                                                         |
| step 9 - NOTIFY:                                                        |
|   * push verdict to client via websocket connection                     |
|   * client shows verdict with per-test-case breakdown                   |
|   * show runtime percentile compared to other accepted solutions        |
+-------------------------------------------------------------------------+
```

## SECTION 6: SANDBOXED EXECUTION

### ISOLATION LAYERS

```
+-------------------------------------------------------------------------+
| executing untrusted code is the most security-critical component.       |
| multiple layers of isolation are used for defense in depth.             |
|                                                                         |
| layer 1 - CONTAINERIZATION (docker):                                    |
|                                                                         |
| * each submission runs in a fresh docker container                      |
| * container uses a minimal base image (alpine + compiler)               |
| * container is destroyed after execution (no state leaks)               |
| * read-only filesystem except for /tmp working directory                |
| * no volume mounts to host filesystem                                   |
|                                                                         |
| layer 2 - SYSTEM CALL FILTERING (seccomp / apparmor):                   |
|                                                                         |
| * seccomp-bpf profile restricts available system calls                  |
| * whitelist approach: only allow read, write, mmap, exit, etc.          |
| * block dangerous syscalls: execve (after initial exec), ptrace,        |
|   socket, bind, connect, mount, reboot, kexec                           |
| * apparmor profile restricts file access paths                          |
|                                                                         |
| layer 3 - RESOURCE LIMITS (cgroups v2):                                 |
|                                                                         |
| * cpu.max: limits CPU time (wall clock + CPU time)                      |
| * memory.max: hard memory limit, OOM-killed if exceeded                 |
| * pids.max: set to 1-5 to prevent fork bombs                            |
| * io.max: limit disk I/O bandwidth                                      |
|                                                                         |
| layer 4 - NETWORK ISOLATION:                                            |
|                                                                         |
| * container runs with network disabled (--network=none)                 |
| * no DNS resolution, no outbound connections                            |
| * prevents data exfiltration and fetching external help                 |
+-------------------------------------------------------------------------+
```

### ADVANCED ISOLATION WITH FIRECRACKER

```
+--------------------------------------------------------------------------+
| for maximum security, use firecracker microVMs instead of docker:        |
|                                                                          |
| * firecracker is a lightweight VMM (virtual machine monitor)             |
|   created by AWS for lambda and fargate                                  |
|                                                                          |
| * each submission runs in its own microVM with:                          |
|   * separate kernel (not shared with host)                               |
|   * hardware-level isolation via KVM                                     |
|   * boot time: ~125 milliseconds                                         |
|   * memory overhead: ~5 MB per microVM                                   |
|                                                                          |
| * advantages over containers:                                            |
|   * stronger isolation (kernel-level vs namespace-level)                 |
|   * no shared kernel vulnerabilities                                     |
|   * resistant to container escape exploits                               |
|   * better resource accounting accuracy                                  |
|                                                                          |
| * trade-offs:                                                            |
|   * slightly higher startup overhead (125ms vs ~50ms for containers)     |
|   * requires KVM support on host (bare metal or nested virt)             |
|   * more complex image management                                        |
|                                                                          |
| microVM lifecycle:                                                       |
|                                                                          |
|   pre-warm pool --> assign to submission --> execute --> destroy         |
|                                                                          |
| * maintain a pool of pre-booted microVMs (warm pool)                     |
| * submission is assigned an available microVM from the pool              |
| * code is injected, compiled, and executed inside the microVM            |
| * microVM is destroyed after execution (or recycled if safe)             |
+--------------------------------------------------------------------------+
```

### RESOURCE LIMITS AND PROTECTIONS

```
+-------------------------------------------------------------------------+
| specific resource limits enforced per submission:                       |
|                                                                         |
| +------------------+------------------+-----------------------------+   |
| | resource         | typical limit    | enforcement mechanism       |   |
| +------------------+------------------+-----------------------------+   |
| | CPU time         | 1-10 sec         | cgroups cpu.max + alarm()   |   |
| | wall clock time  | 2x CPU limit     | external timer kills proc   |   |
| | memory (heap)    | 256 MB           | cgroups memory.max (OOM)    |   |
| | stack size       | 64 MB            | ulimit -s                   |   |
| | output size      | 64 MB            | pipe buffer monitoring      |   |
| | file size        | 0 (no writes)    | ulimit -f + read-only fs    |   |
| | processes/threads| 1-5              | cgroups pids.max            |   |
| | open files       | 16               | ulimit -n                   |   |
| | network          | disabled         | --network=none              |   |
| +------------------+------------------+-----------------------------+   |
|                                                                         |
| protection against common attacks:                                      |
|                                                                         |
| * fork bomb: pids.max=1 prevents forking entirely                       |
| * memory bomb: cgroups OOM killer terminates immediately                |
| * infinite loop: wall clock timer kills process after limit             |
| * infinite output: pipe monitoring kills after 64 MB stdout             |
| * disk fill: read-only filesystem, tmpfs with size limit                |
| * escape attempts: seccomp blocks dangerous syscalls                    |
| * information leak: fresh environment, no host filesystem access        |
+-------------------------------------------------------------------------+
```

## SECTION 7: TEST CASE MANAGEMENT

### HIDDEN VS SAMPLE TEST CASES

```
+-------------------------------------------------------------------------+
| test cases are the backbone of automated judging accuracy.              |
|                                                                         |
| sample test cases (visible to users):                                   |
|                                                                         |
| * 2-3 simple examples included in problem statement                     |
| * help users understand input/output format                             |
| * typically cover basic cases only                                      |
| * users can test against these before submitting                        |
|                                                                         |
| hidden test cases (used for judging):                                   |
|                                                                         |
| * 10-50 test cases per problem (varies by difficulty)                   |
| * cover edge cases:                                                     |
|   * empty input, single element, minimum values                         |
|   * maximum input size (stress test for TLE)                            |
|   * boundary values (INT_MAX, 0, negative numbers)                      |
|   * special patterns (all same elements, sorted, reverse sorted)        |
|   * random large inputs                                                 |
| * never revealed to users (prevents hardcoding answers)                 |
| * test case quality directly impacts judging fairness                   |
|                                                                         |
| storage:                                                                |
|                                                                         |
| * test case files stored in S3/object storage                           |
| * fetched by judge workers at execution time                            |
| * cached locally on workers for frequently judged problems              |
| * versioned to allow test case updates without breaking history         |
+-------------------------------------------------------------------------+
```

### SPECIAL JUDGES AND VALIDATORS

```
+--------------------------------------------------------------------------+
| some problems have multiple valid answers. a standard diff-based         |
| comparison cannot judge these correctly.                                 |
|                                                                          |
| special judge (checker):                                                 |
|                                                                          |
| * a custom program that validates user output                            |
| * receives: input file, expected output, user output                     |
| * returns: AC or WA with optional feedback message                       |
|                                                                          |
| * examples of problems needing special judges:                           |
|   * "find any valid path" (multiple valid paths exist)                   |
|   * floating-point answers (epsilon comparison)                          |
|   * "output any permutation" (order does not matter)                     |
|   * graph coloring (many valid colorings)                                |
|                                                                          |
| * the checker itself runs in a sandbox (it is also untrusted code        |
|   written by problem setters, though with higher trust level)            |
|                                                                          |
| input validators:                                                        |
|                                                                          |
| * programs that verify test case input is valid                          |
| * ensure input satisfies all stated constraints                          |
| * run once when test cases are uploaded (not per submission)             |
| * catch errors like: values out of range, wrong format, graph            |
|   not connected when it should be, tree with cycles, etc.                |
+--------------------------------------------------------------------------+
```

### STRESS TESTING

```
+-------------------------------------------------------------------------+
| stress testing verifies a problem's test cases are comprehensive        |
| and the intended solution is correct.                                   |
|                                                                         |
| process:                                                                |
|                                                                         |
| * step 1: write a brute-force solution (slow but correct)               |
| * step 2: write a random test case generator                            |
| * step 3: run both solutions on thousands of random inputs              |
| * step 4: if outputs ever differ, we found a bug in either              |
|   the intended solution or the test cases                               |
|                                                                         |
| * this is done during problem creation, not during judging              |
|                                                                         |
| automated stress test pipeline:                                         |
|                                                                         |
|   +-----------+     +---------+     +----------+                        |
|   | generator |---->| brute   |---->| compare  |                        |
|   | (random)  |     | force   |     | outputs  |                        |
|   +-----------+     +---------+     +-----+----+                        |
|        |                                  |                             |
|        +----------> optimal ------>-------+                             |
|                     solution                                            |
|                                                                         |
| * generator outputs random inputs within constraints                    |
| * both solutions run on same inputs                                     |
| * comparator checks for mismatches                                      |
| * runs 10,000+ iterations automatically                                 |
+-------------------------------------------------------------------------+
```

## SECTION 8: LANGUAGE SUPPORT

### COMPILER AND RUNTIME CONFIGURATION

```
+--------------------------------------------------------------------------+
| each supported language has specific compilation and execution           |
| settings defined in the judge configuration.                             |
|                                                                          |
| +------------+------------------------+---------------------------+      |
| | language   | compile command         | run command               |     |
| +------------+------------------------+---------------------------+      |
| | C          | gcc -O2 -std=c17       | ./a.out                   |      |
| |            | -lm -o a.out sol.c     |                           |      |
| | C++        | g++ -O2 -std=c++17     | ./a.out                   |      |
| |            | -o a.out sol.cpp       |                           |      |
| | java       | javac Solution.java     | java -Xmx256m Solution   |      |
| | python 3   | (interpreted)           | python3 sol.py            |     |
| | javascript | (interpreted)           | node sol.js               |     |
| | go         | go build -o sol sol.go  | ./sol                     |     |
| | rust       | rustc -O -o sol sol.rs  | ./sol                     |     |
| +------------+------------------------+---------------------------+      |
|                                                                          |
| compilation timeout: 10 seconds for all languages                        |
| * java compilation is typically slowest (~5 seconds)                     |
| * if compilation exceeds timeout -> CE verdict                           |
+--------------------------------------------------------------------------+
```

### LANGUAGE-SPECIFIC CONSIDERATIONS

```
+-------------------------------------------------------------------------+
| time multipliers:                                                       |
|                                                                         |
| * interpreted languages (python, javascript) are inherently slower      |
|   than compiled languages (C, C++)                                      |
| * to be fair, apply time multipliers:                                   |
|   * C/C++/rust: 1x (baseline)                                           |
|   * java/go: 2x                                                         |
|   * python: 3-5x                                                        |
|   * javascript: 2-3x                                                    |
| * example: if C++ time limit is 2 seconds, python gets 6-10 seconds     |
|                                                                         |
| memory considerations:                                                  |
|                                                                         |
| * java JVM has baseline memory overhead (~50 MB)                        |
| * python interpreter overhead (~30 MB)                                  |
| * memory limits should account for runtime overhead                     |
| * C/C++: 256 MB, java: 512 MB, python: 512 MB                           |
|                                                                         |
| sandboxing challenges per language:                                     |
|                                                                         |
| * java: can use reflection to access internals. disable via             |
|   security manager or module restrictions.                              |
| * python: can import os, subprocess. restrict via seccomp or            |
|   custom import hooks that block dangerous modules.                     |
| * C/C++: can make raw syscalls via inline assembly. seccomp-bpf         |
|   is essential to block this.                                           |
+-------------------------------------------------------------------------+
```

## SECTION 9: CONTEST SYSTEM

### CONTEST LIFECYCLE

```
+--------------------------------------------------------------------------+
| a programming contest is a timed event where participants solve          |
| problems competitively with real-time rankings.                          |
|                                                                          |
| lifecycle:                                                               |
|                                                                          |
| * creation: admin creates contest with problems, time window,            |
|   scoring rules, and registration settings                               |
|                                                                          |
| * registration: users register before start time. some contests          |
|   are open (anyone can join), others require qualification.              |
|                                                                          |
| * start: contest goes live at scheduled time. problems revealed          |
|   simultaneously. countdown timer starts.                                |
|                                                                          |
| * during: users submit solutions, see verdict in real-time.              |
|   leaderboard updates continuously (or frozen in last hour).             |
|                                                                          |
| * freeze (optional): leaderboard frozen in final 15-60 minutes.          |
|   users see their own results but not others. builds suspense.           |
|                                                                          |
| * end: no more submissions accepted. final judging completes.            |
|   leaderboard unfrozen and final rankings published.                     |
|                                                                          |
| * post-contest: editorial published, problems added to practice          |
|   archive, ratings updated based on performance.                         |
+--------------------------------------------------------------------------+
```

### SCORING SYSTEMS

```
+-------------------------------------------------------------------------+
| ICPC-style scoring:                                                     |
|                                                                         |
| * rank by: number of problems solved (primary), then total time         |
|   (secondary, lower is better)                                          |
| * time = sum of solve times for accepted problems                       |
| * penalty: +20 minutes per wrong submission before AC                   |
| * no partial credit (all-or-nothing per problem)                        |
| * encourages solving more problems over optimizing solutions            |
|                                                                         |
| example:                                                                |
|   user solves problem A at t=15min (0 wrong attempts): time = 15        |
|   user solves problem B at t=45min (2 wrong attempts): time = 85        |
|   total: 2 problems solved, 100 minutes penalty time                    |
|                                                                         |
| codeforces-style scoring:                                               |
|                                                                         |
| * each problem has max points (e.g., 500, 1000, 1500, 2000)             |
| * points decrease over time: score = max - decay * minutes_elapsed      |
| * wrong submissions incur point penalty (e.g., -50 per WA)              |
| * partial credit possible: higher difficulty = more points              |
| * rating system (elo-like) updates after each contest                   |
|                                                                         |
| example:                                                                |
|   problem worth 1000 points, decay = 4/minute                           |
|   solved at t=30min with 1 WA: 1000 - 4*30 - 50 = 830 points            |
+-------------------------------------------------------------------------+
```

### ANTI-CHEATING MEASURES

```
+--------------------------------------------------------------------------+
| cheating prevention is essential for contest integrity.                  |
|                                                                          |
| MOSS (measure of software similarity):                                   |
|                                                                          |
| * stanford's plagiarism detection system for code                        |
| * compares all pairs of submissions for a problem                        |
| * works by tokenizing code and finding matching token sequences          |
| * robust against: variable renaming, reordering, adding comments,        |
|   changing whitespace, converting loops to recursion                     |
| * produces similarity percentage and highlighted comparison              |
| * run after each contest on all accepted submissions                     |
|                                                                          |
| additional anti-cheat measures:                                          |
|                                                                          |
| * IP monitoring: flag multiple accounts from same IP during contest      |
| * submission timing: flag identical submissions within seconds           |
| * code structure analysis: detect templates shared between accounts      |
| * account verification: email/phone verification for contest accounts    |
|                                                                          |
| * proctoring (for high-stakes contests):                                 |
|   * webcam monitoring during contest                                     |
|   * screen recording of coding environment                               |
|   * browser lockdown (no tab switching)                                  |
|   * copy-paste detection in the editor                                   |
|                                                                          |
| * post-contest review:                                                   |
|   * MOSS report reviewed by admin team                                   |
|   * flagged pairs manually investigated                                  |
|   * penalties: score removal, temp ban, permanent ban for repeat         |
+--------------------------------------------------------------------------+
```

## SECTION 10: SCALING

### WORKER AUTO-SCALING

```
+--------------------------------------------------------------------------+
| the judge worker pool must scale dynamically based on demand.            |
|                                                                          |
| scaling strategy:                                                        |
|                                                                          |
| * metric: kafka consumer lag (messages in queue awaiting pickup)         |
| * target: keep average wait time under 5 seconds                         |
| * scale-up: when lag > threshold for 30 seconds, add workers             |
| * scale-down: when lag = 0 for 5 minutes, remove workers                 |
| * minimum: always keep 10 workers warm (instant availability)            |
| * maximum: cap at 1000 workers (cost protection)                         |
|                                                                          |
| implementation with kubernetes:                                          |
|                                                                          |
| * judge workers run as kubernetes pods                                   |
| * horizontal pod autoscaler (HPA) with custom kafka lag metric           |
| * cluster autoscaler adds nodes when pods cannot be scheduled            |
| * spot/preemptible instances for cost savings (workers are stateless     |
|   and fault-tolerant since failed submissions are re-queued)             |
|                                                                          |
| pre-scaling for contests:                                                |
|                                                                          |
| * known contest start times allow pre-scaling 10 minutes before          |
| * scale to estimated peak (registered_users * 0.3 = expected             |
|   concurrent submitters in first 5 minutes)                              |
| * gradual scale-down over 2 hours after contest ends                     |
+--------------------------------------------------------------------------+
```

### PRIORITY QUEUES

```
+--------------------------------------------------------------------------+
| not all submissions are equal. priority queuing ensures fair and         |
| responsive judging during high load.                                     |
|                                                                          |
| priority levels:                                                         |
|                                                                          |
| * P0 (highest): contest submissions during active contest. these         |
|   directly affect competitive rankings and user experience.              |
|                                                                          |
| * P1: "run code" (test against sample cases). fast feedback loop         |
|   is critical for user engagement. run only 2-3 sample cases.            |
|                                                                          |
| * P2: practice submissions. standard priority for normal usage.          |
|                                                                          |
| * P3 (lowest): rejudge requests (admin re-evaluates old submissions      |
|   after test case changes). can be batched during off-peak hours.        |
|                                                                          |
| implementation:                                                          |
|                                                                          |
| * separate kafka topics per priority: judge.p0, judge.p1, etc.           |
| * workers check P0 first, then P1, then P2, then P3                      |
| * dedicated worker pool for P0 during contests (not shared)              |
| * starvation prevention: P3 gets at least 5% of worker capacity          |
+--------------------------------------------------------------------------+
```

### RESULT CACHING AND OPTIMIZATION

```
+--------------------------------------------------------------------------+
| caching and optimization reduce compute costs and improve latency.       |
|                                                                          |
| compilation caching:                                                     |
|                                                                          |
| * hash the source code to detect identical resubmissions                 |
| * if same code was submitted before for same problem, return             |
|   cached verdict without re-judging                                      |
| * cache key: SHA256(problem_id + language + source_code)                 |
| * cache store: redis with 24-hour TTL                                    |
| * cache hit rate: ~15-20% (users often resubmit same code)               |
|                                                                          |
| test case optimization:                                                  |
|                                                                          |
| * order test cases by difficulty (easy first)                            |
| * stop on first failure (no need to run remaining test cases)            |
| * this reduces average execution time significantly since most           |
|   wrong answers fail on early/simple test cases                          |
|                                                                          |
| binary caching:                                                          |
|                                                                          |
| * cache compiled binaries (for compiled languages)                       |
| * if same source hash exists, skip compilation step                      |
| * saves 2-5 seconds per cached submission                                |
|                                                                          |
| hot problem optimization:                                                |
|                                                                          |
| * popular problems (top 100 by daily submissions) have test cases        |
|   pre-cached on all worker nodes in local SSD                            |
| * avoids S3 fetch latency for every submission                           |
+--------------------------------------------------------------------------+
```

## SECTION 11: INTERVIEW Q&A

### QUESTION 1

```
+--------------------------------------------------------------------------+
| Q: how would you ensure that user code cannot escape the sandbox         |
|    and affect the host system?                                           |
|                                                                          |
| A: use defense in depth with multiple isolation layers. first,           |
|    run each submission in a separate container or firecracker            |
|    microVM with its own filesystem and network namespace. second,        |
|    apply seccomp-bpf profiles that whitelist only safe system            |
|    calls (read, write, mmap, exit) and block dangerous ones              |
|    (execve after initial exec, socket, ptrace, mount). third,            |
|    use cgroups to limit CPU, memory, and PIDs so even if code            |
|    tries resource exhaustion it is killed. fourth, disable               |
|    networking entirely (--network=none). fifth, use a read-only          |
|    filesystem with a small tmpfs for working files. the container        |
|    is destroyed after execution so no persistent state survives.         |
+--------------------------------------------------------------------------+
```

### QUESTION 2

```
+--------------------------------------------------------------------------+
| Q: how do you handle a situation where 10,000 users submit code          |
|    simultaneously at the start of a contest?                             |
|                                                                          |
| A: pre-scale judge workers 10 minutes before contest start based         |
|    on registered participant count. use a message queue (kafka) to       |
|    buffer the burst of submissions so no submissions are lost even       |
|    if workers cannot process them instantly. contest submissions         |
|    go to a high-priority queue with dedicated workers. the web           |
|    tier and submission service are horizontally scaled and behind        |
|    a load balancer. rate limiting prevents any single user from          |
|    flooding the queue (max 1 submission per 10 seconds). the             |
|    queue provides natural backpressure and ordering. users see           |
|    "judging..." status with estimated wait time while their              |
|    submission is in the queue.                                           |
+--------------------------------------------------------------------------+
```

### QUESTION 3

```
+-------------------------------------------------------------------------+
| Q: how would you make verdicts deterministic and reproducible?          |
|                                                                         |
| A: determinism requires controlling all sources of non-determinism.     |
|    first, use fixed compiler versions and flags (docker image pins      |
|    exact versions). second, enforce single-threaded execution           |
|    (pids.max=1) to avoid thread scheduling non-determinism. third,      |
|    use CPU time limits (not wall clock) for timing to avoid             |
|    variability from system load. fourth, disable ASLR in the            |
|    container so memory layouts are consistent. fifth, no network        |
|    or external I/O that could vary between runs. for languages          |
|    with non-deterministic hash maps (python 3.6+, java), document       |
|    that solutions should not depend on iteration order. if a            |
|    verdict is disputed, re-run 3 times and take majority result.        |
+-------------------------------------------------------------------------+
```

### QUESTION 4

```
+--------------------------------------------------------------------------+
| Q: how would you design the real-time contest leaderboard?               |
|                                                                          |
| A: use redis sorted sets for O(log N) rank operations. each              |
|    participant has a score in the sorted set. when a verdict             |
|    arrives, recalculate the user's score and update with ZADD.           |
|    ZREVRANK gives the user's current rank. ZREVRANGE returns the         |
|    top-K for the leaderboard page. for ICPC scoring, the sort            |
|    key is: (problems_solved * 10000000 - total_penalty_time) to          |
|    achieve correct ordering with a single sorted set. for large          |
|    contests (100K+ participants), shard by rank ranges and merge.        |
|    during the freeze period, maintain two views: a frozen public         |
|    leaderboard and a live internal one for the reveal. broadcast         |
|    updates to connected clients via websocket with throttling            |
|    (max 1 update per second per client to prevent flooding).             |
+--------------------------------------------------------------------------+
```

### QUESTION 5

```
+--------------------------------------------------------------------------+
| Q: how do you detect plagiarism among contest submissions?               |
|                                                                          |
| A: run MOSS (measure of software similarity) after each contest          |
|    on all accepted submissions per problem. MOSS tokenizes code,         |
|    normalizes variable names and formatting, then finds longest          |
|    common subsequences between all pairs. pairs with similarity          |
|    above 80% are flagged for manual review. additionally, compare        |
|    submission timestamps: if two users submit near-identical code        |
|    within minutes, it is highly suspicious. check IP addresses for       |
|    multiple accounts submitting from the same location. for code         |
|    sharing via external channels, analyze structural patterns like       |
|    identical variable naming conventions, same helper functions,         |
|    and identical algorithmic approach order.                             |
+--------------------------------------------------------------------------+
```

### QUESTION 6

```
+--------------------------------------------------------------------------+
| Q: how would you support adding a new programming language?              |
|                                                                          |
| A: language support is configured declaratively, not hardcoded.          |
|    each language has a config entry specifying: compiler/interpreter     |
|    binary and version, compile command template, run command             |
|    template, file extension, time multiplier, memory multiplier,         |
|    and a docker base image containing the toolchain. to add a new        |
|    language: create a docker image with the compiler/runtime,            |
|    add a config entry with the above fields, run the existing test       |
|    suite to verify compilation and execution work correctly, and         |
|    deploy. the judge worker dynamically selects the correct docker       |
|    image based on submission language. no code changes needed in         |
|    the judge engine itself. time/memory multipliers are tuned by         |
|    benchmarking known solutions in the new language.                     |
+--------------------------------------------------------------------------+
```

### QUESTION 7

```
+--------------------------------------------------------------------------+
| Q: what database would you choose for storing submissions and why?       |
|                                                                          |
| A: use postgresql as the primary database for submissions, problems,     |
|    and user data. it handles relational queries well (join user          |
|    with submission, filter by problem, sort by time), supports           |
|    JSONB for flexible metadata, and has excellent indexing. for          |
|    test case files and code blobs, use S3/object storage since           |
|    they are write-once-read-many and can be large. for leaderboard       |
|    and caching, use redis sorted sets. for the submission queue,         |
|    use kafka for its durability, ordering guarantees, and ability        |
|    to replay messages. postgresql handles the expected write load        |
|    (~350 writes/sec at peak) easily. read replicas serve the high        |
|    read traffic (problem pages, history, profiles). partition the        |
|    submissions table by created_at for efficient queries on recent       |
|    submissions.                                                          |
+--------------------------------------------------------------------------+
```

### QUESTION 8

```
+--------------------------------------------------------------------------+
| Q: how would you handle a problem where test cases need to be            |
|    updated after users have already submitted solutions?                 |
|                                                                          |
| A: test case updates require careful handling. first, version all        |
|    test cases so historical submissions reference the version they       |
|    were judged against. second, when test cases are updated, mark        |
|    the problem as "rejudge pending." third, enqueue all accepted         |
|    submissions for that problem into the low-priority rejudge            |
|    queue. fourth, rejudge runs during off-peak hours to minimize         |
|    impact on real-time judging. fifth, if a previously accepted          |
|    solution now fails, update the verdict but optionally notify          |
|    the user. for contests, test case changes are extremely rare          |
|    and require admin approval with full audit log. maintain a            |
|    changelog for all test case modifications per problem.                |
+--------------------------------------------------------------------------+
```

### QUESTION 9

```
+--------------------------------------------------------------------------+
| Q: how would you implement a "run code" feature that executes            |
|    against custom input without formally submitting?                     |
|                                                                          |
| A: "run code" is a lightweight version of the judge flow. the user       |
|    provides code and custom stdin input. the system compiles and         |
|    runs the code against only that single input (no hidden test          |
|    cases). differences from formal submission: uses P1 priority          |
|    queue (fast feedback), does not record in submission history,         |
|    returns full stdout/stderr to the user (formal submissions only       |
|    show verdict). execution limits are the same as formal judging        |
|    for security. the result is streamed back via websocket for           |
|    instant display. implement aggressive rate limiting (max 5 runs       |
|    per minute) since users tend to run code frequently during            |
|    debugging. cache compiled binaries so repeated runs of the            |
|    same code with different inputs skip recompilation.                   |
+--------------------------------------------------------------------------+
```

### QUESTION 10

```
+--------------------------------------------------------------------------+
| Q: how would you design the system to support 50,000 concurrent          |
|    users viewing a real-time contest leaderboard?                        |
|                                                                          |
| A: the leaderboard must handle high read traffic with minimal            |
|    staleness. compute the leaderboard in redis sorted sets (single       |
|    source of truth for rankings). snapshot the top-500 leaderboard       |
|    every 2 seconds into a CDN-cacheable JSON payload. clients            |
|    fetch the snapshot via CDN (no backend hit for most users).           |
|    for users who want their own rank, a separate lightweight API         |
|    queries redis ZREVRANK for their specific score. use websocket        |
|    connections for the top-50 live view (push updates). for lower        |
|    ranks, poll every 10 seconds. this architecture means: 50,000         |
|    users hit CDN (not our servers), only the top-50 live view has        |
|    websocket connections (~200 connections max), and individual          |
|    rank checks are O(log N) redis calls. total backend load is           |
|    minimal regardless of viewer count.                                   |
+--------------------------------------------------------------------------+
```
