# COLLABORATIVE EDITOR SYSTEM DESIGN (GOOGLE DOCS)
*Complete Design: Requirements, Architecture, and Interview Guide*

A real-time collaborative editor allows multiple users to simultaneously edit
the same document while seeing each other's changes instantly. At scale, it
must resolve conflicting edits, maintain consistency, broadcast cursor positions,
and persist every version of the document - all with sub-100ms latency.

## SECTION 1: UNDERSTANDING THE PROBLEM

### WHAT IS COLLABORATIVE EDITING?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  A collaborative editor lets multiple people edit a document at the     |
|  same time, from anywhere in the world:                                 |
|                                                                         |
|  USER EXPERIENCE:                                                       |
|  1. Open a document via a shared link                                   |
|  2. See the document content and other users' cursors in real-time      |
|  3. Type anywhere - your changes appear instantly for everyone          |
|  4. See colored cursors showing where others are editing                |
|  5. Leave comments on specific text selections                          |
|  6. View version history and restore previous versions                  |
|  7. Share the document with specific people or via link                 |
|                                                                         |
|  EXAMPLES:                                                              |
|  * Google Docs         - OT-based, most widely used                     |
|  * Notion              - block-based CRDT                               |
|  * Figma               - CRDT-based for design collaboration            |
|  * Microsoft 365 Online - OT-based collaborative editing                |
|  * VS Code Live Share  - CRDT-based code collaboration                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY IS THIS HARD TO BUILD?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY CHALLENGES:                                                        |
|                                                                         |
|  1. CONCURRENT EDITS ON THE SAME TEXT                                   |
|  ----------------------------------------                               |
|  Two users type at the same position simultaneously.                    |
|  Whose edit "wins"? How do you merge them?                              |
|  Naive approaches (last-write-wins) lose data.                          |
|                                                                         |
|  2. CONSISTENCY WITHOUT LOCKING                                         |
|  ---------------------------------                                      |
|  Locking paragraphs/sections kills the real-time experience.            |
|  We need lock-free conflict resolution.                                 |
|  All clients must converge to the same final state.                     |
|                                                                         |
|  3. NETWORK LATENCY & ORDERING                                          |
|  ---------------------------------                                      |
|  Operations arrive at the server in different orders.                   |
|  A user in Tokyo and one in NYC have ~150ms RTT.                        |
|  Out-of-order operations must still produce correct results.            |
|                                                                         |
|  4. REAL-TIME CURSOR PRESENCE                                           |
|  ------------------------------                                         |
|  Each user's cursor position must be broadcast to all others.           |
|  Selections, typing indicators, and user colors add complexity.         |
|  Must be low-latency but not overload the network.                      |
|                                                                         |
|  5. SCALE                                                               |
|  --------                                                               |
|  Millions of documents open simultaneously.                             |
|  Hundreds of concurrent editors per document (e.g., company all-hands). |
|  Persistent WebSocket connections for every active user.                |
|                                                                         |
|  6. OFFLINE EDITING                                                     |
|  ------------------                                                     |
|  Users on flaky connections (mobile, airplane) edit locally.            |
|  When they reconnect, their changes must merge without conflicts.       |
|  This is one of the hardest problems in distributed systems.            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: REQUIREMENTS

### FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS:                                               |
|                                                                         |
|  1. REAL-TIME COLLABORATIVE EDITING                                     |
|     * Multiple users edit the same document simultaneously              |
|     * Changes appear on all clients within ~100ms                       |
|     * No data loss even with concurrent edits at same position          |
|     * Support for text formatting (bold, italic, headers, lists)        |
|                                                                         |
|  2. CURSOR PRESENCE                                                     |
|     * Show each user's cursor position in real-time                     |
|     * Display user name labels on cursors                               |
|     * Show text selection ranges                                        |
|     * Typing indicators                                                 |
|     * Unique color per user                                             |
|                                                                         |
|  3. COMMENTS & SUGGESTIONS                                              |
|     * Add comments anchored to text selections                          |
|     * Reply threads on comments                                         |
|     * Suggest edits (tracked changes mode)                              |
|     * Resolve/reopen comments                                           |
|                                                                         |
|  4. VERSION HISTORY                                                     |
|     * View all past versions of the document                            |
|     * See who made which changes (attribution)                          |
|     * Restore any previous version                                      |
|     * Name specific versions                                            |
|                                                                         |
|  5. SHARING & PERMISSIONS                                               |
|     * Share with specific users (email)                                 |
|     * Link sharing with permission levels                               |
|     * Permission levels: Owner, Editor, Commenter, Viewer               |
|     * Real-time permission changes (revoke access instantly)            |
|     * Organization-level sharing settings                               |
|                                                                         |
|  6. DOCUMENT MANAGEMENT                                                 |
|     * Create, rename, delete, and organize documents                    |
|     * Folders and search                                                |
|     * Import/export (Word, PDF, Markdown)                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### NON-FUNCTIONAL REQUIREMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NON-FUNCTIONAL REQUIREMENTS:                                           |
|                                                                         |
|  1. LOW LATENCY                                                         |
|     * Local edit appears instantly (0ms perceived latency)              |
|     * Remote edits sync within <100ms over good networks                |
|     * Cursor positions update within <50ms                              |
|                                                                         |
|  2. CONSISTENCY                                                         |
|     * All users must converge to the same document state                |
|     * No lost edits - every keystroke is preserved                      |
|     * Eventual consistency model (strong eventual consistency           |
|       if using CRDTs)                                                   |
|                                                                         |
|  3. AVAILABILITY                                                        |
|     * 99.99% uptime (52 min downtime/year)                              |
|     * Graceful degradation: offline editing works                       |
|     * No single point of failure                                        |
|                                                                         |
|  4. SCALABILITY                                                         |
|     * Millions of documents open concurrently                           |
|     * Up to 100+ concurrent editors per document                        |
|     * Billions of operations per day                                    |
|                                                                         |
|  5. DURABILITY                                                          |
|     * Zero data loss - every operation persisted                        |
|     * Document recoverable even after accidental deletion               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3: BACK-OF-ENVELOPE ESTIMATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALE ASSUMPTIONS                                                      |
|                                                                         |
|  Total registered users:     1 billion                                  |
|  Daily active users (DAU):   200 million                                |
|  Total documents:            5 billion                                  |
|  Documents opened per day:   500 million                                |
|  Concurrently open docs:     50 million (at peak)                       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  CONCURRENT EDITOR ESTIMATES                                            |
|                                                                         |
|  Average editors per open doc:     1.5                                  |
|  Docs with 2+ editors (collab):    ~10% of open docs = 5M               |
|  Peak concurrent WebSocket conns:  ~75 million                          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  OPERATIONS PER SECOND                                                  |
|                                                                         |
|  Average typing speed:    5 chars/sec per active user                   |
|  Active typers at peak:   10 million users                              |
|  Edits/sec at peak:       50 million ops/sec                            |
|  Cursor updates/sec:      75 million (every user, every 1s)             |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  STORAGE ESTIMATES                                                      |
|                                                                         |
|  Average document size:        50 KB (text + formatting)                |
|  Average ops log per doc:      500 KB (uncompacted)                     |
|  Total document storage:       5B * 50KB = 250 TB                       |
|  Total ops log storage:        5B * 500KB = 2.5 PB                      |
|  With compaction (10x):        ~250 TB ops log                          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  BANDWIDTH                                                              |
|                                                                         |
|  Average operation size:     ~100 bytes                                 |
|  Peak outbound bandwidth:    50M ops/sec * 100B = 5 GB/s                |
|  With fan-out (avg 1.5):     ~7.5 GB/s outbound                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: HIGH-LEVEL ARCHITECTURE

