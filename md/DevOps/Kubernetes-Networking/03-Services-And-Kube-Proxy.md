# CHAPTER 3: SERVICES AND KUBE-PROXY
*How Kubernetes Routes Traffic to Pods*

Services are one of Kubernetes' most important abstractions. They provide
stable network identities for ephemeral pods. This chapter explains how
services work internally and the different implementation modes.

## SECTION 3.1: WHY SERVICES EXIST

### THE EPHEMERAL POD PROBLEM

Pods are designed to be disposable:
- They can be killed and recreated at any time
- They get new IP addresses when recreated
- They can scale from 1 to 100 instances

This creates a fundamental problem:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM                                                           |
|                                                                         |
|  TIME 0:                                                               |
|  Frontend connects to backend at 10.244.1.5                           |
|  +----------+         +----------+                                    |
|  | Frontend |-------->| Backend  |                                    |
|  |          |         |10.244.1.5|                                    |
|  +----------+         +----------+                                    |
|                                                                         |
|  TIME 1: Backend pod dies and restarts                                |
|  +----------+         +----------+                                    |
|  | Frontend |-------->| Backend  |                                    |
|  |          |    [ ]    |10.244.1.9| <- NEW IP!                         |
|  +----------+         +----------+                                    |
|                                                                         |
|  Frontend still tries 10.244.1.5 -> Connection fails!                  |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  WHAT IF THERE ARE MULTIPLE BACKENDS?                                  |
|                                                                         |
|  +----------+         +----------+ 10.244.1.5                        |
|  | Frontend |-------->| Backend1 |                                    |
|  |          |    ?    +----------+ 10.244.1.6                        |
|  |          |         | Backend2 |                                    |
|  |          |         +----------+ 10.244.1.7                        |
|  |          |         | Backend3 |                                    |
|  +----------+         +----------+                                    |
|                                                                         |
|  Which IP should frontend use?                                        |
|  How does it know about all backends?                                 |
|  What if Backend2 dies?                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### THE SERVICE SOLUTION

A Service provides:

1. STABLE VIRTUAL IP (ClusterIP)
A single IP that never changes

2. DNS NAME
A hostname that resolves to the stable IP

3. LOAD BALANCING
Distributes traffic across all backend pods

4. SERVICE DISCOVERY
Automatically tracks pod additions/removals

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WITH A SERVICE                                                        |
|                                                                         |
|                        SERVICE: backend-svc                            |
|                        ClusterIP: 10.96.0.10                          |
|                        DNS: backend-svc.default.svc.cluster.local     |
|                                                                         |
|  +----------+              |                                           |
|  | Frontend |--------------+                                           |
|  |          |              |                                           |
|  | Connects |              | (Load balances)                           |
|  | to:      |              |                                           |
|  | backend- |              +---------------------+                    |
|  | svc:8080 |              |                     |                    |
|  +----------+              |                     |                    |
|                            v                     v                    |
|                   +--------------+      +--------------+              |
|                   |   Backend1   |      |   Backend2   |              |
|                   |  10.244.1.5  |      |  10.244.1.6  |              |
|                   +--------------+      +--------------+              |
|                                                                         |
|  * Frontend always uses 10.96.0.10 or DNS name                        |
|  * Service automatically discovers backend pods via selectors         |
|  * If Backend1 dies, traffic goes to Backend2                        |
|  * If Backend3 is added, it automatically joins the pool             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.2: SERVICE TYPES EXPLAINED

Kubernetes supports FOUR service types:

### CLUSTERIP — INTERNAL ACCESS ONLY (DEFAULT)

The most common service type. Creates a virtual IP accessible only within
the cluster.

