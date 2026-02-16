================================================================================
         CHAPTER 6: SHARDING AND REPLICATION
         Distributing Data Across Multiple Nodes
================================================================================

As data grows beyond what a single server can handle, we must distribute
it across multiple machines. Sharding and replication are the two
fundamental techniques for this.


================================================================================
SECTION 6.1: REPLICATION
================================================================================

THE CONCEPT
───────────

Replication means keeping copies of data on multiple machines.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WHY REPLICATE?                                                        │
    │                                                                         │
    │  1. HIGH AVAILABILITY                                                  │
    │     If one server dies, others can serve requests                     │
    │     No single point of failure                                        │
    │                                                                         │
    │  2. INCREASED READ THROUGHPUT                                          │
    │     Multiple servers can handle read requests                         │
    │     Scale reads horizontally                                          │
    │                                                                         │
    │  3. GEOGRAPHIC DISTRIBUTION                                            │
    │     Keep data close to users                                          │
    │     Reduce latency for global applications                            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


REPLICATION ARCHITECTURES
─────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  1. LEADER-FOLLOWER (Master-Slave)                                    │
    │  ═════════════════════════════════                                      │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Writes ────► LEADER (Primary/Master)                          │  │
    │  │                   │                                             │  │
    │  │                   │ Replication Stream                          │  │
    │  │                   │                                             │  │
    │  │              ┌────┴────┬───────────┐                           │  │
    │  │              ▼         ▼           ▼                           │  │
    │  │          Follower  Follower   Follower                        │  │
    │  │          (Replica) (Replica)  (Replica)                       │  │
    │  │              ▲         ▲           ▲                           │  │
    │  │              └────┬────┴───────────┘                           │  │
    │  │                   │                                             │  │
    │  │  Reads ───────────┘                                            │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  HOW IT WORKS:                                                         │
    │  • All writes go to leader                                            │
    │  • Leader writes to local storage                                     │
    │  • Leader sends changes to followers (replication log)               │
    │  • Followers apply changes to their storage                          │
    │  • Reads can go to leader or any follower                            │
    │                                                                         │
    │  USED BY: PostgreSQL, MySQL, MongoDB, Redis Sentinel                  │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  SYNCHRONOUS vs ASYNCHRONOUS REPLICATION                              │
    │                                                                         │
    │  SYNCHRONOUS:                                                          │
    │  ┌──────────────────────────────────────────────────────────────────┐ │
    │  │ Client → Write → Leader                                         │ │
    │  │                     │                                            │ │
    │  │                     ├──► Follower 1 ──► ACK ──┐                 │ │
    │  │                     ├──► Follower 2 ──► ACK ──┤                 │ │
    │  │                     └──► Follower 3 ──► ACK ──┤                 │ │
    │  │                                               │                  │ │
    │  │ Client ◄── Success ◄── Wait for all ACKs ◄───┘                 │ │
    │  └──────────────────────────────────────────────────────────────────┘ │
    │                                                                         │
    │  PROS: No data loss, strong consistency                               │
    │  CONS: Higher latency, leader blocked if follower slow               │
    │                                                                         │
    │  ASYNCHRONOUS:                                                         │
    │  ┌──────────────────────────────────────────────────────────────────┐ │
    │  │ Client → Write → Leader → Success immediately                   │ │
    │  │                     │                                            │ │
    │  │                     └──► Followers (eventually)                 │ │
    │  └──────────────────────────────────────────────────────────────────┘ │
    │                                                                         │
    │  PROS: Lower latency, leader not blocked                              │
    │  CONS: Data loss possible, eventual consistency                       │
    │                                                                         │
    │  SEMI-SYNCHRONOUS (Common compromise):                                │
    │  Wait for 1 follower ACK, replicate to others async                  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  2. LEADER-LEADER (Multi-Master)                                      │
    │  ═══════════════════════════════                                        │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │         ┌─────────────┐        ┌─────────────┐                 │  │
    │  │  Writes │   Leader 1  │◄──────►│   Leader 2  │ Writes         │  │
    │  │   ────► │ (US-East)   │        │ (EU-West)   │ ◄────          │  │
    │  │         └─────────────┘        └─────────────┘                 │  │
    │  │                │                      │                        │  │
    │  │                │  Bidirectional       │                        │  │
    │  │                │  Replication         │                        │  │
    │  │                │                      │                        │  │
    │  │                ▼                      ▼                        │  │
    │  │         [US Users]              [EU Users]                     │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  USE CASE: Multi-region deployments where writes can happen anywhere  │
    │                                                                         │
    │  CHALLENGE: WRITE CONFLICTS!                                          │
    │                                                                         │
    │  Scenario:                                                             │
    │  • Leader 1: UPDATE users SET name='Alice' WHERE id=1                │
    │  • Leader 2: UPDATE users SET name='Alicia' WHERE id=1               │
    │  • Both happen simultaneously before replication                      │
    │  → Which value wins?                                                  │
    │                                                                         │
    │  CONFLICT RESOLUTION:                                                  │
    │  • Last-Write-Wins (timestamp)                                        │
    │  • Custom conflict resolution (application logic)                     │
    │  • Conflict-free data types (CRDTs)                                  │
    │                                                                         │
    │  GENERALLY AVOIDED: Too complex for most applications                 │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  3. LEADERLESS REPLICATION                                            │
    │  ════════════════════════════                                           │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Client writes to multiple nodes simultaneously                │  │
    │  │                                                                 │  │
    │  │         ┌───────────────────────────────────────────┐          │  │
    │  │         │                                           │          │  │
    │  │         ▼              ▼              ▼             │          │  │
    │  │    ┌─────────┐   ┌─────────┐   ┌─────────┐         │          │  │
    │  │    │ Node 1  │   │ Node 2  │   │ Node 3  │  ◄──────┘          │  │
    │  │    └─────────┘   └─────────┘   └─────────┘                     │  │
    │  │         │              │              │                        │  │
    │  │         └──────────────┼──────────────┘                        │  │
    │  │                        │                                       │  │
    │  │         Client reads from multiple nodes                       │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  QUORUM READS AND WRITES:                                             │
    │                                                                         │
    │  N = Total nodes                                                       │
    │  W = Nodes that must acknowledge write                                │
    │  R = Nodes that must respond to read                                  │
    │                                                                         │
    │  RULE: W + R > N ensures we read at least one node with latest data  │
    │                                                                         │
    │  EXAMPLE (N=3):                                                        │
    │  • W=2, R=2: Write to 2 nodes, read from 2 nodes                     │
    │  • At least 1 node overlaps → guaranteed to see latest value         │
    │                                                                         │
    │  USED BY: DynamoDB, Cassandra, Riak                                   │
    │                                                                         │
    │  PROS:                                                                 │
    │  ✓ No single point of failure (no leader election)                   │
    │  ✓ High availability                                                 │
    │  ✓ Good for write-heavy workloads                                    │
    │                                                                         │
    │  CONS:                                                                 │
    │  ✗ Higher read/write latency (multiple nodes)                        │
    │  ✗ More complex consistency handling                                 │
    │  ✗ Conflict resolution needed                                        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


