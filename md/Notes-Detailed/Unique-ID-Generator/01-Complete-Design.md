# DESIGN A UNIQUE ID GENERATOR (SNOWFLAKE-STYLE)

*Complete Design: Requirements, Architecture, and Interview Guide*

## SECTION 1: UNDERSTANDING THE PROBLEM

Every distributed system needs a way to uniquely identify entities - messages,
orders, users, events, database rows. At small scale, a single database
auto-incrementing counter works fine. At large scale, it falls apart.

### WHY AUTO-INCREMENT FAILS AT SCALE

```
  +------------------+       +-----------------------------+
  |   App Server A   |       |   App Server B              |
  +--------+---------+       +--------+--------------------+
           |                                               |
           |    INSERT ... (wait)                          |
           +----------+  +---------------------------------+
                                                        |  |
                      v  v                                  
              +-------+--+---------------------------------+
              |  Single Database                           |
              |  id = id + 1                               |
              +--------------------------------------------+

  Problems:                                                 
  * Single point of failure (SPOF)                          
  * Write bottleneck - all servers contend for one counter  
  * Cross-region latency - if DB is in US, Asia servers wait
  * Cannot pre-allocate IDs without coordination            
```

### WHY UUIDS AREN'T IDEAL EITHER

```
  UUID v4 example: 550e8400-e29b-41d4-a716-446655440000   

  +------------------------------------------------------+
  |                  UUID Properties                     |
  +------------------------------------------------------+
  | Size          | 128-bit (36 chars as string)         |
  | Sortable?     | No (v4 is random)                    |
  | Coordination? | None needed (great!)                 |
  | DB Indexes    | Poor - random inserts fragment       |
  |               | B-tree indexes badly                 |
  | Human-readable| No - long hex strings                |
  +------------------------------------------------------+
```

### WHAT WE ACTUALLY NEED

```
  +---------------------------------------------------------+
  |            Ideal Distributed ID Properties              |
  +---------------------------------------------------------+
  |  1. Globally unique - no duplicates across all nodes    |
  |  2. Roughly time-sortable - newer IDs > older IDs       |
  |  3. Compact - fits in 64-bit integer                    |
  |  4. No coordination - each server generates locally     |
  |  5. High throughput - thousands per millisecond         |
  +---------------------------------------------------------+
```

## SECTION 2: REQUIREMENTS

### FUNCTIONAL REQUIREMENTS

```
  +------------------------------------------------------------+
  |                  Functional Requirements                   |
  +------------------------------------------------------------+
  |                                                            |
  |  F1. Generate globally unique IDs across all servers       |
  |  F2. IDs must be roughly time-ordered (sortable)           |
  |  F3. IDs must be 64-bit numeric (fits in a long)           |
  |  F4. IDs must be monotonically increasing per server       |
  |                                                            |
  +------------------------------------------------------------+
```

### NON-FUNCTIONAL REQUIREMENTS

```
  +------------------------------------------------------------+
  |                Non-Functional Requirements                 |
  +------------------------------------------------------------+
  |                                                            |
  |  NF1. Throughput: 10,000+ IDs/sec per server               |
  |  NF2. No coordination between servers to generate IDs      |
  |  NF3. No single point of failure                           |
  |  NF4. Low latency: < 1ms per ID generation                 |
  |  NF5. Availability: 99.99%+ - ID gen must never block      |
  |                                                            |
  +------------------------------------------------------------+
```

## SECTION 3: ALL APPROACHES - DEEP COMPARISON

### APPROACH 1: UUID (UNIVERSALLY UNIQUE IDENTIFIER)

128-bit identifiers, standardized in RFC 4122.

```
  +-----------------------------------------------------------------+
  |                     UUID Versions Overview                      |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  UUID v1 - Timestamp + MAC Address                              |
  |    Format: [time_low]-[time_mid]-[time_hi]-[clock]-[MAC]        |
  |    Pros: Encodes creation time, unique per machine              |
  |    Cons: Leaks MAC address (privacy), not monotonic             |
  |                                                                 |
  |  UUID v4 - Fully Random                                         |
  |    Format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx                 |
  |    Pros: No coordination, trivial to generate                   |
  |    Cons: Not sortable, 128-bit, terrible index locality         |
  |                                                                 |
  |  UUID v7 - Timestamp prefix + Random (RFC 9562, 2024)           |
  |    Format: [48-bit unix_ts_ms]-[4-bit ver]-[rand]-[rand]        |
  |    Pros: Time-sortable! Good index locality                     |
  |    Cons: Still 128-bit, relatively new standard                 |
  |                                                                 |
  +-----------------------------------------------------------------+
```