```
+--------------------------------------------------------------------------+
|                                                                          |
|  OVERALL SYSTEM ARCHITECTURE                                             |
|                                                                          |
|  +----------+     +------------------+     +------------------------+    |
|  |  Client   |<--->| WebSocket Gateway|<--->| Document Service      |    |
|  |  (Browser)|     | (Connection Mgmt)|     | (OT/CRDT Engine)      |    |
|  +----------+     +------------------+     +------------------------+    |
|       |                    |                         |                   |
|       |                    |                         v                   |
|       |                    |                +-----------------+          |
|       |                    |                | Operation Log   |          |
|       |                    |                | (Append-only)   |          |
|       |                    |                +-----------------+          |
|       |                    |                         |                   |
|       |                    v                         v                   |
|       |           +-----------------+       +-----------------+          |
|       |           | Presence Service|       | Document Storage|          |
|       |           | (Cursors/Users) |       | (Snapshots+Ops) |          |
|       |           +-----------------+       +-----------------+          |
|       |                                              |                   |
|       v                                              v                   |
|  +----------+                               +-----------------+          |
|  | Auth &   |                               | Version History |          |
|  | Perms    |                               | Service         |          |
|  | Service  |                               +-----------------+          |
|  +----------+                                                            |
|                                                                          |
+--------------------------------------------------------------------------+
```

### COMPONENT RESPONSIBILITIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. CLIENT (Browser/App)                                                |
|  -------------------------                                              |
|  * Renders the document (rich text editor)                              |
|  * Captures local edits as operations                                   |
|  * Applies local operations immediately (optimistic)                    |
|  * Maintains WebSocket connection to gateway                            |
|  * Receives remote operations and transforms them locally               |
|  * Manages local operation buffer for unacknowledged ops                |
|                                                                         |
|  2. WEBSOCKET GATEWAY                                                   |
|  ----------------------                                                 |
|  * Manages persistent WebSocket connections                             |
|  * Routes operations to the correct document session                    |
|  * Handles connection lifecycle (open, heartbeat, reconnect)            |
|  * Broadcasts operations to all clients on the same document            |
|  * Session affinity: all users on a doc connect to same gateway         |
|                                                                         |
|  3. DOCUMENT SERVICE (OT/CRDT ENGINE)                                   |
|  --------------------------------------                                 |
|  * Receives operations from clients                                     |
|  * Transforms operations (OT) or merges (CRDT)                          |
|  * Maintains canonical document state in memory                         |
|  * Assigns sequential version numbers to operations                     |
|  * Persists operations to the operation log                             |
|                                                                         |
|  4. OPERATION LOG                                                       |
|  -----------------                                                      |
|  * Append-only log of every operation on every document                 |
|  * Used for: conflict resolution, version history, recovery             |
|  * Periodically compacted into snapshots                                |
|                                                                         |
|  5. PRESENCE SERVICE                                                    |
|  --------------------                                                   |
|  * Tracks which users are in which documents                            |
|  * Broadcasts cursor positions and selections                           |
|  * Manages user colors and typing indicators                            |
|  * Ephemeral data - not durably stored                                  |
|                                                                         |
|  6. DOCUMENT STORAGE                                                    |
|  --------------------                                                   |
|  * Stores document snapshots (full content at a point in time)          |
|  * Stores the ops log between snapshots                                 |
|  * Retrieval: load latest snapshot + replay ops since snapshot          |
|                                                                         |
|  7. AUTH & PERMISSIONS SERVICE                                          |
|  ------------------------------                                         |
|  * Authenticates users on WebSocket connect                             |
|  * Checks permissions before applying operations                        |
|  * Manages ACLs, link sharing, org-level policies                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### REQUEST FLOW: USER TYPES A CHARACTER

