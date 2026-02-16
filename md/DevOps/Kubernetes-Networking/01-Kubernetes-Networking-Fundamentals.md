# CHAPTER 1: KUBERNETES NETWORKING FUNDAMENTALS
*Understanding the Model That Makes Cluster Networking Work*

Kubernetes networking is fundamentally different from traditional infrastructure
networking. This chapter explains the core concepts, requirements, and design
decisions that shape how pods, services, and nodes communicate.

By the end of this chapter, you'll understand:
- Why Kubernetes networking is designed the way it is
- The four fundamental networking problems Kubernetes solves
- The Kubernetes networking model and its requirements
- How IP addresses are assigned and managed

## SECTION 1.1: THE FOUR NETWORKING PROBLEMS

Kubernetes identifies FOUR distinct networking challenges:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE FOUR KUBERNETES NETWORKING CHALLENGES                             |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  1. CONTAINER-TO-CONTAINER COMMUNICATION                         | |
|  |     How do containers within the same pod communicate?           | |
|  |     Solution: Shared network namespace (localhost)               | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  2. POD-TO-POD COMMUNICATION                                     | |
|  |     How do pods communicate with other pods?                     | |
|  |     Solution: Flat network where every pod can reach every pod   | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  3. POD-TO-SERVICE COMMUNICATION                                 | |
|  |     How do pods access services (stable endpoints)?              | |
|  |     Solution: Virtual IPs and kube-proxy                         | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  4. EXTERNAL-TO-SERVICE COMMUNICATION                            | |
|  |     How does external traffic reach services?                    | |
|  |     Solution: LoadBalancers, Ingress, NodePort                   | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

Let's examine each problem in detail.

## SECTION 1.2: CONTAINER-TO-CONTAINER COMMUNICATION

### THE POD NETWORKING MODEL

In Kubernetes, the fundamental deployment unit is a POD, not a container.
A pod can contain one or more containers that are tightly coupled.

KEY INSIGHT: All containers in a pod share the SAME network namespace.

```
+-------------------------------------------------------------------------+
|                                                                         |
|                             POD                                        |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |                  SHARED NETWORK NAMESPACE                       |   |
|  |                                                                 |   |
|  |   +-------------+    +-------------+    +-------------+        |   |
|  |   | Container A |    | Container B |    | Container C |        |   |
|  |   |  (app)      |    |  (sidecar)  |    |  (logging)  |        |   |
|  |   |             |    |             |    |             |        |   |
|  |   | Port: 8080  |    | Port: 9090  |    | Port: 3000  |        |   |
|  |   +-------------+    +-------------+    +-------------+        |   |
|  |           |                 |                 |                |   |
|  |           |                 |                 |                |   |
|  |           +-----------------+-----------------+                |   |
|  |                             |                                   |   |
|  |                       SHARED eth0                              |   |
|  |                     IP: 10.244.1.5                             |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  WHAT THIS MEANS:                                                      |
|  * All containers share the SAME IP address (10.244.1.5)              |
|  * Container A can reach Container B via localhost:9090               |
|  * Container B can reach Container A via localhost:8080               |
|  * Containers CANNOT use the same port (conflict!)                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY SHARE A NETWORK NAMESPACE?

This design enables several important patterns:

```bash
1. SIDECAR PATTERN
   A sidecar container can intercept all traffic to the main container:

   Example: Istio service mesh injects an Envoy proxy sidecar
   * Main app listens on localhost:8080
   * Envoy intercepts external traffic, applies policies
   * Envoy forwards to localhost:8080

2. ADAPTER PATTERN
   A container can transform data format for the main container:

   Example: Log adapter
   * Main app writes logs in custom format
   * Adapter reads from shared volume
   * Adapter outputs logs in standardized format

3. AMBASSADOR PATTERN
   A container provides simplified access to external services:

   Example: Database proxy
   * Main app connects to localhost:5432
   * Ambassador container handles connection pooling,
     service discovery, failover to actual database