```
  UUID v4 Index Problem (B-tree):                            

  +--+--+--+--+--+--+--+--+--+------------------------------+
  |  B-tree leaf pages                                      |
  +--+--+--+--+--+--+--+--+--+------------------------------+
    ^        ^     ^          ^                              
    |        |     |          |     Random inserts scatter   
    Insert1  Insert4 Insert2  Insert3   across all pages     
                                        > cache misses       
                                        > page splits        
                                        > write amplification
```

### APPROACH 2: DATABASE AUTO-INCREMENT

```
  +-------------------------------------------------+
  |          Database Auto-Increment                |
  +-------------------------------------------------+
  |                                                 |
  |  CREATE TABLE ids (                             |
  |    id BIGINT AUTO_INCREMENT PRIMARY KEY         |
  |  );                                             |
  |                                                 |
  |  INSERT INTO ids VALUES();  -- id = 1           |
  |  INSERT INTO ids VALUES();  -- id = 2           |
  |  INSERT INTO ids VALUES();  -- id = 3           |
  |                                                 |
  +-------------------------------------------------+

  +----------------+          +---------------------+
  |  App Server A  +--------->|                     |
  +----------------+          |  Single             |
                              |  MySQL    |  <-- SPOF
  +----------------+          |  Server             |
  |  App Server B  +--------->|                     |
  +----------------+          +---------------------+

  Pros: Simple, perfectly sequential, sortable       
  Cons: SPOF, throughput bottleneck (~1K-10K/sec),   
        doesn't scale horizontally                   
```

### APPROACH 3: DATABASE TICKET SERVER (FLICKR)

Flickr's clever trick: run TWO database servers with different increments.

```
  +-------------------------------------------------------+
  |           Flickr Ticket Server Approach               |
  +-------------------------------------------------------+
  |                                                       |
  |  Server A: auto_increment_increment = 2               |
  |            auto_increment_offset    = 1               |
  |            Generates: 1, 3, 5, 7, 9, ...              |
  |                                                       |
  |  Server B: auto_increment_increment = 2               |
  |            auto_increment_offset    = 2               |
  |            Generates: 2, 4, 6, 8, 10, ...             |
  |                                                       |
  +-------------------------------------------------------+

  +----------------+      +-------------------------------+
  |  App Servers   +----->|  Ticket Server A  |  (odd IDs) 
  |  (round-robin) |      +-------------------------------+
  |                                                       |
  |                |      +-------------------------------+
  |                +----->|  Ticket Server B  |  (even IDs)
  +----------------+      +-------------------------------+

  Pros: Simple HA, easy to understand                      
  Cons: Still DB-dependent, IDs not globally sorted        
        (A gives 5, B gives 6, but 6 happened before 5),   
        adding a 3rd server requires reconfiguration       
```

### APPROACH 4: TWITTER SNOWFLAKE (64-BIT) - THE MAIN APPROACH

```
  +================================================================------+
  ||                  TWITTER SNOWFLAKE LAYOUT                     |     |
  ||                     (64-bit integer)                          |     |
  +================================================================------+

  +---+------------------------------------------+----------+------------+
  | 0 |        41-bit timestamp                  | 10-bit   | 12-bit     |
  |   |        (milliseconds since epoch)        | machine  | sequence   |
  |   |                                          | ID       | number     |
  +---+------------------------------------------+----------+------------+
  bit  63                                    22       12          0       

  +----------------------------------------------------------------------+
  |  Field Breakdown:                                                    |
  +----------------------------------------------------------------------+
  |                                                                      |
  |  Sign bit (1 bit):                                                   |
  |    Always 0. Keeps ID positive in signed 64-bit languages.           |
  |                                                                      |
  |  Timestamp (41 bits):                                                |
  |    Milliseconds since custom epoch (not Unix epoch).                 |
  |    2^41 ms = ~69.7 years of IDs.                                     |
  |    Twitter epoch: 1288834974657 (Nov 4, 2010)                        |
  |                                                                      |
  |  Machine ID (10 bits):                                               |
  |    5 bits datacenter + 5 bits worker = 1024 machines.                |
  |    OR: 10 bits worker = 1024 workers total.                          |
  |                                                                      |
  |  Sequence (12 bits):                                                 |
  |    Per-millisecond counter: 0 to 4095.                               |
  |    Resets to 0 each millisecond.                                     |
  |    = 4,096 IDs per millisecond per machine                           |
  |    = 4,096,000 IDs per second per machine                            |
  |                                                                      |
  +----------------------------------------------------------------------+
```