```
+--------------------------------------------------------------------------+
|                                                                          |
|  FLOW: User A types "H" at position 5 in a shared document               |
|                                                                          |
|  Step 1: LOCAL APPLICATION (instant)                                     |
|  +--------+                                                              |
|  | User A | types "H"                                                    |
|  | Client | -> applies Insert("H", pos=5) to local doc immediately       |
|  +--------+ -> adds op to outgoing buffer                                |
|                                                                          |
|  Step 2: SEND TO SERVER                                                  |
|  +--------+           +----------+                                       |
|  | User A | --op----> | WebSocket|                                       |
|  | Client |  (ws msg) | Gateway  |                                       |
|  +--------+           +----------+                                       |
|                            |                                             |
|  Step 3: PROCESS ON SERVER |                                             |
|                            v                                             |
|                    +--------------+                                      |
|                    | Document Svc | -> transform op against any          |
|                    | (OT Engine)  |    concurrent ops                    |
|                    +--------------+ -> assign version number             |
|                            |        -> persist to ops log                |
|                            |                                             |
|  Step 4: BROADCAST TO ALL CLIENTS                                        |
|                            |                                             |
|              +-------------+-------------+                               |
|              |             |             |                               |
|              v             v             v                               |
|         +--------+   +--------+   +--------+                             |
|         | User A |   | User B |   | User C |                             |
|         | (ACK)  |   | (apply)|   | (apply)|                             |
|         +--------+   +--------+   +--------+                             |
|                                                                          |
|  Step 5: ACKNOWLEDGMENT                                                  |
|  User A receives ACK -> removes op from outgoing buffer                  |
|  User B, C receive op -> transform against their local pending ops       |
|                        -> apply to their local document                  |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 5: DEEP DIVE - CONFLICT RESOLUTION

### THE CORE PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY DO CONFLICTS HAPPEN?                                               |
|                                                                         |
|  Two users edit the same document concurrently. Due to network          |
|  latency, each user's operation is based on a stale version of          |
|  the document.                                                          |
|                                                                         |
|  EXAMPLE:                                                               |
|                                                                         |
|  Initial document: "ABCD"                                               |
|                                                                         |
|  User A: Insert "X" at position 1  -> "AXBCD"                           |
|  User B: Delete char at position 2  -> "ABD"                            |
|                                                                         |
|  Both ops are based on "ABCD". If we apply them naively:                |
|                                                                         |
|  Server receives A first, then B:                                       |
|    "ABCD" -> Insert X@1 -> "AXBCD" -> Delete @2 -> "AXCD"               |
|    (Deleted "B" - correct!)                                             |
|                                                                         |
|  Server receives B first, then A:                                       |
|    "ABCD" -> Delete @2 -> "ABD" -> Insert X@1 -> "AXBD"                 |
|    (Wrong! "C" was deleted instead of "B", and result differs)          |
|                                                                         |
|  THE ORDER OF ARRIVAL CHANGES THE RESULT.                               |
|  We need a mechanism that produces the same result regardless           |
|  of the order operations arrive.                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### APPROACH 1: OPERATIONAL TRANSFORMATION (OT)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OPERATIONAL TRANSFORMATION (OT)                                        |
|                                                                         |
|  CORE IDEA:                                                             |
|  When two operations are concurrent, transform one against the          |
|  other so that applying them in any order produces the same result.     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  HOW IT WORKS:                                                          |
|                                                                         |
|  Given two concurrent operations O1 and O2 (both based on the           |
|  same document state), we compute:                                      |
|                                                                         |
|     O1' = transform(O1, O2)     (O1 transformed against O2)             |
|     O2' = transform(O2, O1)     (O2 transformed against O1)             |
|                                                                         |
|  Such that:                                                             |
|     apply(apply(doc, O1), O2') == apply(apply(doc, O2), O1')            |
|                                                                         |
|  This is called the TRANSFORMATION PROPERTY (TP1).                      |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  CONCRETE EXAMPLE:                                                      |
|                                                                         |
|  Document: "ABCD"   (version 5)                                         |
|                                                                         |
|  O1: Insert("X", pos=1)    from User A (based on v5)                    |
|  O2: Delete(pos=2)          from User B (based on v5)                   |
|                                                                         |
|  Server receives O1 first:                                              |
|    Apply O1: "ABCD" -> "AXBCD"                                          |
|                                                                         |
|    Now transform O2 against O1:                                         |
|    O2 was Delete(pos=2). O1 inserted a char before pos 2.               |
|    So O2's position shifts right by 1.                                  |
|    O2' = Delete(pos=3)                                                  |
|                                                                         |
|    Apply O2': "AXBCD" -> "AXBD" -- wait, that deletes "C"!              |
|                                                                         |
|  Actually, let's be precise:                                            |
|  O2 = Delete(pos=2) means delete char at index 2 = "C"                  |
|  After O1 inserts "X" at pos 1, "C" is now at index 3                   |
|  O2' = Delete(pos=3)                                                    |
|  "AXBCD" -> Delete@3 -> "AXBD"                                          |
|                                                                         |
|  On User B's side (received O1 after applying O2 locally):              |
|  Local: "ABCD" -> Delete@2 -> "ABD"                                     |
|  Transform O1 against O2: Insert was at pos 1, which is before          |
|  the delete at pos 2, so no shift needed.                               |
|  O1' = Insert("X", pos=1)                                               |
|  "ABD" -> Insert X@1 -> "AXBD"                                          |
|                                                                         |
|  BOTH SIDES CONVERGE TO "AXBD"                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### OT TRANSFORMATION RULES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TRANSFORM RULES FOR BASIC OPERATIONS:                                  |
|                                                                         |
|  Operations: Insert(char, pos), Delete(pos)                             |
|                                                                         |
|  1. Insert vs Insert:                                                   |
|     If O1=Insert(c1, p1) and O2=Insert(c2, p2):                         |
|     * If p1 < p2:  O2' = Insert(c2, p2+1)                               |
|     * If p1 > p2:  O1' = Insert(c1, p1+1)                               |
|     * If p1 == p2: break tie by user ID                                 |
|                                                                         |
|  2. Insert vs Delete:                                                   |
|     If O1=Insert(c, p1) and O2=Delete(p2):                              |
|     * If p1 <= p2: O2' = Delete(p2+1) (insert shifts delete right)      |
|     * If p1 > p2:  O1' = Insert(c, p1-1) (delete shifts insert left)    |
|                                                                         |
|  3. Delete vs Delete:                                                   |
|     If O1=Delete(p1) and O2=Delete(p2):                                 |
|     * If p1 < p2:  O2' = Delete(p2-1)                                   |
|     * If p1 > p2:  O1' = Delete(p1-1)                                   |
|     * If p1 == p2: both deleted same char -> O2' = no-op                |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  THE SERVER'S ROLE IN OT:                                               |
|                                                                         |
|  The server acts as the SINGLE SOURCE OF TRUTH.                         |
|  It serializes all operations into a total order.                       |
|  Each operation gets a sequential version number.                       |
|                                                                         |
|  Client sends: (operation, basedOnVersion)                              |
|  Server: transforms op against all ops between basedOnVersion           |
|          and current version, then applies and broadcasts.              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### APPROACH 2: CRDTS (CONFLICT-FREE REPLICATED DATA TYPES)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CRDTs - CONFLICT-FREE REPLICATED DATA TYPES                            |
|                                                                         |
|  CORE IDEA:                                                             |
|  Design the data structure itself so that concurrent operations         |
|  automatically merge without conflicts. No transformation needed.       |
|  Mathematically guaranteed to converge.                                 |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  HOW IT WORKS FOR TEXT (Sequence CRDTs):                                |
|                                                                         |
|  Instead of positions (index 0, 1, 2...), each character gets           |
|  a GLOBALLY UNIQUE ID that defines its position in the sequence.        |
|                                                                         |
|  Popular algorithms:                                                    |
|  * RGA (Replicated Growable Array)                                      |
|  * LSEQ                                                                 |
|  * Yjs (YATA algorithm)                                                 |
|  * Automerge (RGA-based)                                                |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  EXAMPLE WITH UNIQUE IDs:                                               |
|                                                                         |
|  Document: "ABCD"                                                       |
|  Internal representation:                                               |
|                                                                         |
|  +------+------+------+------+                                          |
|  | A    | B    | C    | D    |                                          |
|  | id:1 | id:2 | id:3 | id:4 |                                          |
|  +------+------+------+------+                                          |
|                                                                         |
|  User A: Insert "X" between id:1 and id:2                               |
|    -> new char gets id: (userA, seq=7)                                  |
|    -> position defined as: after id:1, before id:2                      |
|                                                                         |
|  User B: Delete id:3 (the "C")                                          |
|    -> Tombstone: mark id:3 as deleted (not physically removed)          |
|                                                                         |
|  THESE OPERATIONS COMMUTE:                                              |
|  Regardless of the order you apply them, the result is the same.        |
|  "X" goes between A and B, "C" is tombstoned.                           |
|  Result: "AXBD" (with tombstoned C hidden)                              |
|                                                                         |
|  No transformation needed! The data structure guarantees convergence.   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### OT VS CRDT COMPARISON

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMPARISON: OT vs CRDT                                                 |
|                                                                         |
|  +------------------+------------------------+------------------------+ |
|  | Aspect           | OT                     | CRDT                   | |
|  +------------------+------------------------+------------------------+ |
|  | Central server   | Required (serializes   | Not required (peer-to- | |
|  |                  | operations)            | peer possible)         | |
|  +------------------+------------------------+------------------------+ |
|  | Complexity       | Transform functions    | Data structure design  | |
|  |                  | are hard to get right  | is complex             | |
|  +------------------+------------------------+------------------------+ |
|  | Correctness      | Subtle bugs possible   | Mathematically proven  | |
|  |                  | (TP2 puzzle)           | to converge            | |
|  +------------------+------------------------+------------------------+ |
|  | Memory overhead  | Low - positions are    | Higher - unique IDs    | |
|  |                  | just integers          | per character + tombs  | |
|  +------------------+------------------------+------------------------+ |
|  | Offline support  | Hard - need server to  | Natural - ops merge    | |
|  |                  | serialize ops          | on reconnect           | |
|  +------------------+------------------------+------------------------+ |
|  | Latency          | Server round-trip      | Can apply locally,     | |
|  |                  | needed for ordering    | sync later             | |
|  +------------------+------------------------+------------------------+ |
|  | Undo/Redo        | Complex (must reverse  | Complex (tombstones    | |
|  |                  | transformed ops)       | complicate undo)       | |
|  +------------------+------------------------+------------------------+ |
|  | Proven at scale  | Google Docs (15+ yrs)  | Figma, Yjs, Automerge  | |
|  +------------------+------------------------+------------------------+ |
|  | Best for         | Centralized systems    | P2P, offline-first,    | |
|  |                  | with a server          | decentralized systems  | |
|  +------------------+------------------------+------------------------+ |
|                                                                         |
|  GOOGLE DOCS uses OT with a centralized server.                         |
|  FIGMA uses a CRDT-inspired approach for design collaboration.          |
|  YJS / AUTOMERGE are open-source CRDT libraries for text editing.       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6: DEEP DIVE - REAL-TIME SYNC

### WEBSOCKET CONNECTION MANAGEMENT

```
+--------------------------------------------------------------------------+
|                                                                          |
|  WHY WEBSOCKETS?                                                         |
|                                                                          |
|  HTTP polling:  Client asks "any updates?" every 100ms                   |
|                 -> 600 requests/min per client, massive overhead         |
|                                                                          |
|  Long polling:  Better, but still creates new connections                |
|                 -> Not truly real-time, has reconnection gaps            |
|                                                                          |
|  SSE:           Server -> Client only (unidirectional)                   |
|                 -> Can't send edits back efficiently                     |
|                                                                          |
|  WebSocket:     Full duplex, persistent connection                       |
|                 -> Client and server push data anytime                   |
|                 -> ~100 bytes per message overhead (vs ~800 for HTTP)    |
|                 -> Perfect for real-time bidirectional editing           |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  CONNECTION LIFECYCLE:                                                   |
|                                                                          |
|  1. User opens document                                                  |
|     -> HTTP request to load document content + metadata                  |
|     -> Establish WebSocket connection to gateway                         |
|     -> Authenticate via token in the upgrade request                     |
|     -> Join the document's "room" on the gateway                         |
|                                                                          |
|  2. During editing                                                       |
|     -> Send operations over WebSocket as JSON/binary                     |
|     -> Receive operations from other users                               |
|     -> Periodic heartbeat (ping/pong) every 30 seconds                   |
|                                                                          |
|  3. Reconnection                                                         |
|     -> On disconnect, client buffers local operations                    |
|     -> On reconnect, send "last seen version" to server                  |
|     -> Server replays missed operations since that version               |
|     -> Client applies missed ops + re-sends buffered local ops           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### CLIENT-SIDE PREDICTION & SERVER CANONICAL STATE

