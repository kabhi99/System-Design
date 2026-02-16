# CHAPTER 2: PODS
*The Fundamental Unit of Kubernetes*

The Pod is the smallest deployable unit in Kubernetes. Understanding Pods is
essential because every workload in Kubernetes runs inside a Pod.

## SECTION 2.1: WHAT IS A POD?

### POD DEFINITION

A Pod is:
- The smallest deployable unit in Kubernetes
- A wrapper around one or more containers
- A group of containers that share network and storage
- The unit of scheduling (pods are scheduled, not containers)

### PODS vs CONTAINERS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY PODS, NOT JUST CONTAINERS?                                        |
|                                                                         |
|  A Pod provides:                                                       |
|                                                                         |
|  1. SHARED NETWORK NAMESPACE                                           |
|     * All containers in a pod share IP address                        |
|     * Containers communicate via localhost                            |
|     * No port conflicts between pods (each has own IP)               |
|                                                                         |
|  2. SHARED STORAGE                                                     |
|     * Volumes are defined at pod level                                |
|     * All containers can access shared volumes                       |
|                                                                         |
|  3. SHARED LIFECYCLE                                                   |
|     * Containers start and stop together                              |
|     * Pod is atomic unit of deployment                               |
|                                                                         |
|  4. CO-SCHEDULING                                                      |
|     * Containers in a pod run on same node                           |
|     * Guaranteed to be scheduled together                            |
|                                                                         |
|                                                                         |
|  ANALOGY: Pod = Logical Host                                          |
|                                                                         |
|  Think of a Pod as a single logical machine:                          |
|  * Multiple processes (containers) can run                           |
|  * They share localhost network                                       |
|  * They share filesystem areas                                       |
|  * They share fate (live and die together)                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### POD ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|                              POD                                       |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  SHARED NETWORK NAMESPACE                                       |   |
|  |  IP: 10.244.1.5                                                |   |
|  |                                                                 |   |
|  |  +---------------+   +---------------+   +---------------+    |   |
|  |  |  Container 1  |   |  Container 2  |   |  Container 3  |    |   |
|  |  |  (main app)   |   |  (sidecar)    |   |  (init)       |    |   |
|  |  |               |   |               |   |               |    |   |
|  |  |  Port: 8080   |   |  Port: 9090   |   |  (completed)  |    |   |
|  |  |               |   |               |   |               |    |   |
|  |  |     |         |   |       |       |   |               |    |   |
|  |  +-----+---------+   +-------+-------+   +---------------+    |   |
|  |        |                     |                                |   |
|  |        |   localhost:9090    |                                |   |
|  |        +---------------------+                                |   |
|  |                                                                 |   |
|  |  SHARED VOLUMES                                                |   |
|  |  +---------------------------------------------------------+  |   |
|  |  |  Volume: data-volume                                    |  |   |
|  |  |  (accessible by all containers)                         |  |   |
|  |  +---------------------------------------------------------+  |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  EXTERNAL ACCESS: 10.244.1.5:8080                                     |
|  INTERNAL (between containers): localhost:port                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.2: POD NETWORKING (Deep Dive)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HOW DOES A POD GET AN IP ADDRESS?                                    |
|  ==================================                                     |
|                                                                         |
|  When a pod is created, this happens:                                 |
|                                                                         |
|  1. Scheduler assigns pod to a Node                                   |
|  2. Kubelet on that Node receives pod spec                           |
|  3. Kubelet calls CNI plugin (Calico/Flannel/AWS VPC CNI)           |
|  4. CNI plugin:                                                        |
|     * Creates a network namespace for the pod                        |
|     * Assigns an IP from the node's pod CIDR range                  |
|     * Sets up virtual ethernet (veth) pair                          |
|     * Configures routing                                             |
|  5. Pod now has its own IP!                                          |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                         NODE                                    |   |
|  |                    (Pod CIDR: 10.244.1.0/24)                   |   |
|  |                                                                 |   |
|  |  +----------------------------------------------------------+  |   |
|  |  |  POD (gets IP from node's CIDR)                          |  |   |
|  |  |                                                          |  |   |
|  |  |  Network Namespace: pod-abc123                          |  |   |
|  |  |  IP: 10.244.1.5 (assigned by CNI)                       |  |   |
|  |  |                                                          |  |   |
|  |  |  +------------+  +------------+                         |  |   |
|  |  |  | Container1 |  | Container2 |  < Share same IP!      |  |   |
|  |  |  | :8080      |  | :9090      |                         |  |   |
|  |  |  +------------+  +------------+                         |  |   |
|  |  |                                                          |  |   |
|  |  +----------------------------------------------------------+  |   |
|  |                                                                 |   |
|  |  Other pods on same node:                                      |   |
|  |  Pod-2: 10.244.1.6                                            |   |
|  |  Pod-3: 10.244.1.7                                            |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  KEY POINTS:                                                          |
|  * Each NODE has a pod CIDR range (e.g., 10.244.1.0/24)            |
|  * Each POD gets unique IP from that range                          |
|  * All CONTAINERS in a pod share the same IP                        |
|  * Pod IP is EPHEMERAL - changes on restart/reschedule             |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  CONTAINER-TO-CONTAINER COMMUNICATION (Same Pod)                      |
|  ================================================                       |
|                                                                         |
|  Containers in SAME pod share network namespace:                      |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                          POD                                    |   |
|  |                     IP: 10.244.1.5                             |   |
|  |                                                                 |   |
|  |  +----------------+           +----------------+              |   |
|  |  |   App Server   |           |   Log Sidecar  |              |   |
|  |  |                |           |                |              |   |
|  |  |  Port: 8080    |---------->|  Port: 9090    |              |   |
|  |  |                | localhost |                |              |   |
|  |  |  curl http://  |  :9090    |  Receives logs |              |   |
|  |  |  localhost:9090|           |                |              |   |
|  |  |                |           |                |              |   |
|  |  +----------------+           +----------------+              |   |
|  |                                                                 |   |
|  |  COMMUNICATION: localhost:port (NO network hop!)               |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  WHY LOCALHOST WORKS:                                                 |
|  * Containers share the same network namespace                       |
|  * They see the same "localhost"                                     |
|  * Like processes on same machine                                    |
|  * Super fast - no network overhead                                  |
|                                                                         |
|  ⚠️  PORT CONFLICT: Two containers can't use same port!             |
|      Container1 on :8080 + Container2 on :8080 = ERROR              |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  POD-TO-POD COMMUNICATION (Same Node)                                 |
|  ====================================                                   |
|                                                                         |
|  Pods on same node communicate via virtual bridge:                    |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                         NODE 1                                  |   |
|  |                                                                 |   |
|  |  +----------------+         +----------------+                |   |
|  |  |     Pod A      |         |     Pod B      |                |   |
|  |  |  10.244.1.5    |         |  10.244.1.6    |                |   |
|  |  |                |         |                |                |   |
|  |  |  curl http://  |         |  :8080         |                |   |
|  |  |  10.244.1.6:   |         |                |                |   |
|  |  |  8080          |         |                |                |   |
|  |  +-------+--------+         +-------+--------+                |   |
|  |          | veth                      | veth                    |   |
|  |          |                           |                         |   |
|  |          v                           v                         |   |
|  |  +---------------------------------------------------------+  |   |
|  |  |              VIRTUAL BRIDGE (cbr0/cni0)                 |  |   |
|  |  |                                                         |  |   |
|  |  |   Packet from 10.244.1.5 > 10.244.1.6                 |  |   |
|  |  |   Bridge switches packet to Pod B                      |  |   |
|  |  |                                                         |  |   |
|  |  +---------------------------------------------------------+  |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  FLOW:                                                                 |
|  1. Pod A sends packet to 10.244.1.6:8080                            |
|  2. Packet goes through veth to virtual bridge                       |
|  3. Bridge sees 10.244.1.6 is local, switches to Pod B              |
|  4. Pod B receives packet                                            |
|                                                                         |
|  NO NAT, NO ROUTING - Just L2 switching!                             |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  POD-TO-POD COMMUNICATION (Different Nodes)                           |
|  ===========================================                            |
|                                                                         |
|  Pods on different nodes - CNI handles routing:                       |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  NODE 1 (Pod CIDR: 10.244.1.0/24)                               | |
|  |  +----------------+                                              | |
|  |  |     Pod A      |                                              | |
|  |  |  10.244.1.5    | -+                                           | |
|  |  |                |  |                                           | |
|  |  | curl http://   |  |                                           | |
|  |  | 10.244.2.10    |  |                                           | |
|  |  +----------------+  |                                           | |
|  |         |            |                                           | |
|  |         v            |                                           | |
|  |  +-------------+     |                                           | |
|  |  |   Bridge    |     |                                           | |
|  |  +------+------+     |                                           | |
|  |         |            |                                           | |
|  |         v            |                                           | |
|  |  +-------------+     | 10.244.2.0/24 is on Node 2               | |
|  |  |  Routing    |     | Route via overlay/underlay network        | |
|  |  |  Table      | ----+                                           | |
|  |  +------+------+                                                 | |
|  |         |                                                        | |
|  +---------+--------------------------------------------------------+ |
|            |                                                          |
|            |  OVERLAY NETWORK (VXLAN/IPIP) or AWS VPC routing        |
|            |                                                          |
|  +---------+--------------------------------------------------------+ |
|  |         |                                                        | |
|  |         v                                                        | |
|  |  +-------------+                                                 | |
|  |  |  Routing    |                                                 | |
|  |  |  Table      |                                                 | |
|  |  +------+------+                                                 | |
|  |         |                                                        | |
|  |         v                                                        | |
|  |  +-------------+                                                 | |
|  |  |   Bridge    |                                                 | |
|  |  +------+------+                                                 | |
|  |         |                                                        | |
|  |         v                                                        | |
|  |  +----------------+                                              | |
|  |  |     Pod B      |                                              | |
|  |  |  10.244.2.10   |  < Packet arrives here!                     | |
|  |  |  :8080         |                                              | |
|  |  +----------------+                                              | |
|  |                                                                   | |
|  |  NODE 2 (Pod CIDR: 10.244.2.0/24)                               | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  KEY: Each node knows "10.244.2.0/24 > Node 2"                       |
|       CNI sets up these routes automatically!                         |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  KUBERNETES NETWORKING MODEL - THE RULES                              |
|  =======================================                                |
|                                                                         |
|  Kubernetes requires that CNI plugins implement these rules:          |
|                                                                         |
|  1. EVERY POD GETS A UNIQUE IP                                        |
|     * No NAT between pods                                             |
|     * Pod sees its own IP as source                                   |
|                                                                         |
|  2. ALL PODS CAN COMMUNICATE WITH ALL OTHER PODS                      |
|     * Without NAT                                                      |
|     * Regardless of which node they're on                            |
|                                                                         |
|  3. ALL NODES CAN COMMUNICATE WITH ALL PODS                           |
|     * And vice versa                                                  |
|     * Without NAT                                                      |
|                                                                         |
|  RESULT: Flat network where everything can reach everything          |
|          (before Network Policies are applied)                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  IP ADDRESS RANGES IN KUBERNETES:                                     |
|                                                                         |
|  +-----------------+---------------------+--------------------------+ |
|  | Range           | Name                | Used For                 | |
|  +-----------------+---------------------+--------------------------+ |
|  | 10.244.0.0/16   | Pod CIDR            | Pod IPs                  | |
|  | 10.96.0.0/12    | Service CIDR        | ClusterIP (virtual)      | |
|  | 192.168.x.x     | Node IPs            | Actual node addresses    | |
|  +-----------------+---------------------+--------------------------+ |
|                                                                         |
|  Pod CIDR is subdivided per node:                                     |
|  Node 1: 10.244.1.0/24 (256 pods max)                               |
|  Node 2: 10.244.2.0/24 (256 pods max)                               |
|  Node 3: 10.244.3.0/24 (256 pods max)                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHAT IS NAT? (Network Address Translation)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NAT EXPLAINED                                                         |
|  =============                                                          |
|                                                                         |
|  NAT = Changing the source or destination IP address of a packet      |
|        as it passes through a router/firewall                         |
|                                                                         |
|  COMMON EXAMPLE: Your home network                                     |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |   Your Laptop                    Home Router                   |   |
|  |   192.168.1.10                   (does NAT)                    |   |
|  |        |                              |                        |   |
|  |        | Packet:                      |  Internet              |   |
|  |        | src: 192.168.1.10           |                        |   |
|  |        | dst: 8.8.8.8                |                        |   |
|  |        |                              |                        |   |
|  |        +---------->  ROUTER  ---------+---------->             |   |
|  |                        |              |                        |   |
|  |                   NAT changes:        |  Packet after NAT:    |   |
|  |                   src: 192.168.1.10   |  src: 203.0.113.50    |   |
|  |                        v              |  dst: 8.8.8.8         |   |
|  |                   src: 203.0.113.50   |  (public IP!)         |   |
|  |                   (router's public IP)|                        |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  WHY NAT EXISTS:                                                       |
|  * IPv4 addresses are limited (only ~4 billion)                      |
|  * Private IPs (192.168.x.x) can't be used on internet              |
|  * NAT allows many devices to share one public IP                    |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  TYPES OF NAT                                                          |
|  =============                                                          |
|                                                                         |
|  1. SNAT (Source NAT)                                                  |
|  ---------------------                                                  |
|  Changes the SOURCE IP address                                        |
|                                                                         |
|  Use case: Internal device > Internet                                 |
|  Before: src=192.168.1.10 dst=8.8.8.8                                |
|  After:  src=203.0.113.50 dst=8.8.8.8 (source changed!)              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  2. DNAT (Destination NAT)                                             |
|  --------------------------                                             |
|  Changes the DESTINATION IP address                                   |
|                                                                         |
|  Use case: Internet > Internal server (port forwarding)              |
|  Before: src=1.2.3.4 dst=203.0.113.50:80                            |
|  After:  src=1.2.3.4 dst=192.168.1.100:8080 (dest changed!)         |
|                                                                         |
|  KUBERNETES USES DNAT for Services!                                   |
|  ClusterIP:80 > DNAT > Pod-IP:8080                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  3. MASQUERADE                                                         |
|  ----------------                                                       |
|  Special type of SNAT where source IP is dynamically determined      |
|  (uses outgoing interface's IP)                                       |
|                                                                         |
|  Used when the router's IP might change (DHCP)                       |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  PROBLEMS WITH NAT                                                     |
|  ==================                                                     |
|                                                                         |
|  1. BREAKS END-TO-END CONNECTIVITY                                    |
|     * Server sees router's IP, not client's real IP                  |
|     * Can't easily initiate connection TO the client                 |
|                                                                         |
|  2. COMPLICATES DEBUGGING                                              |
|     * "Who sent this request?" - You see NAT IP, not real IP        |
|     * Logs show wrong source                                         |
|                                                                         |
|  3. PERFORMANCE OVERHEAD                                               |
|     * Every packet needs IP rewriting                                |
|     * Connection tracking consumes memory                            |
|                                                                         |
|  4. STATEFUL                                                           |
|     * Must track all connections                                     |
|     * Connection table can fill up                                   |
|                                                                         |
|  5. BREAKS SOME PROTOCOLS                                              |
|     * Protocols that embed IP in payload (SIP, FTP)                 |
|     * Need special handling (ALG - Application Layer Gateway)       |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  WHY KUBERNETES AVOIDS NAT FOR POD-TO-POD                             |
|  =========================================                              |
|                                                                         |
|  WITH NAT (what Kubernetes DOESN'T do):                               |
|  ----------------------------------------                              |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |   Pod A (10.244.1.5) > Pod B (10.244.2.10)                    |   |
|  |                                                                 |   |
|  |   1. Pod A sends: src=10.244.1.5 dst=10.244.2.10              |   |
|  |   2. NAT on Node 1: src=192.168.1.10 dst=10.244.2.10          |   |
|  |                          ^ Node IP (source changed!)          |   |
|  |   3. Pod B receives and sees source = 192.168.1.10            |   |
|  |                                                                 |   |
|  |   PROBLEM: Pod B doesn't know Pod A's real IP!               |   |
|  |   * Can't reply directly to Pod A                             |   |
|  |   * Logs show wrong source                                    |   |
|  |   * Network policies can't work properly                     |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  WITHOUT NAT (what Kubernetes DOES):                                  |
|  -----------------------------------                                   |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |   Pod A (10.244.1.5) > Pod B (10.244.2.10)                    |   |
|  |                                                                 |   |
|  |   1. Pod A sends: src=10.244.1.5 dst=10.244.2.10              |   |
|  |   2. Routed across nodes (NO NAT)                             |   |
|  |   3. Pod B receives: src=10.244.1.5 dst=10.244.2.10          |   |
|  |                           ^ Real Pod A IP!                    |   |
|  |                                                                 |   |
|  |   BENEFIT: Pod B sees Pod A's real IP                        |   |
|  |   * Can reply directly                                        |   |
|  |   * Proper logging                                            |   |
|  |   * Network policies work correctly                          |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ALTERNATIVES TO NAT (How CNI Plugins Route Traffic)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CNI PLUGINS - DIFFERENT APPROACHES                                   |
|  ===================================                                    |
|                                                                         |
|  How to route pod traffic across nodes WITHOUT NAT:                   |
|                                                                         |
|  +-----------------+------------------------------------------------+  |
|  | Approach        | How It Works                                   |  |
|  +-----------------+------------------------------------------------+  |
|  | Overlay Network | Encapsulate pod packets inside another packet |  |
|  | (VXLAN, IPIP)   | Works anywhere, some overhead                  |  |
|  +-----------------+------------------------------------------------+  |
|  | Direct Routing  | Use routing tables to forward pod traffic     |  |
|  | (BGP)           | No encapsulation, needs network support       |  |
|  +-----------------+------------------------------------------------+  |
|  | Cloud Native    | Use cloud VPC's native routing                |  |
|  | (AWS VPC CNI)   | Best performance, cloud-specific              |  |
|  +-----------------+------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  OPTION 1: OVERLAY NETWORK (VXLAN)                                    |
|  ==================================                                     |
|                                                                         |
|  Used by: Flannel (default), Calico (optional), Weave                 |
|                                                                         |
|  HOW IT WORKS:                                                         |
|  Pod packet is ENCAPSULATED inside another UDP packet                |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  Pod A (10.244.1.5) > Pod B (10.244.2.10)                     |   |
|  |                                                                 |   |
|  |  STEP 1: Pod A creates packet                                  |   |
|  |  +---------------------------------------------+               |   |
|  |  | Inner Packet                                |               |   |
|  |  | src: 10.244.1.5  dst: 10.244.2.10         |               |   |
|  |  | payload: "Hello Pod B"                     |               |   |
|  |  +---------------------------------------------+               |   |
|  |                                                                 |   |
|  |  STEP 2: VXLAN encapsulates (adds outer header)               |   |
|  |  +---------------------------------------------------------+   |   |
|  |  | Outer Packet (UDP)                                      |   |   |
|  |  | src: 192.168.1.10 (Node 1)                             |   |   |
|  |  | dst: 192.168.1.11 (Node 2)  < Node-to-node routing     |   |   |
|  |  | +-----------------------------------------------------+|   |   |
|  |  | | Inner Packet (unchanged!)                           ||   |   |
|  |  | | src: 10.244.1.5  dst: 10.244.2.10                  ||   |   |
|  |  | | payload: "Hello Pod B"                              ||   |   |
|  |  | +-----------------------------------------------------+|   |   |
|  |  +---------------------------------------------------------+   |   |
|  |                                                                 |   |
|  |  STEP 3: Node 2 receives, removes outer header                |   |
|  |          Delivers inner packet to Pod B                       |   |
|  |                                                                 |   |
|  |  Pod B sees: src=10.244.1.5 (Pod A's real IP!)               |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  PROS:                                                                 |
|  Y Works on any network (no special config needed)                   |
|  Y Nodes just need to reach each other                               |
|  Y Easy to set up                                                    |
|                                                                         |
|  CONS:                                                                 |
|  X Overhead (extra headers = larger packets)                         |
|  X Slightly higher latency                                           |
|  X MTU issues (may need to reduce)                                   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  OPTION 2: DIRECT ROUTING (BGP)                                       |
|  ===============================                                        |
|                                                                         |
|  Used by: Calico (default mode)                                       |
|                                                                         |
|  HOW IT WORKS:                                                         |
|  Each node advertises its pod CIDR via BGP                           |
|  Network routers learn: "10.244.1.0/24 > Node 1"                     |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  Pod A (10.244.1.5) > Pod B (10.244.2.10)                     |   |
|  |                                                                 |   |
|  |  Packet (NO encapsulation!):                                   |   |
|  |  +---------------------------------------------+               |   |
|  |  | src: 10.244.1.5  dst: 10.244.2.10         |               |   |
|  |  | payload: "Hello Pod B"                     |               |   |
|  |  +---------------------------------------------+               |   |
|  |                                                                 |   |
|  |  ROUTING:                                                       |   |
|  |  * Node 1 routing table: 10.244.2.0/24 > Node 2               |   |
|  |  * Packet routed directly to Node 2                           |   |
|  |  * Node 2 delivers to Pod B                                   |   |
|  |                                                                 |   |
|  |  Pod B sees: src=10.244.1.5 (Pod A's real IP!)               |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  PROS:                                                                 |
|  Y No encapsulation overhead                                         |
|  Y Best performance                                                  |
|  Y Standard networking (BGP is well understood)                     |
|                                                                         |
|  CONS:                                                                 |
|  X Requires network support for BGP                                  |
|  X More complex setup                                                |
|  X May not work in all environments                                 |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  OPTION 3: CLOUD NATIVE (AWS VPC CNI)                                 |
|  =====================================                                  |
|                                                                         |
|  Used by: AWS EKS (default)                                           |
|                                                                         |
|  HOW IT WORKS:                                                         |
|  Pods get REAL VPC IPs (not private CIDR)                            |
|  VPC routing handles everything natively                              |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  TRADITIONAL CNI:              AWS VPC CNI:                    |   |
|  |  Node IP: 10.0.1.100           Node IP: 10.0.1.100            |   |
|  |  Pod IP:  10.244.1.5           Pod IP:  10.0.1.150 < VPC IP!  |   |
|  |          (overlay)                      (real VPC IP)         |   |
|  |                                                                 |   |
|  |  AWS VPC already knows how to route 10.0.1.150!               |   |
|  |  No overlay, no BGP, just native VPC routing                  |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  PROS:                                                                 |
|  Y Best performance (native cloud networking)                        |
|  Y Pods can be accessed directly from VPC                           |
|  Y Security groups work on pods                                     |
|  Y No encapsulation                                                  |
|                                                                         |
|  CONS:                                                                 |
|  X Limited by VPC IP address availability                           |
|  X Cloud-specific (not portable)                                    |
|  X May run out of IPs on busy nodes                                 |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  COMPARISON SUMMARY                                                    |
|  ==================                                                     |
|                                                                         |
|  +-------------+-------------+-------------+-------------------------+ |
|  | Approach    | Performance | Complexity  | Best For                | |
|  +-------------+-------------+-------------+-------------------------+ |
|  | Overlay     | Good        | Low         | Any environment         | |
|  | (VXLAN)     | (overhead)  | (easy)      | On-prem, cloud          | |
|  +-------------+-------------+-------------+-------------------------+ |
|  | Direct      | Excellent   | Medium      | Controlled networks     | |
|  | (BGP)       | (native)    |             | Data centers            | |
|  +-------------+-------------+-------------+-------------------------+ |
|  | Cloud       | Excellent   | Low         | Specific cloud          | |
|  | Native      | (native)    | (managed)   | AWS, GCP, Azure         | |
|  +-------------+-------------+-------------+-------------------------+ |
|                                                                         |
|  KEY POINT: All approaches preserve the source IP (no NAT)!          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHERE KUBERNETES DOES USE NAT (Services)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KUBERNETES USES DNAT FOR SERVICES                                    |
|  ==================================                                     |
|                                                                         |
|  While pod-to-pod is NO NAT, Services DO use DNAT:                    |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  Client Pod > ClusterIP (10.96.0.100:80)                      |   |
|  |                                                                 |   |
|  |  BEFORE (entering iptables):                                   |   |
|  |  src: 10.244.1.5    dst: 10.96.0.100:80                       |   |
|  |                          ^ ClusterIP (virtual)                |   |
|  |                                                                 |   |
|  |  AFTER (DNAT applied):                                        |   |
|  |  src: 10.244.1.5    dst: 10.244.2.10:8080                    |   |
|  |       ^ unchanged!       ^ Real Pod IP                        |   |
|  |                                                                 |   |
|  |  NOTE: Only DESTINATION is changed (DNAT)                     |   |
|  |        SOURCE remains the real client pod IP!                 |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  WHY THIS IS OK:                                                       |
|  * ClusterIP is virtual (doesn't exist anywhere)                     |
|  * DNAT just translates virtual > real IP                           |
|  * Source IP is preserved (no SNAT)                                  |
|  * Server pod can see client's real IP                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXCEPTION: NodePort with externalTrafficPolicy: Cluster              |
|  -------------------------------------------------------              |
|                                                                         |
|  When external traffic enters via NodePort and pod is on              |
|  different node, SNAT may be used (source becomes node IP).          |
|                                                                         |
|  To preserve client IP: externalTrafficPolicy: Local                  |
|  (but traffic only goes to pods on that node)                        |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT HAPPENS TO POD IP WHEN POD DIES?                                |
|  =====================================                                  |
|                                                                         |
|  SCENARIO: Pod crashes or gets rescheduled                            |
|                                                                         |
|  BEFORE:                                                               |
|  +----------------+                                                    |
|  |     Pod        |                                                    |
|  |  10.244.1.5    |  < Clients know this IP                          |
|  +----------------+                                                    |
|                                                                         |
|  POD DIES...                                                           |
|                                                                         |
|  AFTER (new pod created):                                             |
|  +----------------+                                                    |
|  |     Pod        |                                                    |
|  |  10.244.2.99   |  < DIFFERENT IP! (maybe different node too)      |
|  +----------------+                                                    |
|                                                                         |
|  PROBLEMS:                                                             |
|  * Old IP doesn't work anymore                                        |
|  * Clients hardcoding IP will fail                                   |
|  * Need to re-discover the new IP                                    |
|                                                                         |
|  SOLUTION: Services! (see Chapter 4)                                  |
|  * Service has STABLE IP (10.96.0.100)                               |
|  * Service tracks pod IPs via Endpoints                              |
|  * Clients connect to Service, not Pod                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

```bash
VERIFY POD NETWORKING:
----------------------

# See pod IP
kubectl get pod <pod> -o wide

# See which node pod is on
kubectl get pod <pod> -o wide

# Check pod can reach another pod
kubectl exec <pod> -- curl http://<other-pod-ip>:8080

# See pod's network namespace
kubectl exec <pod> -- cat /etc/hosts
kubectl exec <pod> -- ip addr
```

## SECTION 2.3: POD LIFECYCLE

### POD PHASES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  POD LIFECYCLE PHASES                                                  |
|                                                                         |
|  +----------+    +----------+    +----------+    +----------+        |
|  | Pending  |--->| Running  |--->|Succeeded |    |  Failed  |        |
|  +----------+    +----------+    +----------+    +----------+        |
|       |                |                              ^               |
|       |                |                              |               |
|       |                +------------------------------+               |
|       |                                                               |
|       +-----------------------------------------------+               |
|                                                                         |
|  PENDING:                                                              |
|  * Pod accepted by Kubernetes                                         |
|  * Waiting for scheduling                                             |
|  * Waiting for image download                                         |
|  * Waiting for volume mount                                           |
|                                                                         |
|  RUNNING:                                                              |
|  * At least one container is running                                  |
|  * Or starting/restarting                                             |
|                                                                         |
|  SUCCEEDED:                                                            |
|  * All containers completed successfully                              |
|  * Exit code 0                                                        |
|  * Pod won't restart                                                  |
|                                                                         |
|  FAILED:                                                               |
|  * All containers terminated                                          |
|  * At least one failed (non-zero exit)                               |
|                                                                         |
|  UNKNOWN:                                                              |
|  * State cannot be determined                                         |
|  * Usually node communication issue                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CONTAINER STATES

WAITING:
- Container not started yet
- Pulling image, waiting for dependent containers

RUNNING:
- Container is executing
- Started successfully

TERMINATED:
- Container has stopped
- Either completed or failed

## SECTION 2.3: POD SPECIFICATION

### BASIC POD MANIFEST

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  namespace: default
  labels:
    app: myapp
    environment: production
spec:
  containers:
  - name: main-container
    image: nginx:1.21
    ports:
    - containerPort: 80
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

### COMPLETE POD SPEC REFERENCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  POD SPEC FIELDS                                                       |
|                                                                         |
|  CONTAINERS:                                                           |
|  -----------                                                           |
|  spec:                                                                 |
|    containers:                                                        |
|    - name: app                     # Required                         |
|      image: nginx:1.21             # Required                         |
|      imagePullPolicy: Always       # Always, IfNotPresent, Never     |
|      command: ["/bin/sh"]          # Override ENTRYPOINT             |
|      args: ["-c", "echo hello"]    # Override CMD                    |
|      workingDir: /app                                                 |
|      ports:                                                           |
|      - containerPort: 80                                             |
|        protocol: TCP                                                  |
|      env:                                                             |
|      - name: ENV_VAR                                                 |
|        value: "value"                                                |
|      envFrom:                                                         |
|      - configMapRef:                                                  |
|          name: my-config                                              |
|      volumeMounts:                                                    |
|      - name: data                                                     |
|        mountPath: /data                                               |
|                                                                         |
|  RESOURCES:                                                            |
|  ----------                                                            |
|      resources:                                                       |
|        requests:                   # Minimum guaranteed               |
|          memory: "64Mi"                                               |
|          cpu: "250m"               # 250 millicores = 0.25 CPU       |
|        limits:                     # Maximum allowed                  |
|          memory: "128Mi"                                              |
|          cpu: "500m"                                                  |
|                                                                         |
|  PROBES:                                                               |
|  -------                                                               |
|      livenessProbe:                # Is container alive?             |
|        httpGet:                                                       |
|          path: /healthz                                               |
|          port: 8080                                                   |
|        initialDelaySeconds: 15                                        |
|        periodSeconds: 10                                              |
|                                                                         |
|      readinessProbe:               # Is container ready for traffic? |
|        httpGet:                                                       |
|          path: /ready                                                 |
|          port: 8080                                                   |
|        initialDelaySeconds: 5                                         |
|        periodSeconds: 5                                               |
|                                                                         |
|      startupProbe:                 # Has container started?          |
|        httpGet:                                                       |
|          path: /startup                                               |
|          port: 8080                                                   |
|        failureThreshold: 30                                           |
|        periodSeconds: 10                                              |
|                                                                         |
|  VOLUMES:                                                              |
|  --------                                                              |
|    volumes:                                                           |
|    - name: data                                                       |
|      emptyDir: {}                  # Temp storage, deleted with pod  |
|    - name: config                                                     |
|      configMap:                                                       |
|        name: my-config                                                |
|    - name: secret                                                     |
|      secret:                                                          |
|        secretName: my-secret                                          |
|    - name: persistent                                                 |
|      persistentVolumeClaim:                                           |
|        claimName: my-pvc                                              |
|                                                                         |
|  SCHEDULING:                                                           |
|  -----------                                                           |
|    nodeSelector:                   # Simple node selection           |
|      disktype: ssd                                                   |
|                                                                         |
|    nodeName: worker-1              # Schedule on specific node       |
|                                                                         |
|    affinity:                       # Advanced scheduling             |
|      nodeAffinity:                                                   |
|        ...                                                            |
|      podAffinity:                                                    |
|        ...                                                            |
|      podAntiAffinity:                                                |
|        ...                                                            |
|                                                                         |
|    tolerations:                    # Tolerate taints                 |
|    - key: "key"                                                       |
|      operator: "Equal"                                               |
|      value: "value"                                                  |
|      effect: "NoSchedule"                                            |
|                                                                         |
|  SECURITY:                                                             |
|  ---------                                                             |
|    serviceAccountName: my-sa                                          |
|                                                                         |
|    securityContext:                # Pod-level security              |
|      runAsUser: 1000                                                 |
|      runAsGroup: 3000                                                |
|      fsGroup: 2000                                                   |
|                                                                         |
|    containers:                                                        |
|    - securityContext:              # Container-level security        |
|        runAsNonRoot: true                                            |
|        readOnlyRootFilesystem: true                                  |
|        capabilities:                                                 |
|          drop: ["ALL"]                                               |
|                                                                         |
|  RESTART POLICY:                                                       |
|  ---------------                                                       |
|    restartPolicy: Always           # Always, OnFailure, Never        |
|                                                                         |
|  DNS:                                                                  |
|  ----                                                                  |
|    dnsPolicy: ClusterFirst         # Default                         |
|    dnsConfig:                                                         |
|      nameservers:                                                    |
|      - 8.8.8.8                                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.4: MULTI-CONTAINER PODS

### MULTI-CONTAINER PATTERNS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SIDECAR PATTERN                                                       |
|  ---------------                                                       |
|  Secondary container extends/enhances main container                  |
|                                                                         |
|  +------------------------------------------------------------------+ |
|  |                          POD                                     | |
|  |                                                                  | |
|  |  +----------------+    +----------------+                       | |
|  |  |  Main App      |    |  Log Shipper   |                       | |
|  |  |                |--->|  (sidecar)     |---> Log Storage      | |
|  |  |  Writes logs   |    |  Reads logs    |                       | |
|  |  +----------------+    +----------------+                       | |
|  |         |                      ^                                | |
|  |         +----------------------+                                | |
|  |              Shared volume                                      | |
|  +------------------------------------------------------------------+ |
|                                                                         |
|  USE CASES:                                                            |
|  * Log collection (Fluentd, Filebeat)                                |
|  * Service mesh proxy (Envoy, Istio)                                 |
|  * Monitoring agent                                                   |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  AMBASSADOR PATTERN                                                    |
|  ------------------                                                    |
|  Proxy that simplifies access to external services                   |
|                                                                         |
|  +------------------------------------------------------------------+ |
|  |                          POD                                     | |
|  |                                                                  | |
|  |  +----------------+    +----------------+                       | |
|  |  |  Main App      |--->|  Ambassador    |---> Redis Cluster    | |
|  |  |                |    |  (proxy)       |                       | |
|  |  |  localhost:6379|    |  Handles       |                       | |
|  |  |                |    |  discovery     |                       | |
|  |  +----------------+    +----------------+                       | |
|  +------------------------------------------------------------------+ |
|                                                                         |
|  USE CASES:                                                            |
|  * Database proxy                                                     |
|  * Redis cluster proxy                                               |
|  * API gateway                                                        |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  ADAPTER PATTERN                                                       |
|  ---------------                                                       |
|  Transforms output of main container                                  |
|                                                                         |
|  +------------------------------------------------------------------+ |
|  |                          POD                                     | |
|  |                                                                  | |
|  |  +----------------+    +----------------+                       | |
|  |  |  Main App      |--->|  Adapter       |---> Prometheus       | |
|  |  |                |    |                |                       | |
|  |  |  Custom format |    |  Converts to   |                       | |
|  |  |  metrics       |    |  Prometheus    |                       | |
|  |  +----------------+    +----------------+                       | |
|  +------------------------------------------------------------------+ |
|                                                                         |
|  USE CASES:                                                            |
|  * Metrics format conversion                                          |
|  * Log format transformation                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.5: INIT CONTAINERS

### WHAT ARE INIT CONTAINERS?

Init containers run BEFORE the main containers:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INIT CONTAINER SEQUENCE                                               |
|                                                                         |
|  +------------+   +------------+   +------------+   +------------+   |
|  |  Init 1    |-->|  Init 2    |-->|  Init 3    |-->| Main App   |   |
|  |  (wait for |   |  (download |   |  (migrate  |   | (starts)   |   |
|  |   db)      |   |   config)  |   |   db)      |   |            |   |
|  +------------+   +------------+   +------------+   +------------+   |
|       |                |                |                |            |
|       v                v                v                v            |
|     Runs           Runs after        Runs after       Runs after    |
|     first          init 1            init 2           all inits     |
|                    completes         completes        complete      |
|                                                                         |
|  CHARACTERISTICS:                                                      |
|  * Run sequentially (one at a time)                                  |
|  * Must complete successfully                                        |
|  * If any fails, pod restarts                                       |
|  * Can have different image than main containers                    |
|  * Can have different security context                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### INIT CONTAINER EXAMPLE

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp-pod
spec:
  initContainers:
  # Init 1: Wait for database to be ready
  - name: wait-for-db
    image: busybox
    command: ['sh', '-c', 'until nc -z db-service 5432; do sleep 2; done']

  # Init 2: Download configuration
  - name: download-config
    image: busybox
    command: ['wget', '-O', '/config/app.conf', 'http://config-server/app.conf']
    volumeMounts:
    - name: config
      mountPath: /config

  containers:
  - name: app
    image: myapp:v1
    volumeMounts:
    - name: config
      mountPath: /app/config

  volumes:
  - name: config
    emptyDir: {}
```

## SECTION 2.6: POD COMMANDS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  POD MANAGEMENT COMMANDS                                               |
|                                                                         |
|  CREATE/APPLY:                                                         |
|  -------------                                                         |
|  kubectl run nginx --image=nginx            # Imperative              |
|  kubectl apply -f pod.yaml                  # Declarative             |
|  kubectl create -f pod.yaml                 # Declarative             |
|                                                                         |
|  VIEW:                                                                  |
|  -----                                                                  |
|  kubectl get pods                           # List pods               |
|  kubectl get pods -o wide                   # More details            |
|  kubectl get pods -w                        # Watch changes           |
|  kubectl describe pod <pod>                 # Detailed info           |
|  kubectl get pod <pod> -o yaml              # Full YAML               |
|                                                                         |
|  LOGS:                                                                  |
|  -----                                                                  |
|  kubectl logs <pod>                         # View logs               |
|  kubectl logs <pod> -f                      # Follow logs             |
|  kubectl logs <pod> -c <container>          # Specific container      |
|  kubectl logs <pod> --previous              # Previous container      |
|                                                                         |
|  EXECUTE:                                                               |
|  --------                                                               |
|  kubectl exec <pod> -- ls                   # Run command             |
|  kubectl exec -it <pod> -- bash             # Interactive shell       |
|  kubectl exec <pod> -c <container> -- cmd   # Specific container      |
|                                                                         |
|  DEBUG:                                                                 |
|  ------                                                                 |
|  kubectl debug <pod> --image=busybox        # Debug container        |
|  kubectl debug <pod> --copy-to=debug-pod    # Copy pod for debug     |
|                                                                         |
|  DELETE:                                                                |
|  -------                                                                |
|  kubectl delete pod <pod>                   # Delete pod              |
|  kubectl delete -f <file.yaml>              # Delete from file        |
|  kubectl delete pod <pod> --force           # Force delete            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PODS - KEY TAKEAWAYS                                                  |
|                                                                         |
|  WHAT IS A POD                                                         |
|  -------------                                                         |
|  * Smallest deployable unit                                           |
|  * One or more containers                                             |
|  * Shared network (same IP)                                           |
|  * Shared storage (volumes)                                           |
|  * Shared lifecycle                                                   |
|                                                                         |
|  POD PHASES                                                            |
|  ----------                                                            |
|  * Pending > Running > Succeeded/Failed                               |
|                                                                         |
|  MULTI-CONTAINER PATTERNS                                              |
|  ------------------------                                              |
|  * Sidecar: Extend main container (logging, proxy)                   |
|  * Ambassador: Proxy to external services                            |
|  * Adapter: Transform output format                                  |
|                                                                         |
|  INIT CONTAINERS                                                       |
|  ---------------                                                       |
|  * Run before main containers                                         |
|  * Run sequentially                                                   |
|  * Must complete successfully                                         |
|                                                                         |
|  IMPORTANT: Pods are ephemeral!                                       |
|  Don't create pods directly—use Deployments!                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 2