HANDLING LEADER FAILURES
────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  FAILOVER PROCESS                                                      │
    │                                                                         │
    │  1. DETECT FAILURE                                                     │
    │     Heartbeat timeout (e.g., no response for 30 seconds)              │
    │                                                                         │
    │  2. ELECT NEW LEADER                                                   │
    │     Consensus algorithm (Raft, Paxos)                                 │
    │     Or promotion based on most recent data                            │
    │                                                                         │
    │  3. RECONFIGURE SYSTEM                                                 │
    │     Update routing to point to new leader                             │
    │     Other followers replicate from new leader                         │
    │                                                                         │
    │  CHALLENGES:                                                           │
    │                                                                         │
    │  • Split-brain: Two nodes think they're leader                       │
    │    Solution: Fencing (STONITH), quorum-based decisions               │
    │                                                                         │
    │  • Data loss: Async replication → unreplicated writes lost           │
    │    Solution: Sync replication (at cost of latency)                   │
    │                                                                         │
    │  • Replication lag: New leader may be behind                         │
    │    Solution: Promote follower with most recent data                  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 6.2: SHARDING (PARTITIONING)
================================================================================

THE CONCEPT
───────────

Sharding splits data across multiple databases, each holding a subset.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WHY SHARD?                                                            │
    │                                                                         │
    │  Replication copies ALL data to each node.                            │
    │  Fine for read scaling, but:                                          │
    │  • Every node needs enough storage for all data                       │
    │  • Every write goes to every node                                     │
    │  • Can't scale writes                                                 │
    │                                                                         │
    │  Sharding distributes data:                                           │
    │  • Each node stores a subset of data                                  │
    │  • Writes are distributed across shards                               │
    │  • Can scale both reads AND writes                                    │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  BEFORE SHARDING:                                              │  │
    │  │                                                                 │  │
    │  │  ┌─────────────────────────────────────────────────────────┐   │  │
    │  │  │              Single Database                            │   │  │
    │  │  │              10TB of data                               │   │  │
    │  │  │              100K writes/sec (bottleneck!)              │   │  │
    │  │  └─────────────────────────────────────────────────────────┘   │  │
    │  │                                                                 │  │
    │  │  AFTER SHARDING (4 shards):                                    │  │
    │  │                                                                 │  │
    │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │  │
    │  │  │ Shard 1  │ │ Shard 2  │ │ Shard 3  │ │ Shard 4  │         │  │
    │  │  │   2.5TB  │ │   2.5TB  │ │   2.5TB  │ │   2.5TB  │         │  │
    │  │  │  25K w/s │ │  25K w/s │ │  25K w/s │ │  25K w/s │         │  │
    │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │  │
    │  │                                                                 │  │
    │  │  Total: 4 × 25K = 100K writes/sec                              │  │
    │  │  Each shard is smaller and faster                              │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