```

### HOW IS THE SHARED NAMESPACE CREATED?

When Kubernetes creates a pod:

```
STEP 1: Create "pause" container
+-- This container holds the network namespace
+-- It does almost nothing (just pauses/sleeps)
+-- Its only job is to own the namespace
+-- If app container crashes, namespace survives

STEP 2: Create app containers with shared namespace
+-- --net=container:pause_container_id
+-- Each container joins the pause container's namespace
+-- They all share eth0, routing table, etc.

+-------------------------------------------------------------------------+
|                                                                         |
|                             POD                                        |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |       +------------+                                           |   |
|  |       |   PAUSE    | < Holds network namespace                |   |
|  |       | container  |   Extremely lightweight                  |   |
|  |       |            |   Runs: /pause (or equivalent)           |   |
|  |       +------+-----+                                           |   |
|  |              |                                                 |   |
|  |              | Network Namespace                               |   |
|  |              |                                                 |   |
|  |   +----------+------------------------------------------+     |   |
|  |   |          |                                          |     |   |
|  |   |  +-------+-------+    +--------------+             |     |   |
|  |   |  |  App Container |    | Sidecar      |             |     |   |
|  |   |  |  --net=pause   |    | --net=pause  |             |     |   |
|  |   |  +---------------+    +--------------+             |     |   |
|  |   |                                                     |     |   |
|  |   |            Shared namespace (eth0, lo)             |     |   |
|  |   +-----------------------------------------------------+     |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### PRACTICAL IMPLICATIONS

1. PORT CONFLICTS ARE YOUR PROBLEM
If two containers in a pod both want port 80, one will fail.
You must coordinate ports within the pod.

2. LOCALHOST IS FAST
Communication between containers in a pod is just loopback.
No network stack overhead, no NAT, no routing.

3. CONTAINERS SHARE FATE
If the network namespace fails, all containers fail.
This is usually what you want for tightly coupled containers.

## SECTION 1.3: POD-TO-POD COMMUNICATION

### THE FUNDAMENTAL REQUIREMENTS

Kubernetes imposes THREE fundamental networking requirements:

REQUIREMENT 1: EVERY POD GETS A UNIQUE IP
-----------------------------------------
Each pod receives a cluster-unique IP address.
There are no NAT gateways between pods.

WHY: Simplifies application development. Apps can use
their pod IP directly without port mapping complexity.

REQUIREMENT 2: PODS CAN COMMUNICATE WITHOUT NAT
-----------------------------------------------
Any pod can reach any other pod using its IP address.
No Network Address Translation.

WHY: Pods appear as real hosts on a flat network.
Port numbers mean what they say.

REQUIREMENT 3: AGENTS ON A NODE CAN REACH ALL PODS ON THAT NODE
--------------------------------------------------------------
Node-level services (kubelet, kube-proxy) can communicate
with all pods running on their node.

WHY: Control plane components need to manage pods.

### THE FLAT NETWORK MODEL

Kubernetes requires a "flat" network where all pods can reach all pods:

```
+-------------------------------------------------------------------------+
|                                                                         |
|                   KUBERNETES FLAT NETWORK                              |
|                                                                         |
|   NODE 1 (10.0.1.0/24)                NODE 2 (10.0.2.0/24)            |
|   +---------------------+             +---------------------+         |
|   |                     |             |                     |         |
|   |  +-------+ +-------+|             |+-------+ +-------+  |         |
|   |  |Pod A  | |Pod B  ||             ||Pod C  | |Pod D  |  |         |
|   |  |10.0.1.2| |10.0.1.3|             ||10.0.2.2| |10.0.2.3|  |         |
|   |  +---+---+ +---+---+|             |+---+---+ +---+---+  |         |
|   |      |         |    |             |    |         |      |         |
|   |      +----+----+    |             |    +----+----+      |         |
|   |           |         |             |         |           |         |
|   |      Node Network   |             |    Node Network     |         |
|   +-----------+---------+             +---------+-----------+         |
|               |                                 |                      |
|               |       Cluster Network           |                      |
|               +-------------+-------------------+                      |
|                             |                                          |
|  REQUIREMENTS:                                                         |
|  Y Pod A (10.0.1.2) can reach Pod D (10.0.2.3) directly              |
|  Y No NAT - Pod D sees source IP as 10.0.1.2                         |
|  Y All pods have routable IPs within cluster                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY A FLAT NETWORK?

Consider the alternative-NAT-based networking like Docker default:

```sql
WITH NAT (Docker default style):