```
  ID Generation Algorithm:                             

  +---------------------------------------------------+
  |  1. Get current timestamp in milliseconds         |
  |  2. If timestamp == lastTimestamp:                |
  |       sequence = (sequence + 1) & 0xFFF           |
  |       if sequence == 0:                           |
  |         wait until next millisecond               |
  |  3. If timestamp < lastTimestamp:                 |
  |       REJECT - clock went backward!               |
  |  4. If timestamp > lastTimestamp:                 |
  |       sequence = 0                                |
  |  5. lastTimestamp = timestamp                     |
  |  6. Return:                                       |
  |       (timestamp - epoch) << 22                   |
  |       | (machineId << 12)                         |
  |       | sequence                                  |
  +---------------------------------------------------+
```

### APPROACH 5: INSTAGRAM'S ID GENERATION

Similar to Snowflake but uses PostgreSQL shard IDs.

```
  +----------------------------------------------------------------+
  |                Instagram ID Layout (64-bit)                    |
  +----------------------------------------------------------------+
  |                                                                |
  |  +---+--------------------------------------+---------+------+ |
  |  | 0 | 41-bit timestamp                     | 13-bit  | 10   | |
  |  |   | (ms since Instagram epoch)           | shard   | bit  | |
  |  |   |                                      | ID      | seq  | |
  |  +---+--------------------------------------+---------+------+ |
  |                                                                |
  |  Shard ID (13 bits) = 8192 logical shards                      |
  |  Sequence (10 bits) = 1024 IDs/ms/shard                        |
  |                                                                |
  |  Generated inside PostgreSQL using PL/pgSQL functions.         |
  |  Each shard is a separate PostgreSQL schema.                   |
  |                                                                |
  +----------------------------------------------------------------+
```

### APPROACH 6: ULID (UNIVERSALLY UNIQUE LEXICOGRAPHICALLY SORTABLE ID)