SHARDING STRATEGIES
───────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  1. RANGE-BASED SHARDING                                              │
    │  ════════════════════════                                               │
    │                                                                         │
    │  Assign ranges of keys to each shard.                                 │
    │                                                                         │
    │  user_id 1-1,000,000       → Shard 1                                  │
    │  user_id 1,000,001-2,000,000 → Shard 2                                │
    │  user_id 2,000,001-3,000,000 → Shard 3                                │
    │                                                                         │
    │  PROS:                                                                 │
    │  ✓ Range queries are efficient (all data on one shard)               │
    │  ✓ Easy to understand                                                 │
    │                                                                         │
    │  CONS:                                                                 │
    │  ✗ Hot spots: Recent users (high IDs) hit one shard                  │
    │  ✗ Uneven distribution if data isn't uniform                         │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  2. HASH-BASED SHARDING                                               │
    │  ═══════════════════════                                                │
    │                                                                         │
    │  Hash the key and use modulo to select shard.                         │
    │                                                                         │
    │  shard = hash(user_id) % num_shards                                   │
    │                                                                         │
    │  user_id 12345 → hash(12345) = 98765 → 98765 % 4 = 1 → Shard 1      │
    │  user_id 67890 → hash(67890) = 54321 → 54321 % 4 = 1 → Shard 1      │
    │  user_id 11111 → hash(11111) = 22222 → 22222 % 4 = 2 → Shard 2      │
    │                                                                         │
    │  PROS:                                                                 │
    │  ✓ Even distribution across shards                                   │
    │  ✓ No hot spots                                                       │
    │                                                                         │
    │  CONS:                                                                 │
    │  ✗ Range queries require hitting all shards                          │
    │  ✗ Adding/removing shards requires resharding (expensive!)           │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  3. CONSISTENT HASHING                                                │
    │  ══════════════════════                                                 │
    │                                                                         │
    │  Solves the resharding problem of simple hash-based sharding.         │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │                        HASH RING                               │  │
    │  │                                                                 │  │
    │  │                          0°                                    │  │
    │  │                     ┌────●────┐                                │  │
    │  │                    ╱   Node A  ╲                               │  │
    │  │                   ╱             ╲                              │  │
    │  │              270°●               ● 90°                         │  │
    │  │              Node D             Node B                         │  │
    │  │                   ╲             ╱                              │  │
    │  │                    ╲   Node C  ╱                               │  │
    │  │                     └────●────┘                                │  │
    │  │                         180°                                   │  │
    │  │                                                                 │  │
    │  │  Keys are hashed onto the ring.                               │  │
    │  │  Walk clockwise to find the node that owns the key.           │  │
    │  │                                                                 │  │
    │  │  Key at 45° → walk clockwise → Node B (at 90°)               │  │
    │  │  Key at 200° → walk clockwise → Node D (at 270°)             │  │
    │  │                                                                 │  │
    │  │  ADDING A NODE:                                                │  │
    │  │  Only keys between previous node and new node need to move    │  │
    │  │  (not all keys like in hash-based sharding!)                  │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  USED BY: DynamoDB, Cassandra, Riak, Memcached                        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