```
+--------------------------------------------------------------------------+
|                                                                          |
|  CLIENT-SIDE PREDICTION MODEL:                                           |
|                                                                          |
|  The client does NOT wait for server confirmation before showing         |
|  the user's own edits. This is critical for a responsive experience.     |
|                                                                          |
|  CLIENT STATE MACHINE:                                                   |
|                                                                          |
|  +-------------------+                                                   |
|  | SYNCHRONIZED      | No pending ops, client matches server             |
|  +-------------------+                                                   |
|        | user types                                                      |
|        v                                                                 |
|  +-------------------+                                                   |
|  | AWAITING ACK      | One op sent to server, waiting for ACK            |
|  |                   | Apply local edits instantly                       |
|  +-------------------+ Buffer new ops (don't send yet)                   |
|        | ACK received (no new local ops)                                 |
|        v                                                                 |
|  +-------------------+                                                   |
|  | SYNCHRONIZED      | Back to synced state                              |
|  +-------------------+                                                   |
|                                                                          |
|  If new ops were buffered while AWAITING ACK:                            |
|        | ACK received (has buffered ops)                                 |
|        v                                                                 |
|  +-------------------+                                                   |
|  | AWAITING ACK      | Send buffered ops as one batch                    |
|  | WITH BUFFER       | Start buffering new ops again                     |
|  +-------------------+                                                   |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  HANDLING REMOTE OPS WHILE AWAITING ACK:                                 |
|                                                                          |
|  When the client receives a remote op while it has pending local ops:    |
|                                                                          |
|  1. Transform the remote op against all pending local ops                |
|  2. Apply the transformed remote op to the local document                |
|  3. Also transform the pending local ops against the remote op           |
|     (so they're still valid when sent to the server)                     |
|                                                                          |
|  This ensures the client always shows a consistent, responsive           |
|  view while staying in sync with the server.                             |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  SERVER CANONICAL STATE:                                                 |
|                                                                          |
|  The server maintains the "ground truth" document state.                 |
|  Operations are applied in a strict sequential order.                    |
|  Every operation gets a monotonically increasing version number.         |
|  The server never needs to "undo" - it only moves forward.               |
|                                                                          |
+--------------------------------------------------------------------------+
```

### OPERATION BROADCASTING