```
apiVersion: v1
kind: Service
metadata:
  name: backend-svc
spec:
  type: ClusterIP  # Default, can be omitted
  selector:
    app: backend
  ports:
    - port: 80           # Service port
      targetPort: 8080   # Container port

WHAT HAPPENS:
* Kubernetes assigns virtual IP from service CIDR (e.g., 10.96.1.123)
* This IP is VIRTUAL - no interface has this IP
* kube-proxy programs iptables/IPVS to redirect to pod IPs

+-------------------------------------------------------------------------+
|                                                                         |
|  CLUSTERIP SERVICE                                                     |
|                                                                         |
|                                                                         |
|   +------------------------------------------------------------------+ |
|   |                                                                  | |
|   |   VIRTUAL IP: 10.96.1.123                                       | |
|   |   (doesn't exist on any interface - implemented in iptables)    | |
|   |                                                                  | |
|   |                      |                                          | |
|   |                      | iptables DNAT                            | |
|   |                      |                                          | |
|   |            +---------+---------+                                | |
|   |            |         |         |                                | |
|   |            v         v         v                                | |
|   |      +---------+ +---------+ +---------+                       | |
|   |      |  Pod 1  | |  Pod 2  | |  Pod 3  |                       | |
|   |      |10.244   | |10.244   | |10.244   |                       | |
|   |      |.0.10    | |.1.20    | |.2.30    |                       | |
|   |      +---------+ +---------+ +---------+                       | |
|   |                                                                  | |
|   +------------------------------------------------------------------+ |
|                                                                         |
|   ACCESSIBILITY:                                                       |
|   [x] From any pod in the cluster                                       |
|   [x] From nodes                                                        |
|   [ ] From outside the cluster                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### NODEPORT — EXTERNAL ACCESS VIA NODE PORTS

Exposes the service on a port on EVERY node:

```
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  type: NodePort
  selector:
    app: web
  ports:
    - port: 80           # ClusterIP port
      targetPort: 8080   # Container port
      nodePort: 30080    # Port on every node (30000-32767)

+-------------------------------------------------------------------------+
|                                                                         |
|  NODEPORT SERVICE                                                      |
|                                                                         |
|   EXTERNAL CLIENT                                                       |
|         |                                                               |
|         | Can connect to ANY node on port 30080                        |
|         |                                                               |
|         v                                                               |
|   +-------------------------------------------------------------------+|
|   |                                                                   ||
|   |  NODE 1 (192.168.1.10:30080)     NODE 2 (192.168.1.11:30080)     ||
|   |  +------------------------+     +------------------------+       ||
|   |  |                        |     |                        |       ||
|   |  |   Traffic on :30080    |     |   Traffic on :30080    |       ||
|   |  |          |             |     |          |             |       ||
|   |  |          v             |     |          v             |       ||
|   |  |    iptables DNAT      |     |    iptables DNAT      |       ||
|   |  |          |             |     |          |             |       ||
|   |  +----------+-------------+     +----------+-------------+       ||
|   |             |                              |                      ||
|   |             +--------------+---------------+                      ||
|   |                            |                                      ||
|   |                            v                                      ||
|   |           +------------------------------------+                 ||
|   |           |        ClusterIP: 10.96.0.50       |                 ||
|   |           +----------------+-------------------+                 ||
|   |                            |                                      ||
|   |              +-------------+-------------+                        ||
|   |              |             |             |                        ||
|   |              v             v             v                        ||
|   |        +---------+   +---------+   +---------+                   ||
|   |        |  Pod 1  |   |  Pod 2  |   |  Pod 3  |                   ||
|   |        +---------+   +---------+   +---------+                   ||
|   |                                                                   ||
|   +-------------------------------------------------------------------+|
|                                                                         |
|   CLIENT CAN CONNECT TO:                                               |
|   * 192.168.1.10:30080 (Node 1)                                       |
|   * 192.168.1.11:30080 (Node 2)                                       |
|   * ANY other node:30080                                              |
|                                                                         |
|   Traffic will reach pods even if they're not on that node!           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### LOADBALANCER — CLOUD LOAD BALANCER INTEGRATION

Provisions an external load balancer (in cloud environments):