CONSISTENT HASHING DEEP DIVE
────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WHY CONSISTENT HASHING?                                              │
    │                                                                         │
    │  PROBLEM WITH SIMPLE HASH MODULO:                                     │
    │                                                                         │
    │  server = hash(key) % N    (N = number of servers)                   │
    │                                                                         │
    │  With 4 servers (N=4):                                                │
    │  hash("user1") = 14 → 14 % 4 = 2 → Server 2                         │
    │  hash("user2") = 23 → 23 % 4 = 3 → Server 3                         │
    │                                                                         │
    │  ADD 1 SERVER (N=5):                                                  │
    │  hash("user1") = 14 → 14 % 5 = 4 → Server 4 (MOVED!)               │
    │  hash("user2") = 23 → 23 % 5 = 3 → Server 3 (same)                 │
    │                                                                         │
    │  RESULT: ~80% of keys need to be remapped! (N-1)/N keys move        │
    │                                                                         │
    │  This causes:                                                          │
    │  • Cache misses (all cached data in wrong place)                     │
    │  • Massive data transfer during resharding                           │
    │  • Service degradation                                                │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  HOW CONSISTENT HASHING WORKS                                         │
    │                                                                         │
    │  STEP 1: Create a hash ring (0 to 2^32 - 1)                          │
    │                                                                         │
    │              0                                                         │
    │              │                                                         │
    │       ┌──────┴──────┐                                                 │
    │       │             │                                                 │
    │    2^31          2^30                                                  │
    │       │             │                                                 │
    │       └──────┬──────┘                                                 │
    │              │                                                         │
    │            2^32-1 (wraps to 0)                                        │
    │                                                                         │
    │  STEP 2: Place servers on the ring                                    │
    │  Server position = hash(server_id)                                   │
    │                                                                         │
    │                    0                                                   │
    │                    │                                                   │
    │              ●─────┴─────●  Server A (pos: 500M)                      │
    │             /             \                                            │
    │   Server D ●               ● Server B (pos: 1.5B)                    │
    │   (pos: 3B) \             /                                           │
    │              ●─────┬─────●                                            │
    │                    │                                                   │
    │              Server C (pos: 2.5B)                                    │
    │                                                                         │
    │  STEP 3: Place keys on the ring                                       │
    │  Key position = hash(key)                                            │
    │  Walk CLOCKWISE to find owning server                                │
    │                                                                         │
    │  hash("user1") = 700M → clockwise → Server B (at 1.5B)              │
    │  hash("user2") = 2.8B → clockwise → Server D (at 3B)                │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  ADDING A SERVER                                                       │
    │                                                                         │
    │  Add Server E at position 2B (between B and C)                       │
    │                                                                         │
    │  BEFORE:                          AFTER:                              │
    │  Keys 1.5B-2.5B → Server C        Keys 1.5B-2B → Server E           │
    │                                   Keys 2B-2.5B → Server C            │
    │                                                                         │
    │  Only keys between B (1.5B) and E (2B) move!                        │
    │  = 1/N keys move (not N-1/N)                                        │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  VIRTUAL NODES (VNODES)                                               │
    │                                                                         │
    │  PROBLEM: With few physical servers, distribution is uneven          │
    │                                                                         │
    │  Server A: 10% of keys                                               │
    │  Server B: 50% of keys  ← HOT SPOT!                                 │
    │  Server C: 40% of keys                                               │
    │                                                                         │
    │  SOLUTION: Each physical server → multiple virtual nodes             │
    │                                                                         │
    │  Physical Server A → Virtual: A1, A2, A3, A4, A5 (5 positions)      │
    │  Physical Server B → Virtual: B1, B2, B3, B4, B5 (5 positions)      │
    │  Physical Server C → Virtual: C1, C2, C3, C4, C5 (5 positions)      │
    │                                                                         │
    │               0                                                        │
    │          B3 ──┼── A1                                                  │
    │             ╲ │ ╱                                                      │
    │        C2 ──(●)── B1                                                  │
    │             ╱ │ ╲                                                      │
    │          A3 ──┼── C1                                                  │
    │               │                                                        │
    │        (15 virtual nodes spread evenly)                              │
    │                                                                         │
    │  BENEFITS:                                                             │
    │  ✓ More even distribution                                            │
    │  ✓ Smaller servers can have fewer vnodes                            │
    │  ✓ When server fails, load spreads to multiple servers              │
    │                                                                         │
    │  TYPICAL: 100-200 virtual nodes per physical server                  │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  CONSISTENT HASHING IMPLEMENTATION                                    │
    │                                                                         │
    │  class ConsistentHash:                                                 │
    │      def __init__(self, nodes, replicas=100):                        │
    │          self.ring = SortedDict()  # position → node                 │
    │          self.replicas = replicas                                     │
    │                                                                         │
    │          for node in nodes:                                           │
    │              self.add_node(node)                                      │
    │                                                                         │
    │      def add_node(self, node):                                        │
    │          for i in range(self.replicas):                              │
    │              key = f"{node}:{i}"                                     │
    │              position = hash(key) % (2**32)                          │
    │              self.ring[position] = node                              │
    │                                                                         │
    │      def remove_node(self, node):                                     │
    │          for i in range(self.replicas):                              │
    │              key = f"{node}:{i}"                                     │
    │              position = hash(key) % (2**32)                          │
    │              del self.ring[position]                                 │
    │                                                                         │
    │      def get_node(self, key):                                         │
    │          if not self.ring:                                            │
    │              return None                                               │
    │          position = hash(key) % (2**32)                              │
    │          # Find first node clockwise from position                   │
    │          for ring_pos in self.ring.keys():                          │
    │              if ring_pos >= position:                                │
    │                  return self.ring[ring_pos]                          │
    │          # Wrap around to first node                                 │
    │          return self.ring.peekitem(0)[1]                            │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  REPLICATION WITH CONSISTENT HASHING                                  │
    │                                                                         │
    │  Store data on N consecutive nodes (clockwise)                       │
    │                                                                         │
    │  With replication factor = 3:                                        │
    │  Key at position X:                                                   │
    │  - Primary: First node clockwise                                     │
    │  - Replica 1: Second node clockwise                                  │
    │  - Replica 2: Third node clockwise                                   │
    │                                                                         │
    │  DynamoDB, Cassandra use this approach                               │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  4. DIRECTORY-BASED SHARDING                                          │
    │  ════════════════════════════                                           │
    │                                                                         │
    │  A lookup service maintains key → shard mapping.                      │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Client ──► Directory Service ──► Which shard?                 │  │
    │  │                     │                                           │  │
    │  │                     ▼                                           │  │
    │  │  ┌────────────────────────────────────────────────────────┐    │  │
    │  │  │  user:1 → Shard A                                      │    │  │
    │  │  │  user:2 → Shard B                                      │    │  │
    │  │  │  user:3 → Shard A                                      │    │  │
    │  │  │  ...                                                   │    │  │
    │  │  └────────────────────────────────────────────────────────┘    │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  PROS:                                                                 │
    │  ✓ Maximum flexibility                                               │
    │  ✓ Easy to rebalance by updating directory                           │
    │                                                                         │
    │  CONS:                                                                 │
    │  ✗ Directory is single point of failure                              │
    │  ✗ Extra hop for every request                                       │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