```
  +-----------------------------------------------------------------+
  |                    ULID Layout (128-bit)                        |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  +-------------------------------+-----------------------------+|
  |  |  48-bit timestamp (ms)        |  80-bit randomness          ||
  |  |  (10 chars Crockford base32)  |  (16 chars Crockford b32)  | |
  |  +-------------------------------+-----------------------------+|
  |                                                                 |
  |  Example: 01ARZ3NDEKTSV4RRFFQ69G5FAV                            |
  |           |---------|  |---------------|                        |
  |           timestamp     randomness                              |
  |                                                                 |
  |  Properties:                                                    |
  |    - 128-bit, like UUID (compatible with UUID columns)          |
  |    - Lexicographically sortable (string comparison works!)      |
  |    - Crockford Base32 encoding (no ambiguous chars)             |
  |    - 26 characters (shorter than UUID's 36)                     |
  |    - Timestamp prefix > great B-tree index locality             |
  |    - No coordination needed                                     |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### APPROACH 7: SONYFLAKE

```
  +----------------------------------------------------------------+
  |               Sonyflake Layout (64-bit)                        |
  +----------------------------------------------------------------+
  |                                                                |
  |  +--------------------------------------+--------+----------+  |
  |  |  39-bit timestamp                    | 8-bit  | 16-bit   |  |
  |  |  (units of 10ms since epoch)         | seq    | machine  |  |
  |  +--------------------------------------+--------+----------+  |
  |                                                                |
  |  Key differences from Twitter Snowflake:                       |
  |    - Time unit = 10ms (not 1ms)                                |
  |    - 39 bits x 10ms = 174 years (vs Snowflake's 69 years)      |
  |    - 16-bit machine ID = 65,536 machines                       |
  |    - 8-bit sequence = 256 IDs per 10ms per machine             |
  |    - Trade-off: longer lifetime, more machines, lower burst    |
  |                                                                |
  +----------------------------------------------------------------+
```

## SECTION 4: DEEP DIVE: SNOWFLAKE ARCHITECTURE

### SYSTEM ARCHITECTURE

```
  +-----------------------------------------------------------------------+
  |                    Snowflake ID Service                               |
  +-----------------------------------------------------------------------+
  |                                                                       |
  |  +-----------------+    +-----------------+    +--------------------+ |
  |  |  App Server 1   |    |  App Server 2   |    |  App Server 3      | |
  |  +--------+--------+    +--------+--------+    +--------+-----------+ |
  |           |                      |                      |             |
  |           v                      v                      v             |
  |  +--------+--------+    +--------+--------+    +--------+-----------+ |
  |  | ID Generator     |    | ID Generator     |    | ID Generator     | |
  |  | (library/svc)   |    | (library/svc)   |    | (library/svc)      | |
  |  |                 |    |                 |    |                    | |
  |  | machineId = 1   |    | machineId = 2   |    | machineId = 3      | |
  |  | sequence  = 0   |    | sequence  = 0   |    | sequence  = 0      | |
  |  | lastTs    = ... |    | lastTs    = ... |    | lastTs    = ...    | |
  |  +-----------------+    +-----------------+    +--------------------+ |
  |                                                                       |
  |  No communication between generators!                                 |
  |  Each generates independently using its unique machineId.             |
  +-----------------------------------------------------------------------+
```

### WORKER REGISTRATION STRATEGIES

```
  +----------------------------------------------------------------+
  |              Worker / Machine ID Assignment                    |
  +----------------------------------------------------------------+
  |                                                                |
  |  Option A: Static Configuration                                |
  |    - Assign machine IDs via config file or env variable        |
  |    - Simple but manual; risky if IDs collide                   |
  |                                                                |
  |  Option B: ZooKeeper / etcd                                    |
  |    +------------------+                                        |
  |    |    ZooKeeper     |                                        |
  |    |  /snowflake/     |                                        |
  |    |    /worker-001   | <-- ephemeral node, machineId = 1      |
  |    |    /worker-002   | <-- ephemeral node, machineId = 2      |
  |    |    /worker-003   | <-- ephemeral node, machineId = 3      |
  |    +------------------+                                        |
  |    Worker registers on startup, gets next available ID.        |
  |    Ephemeral nodes auto-delete on disconnect.                  |
  |                                                                |
  |  Option C: Database Lease Table                                |
  |    Workers lease a machine ID from a DB table with TTL.        |
  |    Renew lease periodically. Reclaim expired leases.           |
  |                                                                |
  +----------------------------------------------------------------+
```

### SEQUENCE OVERFLOW HANDLING

```
  +----------------------------------------------------------------+
  |              Sequence Overflow (4096 IDs in 1ms)               |
  +----------------------------------------------------------------+
  |                                                                |
  |  Within a single millisecond:                                  |
  |                                                                |
  |  seq = 0    > ID generated                                     |
  |  seq = 1    > ID generated                                     |
  |  seq = 2    > ID generated                                     |
  |  ...                                                           |
  |  seq = 4095 > ID generated                                     |
  |  seq = 4096 > OVERFLOW! (12 bits can't hold this)              |
  |                                                                |
  |  Resolution: spin-wait until next millisecond                  |
  |                                                                |
  |  while (currentTimeMillis() <= lastTimestamp) {                |
  |      // busy wait                                              |
  |  }                                                             |
  |  sequence = 0;   // reset for new millisecond                  |
  |                                                                |
  |  This caps burst throughput at 4,096 IDs/ms/machine.           |
  |  In practice, 4M IDs/sec is more than enough.                  |
  |                                                                |
  +----------------------------------------------------------------+
```

### DATACENTER + WORKER ALLOCATION (10-BIT SPLIT)

```
  +----------------------------------------------------------------+
  |           10-bit Machine ID Split Options                      |
  +----------------------------------------------------------------+
  |                                                                |
  |  Option A: 5-bit datacenter + 5-bit worker                     |
  |    = 32 datacenters x 32 workers = 1,024 generators            |
  |                                                                |
  |    +-----+-----+                                               |
  |    | DC  | WKR |                                               |
  |    |00101|10011|  = datacenter 5, worker 19                    |
  |    +-----+-----+                                               |
  |                                                                |
  |  Option B: 10-bit worker (flat)                                |
  |    = 1,024 generators, no datacenter distinction               |
  |                                                                |
  |  Option C: 3-bit datacenter + 7-bit worker                     |
  |    = 8 datacenters x 128 workers = 1,024 generators            |
  |    Better if you have fewer DCs but more machines per DC.      |
  |                                                                |
  +----------------------------------------------------------------+
```

## SECTION 5: DEEP DIVE: CLOCK SYNCHRONIZATION

### THE CLOCK SKEW PROBLEM

```
  +-----------------------------------------------------------------+
  |                    Clock Skew Scenario                          |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  Time (real) ---------------------------------->                |
  |                                                                 |
  |  Server A:  100  101  102  103  104  ...                        |
  |  Server B:  100  101  102  98!  99   ...                        |
  |                           ^                                     |
  |                           |                                     |
  |                    NTP correction pushed                        |
  |                    clock backward by 4ms                        |
  |                                                                 |
  |  If Server B generates an ID at perceived time 98:              |
  |    - ID will have EARLIER timestamp than IDs already issued     |
  |    - Violates monotonicity guarantee                            |
  |    - Could cause duplicate if sequence wraps to same value      |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### NTP (NETWORK TIME PROTOCOL)

```
  +-----------------------------------------------------------------+
  |                    NTP Architecture                             |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  Stratum 0: Atomic clocks, GPS receivers                        |
  |       |                                                         |
  |       v                                                         |
  |  Stratum 1: Primary time servers (directly connected)           |
  |       |                                                         |
  |       v                                                         |
  |  Stratum 2: Secondary servers (sync from Stratum 1)             |
  |       |                                                         |
  |       v                                                         |
  |  Stratum 3: Your servers (sync from Stratum 2)                  |
  |                                                                 |
  |  Accuracy: ~1-10ms over internet, ~0.1-1ms on LAN               |
  |  Problem: NTP can step clock backward on correction             |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### SNOWFLAKE CLOCK SKEW HANDLING

```
  +-----------------------------------------------------------------+
  |              Snowflake's Defense Against Clock Skew             |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  if (currentTimestamp < lastTimestamp) {                        |
  |      // Clock went backward!                                    |
  |      long offset = lastTimestamp - currentTimestamp;            |
  |                                                                 |
  |      if (offset < TOLERANCE_MS) {    // e.g., 5ms               |
  |          // Small drift - wait it out                           |
  |          sleep(offset);                                         |
  |      } else {                                                   |
  |          // Large drift - refuse to generate                    |
  |          throw ClockMovedBackwardException();                   |
  |          // Alert ops team, investigate NTP                     |
  |      }                                                          |
  |  }                                                              |
  |                                                                 |
  |  Some implementations also:                                     |
  |    - Log the event for monitoring                               |
  |    - Switch to a standby generator                              |
  |    - Use logical clocks as fallback                             |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### GOOGLE TRUETIME

```
  +-----------------------------------------------------------------+
  |                    Google TrueTime                              |
  +-----------------------------------------------------------------+
  |                                                                 |
  |  Instead of returning a single timestamp, TrueTime returns      |
  |  an INTERVAL: [earliest, latest]                                |
  |                                                                 |
  |  API: TT.now() > TTinterval { earliest, latest }                |
  |       TT.after(t) > true if t is definitely in the past         |
  |       TT.before(t) > true if t is definitely in the future      |
  |                                                                 |
  |  Hardware:                                                      |
  |    +-------------------+    +-------------------+               |
  |    |   GPS Receiver    |    |  Atomic Clock     |               |
  |    |   (per DC)        |    |  (per DC)         |               |
  |    +--------+----------+    +--------+----------+               |
  |             |                        |                          |
  |             v                        v                          |
  |    +--------+------------------------+----------+               |
  |    |           Time Master Servers              |               |
  |    |    (cross-reference GPS + atomic)          |               |
  |    +--------------------+-----------------------+               |
  |                         |                                       |
  |                         v                                       |
  |    +--------------------+-----------------------+               |
  |    |         TrueTime Client Library            |               |
  |    |    Uncertainty: typically 1-7ms             |              |
  |    +--------------------------------------------+               |
  |                                                                 |
  |  Used by Google Spanner for globally consistent transactions.   |
  |  Spanner waits out the uncertainty interval before committing,  |
  |  guaranteeing that if T1 commits before T2 starts,              |
  |  then T1's timestamp < T2's timestamp.                          |
  |                                                                 |
  +-----------------------------------------------------------------+
```

### FACEBOOK'S APPROACH

```
  +----------------------------------------------------------------+
  |              Facebook Time Synchronization                     |
  +----------------------------------------------------------------+
  |                                                                |
  |  - Uses NTP but with SMEARING (gradual adjustment)             |
  |  - Instead of stepping clock backward by 5ms instantly:        |
  |      Slow the clock down slightly over minutes/hours           |
  |      so it naturally "catches up" without going backward       |
  |                                                                |
  |  - Deployed dedicated time servers in every datacenter         |
  |  - Monitors clock drift per machine                            |
  |  - Achieves sub-millisecond accuracy within a DC               |
  |                                                                |
  +----------------------------------------------------------------+
```

## SECTION 6: COMPARISON TABLE

```
  +------------------+----------+-----------+---------+------------+-------------+
  |                  | UUID v4  | Snowflake | ULID    | DB Auto-   | Sonyflake   |
  |                  |          |           |         | Increment  |             |
  +------------------+----------+-----------+---------+------------+-------------+
  | Size             | 128-bit  | 64-bit    | 128-bit | 64-bit     | 64-bit      |
  +------------------+----------+-----------+---------+------------+-------------+
  | Time-Sortable    | No       | Yes       | Yes     | Yes        | Yes         |
  +------------------+----------+-----------+---------+------------+-------------+
  | Coordination-    | Yes      | Yes       | Yes     | No (needs  | Yes         |
  | Free             | (great)  | (once for | (great) | central DB)| (once for   |
  |                  |          | machineId)|         |            | machineId)  |
  +------------------+----------+-----------+---------+------------+-------------+
  | Throughput       | Very     | ~4M/sec   | Very    | ~1-10K/sec | ~25K/sec    |
  | (per node)       | High     | /machine  | High    | (DB-bound) | /machine    |
  +------------------+----------+-----------+---------+------------+-------------+
  | DB Index         | Poor     | Excellent | Good    | Excellent  | Excellent   |
  | Friendliness     | (random) | (sorted)  |(sorted) | (seq)      | (sorted)    |
  +------------------+----------+-----------+---------+------------+-------------+
  | Max Lifetime     | N/A      | ~69 yrs   | N/A     | N/A        | ~174 yrs    |
  +------------------+----------+-----------+---------+------------+-------------+
  | Collision Risk   | ~2^-122  | None (if  | ~2^-80  | None       | None (if    |
  |                  |          | configured)|per ms  |            | configured) |
  +------------------+----------+-----------+---------+------------+-------------+
  | Globally         | No       | Roughly   | Yes     | Yes        | Roughly     |
  | Ordered          |          | (within   |         | (strict)   |             |
  |                  |          | machine)  |         |            |             |
  +------------------+----------+-----------+---------+------------+-------------+
```

## SECTION 7: USE CASES - WHEN TO PICK WHICH

```
  +--------------------------------------------------------------------+
  |                    Decision Guide                                  |
  +--------------------------------------------------------------------+
  |                                                                    |
  |  Need 64-bit + sorted + high throughput?                           |
  |    > Twitter Snowflake / Sonyflake                                 |
  |                                                                    |
  |  Need UUID-compatible but sortable?                                |
  |    > ULID or UUID v7                                               |
  |                                                                    |
  |  Simple system, single DB, low scale?                              |
  |    > Database auto-increment                                       |
  |                                                                    |
  |  Need HA with minimal complexity?                                  |
  |    > Flickr ticket servers                                         |
  |                                                                    |
  |  Zero coordination, don't care about size?                         |
  |    > UUID v4                                                       |
  |                                                                    |
  |  Long operational lifetime (100+ years)?                           |
  |    > Sonyflake (174 years)                                         |
  |                                                                    |
  |  Each DB shard generates its own IDs?                              |
  |    > Instagram approach (shard ID embedded)                        |
  |                                                                    |
  +--------------------------------------------------------------------+
```

```
  Real-World Usage:                                                 

  +----------------------------+-----------------------------------+
  |  Company / System          |  Approach Used                    |
  +----------------------------+-----------------------------------+
  |  Twitter                   |  Snowflake (original)             |
  |  Discord                   |  Snowflake variant                |
  |  Instagram                 |  Snowflake + shard ID in PG       |
  |  Flickr                    |  Ticket servers (MySQL)           |
  |  MongoDB                   |  ObjectId (timestamp + random)    |
  |  Cassandra                 |  TimeUUID (UUID v1 variant)       |
  |  Google Spanner            |  TrueTime-based                   |
  |  Segment                   |  KSUID (timestamp + random)       |
  +----------------------------+-----------------------------------+
```

## SECTION 8: FULL SYSTEM DIAGRAM

```
  +====================================================================--+
  |              COMPLETE SNOWFLAKE ID GENERATION SYSTEM                 |
  +====================================================================--+
  |                                                                      |
  |  +------------------+                                                |
  |  | ZooKeeper / etcd |  (worker registration & machine ID lease)      |
  |  +--------+---------+                                                |
  |           |                                                          |
  |           | assigns machineId on startup                             |
  |           |                                                          |
  |  +--------v---------+    +------------------+  +------------------+  |
  |  |  ID Gen Worker 1 |    |  ID Gen Worker 2 |  |  ID Gen Worker N |  |
  |  |  machineId = 1   |    |  machineId = 2   |  |  machineId = N   |  |
  |  |                  |    |                  |  |                  |  |
  |  |  +------------+  |    |  +------------+  |  |  +------------+  |  |
  |  |  | Clock      |  |    |  | Clock      |  |  |  | Clock      |  |  |
  |  |  | Sequence   |  |    |  | Sequence   |  |  |  | Sequence   |  |  |
  |  |  | lastTs     |  |    |  | lastTs     |  |  |  | lastTs     |  |  |
  |  |  +------------+  |    |  +------------+  |  |  +------------+  |  |
  |  +--------+---------+    +--------+---------+  +--------+---------+  |
  |           |                       |                     |            |
  |           v                       v                     v            |
  |  +--------+--------+    +--------+--------+   +--------+-----------+ |
  |  | App / Service A  |    | App / Service B  |   | App / Service C  | |
  |  | (gets IDs via    |    | (gets IDs via    |   | (gets IDs via    | |
  |  |  library call    |    |  library call    |   |  library call    | |
  |  |  or RPC)         |    |  or RPC)         |   |  or RPC)         | |
  |  +-----------------+    +-----------------+   +--------------------+ |
  |                                                                      |
  |  Deployment Options:                                                 |
  |    A. Embedded library - each service has its own generator          |
  |    B. Standalone service - centralized ID service with RPC API       |
  |                                                                      |
  +====================================================================--+
```

## SECTION 9: INTERVIEW Q&A

### Q1: Why not just use UUIDs everywhere?

```
  +-----------------------------------------------------------------+
  |  UUIDs are 128-bit - double the storage of a 64-bit Snowflake   |
  |  ID. For tables with billions of rows, this matters.            |
  |                                                                 |
  |  UUID v4 is random, meaning:                                    |
  |    - B-tree index inserts scatter across all leaf pages         |
  |    - Poor cache locality, frequent page splits                  |
  |    - Significantly slower write performance at scale            |
  |                                                                 |
  |  UUID v4 is not sortable, so you can't efficiently query        |
  |  "all records created after time T" using the ID alone.         |
  |                                                                 |
  |  For systems that need compact, sortable, indexed IDs with      |
  |  high throughput, Snowflake-style IDs are far superior.         |
  +-----------------------------------------------------------------+
```

### Q2: What happens if the clock goes backward on a Snowflake worker?

```
  +-----------------------------------------------------------------+
  |  The generator detects it: currentTs < lastTimestamp.           |
  |                                                                 |
  |  Options:                                                       |
  |    1. Small drift (< 5ms): spin-wait until clock catches up     |
  |    2. Large drift: throw an error, refuse to generate IDs       |
  |    3. Alert the ops team - NTP misconfiguration likely          |
  |    4. Some systems switch to a standby generator                |
  |                                                                 |
  |  NEVER generate an ID with a backward timestamp - this would    |
  |  break the monotonicity guarantee and could cause duplicates    |
  |  if the sequence counter reaches the same value.                |
  +-----------------------------------------------------------------+
```

### Q3: How do you assign machine IDs in a containerized (Kubernetes) environment?

```
  +----------------------------------------------------------------+
  |  Containers are ephemeral - static config doesn't work.        |
  |                                                                |
  |  Approaches:                                                   |
  |    1. ZooKeeper/etcd: register on startup, get next free ID    |
  |       with ephemeral nodes or TTL-based leases                 |
  |    2. Database lease table: claim a row with TTL, renew        |
  |       periodically, reclaim expired leases                     |
  |    3. Hash of pod IP or hostname (mod 1024) - simple but       |
  |       risk of collision; mitigate with collision detection     |
  |    4. StatefulSet ordinal index in Kubernetes (pod-0 = 0,      |
  |       pod-1 = 1, ...) - stable identities across restarts      |
  +----------------------------------------------------------------+
```

### Q4: Can two Snowflake workers generate the same ID?

```
  +----------------------------------------------------------------+
  |  Only if they have the SAME machine ID - which is a            |
  |  configuration bug.                                            |
  |                                                                |
  |  If machine IDs are unique, IDs are guaranteed unique because: |
  |    - Same machine, same ms: sequence number differs            |
  |    - Same machine, different ms: timestamp differs             |
  |    - Different machines: machine ID field differs              |
  |                                                                |
  |  This is why machine ID assignment is critical - use           |
  |  ZooKeeper or a lease mechanism, never manual assignment       |
  |  at scale.                                                     |
  +----------------------------------------------------------------+
```

### Q5: What is the maximum throughput of a single Snowflake worker?

```
  +----------------------------------------------------------------+
  |  12-bit sequence = 4,096 values per millisecond                |
  |  = 4,096 x 1,000 = 4,096,000 IDs per second per worker         |
  |                                                                |
  |  With 1,024 workers: ~4 billion IDs per second total.          |
  |                                                                |
  |  In practice, each ID generation is a simple bit-shift and     |
  |  OR operation (no I/O, no network) - actual throughput is      |
  |  often limited by the caller, not the generator.               |
  +----------------------------------------------------------------+
```

### Q6: How does Snowflake compare to ULID for a new project?

```
  +----------------------------------------------------------------+
  |  Snowflake (64-bit):                                           |
  |    + Compact, fits in BIGINT column                            |
  |    + Perfect for high-throughput systems                       |
  |    + Zero collision by design (with unique machine IDs)        |
  |    - Requires machine ID coordination (once at startup)        |
  |    - 69-year lifetime limit                                    |
  |                                                                |
  |  ULID (128-bit):                                               |
  |    + No coordination at all                                    |
  |    + Lexicographically sortable as strings                     |
  |    + Compatible with UUID columns                              |
  |    + Longer effective lifetime                                 |
  |    - 128-bit, double the storage                               |
  |    - Tiny collision probability (80 bits random per ms)        |
  |    - Slightly worse for numeric comparisons                    |
  |                                                                |
  |  Rule of thumb:                                                |
  |    Backend service IDs, event streams > Snowflake              |
  |    Public-facing IDs, UUID-compat needed > ULID or UUID v7     |
  +----------------------------------------------------------------+
```

### Q7: What is the significance of the custom epoch in Snowflake?

```
  +----------------------------------------------------------------+
  |  The 41-bit timestamp stores milliseconds since a CUSTOM       |
  |  epoch, not the Unix epoch (Jan 1, 1970).                      |
  |                                                                |
  |  Why? The Unix epoch wastes bits on timestamps from 1970       |
  |  to your system's launch date.                                 |
  |                                                                |
  |  Twitter's epoch: Nov 4, 2010 (when Snowflake launched)        |
  |                                                                |
  |  2^41 ms = 2,199,023,255,552 ms ~ 69.7 years                   |
  |                                                                |
  |  By using a recent custom epoch, you maximize the usable       |
  |  lifetime. If your system launches in 2025 with a 2025         |
  |  epoch, you get IDs until ~2094.                               |
  +----------------------------------------------------------------+
```

### Q8: How would you handle a multi-region deployment?

```
  +----------------------------------------------------------------+
  |  Use the datacenter bits in the machine ID field.              |
  |                                                                |
  |  Example with 5-bit DC + 5-bit worker:                         |
  |    US-East: DC=1, workers 0-31                                 |
  |    US-West: DC=2, workers 0-31                                 |
  |    EU:      DC=3, workers 0-31                                 |
  |    Asia:    DC=4, workers 0-31                                 |
  |                                                                |
  |  IDs from different regions are automatically unique.          |
  |  Within a region, IDs are perfectly time-ordered.              |
  |  Across regions, IDs are roughly time-ordered (within          |
  |  clock skew between DCs, typically a few ms with good NTP).    |
  |                                                                |
  |  For strict global ordering, you'd need something like         |
  |  Google TrueTime - but most systems don't need that.           |
  +----------------------------------------------------------------+
```

### Q9: What are recording/pre-allocated ID ranges and when would you use them?

```
  +----------------------------------------------------------------+
  |  Some systems pre-allocate ID ranges to reduce coordination:   |
  |                                                                |
  |  Coordinator assigns:                                          |
  |    Worker A > range [1000, 1999]                               |
  |    Worker B > range [2000, 2999]                               |
  |    Worker C > range [3000, 3999]                               |
  |                                                                |
  |  Each worker increments within its range locally.              |
  |  When range is exhausted, request a new range.                 |
  |                                                                |
  |  Pros: Simple, no per-ID coordination                          |
  |  Cons: Gaps if a worker crashes mid-range,                     |
  |        not time-sortable across workers                        |
  |                                                                |
  |  Used by: Google Bigtable, some batch processing systems.      |
  |  Not ideal when time-ordering is a requirement.                |
  +----------------------------------------------------------------+
```

### Q10: If you were designing a new system today, which approach would you pick?

```
  +----------------------------------------------------------------+
  |  It depends on constraints:                                    |
  |                                                                |
  |  "I need 64-bit, sorted IDs for a high-throughput backend"     |
  |    > Snowflake. Battle-tested, simple, fast.                   |
  |                                                                |
  |  "I need IDs that look like UUIDs but are sortable"            |
  |    > UUID v7 (if standard matters) or ULID (if not).           |
  |                                                                |
  |  "I have a single database and < 10K writes/sec"               |
  |    > Auto-increment. Don't over-engineer.                      |
  |                                                                |
  |  "I'm building a globally distributed system like Spanner"     |
  |    > TrueTime-based approach with commit-wait.                 |
  |                                                                |
  |  Default recommendation for most distributed systems:          |
  |    Snowflake variant with ZooKeeper for worker registration.   |
  |    Simple, proven, handles millions of IDs/sec.                |
  +----------------------------------------------------------------+
```

## SECTION 10: SUMMARY

```
  +================================================================-+
  |  KEY TAKEAWAYS                                                  |
  +================================================================-+
  |                                                                 |
  |  1. Auto-increment is a SPOF - doesn't scale horizontally       |
  |  2. UUID v4 is easy but wastes space and kills DB indexes       |
  |  3. Snowflake is the gold standard for 64-bit distributed IDs   |
  |  4. The 41+10+12 bit layout balances time, machines, and        |
  |     throughput                                                  |
  |  5. Clock skew is the main operational concern - detect and     |
  |     refuse, never generate backward timestamps                  |
  |  6. Machine ID assignment needs coordination ONCE at startup    |
  |  7. ULID/UUID v7 are great alternatives when 128-bit is OK      |
  |  8. Choose based on your constraints: size, sortability,        |
  |     coordination tolerance, and throughput needs                |
  |                                                                 |
  +================================================================-+
```