```
+--------------------------------------------------------------------------+
|                                                                          |
|  BROADCAST STRATEGY:                                                     |
|                                                                          |
|  When the server processes an operation:                                 |
|                                                                          |
|  1. TO THE SENDER:                                                       |
|     Send ACK with the server's version number                            |
|     (Client removes op from pending buffer)                              |
|                                                                          |
|  2. TO ALL OTHER CLIENTS ON THE SAME DOCUMENT:                           |
|     Send the transformed operation with:                                 |
|     * The operation itself                                               |
|     * The server version number                                          |
|     * The user ID of the author                                          |
|                                                                          |
|  BATCHING:                                                               |
|  * Individual keystrokes can be batched into operations                  |
|  * "Hello" might be sent as one Insert("Hello", pos=5)                   |
|    instead of 5 separate inserts                                         |
|  * Batch window: ~50ms (collect ops, send as group)                      |
|  * Reduces network overhead significantly                                |
|                                                                          |
|  MESSAGE FORMAT (example):                                               |
|                                                                          |
|  +----------------------------------+                                    |
|  | type: "operation"                |                                    |
|  | docId: "doc_abc123"              |                                    |
|  | version: 1042                    |                                    |
|  | userId: "user_xyz"               |                                    |
|  | ops: [                           |                                    |
|  |   { type: "insert",             |                                     |
|  |     text: "Hello",              |                                     |
|  |     pos: 5 }                    |                                     |
|  | ]                                |                                    |
|  +----------------------------------+                                    |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 7: DEEP DIVE - STORAGE

### DOCUMENT MODEL

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TWO APPROACHES TO DOCUMENT REPRESENTATION:                             |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  APPROACH 1: TREE OF BLOCKS (Google Docs, Notion style)                 |
|                                                                         |
|  Document                                                               |
|  +-- Paragraph Block (id: b1)                                           |
|  |   +-- TextRun "Hello " (bold=false)                                  |
|  |   +-- TextRun "World" (bold=true)                                    |
|  +-- Heading Block (id: b2, level: 2)                                   |
|  |   +-- TextRun "Section Title"                                        |
|  +-- List Block (id: b3, ordered=true)                                  |
|  |   +-- ListItem Block (id: b4)                                        |
|  |   |   +-- TextRun "First item"                                       |
|  |   +-- ListItem Block (id: b5)                                        |
|  |       +-- TextRun "Second item"                                      |
|  +-- Image Block (id: b6, url: "...")                                   |
|                                                                         |
|  Pros: Natural for rich documents, easy to render                       |
|  Cons: Tree operations are harder to transform (OT on trees)            |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  APPROACH 2: FLAT OPERATIONS LOG (Event Sourcing style)                 |
|                                                                         |
|  The document IS the sequence of all operations applied to it.          |
|                                                                         |
|  Op 1: Insert("H", pos=0, user=A, v=1)                                  |
|  Op 2: Insert("e", pos=1, user=A, v=2)                                  |
|  Op 3: Insert("l", pos=2, user=A, v=3)                                  |
|  Op 4: Insert("l", pos=3, user=A, v=4)                                  |
|  Op 5: Insert("o", pos=4, user=A, v=5)                                  |
|  Op 6: Format(pos=0, len=5, bold=true, user=B, v=6)                     |
|  ...                                                                    |
|                                                                         |
|  To get current doc: replay all ops from the beginning.                 |
|  (With snapshots: load snapshot + replay ops since snapshot)            |
|                                                                         |
|  Pros: Perfect audit trail, easy version history                        |
|  Cons: Replay can be slow for large docs without snapshots              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SNAPSHOTS + OPERATION LOG + COMPACTION

```
+--------------------------------------------------------------------------+
|                                                                          |
|  STORAGE STRATEGY: SNAPSHOTS + OPS LOG                                   |
|                                                                          |
|  TIMELINE:                                                               |
|                                                                          |
|  [Snapshot v0] -> [Op v1] [Op v2] ... [Op v999] -> [Snapshot v1000]      |
|  -> [Op v1001] [Op v1002] ... [Op v1500] -> [Snapshot v1500]             |
|                                                                          |
|  LOADING A DOCUMENT:                                                     |
|  1. Find the latest snapshot (e.g., v1500)                               |
|  2. Load the snapshot (full document content at v1500)                   |
|  3. Replay all ops after v1500 (e.g., v1501 to v1523)                    |
|  4. Now you have the current document at v1523                           |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  SNAPSHOT CREATION TRIGGERS:                                             |
|                                                                          |
|  * Every N operations (e.g., every 1000 ops)                             |
|  * Every T minutes of inactivity (e.g., 5 min with no edits)             |
|  * When all editors leave the document                                   |
|  * Before major operations (permission changes, export)                  |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  COMPACTION:                                                             |
|                                                                          |
|  Over time, the ops log grows unbounded. Compaction reclaims space:      |
|                                                                          |
|  * Ops before the oldest "needed" snapshot can be deleted                |
|  * Version history snapshots are kept at wider intervals:                |
|    * Last 24h: snapshot every 1000 ops                                   |
|    * Last 30d: snapshot every hour                                       |
|    * Older: snapshot every day                                           |
|  * This mirrors how Google Docs version history works:                   |
|    recent changes are fine-grained, old changes are coarse               |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  STORAGE LAYER CHOICES:                                                  |
|                                                                          |
|  +-------------------+------------------------------------------+        |
|  | Component         | Technology Choice                        |        |
|  +-------------------+------------------------------------------+        |
|  | Ops Log           | Kafka / DynamoDB / Cassandra (append)    |        |
|  | Snapshots         | Object Storage (S3/GCS) or blob DB       |        |
|  | Document Metadata | PostgreSQL / Spanner (relational)        |        |
|  | Active Doc State  | In-memory on Document Service node       |        |
|  +-------------------+------------------------------------------+        |
|                                                                          |
|  WHY THESE CHOICES?                                                      |
|  * Ops Log > Kafka/Cassandra: Append-only, high-throughput writes.       |
|    Every keystroke generates an op - need write-optimized storage.       |
|    Kafka also enables real-time fan-out to other collaborators.          |
|  * Snapshots > S3/GCS: Large blobs (full doc state), infrequent          |
|    reads. Object storage is cheapest per GB, highly durable (11 9s).     |
|  * Metadata > PostgreSQL: Relational (doc>owner>permissions>sharing).    |
|    ACID for permission changes. Joins for "list my documents" queries.   |
|  * Active State > In-memory: Sub-ms op application. Collaborators        |
|    need instant response. Reconstruct from ops log on server restart.    |
|                                                                          |
+--------------------------------------------------------------------------+
```

### VERSION HISTORY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  VERSION HISTORY IMPLEMENTATION:                                        |
|                                                                         |
|  Users expect to see a timeline of changes and restore old versions.    |
|                                                                         |
|  HOW IT WORKS:                                                          |
|                                                                         |
|  1. AUTOMATIC VERSIONS (unnamed)                                        |
|     Created automatically during editing sessions.                      |
|     Grouped by user and time window (e.g., all edits by User A          |
|     within a 30-minute window = one version entry).                     |
|                                                                         |
|  2. NAMED VERSIONS (manual)                                             |
|     User explicitly names a version ("Final Draft v2").                 |
|     Creates a snapshot with a label.                                    |
|                                                                         |
|  3. VIEWING A VERSION                                                   |
|     Load the snapshot at that version.                                  |
|     Show diff highlighting (additions in green, deletions in red).      |
|     Show who made each change (attribution).                            |
|                                                                         |
|  4. RESTORING A VERSION                                                 |
|     Does NOT delete history - it creates a new operation:               |
|     "Replace entire document with content from version X."              |
|     All editors see the restoration in real-time.                       |
|                                                                         |
|  ATTRIBUTION:                                                           |
|  Every operation records the user ID.                                   |
|  The document can be rendered with per-character attribution:           |
|  "This word was written by Alice, that word by Bob."                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8: DEEP DIVE - PRESENCE & CURSORS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PRESENCE SYSTEM DESIGN:                                                |
|                                                                         |
|  Presence data is EPHEMERAL - it matters only while users are active.   |
|  It does NOT need durable storage.                                      |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  CURSOR POSITION BROADCASTING:                                          |
|                                                                         |
|  Each client sends cursor updates to the server:                        |
|                                                                         |
|  +------------------------------------+                                 |
|  | type: "cursor"                     |                                 |
|  | docId: "doc_abc123"                |                                 |
|  | userId: "user_xyz"                 |                                 |
|  | cursor: {                          |                                 |
|  |   anchor: { blockId: "b1",        |                                  |
|  |             offset: 12 }          |                                  |
|  |   focus:  { blockId: "b1",        |                                  |
|  |             offset: 18 }          |                                  |
|  | }                                  |                                 |
|  +------------------------------------+                                 |
|                                                                         |
|  anchor != focus means the user has selected text (range).              |
|  anchor == focus means the cursor is a simple caret.                    |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  THROTTLING CURSOR UPDATES:                                             |
|                                                                         |
|  Cursor moves on EVERY keystroke and mouse movement.                    |
|  Broadcasting every single move would flood the network.                |
|                                                                         |
|  Strategy:                                                              |
|  * Throttle cursor updates to ~10-20 per second per user                |
|  * Batch with operation messages when possible                          |
|  * Use "last writer wins" - only latest cursor position matters         |
|  * Drop stale cursor updates if a newer one is queued                   |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  USER COLOR ASSIGNMENT:                                                 |
|                                                                         |
|  When a user joins a document editing session:                          |
|  1. Server assigns a color from a predefined palette                    |
|  2. Colors are recycled when users leave                                |
|  3. Palette: 8-12 distinct, accessible colors                           |
|  4. Same user gets same color if they rejoin quickly                    |
|                                                                         |
|  Display:                                                               |
|  * Cursor caret: thin vertical line in user's color                     |
|  * Selection: semi-transparent highlight in user's color                |
|  * Name label: small tag above cursor showing user name                 |
|  * Fade out: cursor disappears after ~30s of inactivity                 |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  TYPING INDICATORS:                                                     |
|                                                                         |
|  "Alice is typing..." shown at the top or near their cursor.            |
|  * Set typing = true when user sends an operation                       |
|  * Set typing = false after 3 seconds of no operations                  |
|  * This is purely client-side logic with server broadcast               |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  ACTIVE USER LIST:                                                      |
|                                                                         |
|  Show avatars of all users currently viewing/editing the document.      |
|  * Maintained by the presence service                                   |
|  * Updated on WebSocket connect/disconnect                              |
|  * Heartbeat-based: user is "present" if heartbeat received             |
|    within last 60 seconds                                               |
|  * Distinguish: "viewing" vs "editing" based on recent operations       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: DEEP DIVE - PERMISSIONS & SHARING

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ACCESS CONTROL MODEL:                                                   |
|                                                                          |
|  Permission levels (from most to least privileged):                      |
|                                                                          |
|  +----------+----------------------------------------------------+       |
|  | Level    | Capabilities                                       |       |
|  +----------+----------------------------------------------------+       |
|  | Owner    | All below + delete doc + transfer ownership         |      |
|  +----------+----------------------------------------------------+       |
|  | Editor   | All below + edit document content                   |      |
|  +----------+----------------------------------------------------+       |
|  | Commenter| All below + add/reply to comments                   |      |
|  +----------+----------------------------------------------------+       |
|  | Viewer   | Read document + view comments                       |      |
|  +----------+----------------------------------------------------+       |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  ACL (ACCESS CONTROL LIST) STRUCTURE:                                    |
|                                                                          |
|  Each document has an ACL:                                               |
|                                                                          |
|  +------------------------------------------+                            |
|  | Document: doc_abc123                      |                           |
|  | Owner: alice@example.com                  |                           |
|  +------------------------------------------+                            |
|  | User Permissions:                         |                           |
|  |   alice@example.com  -> Owner             |                           |
|  |   bob@example.com    -> Editor            |                           |
|  |   carol@example.com  -> Commenter         |                           |
|  +------------------------------------------+                            |
|  | Link Sharing:                             |                           |
|  |   Enabled: true                           |                           |
|  |   Link Permission: Viewer                 |                           |
|  |   Link URL: docs.app/d/abc123             |                           |
|  +------------------------------------------+                            |
|  | Org Settings:                             |                           |
|  |   Anyone at @example.com -> Viewer        |                           |
|  +------------------------------------------+                            |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  LINK SHARING MODES:                                                     |
|                                                                          |
|  1. RESTRICTED: Only explicitly added users can access                   |
|  2. ANYONE WITH LINK: Anyone with URL gets specified permission          |
|     * Link as Viewer                                                     |
|     * Link as Commenter                                                  |
|     * Link as Editor                                                     |
|  3. ORGANIZATION: Anyone in the org gets specified permission            |
|  4. PUBLIC: Anyone on the internet (for published documents)             |
|                                                                          |
|  ====================================================================    |
|                                                                          |
|  REAL-TIME PERMISSION CHANGES:                                           |
|                                                                          |
|  When the owner downgrades someone from Editor to Viewer:                |
|                                                                          |
|  1. Update ACL in the database                                           |
|  2. Push permission change event via WebSocket to the affected user      |
|  3. Client immediately switches to read-only mode                        |
|  4. Any pending (unsent) operations from the user are discarded          |
|  5. Server rejects any operations from the user after the change         |
|                                                                          |
|  This must happen in REAL-TIME - you cannot let a revoked editor         |
|  continue editing, even for a few seconds.                               |
|                                                                          |
+--------------------------------------------------------------------------+
```