CHOOSING A SHARD KEY
────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  SHARD KEY SELECTION                                                   │
    │                                                                         │
    │  The shard key determines which shard stores a record.                │
    │  Choose carefully - it's hard to change later!                        │
    │                                                                         │
    │  GOOD SHARD KEY:                                                       │
    │  • High cardinality (many unique values)                              │
    │  • Even distribution                                                  │
    │  • Matches query patterns                                             │
    │                                                                         │
    │  EXAMPLES:                                                             │
    │                                                                         │
    │  E-COMMERCE (Orders table):                                           │
    │  ───────────────────────────                                            │
    │  ✗ order_date: Hot spots on recent dates                             │
    │  ✗ status: Only a few values (pending, completed)                    │
    │  ✓ user_id: Good distribution, user queries fast                     │
    │  ✓ order_id: Even distribution                                        │
    │                                                                         │
    │  SOCIAL MEDIA (Posts table):                                          │
    │  ─────────────────────────────                                          │
    │  ✗ celebrity user_id: Hot spots (millions of posts)                  │
    │  ✓ post_id: Even distribution                                         │
    │  ✓ Compound: user_id + post_date                                      │
    │                                                                         │
    │  AVOID:                                                                │
    │  • Monotonically increasing keys (timestamp, auto-increment)         │
    │    → All recent writes go to one shard                               │
    │  • Low cardinality keys (country, status)                            │
    │    → Uneven distribution                                             │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