```
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  type: LoadBalancer
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 8080

+-------------------------------------------------------------------------+
|                                                                         |
|  LOADBALANCER SERVICE (AWS Example)                                    |
|                                                                         |
|   INTERNET                                                              |
|       |                                                                |
|       v                                                                |
|   +---------------------------------------------------------------+   |
|   |              AWS Elastic Load Balancer                        |   |
|   |              DNS: abc123.us-west-2.elb.amazonaws.com         |   |
|   |              External IP: 54.123.45.67                        |   |
|   |                                                               |   |
|   |  * Provisioned automatically by cloud-controller-manager     |   |
|   |  * Sends traffic to NodePort on healthy nodes                |   |
|   |  * Health checks nodes automatically                         |   |
|   |                                                               |   |
|   +---------------------------+-----------------------------------+   |
|                               |                                        |
|                               v                                        |
|   +---------------------------------------------------------------+   |
|   |                        NodePort                               |   |
|   |                                                               |   |
|   |    Node 1:30123           Node 2:30123          Node 3:30123 |   |
|   |         |                      |                      |       |   |
|   +---------+----------------------+----------------------+-------+   |
|             |                      |                      |           |
|             +----------------------+----------------------+           |
|                                    |                                   |
|                                    v                                   |
|   +---------------------------------------------------------------+   |
|   |                        ClusterIP                              |   |
|   |                                                               |   |
|   |                 +-----------------------+                     |   |
|   |                 |    Pod 1  |  Pod 2    |                     |   |
|   |                 +-----------------------+                     |   |
|   |                                                               |   |
|   +---------------------------------------------------------------+   |
|                                                                         |
|   LoadBalancer = ClusterIP + NodePort + Cloud Load Balancer           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### EXTERNALNAME — DNS ALIAS

Maps a service to an external DNS name (no proxying):

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-database
spec:
  type: ExternalName
  externalName: db.example.com

WHAT HAPPENS:
* DNS query for my-database.default.svc.cluster.local
* Returns CNAME: db.example.com
* No ClusterIP assigned
* No proxying—just DNS aliasing

USE CASES:
* Pointing to external databases
* Migrating from external to internal services
* Different environments (staging -> external, prod -> internal)
```

## SECTION 3.3: HOW SERVICES WORK — ENDPOINTS AND SELECTORS

### THE SELECTOR -> ENDPOINT FLOW

Services find their backend pods using SELECTORS:

```
SERVICE:
+----------------------------------------------------------------+
|  apiVersion: v1                                                |
|  kind: Service                                                 |
|  metadata:                                                     |
|    name: backend-svc                                          |
|  spec:                                                         |
|    selector:           <-- Selector                           |
|      app: backend                                             |
|      tier: api                                                |
|    ports:                                                      |
|      - port: 80                                               |
|        targetPort: 8080                                       |
+----------------------------------------------------------------+

MATCHING PODS:
+----------------------------------------------------------------+
|  apiVersion: v1                                                |
|  kind: Pod                                                     |
|  metadata:                                                     |
|    name: backend-pod-1                                        |
|    labels:             <-- Labels must match selector         |
|      app: backend                                             |
|      tier: api                                                |
|  ...                                                           |
+----------------------------------------------------------------+
```

### ENDPOINTS OBJECT

Kubernetes automatically creates an ENDPOINTS object for each service:

```bash
# View endpoints for a service
kubectl get endpoints backend-svc

NAME          ENDPOINTS                                          AGE
backend-svc   10.244.0.10:8080,10.244.1.20:8080,10.244.2.30:8080 1d

# Detailed view
kubectl describe endpoints backend-svc

Name:         backend-svc
Namespace:    default
Labels:       <none>
Annotations:  <none>
Subsets:
  Addresses:          10.244.0.10, 10.244.1.20, 10.244.2.30
  NotReadyAddresses:  <none>
  Ports:
    Name     Port  Protocol
    ----     ----  --------
    <unset>  8080  TCP
```