Pod A (172.17.0.2 on Node1) wants to reach Pod C (172.17.0.2 on Node2)

PROBLEMS:
* Both pods might have the SAME IP (overlapping ranges)!
* Need complex port mappings
* Pod C sees traffic from Node2's IP, not Pod A's IP
* Application code needs awareness of NAT
* Service discovery becomes complicated
* Network policies can't filter by pod IP

WITH FLAT NETWORK (Kubernetes):

Pod A (10.0.1.2) wants to reach Pod C (10.0.2.2)

BENEFITS:
* Every pod has unique IP-no conflicts
* No port mapping needed
* Pod C sees traffic from 10.0.1.2 (Pod A's real IP)
* Applications work as if on traditional network
* Network policies can filter by source pod
* Service discovery is straightforward
```

### HOW IS THE FLAT NETWORK ACHIEVED?

Kubernetes DOES NOT implement networking itself!

Instead, it specifies the requirements and relies on CNI plugins to implement:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KUBERNETES NETWORKING DELEGATION                                      |
|                                                                         |
|       Kubernetes                      CNI Plugin                       |
|  +-----------------+            +---------------------+               |
|  |                 |            |                     |               |
|  | "I need a flat  |            | "I'll implement it  |               |
|  |  network where  | ---------> |  using one of many  |               |
|  |  all pods can   |            |  possible methods"  |               |
|  |  reach all pods"|            |                     |               |
|  |                 |            | * Overlay (VXLAN)   |               |
|  +-----------------+            | * BGP routing       |               |
|                                 | * Host routing      |               |
|                                 | * Cloud provider    |               |
|                                 +---------------------+               |
|                                                                         |
|  CNI PLUGIN EXAMPLES:                                                  |
|  * Flannel      - Simple overlay (VXLAN)                              |
|  * Calico       - BGP routing, network policies                       |
|  * Weave        - Encrypted overlay                                   |
|  * Cilium       - eBPF-based, advanced features                       |
|  * AWS VPC CNI  - Native AWS networking                               |
|  * Azure CNI    - Native Azure networking                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.4: IP ADDRESS MANAGEMENT (IPAM)

### WHERE DO POD IPs COME FROM?

Every pod needs a unique IP address. Here's how it works:

```python
CLUSTER-LEVEL: Pod CIDR
-----------------------
The cluster is configured with a large IP range for all pods.

Example: --pod-network-cidr=10.244.0.0/16

This provides 65,536 IP addresses for pods cluster-wide.

NODE-LEVEL: Per-Node Subnet
---------------------------
Each node gets a subset of the cluster's pod CIDR.

Example:
* Node 1: 10.244.0.0/24 (256 addresses)
* Node 2: 10.244.1.0/24 (256 addresses)
* Node 3: 10.244.2.0/24 (256 addresses)

This is managed by the CNI plugin.

POD-LEVEL: IP Assignment
------------------------
When a pod starts on a node, the CNI plugin assigns an IP
from that node's subnet.

Example: Pod on Node 2 gets 10.244.1.15
```

### IPAM STRATEGIES

Different CNI plugins use different IP allocation strategies:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IPAM STRATEGIES                                                       |
|                                                                         |
|  1. HOST-LOCAL (Most common)                                           |
|  -----------------------------                                         |
|  * Each node manages its own IP pool                                  |
|  * Simple, works offline                                              |
|  * Used by: Flannel, Calico (default)                                |
|                                                                         |
|      Node 1                    Node 2                                  |
|      Pool: 10.244.0.0/24       Pool: 10.244.1.0/24                    |
|      Allocated: .2, .3, .4     Allocated: .2, .3                      |
|      Next: .5                  Next: .4                               |
|                                                                         |
|  2. DHCP                                                               |
|  -------                                                               |
|  * External DHCP server assigns IPs                                   |
|  * Used when integrating with existing infrastructure                 |
|  * Requires DHCP server in each network segment                       |
|                                                                         |
|  3. CLOUD-PROVIDER                                                     |
|  ------------------                                                    |
|  * Cloud provider manages IP allocation                               |
|  * AWS VPC CNI: Pods get IPs from VPC subnet                         |
|  * Azure CNI: Pods get IPs from Azure VNET                           |
|  * Maximum integration with cloud networking                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### THE IP EXHAUSTION PROBLEM

Pod IPs can run out! This is a common production issue.

SCENARIO:
- Node has /24 subnet (254 usable IPs)
- Running 300 pods on node
- Pod scheduling fails: "insufficient IPs"

SYMPTOMS:
- Pods stuck in "ContainerCreating"
- CNI plugin logs show allocation failures
- Events show "failed to allocate IP"

SOLUTIONS:

1. LARGER SUBNETS
Use /23 or /22 per node if you run many pods
Trade-off: Uses more IP space cluster-wide

2. IP RECYCLING
Ensure terminated pod IPs are reclaimed quickly
Check for stale IP allocations

3. CLOUD-NATIVE IPAM
AWS VPC CNI: Attach multiple ENIs to get more IPs
GKE: Use VPC-native clusters with alias IPs

4. POD DENSITY LIMITS
Set maxPods per node to match available IPs

## SECTION 1.5: THE KUBERNETES NETWORKING MODEL

### COMPREHENSIVE OVERVIEW

Let's visualize the complete networking model:

```
+-------------------------------------------------------------------------+
|                                                                         |
|                KUBERNETES NETWORKING MODEL                             |
|                                                                         |
|  EXTERNAL WORLD (Internet)                                             |
|        |                                                                |
|        v                                                                |
|  +-------------------------------------------------------------------+ |
|  |  INGRESS CONTROLLER                                               | |
|  |  Routes HTTP/HTTPS traffic to services                           | |
|  |  * Path-based routing (/api > api-service)                       | |
|  |  * Host-based routing (api.example.com > api-service)           | |
|  |  * TLS termination                                               | |
|  +----------------------------+--------------------------------------+ |
|                               |                                        |
|                               v                                        |
|  +-------------------------------------------------------------------+ |
|  |  SERVICES                                                         | |
|  |  Stable network identity for pods                                | |
|  |                                                                   | |
|  |  +-----------------+  +-----------------+  +-----------------+   | |
|  |  |  ClusterIP      |  |  NodePort       |  |  LoadBalancer   |   | |
|  |  |  10.96.0.1      |  |  10.96.0.2      |  |  10.96.0.3      |   | |
|  |  |  Internal only  |  |  + Node:30080   |  |  + External LB  |   | |
|  |  +--------+--------+  +--------+--------+  +--------+--------+   | |
|  |           |                    |                    |            | |
|  |           +--------------------+--------------------+            | |
|  |                                |                                  | |
|  |                    +-----------+-----------+                     | |
|  |                    |     ENDPOINTS         |                     | |
|  |                    |  (Pod IP:Port list)   |                     | |
|  |                    +-----------------------+                     | |
|  |                                                                   | |
|  +----------------------------+--------------------------------------+ |
|                               |                                        |
|                               v                                        |
|  +-------------------------------------------------------------------+ |
|  |  POD NETWORK (Flat network via CNI)                              | |
|  |                                                                   | |
|  |   NODE 1                              NODE 2                      | |
|  |   +----------------------+            +----------------------+   | |
|  |   | +--------+ +--------+|            |+--------+ +--------+ |   | |
|  |   | | Pod A  | | Pod B  ||            || Pod C  | | Pod D  | |   | |
|  |   | |10.244  | |10.244  ||<---------->||10.244  | |10.244  | |   | |
|  |   | |.0.2    | |.0.3    ||  Direct    ||.1.2    | |.1.3    | |   | |
|  |   | +--------+ +--------+|  pod-to-   |+--------+ +--------+ |   | |
|  |   |                      |  pod       |                      |   | |
|  |   +----------------------+            +----------------------+   | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

### IP ADDRESS RANGES IN A CLUSTER

A typical Kubernetes cluster has THREE distinct IP ranges:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THREE IP RANGES IN KUBERNETES                                         |
|                                                                         |
|  1. NODE IP RANGE                                                      |
|  -------------------                                                   |
|  * The actual IPs of your nodes (VMs/physical machines)               |
|  * Example: 192.168.1.0/24                                            |
|  * Comes from your infrastructure (data center, cloud)                |
|  * This is what external clients can reach                            |
|                                                                         |
|  2. POD IP RANGE (--pod-network-cidr)                                 |
|  ------------------------------------                                  |
|  * IPs assigned to pods                                               |
|  * Example: 10.244.0.0/16                                             |
|  * Managed by CNI plugin                                              |
|  * Typically NOT routable outside cluster                             |
|                                                                         |
|  3. SERVICE IP RANGE (--service-cluster-ip-range)                     |
|  -----------------------------------------------                       |
|  * Virtual IPs for services                                           |
|  * Example: 10.96.0.0/12                                              |
|  * Never assigned to actual interfaces                                |
|  * Implemented via iptables/IPVS rules                                |
|                                                                         |
|  THESE RANGES MUST NOT OVERLAP!                                       |
|                                                                         |
|  Node IPs:    192.168.1.0/24    Y                                     |
|  Pod IPs:     10.244.0.0/16     Y (no overlap)                        |
|  Service IPs: 10.96.0.0/12      Y (no overlap)                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.6: NETWORK NAMESPACES IN KUBERNETES

### HOW PODS GET THEIR NETWORK

Every pod has its own Linux network namespace. Here's the process:

```
POD CREATION NETWORK SETUP:

1. kubelet receives instruction to create pod
   |
   v
2. Container runtime creates "pause" container
   This container establishes the network namespace
   |
   v
3. kubelet calls CNI plugin (via CNI binary)
   "Please set up networking for namespace X"
   |
   v
4. CNI plugin:
   a) Creates veth pair
   b) Moves one end into pod's namespace (becomes eth0)
   c) Attaches other end to node's network
   d) Assigns IP address to eth0
   e) Sets up routes
   f) Returns IP address to kubelet
   |
   v
5. kubelet starts app containers in same namespace
   |
   v
6. Pod is now networked and ready
```

### EXAMINING POD NETWORK NAMESPACE

You can inspect a pod's network namespace:

```bash
# Get the pod's container ID
kubectl get pod my-pod -o jsonpath='{.status.containerStatuses[0].containerID}'
# Returns: docker://abc123...

# Find the process ID
docker inspect abc123 --format '{{.State.Pid}}'
# Returns: 12345

# Enter the namespace and inspect
nsenter -t 12345 -n ip addr
# Shows:
# 1: lo: <LOOPBACK,UP,LOWER_UP>
#     inet 127.0.0.1/8
# 3: eth0@if123: <BROADCAST,MULTICAST,UP,LOWER_UP>
#     inet 10.244.0.15/24

nsenter -t 12345 -n ip route
# Shows:
# default via 10.244.0.1 dev eth0
# 10.244.0.0/24 dev eth0 proto kernel scope link src 10.244.0.15
```

## SECTION 1.7: DNS IN KUBERNETES

### WHY DNS MATTERS

Pods are ephemeral-they get new IPs when they restart. You can't hardcode IPs.
DNS provides stable names that resolve to current pod IPs.

### COREDNS: KUBERNETES' DNS SERVER

Every Kubernetes cluster runs CoreDNS, which provides:

- Service discovery (service names > IPs)
- Pod DNS records
- External DNS forwarding

CoreDNS runs as a Deployment in kube-system namespace:

```bash
kubectl get pods -n kube-system -l k8s-app=kube-dns
# NAME                       READY   STATUS    RESTARTS   AGE
# coredns-5644d7b6d9-abcde   1/1     Running   0          1d
# coredns-5644d7b6d9-fghij   1/1     Running   0          1d
```

### DNS CONFIGURATION IN PODS

Every pod gets DNS automatically configured:

```
# Inside a pod:
cat /etc/resolv.conf

nameserver 10.96.0.10          < CoreDNS service IP
search default.svc.cluster.local svc.cluster.local cluster.local
options ndots:5

WHAT THIS MEANS:

nameserver 10.96.0.10
+-- All DNS queries go to CoreDNS

search default.svc.cluster.local svc.cluster.local cluster.local
+-- Search domains for short names
    "mysql" becomes "mysql.default.svc.cluster.local"

options ndots:5
+-- Names with fewer than 5 dots get search domain appended
    This is why "mysql" works instead of full FQDN
```

### SERVICE DNS NAMES

Services get predictable DNS names:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICE DNS NAME FORMAT                                               |
|                                                                         |
|  Full name: <service>.<namespace>.svc.<cluster-domain>                |
|                                                                         |
|  Example:   mysql.database.svc.cluster.local                          |
|             +--+--+ +---+---+ +++ +-----+-----+                        |
|                |       |      |        |                               |
|                |       |      |        +-- Cluster domain (default)   |
|                |       |      +-- Service indicator                   |
|                |       +-- Namespace name                             |
|                +-- Service name                                        |
|                                                                         |
|  SHORT NAMES (within same namespace):                                  |
|  * mysql                                                               |
|  * mysql.database                                                      |
|  * mysql.database.svc                                                  |
|                                                                         |
|  All resolve to the same service!                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HEADLESS SERVICES: DIRECT POD ACCESS

Regular services return the service's virtual IP. Sometimes you need individual
pod IPs (for databases, stateful apps).

Headless services (clusterIP: None) return pod IPs directly:

```bash
# Headless service definition
apiVersion: v1
kind: Service
metadata:
  name: mysql
spec:
  clusterIP: None  # < This makes it headless
  selector:
    app: mysql
  ports:
    - port: 3306

# DNS query result for headless service:
dig mysql.default.svc.cluster.local

# Returns MULTIPLE A records (one per pod):
# mysql.default.svc.cluster.local. IN A 10.244.0.5
# mysql.default.svc.cluster.local. IN A 10.244.1.3
# mysql.default.svc.cluster.local. IN A 10.244.2.7

# Individual pods get DNS names too:
# mysql-0.mysql.default.svc.cluster.local > 10.244.0.5
# mysql-1.mysql.default.svc.cluster.local > 10.244.1.3
# mysql-2.mysql.default.svc.cluster.local > 10.244.2.7
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KUBERNETES NETWORKING FUNDAMENTALS                                    |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  THE FOUR NETWORKING PROBLEMS                                    | |
|  |  1. Container-to-Container: Shared namespace (localhost)         | |
|  |  2. Pod-to-Pod: Flat network via CNI                            | |
|  |  3. Pod-to-Service: Virtual IPs via kube-proxy                  | |
|  |  4. External-to-Service: Ingress/LoadBalancer/NodePort          | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  THE FLAT NETWORK MODEL                                          | |
|  |  * Every pod gets a unique, routable IP                         | |
|  |  * All pods can reach all pods without NAT                      | |
|  |  * Implemented by CNI plugins, not Kubernetes itself            | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  THREE IP RANGES                                                 | |
|  |  * Node IPs: Physical/VM IPs (your infrastructure)              | |
|  |  * Pod IPs: Assigned by CNI (--pod-network-cidr)               | |
|  |  * Service IPs: Virtual IPs (--service-cluster-ip-range)       | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  DNS                                                              | |
|  |  * CoreDNS provides service discovery                           | |
|  |  * Services: <svc>.<ns>.svc.cluster.local                       | |
|  |  * Headless services return individual pod IPs                  | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  KEY INSIGHT:                                                          |
|  Kubernetes specifies WHAT networking should do.                       |
|  CNI plugins implement HOW it actually works.                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHAT'S NEXT?

Chapter 2 will deep-dive into CNI plugins-how they implement the flat network
and the trade-offs between different approaches (overlay vs routing vs cloud).

## END OF CHAPTER 1