## SECTION 10: SCALING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALING STRATEGY:                                                      |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  1. SHARDING BY DOCUMENT ID                                             |
|  ----------------------------                                           |
|                                                                         |
|  Each document is owned by exactly one Document Service node.           |
|  Shard key: hash(docId) % number_of_shards                              |
|                                                                         |
|  +----------+    +----------+    +----------+                           |
|  | Shard 0  |    | Shard 1  |    | Shard 2  |                           |
|  | docs     |    | docs     |    | docs     |                           |
|  | 0-999    |    | 1000-1999|    | 2000-2999|                           |
|  +----------+    +----------+    +----------+                           |
|                                                                         |
|  Why document-level sharding?                                           |
|  * All operations on a doc go to one node (serialization)               |
|  * No cross-shard coordination needed for conflict resolution           |
|  * Simple consistent hashing for shard assignment                       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  2. SESSION AFFINITY FOR WEBSOCKET                                      |
|  ------------------------------------                                   |
|                                                                         |
|  All users editing the same document connect to the SAME gateway.       |
|  This avoids cross-gateway communication for broadcasting ops.          |
|                                                                         |
|  How?                                                                   |
|  * Load balancer uses docId in the WebSocket URL to route               |
|  * e.g., wss://gateway.app/ws?docId=abc123                              |
|  * Consistent hashing maps docId -> gateway server                      |
|  * If a gateway fails, connections rehash to a new gateway              |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  3. MULTI-REGION DEPLOYMENT                                             |
|  ----------------------------                                           |
|                                                                         |
|  For global low-latency access:                                         |
|                                                                         |
|  LEADER-PER-DOCUMENT MODEL:                                             |
|  * Each document has a "home region" (where it was created              |
|    or where most editors are)                                           |
|  * The home region runs the OT/CRDT engine for that doc                 |
|  * Other regions proxy WebSocket connections to the home region         |
|                                                                         |
|  +-------------+        +-------------+        +-------------+          |
|  | US-EAST     |<------>| EU-WEST     |<------>| AP-SOUTH    |          |
|  | Leader for  |        | Leader for  |        | Leader for  |          |
|  | doc A, C    |        | doc B, D    |        | doc E, F    |          |
|  +-------------+        +-------------+        +-------------+          |
|                                                                         |
|  Alternative: CRDT allows true multi-leader (no single home region),    |
|  but adds complexity in garbage collection and tombstone management.    |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  4. OFFLINE EDITING + SYNC                                              |
|  ---------------------------                                            |
|                                                                         |
|  WITH OT (harder):                                                      |
|  * Client buffers ops locally while offline                             |
|  * On reconnect, sends all ops with base version                        |
|  * Server transforms them against all ops that happened while offline   |
|  * Risk: large divergence makes transformation expensive                |
|                                                                         |
|  WITH CRDT (natural):                                                   |
|  * Client applies ops to local CRDT state                               |
|  * On reconnect, sync CRDT states (merge)                               |
|  * Convergence is guaranteed by CRDT properties                         |
|  * This is why CRDTs are preferred for offline-first apps               |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  5. HANDLING HOT DOCUMENTS                                              |
|  ---------------------------                                            |
|                                                                         |
|  A viral document with 500+ concurrent editors:                         |
|                                                                         |
|  * Single Document Service node becomes bottleneck                      |
|  * Solutions:                                                           |
|    a) Vertical scaling (bigger machine for hot docs)                    |
|    b) Operation batching (group ops before transform)                   |
|    c) Read replicas for viewers (only editors need the leader)          |
|    d) Rate limiting per user (max ops/sec)                              |
|    e) Segment the document (different sections on different nodes)      |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  6. WEBSOCKET CONNECTION SCALING                                        |
|  ----------------------------------                                     |
|                                                                         |
|  Problem: 75 million concurrent WebSocket connections                   |
|                                                                         |
|  Each connection consumes:                                              |
|  * ~20 KB memory on the server                                          |
|  * A file descriptor                                                    |
|  * Kernel socket buffer space                                           |
|                                                                         |
|  A single server can handle ~500K-1M connections.                       |
|  Need: 75M / 750K = ~100 gateway servers.                               |
|                                                                         |
|  Add connection limits per gateway, horizontal auto-scaling,            |
|  and health-check-based load balancing.                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11: INTERVIEW Q&A