CHALLENGES OF SHARDING
──────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  SHARDING CHALLENGES                                                   │
    │                                                                         │
    │  1. CROSS-SHARD QUERIES                                               │
    │  ─────────────────────────                                              │
    │  Query needs data from multiple shards.                               │
    │                                                                         │
    │  Example: "Find all orders for user 123"                              │
    │  If orders sharded by order_id, must query ALL shards                │
    │                                                                         │
    │  Solutions:                                                            │
    │  • Shard by query-relevant key (user_id for user queries)            │
    │  • Scatter-gather: Query all shards, merge results                   │
    │  • Denormalize: Store data in multiple shards                        │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  2. CROSS-SHARD JOINS                                                 │
    │  ───────────────────────                                                │
    │  Can't JOIN tables on different shards efficiently.                   │
    │                                                                         │
    │  Solutions:                                                            │
    │  • Denormalize (embed related data)                                   │
    │  • Application-level joins (query both, join in app)                 │
    │  • Avoid JOINs (NoSQL approach)                                      │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  3. CROSS-SHARD TRANSACTIONS                                          │
    │  ──────────────────────────────                                         │
    │  ACID transactions don't work across shards.                          │
    │                                                                         │
    │  Solutions:                                                            │
    │  • Two-phase commit (2PC) - expensive                                │
    │  • SAGA pattern - compensating transactions                          │
    │  • Design to keep related data on same shard                         │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  4. RESHARDING                                                         │
    │  ──────────────                                                         │
    │  Adding/removing shards requires moving data.                         │
    │                                                                         │
    │  Solutions:                                                            │
    │  • Use consistent hashing (minimal data movement)                    │
    │  • Online resharding tools                                           │
    │  • Plan for growth (start with more shards)                          │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  5. HOT SPOTS                                                          │
    │  ─────────────                                                          │
    │  One shard gets disproportionate traffic.                             │
    │                                                                         │
    │  Solutions:                                                            │
    │  • Better shard key selection                                        │
    │  • Split hot shards                                                  │
    │  • Add salt to keys (randomize distribution)                         │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 6.3: REPLICATION + SHARDING TOGETHER
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  COMBINING SHARDING AND REPLICATION                                   │
    │                                                                         │
    │  In production, you usually use BOTH:                                 │
    │  • Sharding for write scalability and storage                        │
    │  • Replication for availability and read scalability                 │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │                        PRODUCTION SETUP                        │  │
    │  │                                                                 │  │
    │  │  ┌────────────────────────────────────────────────────────┐   │  │
    │  │  │                      SHARD 1                           │   │  │
    │  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │  │
    │  │  │  │   Leader    │  │  Follower   │  │  Follower   │   │   │  │
    │  │  │  │ (writes)    │──│ (reads)     │──│ (reads)     │   │   │  │
    │  │  │  └─────────────┘  └─────────────┘  └─────────────┘   │   │  │
    │  │  └────────────────────────────────────────────────────────┘   │  │
    │  │                                                                 │  │
    │  │  ┌────────────────────────────────────────────────────────┐   │  │
    │  │  │                      SHARD 2                           │   │  │
    │  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │  │
    │  │  │  │   Leader    │  │  Follower   │  │  Follower   │   │   │  │
    │  │  │  │ (writes)    │──│ (reads)     │──│ (reads)     │   │   │  │
    │  │  │  └─────────────┘  └─────────────┘  └─────────────┘   │   │  │
    │  │  └────────────────────────────────────────────────────────┘   │  │
    │  │                                                                 │  │
    │  │  ┌────────────────────────────────────────────────────────┐   │  │
    │  │  │                      SHARD 3                           │   │  │
    │  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │  │
    │  │  │  │   Leader    │  │  Follower   │  │  Follower   │   │   │  │
    │  │  │  │ (writes)    │──│ (reads)     │──│ (reads)     │   │   │  │
    │  │  │  └─────────────┘  └─────────────┘  └─────────────┘   │   │  │
    │  │  └────────────────────────────────────────────────────────┘   │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  Each shard has:                                                       │
    │  • 1 leader for writes                                                │
    │  • 2+ followers for reads and failover                               │
    │                                                                         │
    │  Gives you:                                                            │
    │  ✓ Write scalability (multiple shards)                               │
    │  ✓ Storage scalability (data distributed)                            │
    │  ✓ Read scalability (multiple replicas per shard)                    │
    │  ✓ High availability (failover within each shard)                    │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 6.4: ADVANCED REPLICATION TOPICS