### ENDPOINT SLICES (NEW)

For large clusters, Kubernetes now uses EndpointSlices:

```bash
# View endpoint slices
kubectl get endpointslices

NAME                 ADDRESSTYPE   PORTS   ENDPOINTS                    AGE
backend-svc-abc123   IPv4          8080    10.244.0.10,10.244.1.20...  1d
```

Why EndpointSlices?
- Large services might have thousands of endpoints
- Single Endpoints object becomes too large
- EndpointSlices split endpoints into manageable chunks (100 by default)
- Updates are more efficient (change one slice, not entire list)

### THE ENDPOINT CONTROLLER

The kube-controller-manager runs an Endpoint Controller that:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ENDPOINT CONTROLLER FLOW                                              |
|                                                                         |
|  1. WATCH for Service changes                                          |
|     |                                                                   |
|     v                                                                   |
|  2. WATCH for Pod changes                                              |
|     |                                                                   |
|     v                                                                   |
|  3. For each Service, find pods matching selector                      |
|     |                                                                   |
|     v                                                                   |
|  4. Create/Update Endpoints object with pod IPs                       |
|     |                                                                   |
|     v                                                                   |
|  5. ONLY include pods that:                                            |
|     * Have matching labels                                             |
|     * Are in "Running" phase                                           |
|     * Have passed readiness probe                                      |
|     |                                                                   |
|     v                                                                   |
|  6. kube-proxy watches Endpoints and updates iptables/IPVS            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.4: KUBE-PROXY — THE SERVICE IMPLEMENTATION

### WHAT IS KUBE-PROXY?

kube-proxy is a network proxy that runs on every node. It implements the
Service abstraction by programming the data plane (iptables or IPVS).

kube-proxy DOES NOT proxy traffic itself (despite the name)!
It programs rules that the kernel uses to redirect traffic.

### KUBE-PROXY MODES

kube-proxy supports THREE modes:

1. iptables mode (default)
2. IPVS mode (high performance)
3. userspace mode (legacy, don't use)

### IPTABLES MODE — HOW IT WORKS

When using iptables mode, kube-proxy creates chains of rules:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IPTABLES RULES FOR A SERVICE                                          |
|                                                                         |
|  Service: backend-svc                                                   |
|  ClusterIP: 10.96.0.100:80                                             |
|  Endpoints: 10.244.0.10:8080, 10.244.1.20:8080, 10.244.2.30:8080      |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  CHAIN: KUBE-SERVICES                                                  |
|  Rule: -d 10.96.0.100/32 -p tcp --dport 80 -j KUBE-SVC-XXXXXX        |
|        (If destination is service IP, jump to service chain)          |
|                                                                         |
|  CHAIN: KUBE-SVC-XXXXXX (the service chain)                           |
|  Rule 1: -m statistic --mode random --probability 0.33333            |
|          -j KUBE-SEP-AAAAAA                                           |
|          (33% chance: go to endpoint A)                               |
|                                                                         |
|  Rule 2: -m statistic --mode random --probability 0.50000            |
|          -j KUBE-SEP-BBBBBB                                           |
|          (50% of remaining = 33% total: go to endpoint B)            |
|                                                                         |
|  Rule 3: -j KUBE-SEP-CCCCCC                                          |
|          (Remaining 33%: go to endpoint C)                            |
|                                                                         |
|  CHAIN: KUBE-SEP-AAAAAA (endpoint A)                                  |
|  Rule: -p tcp -j DNAT --to-destination 10.244.0.10:8080              |
|        (Change destination to pod IP)                                 |
|                                                                         |
|  CHAIN: KUBE-SEP-BBBBBB (endpoint B)                                  |
|  Rule: -p tcp -j DNAT --to-destination 10.244.1.20:8080              |
|                                                                         |
|  CHAIN: KUBE-SEP-CCCCCC (endpoint C)                                  |
|  Rule: -p tcp -j DNAT --to-destination 10.244.2.30:8080              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### VIEWING IPTABLES RULES

You can see the actual rules kube-proxy creates:

```bash
# See all kube-proxy chains
iptables -t nat -L | grep KUBE

# See rules for a specific service
iptables -t nat -L KUBE-SERVICES -n | grep <service-ip>

# Full detail with line numbers
iptables -t nat -L KUBE-SVC-XXXXX -n -v --line-numbers
```

### IPTABLES MODE LIMITATIONS

LIMITATION 1: O(n) RULE MATCHING
- Each service adds multiple iptables rules
- 10,000 services = 100,000+ rules
- Every packet traverses rules sequentially
- Performance degrades with scale

LIMITATION 2: NO GRACEFUL TERMINATION
- When endpoint removed, connection immediately fails
- No connection draining

LIMITATION 3: LIMITED LOAD BALANCING
- Only random (statistical) balancing
- No least-connections, weighted, etc.

### IPVS MODE — HIGH PERFORMANCE

IPVS (IP Virtual Server) is a transport-layer load balancer built into Linux:

```bash
ENABLING IPVS MODE:
# Edit kube-proxy ConfigMap
kubectl edit configmap kube-proxy -n kube-system

# Change mode to "ipvs"
mode: "ipvs"

# Restart kube-proxy pods
kubectl rollout restart daemonset kube-proxy -n kube-system
```

### WHY IPVS IS FASTER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IPTABLES vs IPVS                                                      |
|                                                                         |
|  IPTABLES:                                                             |
|                                                                         |
|  Packet -> Rule 1 -> Rule 2 -> Rule 3 -> ... -> Rule N -> Match!            |
|                                                                         |
|  * Sequential rule matching O(n)                                       |
|  * 10,000 services = slow!                                            |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  IPVS:                                                                  |
|                                                                         |
|  Packet -> Hash Table Lookup -> Match!                                   |
|                                                                         |
|  * Hash-based lookup O(1)                                              |
|  * 10,000 services = still fast!                                      |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  IPVS LOAD BALANCING ALGORITHMS:                                       |
|                                                                         |
|  * rr  - Round Robin (default)                                        |
|  * lc  - Least Connection                                             |
|  * dh  - Destination Hashing                                          |
|  * sh  - Source Hashing (sticky sessions)                             |
|  * sed - Shortest Expected Delay                                      |
|  * nq  - Never Queue                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### VIEWING IPVS RULES

```bash
# Install ipvsadm tool
apt-get install ipvsadm

# List all virtual servers
ipvsadm -Ln

IP Virtual Server version 1.2.1 (size=4096)
Prot LocalAddress:Port Scheduler Flags
  -> RemoteAddress:Port           Forward Weight ActiveConn InActConn
TCP  10.96.0.100:80 rr
  -> 10.244.0.10:8080             Masq    1      0          0
  -> 10.244.1.20:8080             Masq    1      0          0
  -> 10.244.2.30:8080             Masq    1      0          0
```

## SECTION 3.5: SERVICE TRAFFIC POLICIES

### EXTERNALTRAFFICPOLICY

Controls how EXTERNAL traffic is routed:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  externalTrafficPolicy: Cluster (default)                              |
|  -----------------------------------------                              |
|                                                                         |
|  External traffic -> Any node -> Potentially forwarded to another node   |
|                                                                         |
|   Client                                                               |
|     |                                                                   |
|     v                                                                   |
|   Node 1 (no matching pod) ----SNAT----> Node 2 (has pod)             |
|                                          |                             |
|                                          v                             |
|                                        Pod                             |
|                                                                         |
|  CHARACTERISTICS:                                                      |
|  * Load balanced across ALL pods                                       |
|  * Extra hop if pod not on receiving node                             |
|  * Client IP is NATed (pod sees node IP, not client IP)              |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  externalTrafficPolicy: Local                                          |
|  -----------------------------                                         |
|                                                                         |
|  External traffic -> Only to pods on the receiving node                 |
|                                                                         |
|   Client                                                               |
|     |                                                                   |
|     v                                                                   |
|   Node 1 (has pod) ----> Pod (on same node)                           |
|                                                                         |
|   Client                                                               |
|     |                                                                   |
|     v                                                                   |
|   Node 2 (no matching pod) ----> DROPPED (no local pod)               |
|                                                                         |
|  CHARACTERISTICS:                                                      |
|  * Preserves client IP (pod sees real client IP)                      |
|  * No extra hop                                                        |
|  * Uneven distribution if pods not on all nodes                       |
|  * Requires external LB to handle node without pods                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### INTERNALTRAFFICPOLICY

Controls how INTERNAL (pod-to-service) traffic is routed:

```yaml
spec:
  internalTrafficPolicy: Local  # Only route to pods on same node

USE CASES:
* Reduce cross-node traffic for high-volume internal services
* Node-local caching services
* Lower latency requirements
```

## SECTION 3.6: HEADLESS SERVICES

### WHAT IS A HEADLESS SERVICE?

A headless service has clusterIP: None. It doesn't get a virtual IP.
Instead, DNS returns the individual pod IPs.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: db-headless
spec:
  clusterIP: None  # This makes it headless
  selector:
    app: database
  ports:
    - port: 5432
```

### HEADLESS DNS BEHAVIOR

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REGULAR SERVICE DNS:                                                  |
|                                                                         |
|  dig backend-svc.default.svc.cluster.local                            |
|                                                                         |
|  ANSWER:                                                               |
|  backend-svc.default.svc.cluster.local. IN A 10.96.0.100              |
|                                                                         |
|  Returns: ClusterIP (single virtual IP)                               |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  HEADLESS SERVICE DNS:                                                 |
|                                                                         |
|  dig db-headless.default.svc.cluster.local                            |
|                                                                         |
|  ANSWER:                                                               |
|  db-headless.default.svc.cluster.local. IN A 10.244.0.10              |
|  db-headless.default.svc.cluster.local. IN A 10.244.1.20              |
|  db-headless.default.svc.cluster.local. IN A 10.244.2.30              |
|                                                                         |
|  Returns: All pod IPs directly                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### USE CASES FOR HEADLESS SERVICES

1. STATEFULSETS
Each pod needs unique identity:
mysql-0.mysql-headless.default.svc.cluster.local -> 10.244.0.5
mysql-1.mysql-headless.default.svc.cluster.local -> 10.244.1.6
mysql-2.mysql-headless.default.svc.cluster.local -> 10.244.2.7

2. CLIENT-SIDE LOAD BALANCING
Application gets all IPs and balances itself
Useful for gRPC which maintains persistent connections

3. SERVICE DISCOVERY
Get list of all backend IPs for custom routing logic

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICES AND KUBE-PROXY - KEY TAKEAWAYS                              |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  SERVICE TYPES                                                   | |
|  |  * ClusterIP: Internal only (default)                           | |
|  |  * NodePort: Expose on node ports (30000-32767)                 | |
|  |  * LoadBalancer: Cloud load balancer                            | |
|  |  * ExternalName: DNS alias                                      | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  SERVICE DISCOVERY                                               | |
|  |  * Selectors match pod labels                                   | |
|  |  * Endpoint controller creates Endpoints objects                | |
|  |  * Only Ready pods are included                                 | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  KUBE-PROXY MODES                                                | |
|  |  * iptables: Default, O(n) rules, simple                       | |
|  |  * IPVS: High-performance, O(1) lookup, more algorithms        | |
|  |  * Use IPVS for >1000 services                                  | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  TRAFFIC POLICIES                                                | |
|  |  * externalTrafficPolicy: Cluster (NAT) vs Local (preserve IP) | |
|  |  * internalTrafficPolicy: Control internal routing              | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 3