```
+--------------------------------------------------------------------------+
|                                                                          |
|  Q1: WHAT IS THE DIFFERENCE BETWEEN OT AND CRDT?                         |
|                                                                          |
|  OT transforms concurrent operations against each other to maintain      |
|  consistency. It requires a central server to serialize operations.      |
|                                                                          |
|  CRDTs use specially designed data structures where concurrent           |
|  operations commute - they produce the same result regardless of         |
|  order. No central server needed; convergence is mathematically          |
|  guaranteed.                                                             |
|                                                                          |
|  OT: proven at scale (Google Docs), lower memory, needs server.          |
|  CRDT: better for offline/P2P, higher memory (unique IDs per char),      |
|  used by Figma and Yjs.                                                  |
|                                                                          |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
|                                                                          |
|  Q2: HOW DOES OFFLINE EDITING WORK?                                      |
|                                                                          |
|  WITH OT: Client buffers operations locally. On reconnect, it sends      |
|  all ops with the base version number. The server transforms them        |
|  against all ops that arrived while the user was offline. This can be    |
|  expensive if the user was offline for a long time.                      |
|                                                                          |
|  WITH CRDT: Much more natural. The client continues editing its local    |
|  CRDT state. On reconnect, it syncs with the server. Because CRDT        |
|  operations commute, the merge is automatic and correct. This is why     |
|  offline-first applications prefer CRDTs.                                |
|                                                                          |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
|                                                                          |
|  Q3: HOW DO YOU SCALE WEBSOCKET CONNECTIONS TO MILLIONS OF USERS?        |
|                                                                          |
|  1. Horizontal scaling: many WebSocket gateway servers behind a          |
|     load balancer. Each server handles ~500K-1M connections.             |
|                                                                          |
|  2. Session affinity: route all users of the same document to the        |
|     same gateway (consistent hashing on docId). This avoids cross-       |
|     gateway communication when broadcasting operations.                  |
|                                                                          |
|  3. Connection management: heartbeats to detect dead connections,        |
|     graceful reconnection with last-seen version, connection pooling.    |
|                                                                          |
|  4. Auto-scaling: monitor connections per gateway, scale up when         |
|     utilization exceeds threshold.                                       |
|                                                                          |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
|                                                                          |
|  Q4: WHAT CONSISTENCY MODEL DOES THIS SYSTEM USE?                        |
|                                                                          |
|  STRONG EVENTUAL CONSISTENCY:                                            |
|                                                                          |
|  * All replicas that have received the same set of operations will       |
|    be in the same state (convergence).                                   |
|  * Replicas may temporarily diverge (user sees their own edits           |
|    before server confirmation), but they will always converge.           |
|                                                                          |
|  This is weaker than strong consistency (which would require waiting     |
|  for server confirmation before showing any edit), but stronger than     |
|  eventual consistency (because convergence is guaranteed, not just       |
|  probable).                                                              |
|                                                                          |
|  OT achieves this via the central server's total ordering.               |
|  CRDTs achieve this via their mathematical properties.                   |
|                                                                          |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
|                                                                          |
|  Q5: HOW DOES VERSION HISTORY WORK?                                      |
|                                                                          |
|  The system stores an append-only operations log. Periodically,          |
|  snapshots capture the full document state.                              |
|                                                                          |
|  To view version history:                                                |
|  * Show snapshots as version entries, grouped by time and user           |
|  * Allow viewing the document at any snapshot                            |
|  * Show diffs between versions (compare snapshots)                       |
|  * Show per-character attribution (who wrote what)                       |
|                                                                          |
|  To restore a version:                                                   |
|  * Load the snapshot content                                             |
|  * Create a new operation: "replace document with snapshot content"      |
|  * This operation goes through the normal OT/CRDT pipeline               |
|  * History is preserved - restoration is just another edit               |
|                                                                          |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
|                                                                          |
|  Q6: WALK THROUGH A CONFLICT EXAMPLE.                                    |
|                                                                          |
|  Document: "Hello World" (version 10)                                    |
|                                                                          |
|  User A (based on v10): Delete "World" (pos 6-10)                        |
|  User B (based on v10): Bold "World" (pos 6-10)                          |
|                                                                          |
|  Server receives A first:                                                |
|    v11: "Hello " (World deleted)                                         |
|                                                                          |
|  Server receives B (based on v10, but server is at v11):                 |
|    Transform Bold(pos 6-10) against Delete(pos 6-10):                    |
|    The text that B wants to bold no longer exists.                       |
|    B's operation becomes a NO-OP.                                        |
|                                                                          |
|  Result: "Hello " - User A's delete wins. User B's bold is               |
|  meaningless because the target text was deleted.                        |
|                                                                          |
|  Both clients converge to "Hello ".                                      |
|  No data is lost (the delete was intentional, the bold target is gone).  |
|                                                                          |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
|                                                                          |
|  Q7: WHY NOT JUST USE LOCKING?                                           |
|                                                                          |
|  Locking (e.g., lock a paragraph while someone edits it) seems           |
|  simpler, but it destroys the real-time collaborative experience:        |
|                                                                          |
|  1. Users would see "This section is locked by Alice" - frustrating      |
|  2. Lock granularity problem: too coarse = too restrictive,              |
|     too fine = too much overhead                                         |
|  3. Dead locks: User goes offline while holding a lock                   |
|  4. Performance: lock acquisition and release add latency                |
|  5. User expectation: Google Docs allows anyone to type anywhere         |
|     at any time. Locking violates this expectation.                      |
|                                                                          |
|  OT and CRDTs give us the ILLUSION of no conflicts while                 |
|  handling them transparently behind the scenes.                          |
|                                                                          |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
|                                                                          |
|  Q8: HOW DO YOU HANDLE A DOCUMENT WITH 500+ CONCURRENT EDITORS?          |
|                                                                          |
|  This is a "hot partition" problem. Strategies:                          |
|                                                                          |
|  1. SEPARATE VIEWERS FROM EDITORS:                                       |
|     Viewers (read-only) connect to read replicas. Only editors           |
|     connect to the leader. Reduces load dramatically since most          |
|     users are viewers.                                                   |
|                                                                          |
|  2. OPERATION BATCHING:                                                  |
|     Instead of processing one op at a time, batch ops in 50ms            |
|     windows. Transform and broadcast in bulk.                            |
|                                                                          |
|  3. PRESENCE THROTTLING:                                                 |
|     With 500 users, showing 500 cursors is overwhelming.                 |
|     Show only nearby cursors or cursors of "important" users.            |
|     Throttle cursor updates more aggressively.                           |
|                                                                          |
|  4. VERTICAL SCALING:                                                    |
|     Detect hot documents and migrate them to beefier machines.           |
|                                                                          |
|  5. RATE LIMITING:                                                       |
|     Cap operations per user per second to prevent abuse.                 |
|                                                                          |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
|                                                                          |
|  Q9: HOW WOULD YOU ADD REAL-TIME COMMENTS?                               |
|                                                                          |
|  Comments are anchored to text ranges in the document.                   |
|                                                                          |
|  CHALLENGE: The text the comment is anchored to may be edited or         |
|  deleted by other users.                                                 |
|                                                                          |
|  APPROACH:                                                               |
|  1. Anchor comments to character IDs (CRDT) or markers (OT)              |
|     rather than positions.                                               |
|  2. If anchored text is edited, the comment "follows" the text.          |
|  3. If anchored text is deleted, the comment becomes "orphaned"          |
|     - show it with "referenced text was deleted" note.                   |
|  4. Comments themselves are a separate data structure (not part of       |
|     the document OT/CRDT), synced via their own channel.                 |
|  5. Comment CRUD operations: create, reply, resolve, delete - all        |
|     broadcast in real-time via WebSocket.                                |
|                                                                          |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
|                                                                          |
|  Q10: WHAT HAPPENS WHEN THE SERVER CRASHES MID-OPERATION?                |
|                                                                          |
|  SCENARIO: Document Service node crashes after receiving an op           |
|  but before persisting it.                                               |
|                                                                          |
|  RECOVERY:                                                               |
|  1. The client never received an ACK for the operation.                  |
|  2. Client detects disconnection via WebSocket close/heartbeat fail.     |
|  3. Client reconnects to a new Document Service node.                    |
|  4. New node loads latest snapshot + ops log = last consistent state.    |
|  5. Client re-sends all unacknowledged operations (from its buffer).     |
|  6. Server processes them as normal (transform + apply + persist).       |
|                                                                          |
|  KEY INSIGHT: The client's pending operation buffer acts as a WAL        |
|  (write-ahead log). No operation is ever lost because the client         |
|  retains it until the server ACKs.                                       |
|                                                                          |
|  For the server: write ops to the durable log BEFORE broadcasting.       |
|  This ensures that even if the server crashes after persist but          |
|  before broadcast, the op is recoverable.                                |
|                                                                          |
+--------------------------------------------------------------------------+
```