================================================================================

CHANGE DATA CAPTURE (CDC)
─────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CHANGE DATA CAPTURE (CDC)                                            │
    │                                                                         │
    │  Capture database changes as a stream of events.                      │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Database ──► WAL ──► CDC Tool ──► Stream ──► Consumers        │  │
    │  │     │         │      (Debezium)      │                         │  │
    │  │  INSERT       │                      │                         │  │
    │  │  UPDATE       ▼                      ▼                         │  │
    │  │  DELETE    Write-Ahead             Kafka                       │  │
    │  │              Log                                                │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  HOW CDC WORKS:                                                        │
    │  1. Database writes to WAL (transaction log)                         │
    │  2. CDC tool reads WAL in real-time                                  │
    │  3. Converts to events: { op: "INSERT", table: "users", data: {...}}│
    │  4. Publishes to message queue (Kafka)                               │
    │  5. Consumers react to changes                                       │
    │                                                                         │
    │  USE CASES:                                                            │
    │  • Real-time data sync between systems                               │
    │  • Cache invalidation (DB change → invalidate cache)                │
    │  • Analytics pipelines                                               │
    │  • Event sourcing / CQRS                                            │
    │  • Microservices data sync                                           │
    │  • Outbox pattern implementation                                     │
    │                                                                         │
    │  TOOLS: Debezium, Maxwell (MySQL), AWS DMS                           │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


WRITE-AHEAD LOG (WAL)
─────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WRITE-AHEAD LOG (WAL)                                                │
    │                                                                         │
    │  Durability technique: Log changes before applying to database.       │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Transaction comes in                                          │  │
    │  │         │                                                       │  │
    │  │         ▼                                                       │  │
    │  │  1. Write to WAL (sequential, fast) ──► Disk                  │  │
    │  │         │                                                       │  │
    │  │         ▼                                                       │  │
    │  │  2. ACK to client ("committed")                                │  │
    │  │         │                                                       │  │
    │  │         ▼                                                       │  │
    │  │  3. Eventually apply to data files (async)                    │  │
    │  │                                                                 │  │
    │  │  ON CRASH RECOVERY:                                            │  │
    │  │  Replay WAL to restore committed transactions                 │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  WHY SEQUENTIAL WRITES:                                                │
    │  • Sequential I/O is 100x faster than random I/O                     │
    │  • WAL is append-only (always sequential)                            │
    │  • Data files have random access patterns                            │
    │                                                                         │
    │  WAL STRUCTURE:                                                        │
    │  ┌──────────────────────────────────────────────────────────────────┐ │
    │  │ LSN 1 │ LSN 2 │ LSN 3 │ LSN 4 │ LSN 5 │ ...                    │ │
    │  │ BEGIN │INSERT │UPDATE │DELETE │COMMIT │                        │ │
    │  └──────────────────────────────────────────────────────────────────┘ │
    │  LSN = Log Sequence Number (monotonically increasing)                │
    │                                                                         │
    │  REPLICATION USES WAL:                                                 │
    │  Leader → WAL → Ship to Followers → Apply WAL                       │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


GEOGRAPHIC (MULTI-REGION) REPLICATION
─────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  GEOGRAPHIC REPLICATION                                               │
    │                                                                         │
    │  Replicate data across regions/continents.                           │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │    US-East (Primary)      EU-West           Asia-Pacific       │  │
    │  │    ┌─────────────┐       ┌─────────────┐   ┌─────────────┐    │  │
    │  │    │   Leader    │──────►│  Follower   │   │  Follower   │    │  │
    │  │    │ (Writes)    │   │   │  (Reads)    │   │  (Reads)    │    │  │
    │  │    └─────────────┘   │   └─────────────┘   └─────────────┘    │  │
    │  │                      │                                         │  │
    │  │                      └──────────────────────────────────────►  │  │
    │  │                               ~100ms latency                   │  │
    │  │                                                                 │  │
    │  │  US users write to US-East                                    │  │
    │  │  EU users read from EU-West (low latency)                    │  │
    │  │  EU users write to US-East (higher latency)                  │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  CHALLENGES:                                                           │
    │  • Replication lag (100-500ms cross-region)                         │
    │  • Read-your-writes consistency                                      │
    │  • Conflict resolution for multi-master                             │
    │  • Compliance (data residency laws)                                 │
    │                                                                         │
    │  STRATEGIES:                                                           │
    │                                                                         │
    │  1. SINGLE LEADER (Active-Passive)                                   │
    │     One region handles all writes                                    │
    │     Simplest, but writes have cross-region latency                  │
    │                                                                         │
    │  2. MULTI-LEADER (Active-Active)                                     │
    │     Writes to local leader, sync between regions                    │
    │     Complex conflict resolution needed                               │
    │                                                                         │
    │  3. PARTITIONED BY REGION                                            │
    │     US data stays in US, EU data stays in EU                        │
    │     Good for compliance, but cross-region queries hard              │
    │                                                                         │
    │  SERVICES: CockroachDB, Spanner, DynamoDB Global Tables            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
CHAPTER SUMMARY
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  SHARDING & REPLICATION - KEY TAKEAWAYS                               │
    │                                                                         │
    │  REPLICATION                                                           │
    │  ───────────                                                           │
    │  • Same data on multiple nodes                                        │
    │  • Leader-Follower: Most common, writes to leader                    │
    │  • Sync vs Async: Trade-off between durability and latency           │
    │  • Use for: HA, read scaling, geographic distribution                │
    │                                                                         │
    │  SHARDING                                                              │
    │  ────────                                                              │
    │  • Different data on different nodes                                  │
    │  • Hash-based: Even distribution                                      │
    │  • Range-based: Efficient range queries                               │
    │  • Consistent hashing: Minimal resharding                             │
    │  • Use for: Write scaling, storage scaling                            │
    │                                                                         │
    │  SHARD KEY SELECTION                                                   │
    │  ────────────────────                                                  │
    │  • High cardinality                                                   │
    │  • Even distribution                                                  │
    │  • Matches query patterns                                             │
    │  • Avoid: timestamps, low cardinality                                 │
    │                                                                         │
    │  CHALLENGES                                                            │
    │  ──────────                                                            │
    │  • Cross-shard queries/joins                                          │
    │  • Distributed transactions                                           │
    │  • Resharding                                                         │
    │  • Hot spots                                                          │
    │                                                                         │
    │  INTERVIEW TIP                                                         │
    │  ─────────────                                                         │
    │  Know when to use sharding vs replication.                            │
    │  Be ready to discuss shard key selection and trade-offs.             │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
                              END OF CHAPTER 6
================================================================================

