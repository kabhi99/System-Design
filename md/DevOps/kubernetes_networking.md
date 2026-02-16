# KUBERNETES NETWORKING — FROM ZERO TO HERO
*Complete Guide: Basics to Advanced*

### Table of Contents

Part 1: Kubernetes Networking Model
1.1 The Kubernetes Network Model
1.2 Four Types of Communication
1.3 Key Requirements

Part 2: Pod Networking
2.1 Pod Network Namespace
2.2 Containers in Same Pod
2.3 Pod-to-Pod Communication (Same Node)
2.4 Pod-to-Pod Communication (Different Nodes)

Part 3: Container Network Interface (CNI)
3.1 What is CNI?
3.2 Popular CNI Plugins
3.3 CNI Plugin Comparison
3.4 How CNI Works

Part 4: Services — The Heart of Kubernetes Networking
4.1 Why Services?
4.2 ClusterIP Service
4.3 NodePort Service
4.4 LoadBalancer Service
4.5 ExternalName Service
4.6 Headless Services

Part 5: Service Discovery
5.1 DNS in Kubernetes
5.2 CoreDNS
5.3 DNS Record Types
5.4 Service Discovery Patterns

Part 6: kube-proxy and Service Implementation
6.1 What is kube-proxy?
6.2 iptables Mode
6.3 IPVS Mode
6.4 Userspace Mode (Legacy)

Part 7: Ingress
7.1 What is Ingress?
7.2 Ingress Controllers
7.3 Ingress Rules and Paths
7.4 TLS/SSL Termination
7.5 Ingress vs LoadBalancer vs NodePort

Part 8: Network Policies
8.1 What are Network Policies?
8.2 Default Behavior
8.3 Ingress Policies
8.4 Egress Policies
8.5 Policy Examples

Part 9: Advanced Topics
9.1 Service Mesh (Istio, Linkerd)
9.2 Multi-Cluster Networking
9.3 IPv4/IPv6 Dual Stack
9.4 Network Troubleshooting

Part 10: CNI Deep Dives
10.1 Calico
10.2 Flannel
10.3 Cilium
10.4 AWS VPC CNI

## PART 1: KUBERNETES NETWORKING MODEL

### 1.1 THE KUBERNETES NETWORK MODEL

```
+-------------------------------------------------------------------------+
|                    KUBERNETES NETWORKING PHILOSOPHY                     |
|                                                                         |
|  Kubernetes networking is designed to be FLAT and SIMPLE.              |
|  Every Pod gets its own IP address.                                    |
|  No NAT between Pods.                                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  FUNDAMENTAL REQUIREMENTS:                                              |
|                                                                         |
|  1. All Pods can communicate with all other Pods without NAT          |
|                                                                         |
|  2. All Nodes can communicate with all Pods without NAT               |
|                                                                         |
|  3. The IP a Pod sees itself as is the same IP others see it as       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHY FLAT NETWORK?                                                      |
|                                                                         |
|  In Docker (default):                                                  |
|    Container A (172.17.0.2) > NAT > Host IP > NAT > Container B       |
|    Complex! Port mappings, NAT traversal issues.                       |
|                                                                         |
|  In Kubernetes:                                                         |
|    Pod A (10.244.1.5) > directly > Pod B (10.244.2.10)                |
|    Simple! Just like VMs on same network.                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 1.2 FOUR TYPES OF COMMUNICATION

```
+-------------------------------------------------------------------------+
|                    KUBERNETES COMMUNICATION TYPES                       |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  1. CONTAINER-TO-CONTAINER (Same Pod)                          |   |
|  |     ---------------------------------                          |   |
|  |     * Share same network namespace                             |   |
|  |     * Communicate via localhost                                |   |
|  |     * Share same IP address                                    |   |
|  |                                                                 |   |
|  |     +-----------------------------+                            |   |
|  |     |          POD                |                            |   |
|  |     |  +-----+    +-----+        |                            |   |
|  |     |  |App A|<-->|App B|        |  localhost:8080            |   |
|  |     |  |:8080|    |:9090|        |                            |   |
|  |     |  +-----+    +-----+        |                            |   |
|  |     |        Same Network NS     |                            |   |
|  |     +-----------------------------+                            |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  2. POD-TO-POD (Same or Different Node)                        |   |
|  |     -------------------------------------                      |   |
|  |     * Direct IP communication                                  |   |
|  |     * No NAT required                                          |   |
|  |     * Handled by CNI plugin                                    |   |
|  |                                                                 |   |
|  |     +------------+          +------------+                     |   |
|  |     |   Pod A    |          |   Pod B    |                     |   |
|  |     | 10.244.1.5 |--------> | 10.244.2.3 |                     |   |
|  |     +------------+          +------------+                     |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  3. POD-TO-SERVICE                                              |   |
|  |     -----------------                                           |   |
|  |     * Service provides stable IP and DNS name                  |   |
|  |     * Load balances across Pod replicas                        |   |
|  |     * Implemented by kube-proxy (iptables/IPVS)                |   |
|  |                                                                 |   |
|  |     +------------+          +--------------------+             |   |
|  |     |   Pod A    |          |      Service       |             |   |
|  |     |            |--------> |   my-service       | --> Pods    |   |
|  |     +------------+          |   10.96.10.5       |             |   |
|  |                             +--------------------+             |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |  4. EXTERNAL-TO-SERVICE                                         |   |
|  |     ---------------------                                       |   |
|  |     * External traffic reaching cluster                        |   |
|  |     * Ingress, LoadBalancer, NodePort                          |   |
|  |                                                                 |   |
|  |     +------------+          +--------------------+             |   |
|  |     |  Internet  |          |      Ingress       |             |   |
|  |     |   Client   |--------> |   my-app.com       | --> Pods    |   |
|  |     +------------+          +--------------------+             |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 2: POD NETWORKING

### 2.1 POD NETWORK NAMESPACE

```
+-------------------------------------------------------------------------+
|                    POD = SHARED NETWORK NAMESPACE                       |
|                                                                         |
|  All containers in a Pod share the same network namespace.             |
|  This is achieved using a "pause" container.                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  +------------------------------------------------------------------+  |
|  |                           POD                                     |  |
|  |                                                                   |  |
|  |  +-----------------------------------------------------------+   |  |
|  |  |              Shared Network Namespace                      |   |  |
|  |  |                                                            |   |  |
|  |  |   +---------+  +---------+  +---------+                   |   |  |
|  |  |   | pause   |  | App     |  | Sidecar |                   |   |  |
|  |  |   |container|  |container|  |container|                   |   |  |
|  |  |   |         |  |  :8080  |  |  :9090  |                   |   |  |
|  |  |   +---------+  +---------+  +---------+                   |   |  |
|  |  |        |                                                   |   |  |
|  |  |   Holds the    App uses      Sidecar can                  |   |  |
|  |  |   network NS   localhost     reach App                    |   |  |
|  |  |                :8080         on localhost:8080            |   |  |
|  |  |                                                            |   |  |
|  |  |                    +---------+                             |   |  |
|  |  |                    |  eth0   |  Pod IP: 10.244.1.5        |   |  |
|  |  |                    +----+----+                             |   |  |
|  |  |                         |                                  |   |  |
|  |  +-------------------------+----------------------------------+   |  |
|  |                            |                                      |  |
|  +----------------------------+--------------------------------------+  |
|                               |                                         |
|                          veth pair                                      |
|                               |                                         |
|                        +------+------+                                  |
|                        | Node Network|                                  |
|                        +-------------+                                  |
|                                                                         |
|  THE "PAUSE" CONTAINER:                                                |
|  * First container created in the Pod                                  |
|  * Creates and holds the network namespace                             |
|  * Does nothing (just sleeps)                                          |
|  * Other containers join its network namespace                         |
|  * If pause dies, Pod's network is lost                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.2 POD-TO-POD COMMUNICATION (SAME NODE)

```
+-------------------------------------------------------------------------+
|                    SAME NODE POD COMMUNICATION                          |
|                                                                         |
|  +------------------------------------------------------------------+  |
|  |                         NODE 1                                    |  |
|  |                                                                   |  |
|  |   +-----------------+          +-----------------+               |  |
|  |   |      Pod A      |          |      Pod B      |               |  |
|  |   |   10.244.1.5    |          |   10.244.1.6    |               |  |
|  |   |                 |          |                 |               |  |
|  |   |   +---------+   |          |   +---------+   |               |  |
|  |   |   |  eth0   |   |          |   |  eth0   |   |               |  |
|  |   |   +----+----+   |          |   +----+----+   |               |  |
|  |   +--------+--------+          +--------+--------+               |  |
|  |            | veth                       | veth                    |  |
|  |            |                            |                         |  |
|  |   +--------+----------------------------+--------+               |  |
|  |   |                  cbr0 (bridge)               |               |  |
|  |   |                  10.244.1.1                  |               |  |
|  |   +----------------------------------------------+               |  |
|  |                                                                   |  |
|  |   Pod A > Pod B:                                                  |  |
|  |   1. Packet leaves Pod A's eth0                                  |  |
|  |   2. Goes through veth to bridge                                 |  |
|  |   3. Bridge sees dest 10.244.1.6 is local                       |  |
|  |   4. Forwards to Pod B's veth                                    |  |
|  |   5. Arrives at Pod B's eth0                                     |  |
|  |                                                                   |  |
|  |   Just like two VMs on same network switch!                      |  |
|  |                                                                   |  |
|  +------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.3 POD-TO-POD COMMUNICATION (DIFFERENT NODES)

```
+-------------------------------------------------------------------------+
|                    CROSS-NODE POD COMMUNICATION                         |
|                                                                         |
|  +---------------------------+      +---------------------------+      |
|  |         NODE 1            |      |         NODE 2            |      |
|  |    (192.168.1.10)         |      |    (192.168.1.11)         |      |
|  |                           |      |                           |      |
|  |   +-----------------+     |      |     +-----------------+   |      |
|  |   |      Pod A      |     |      |     |      Pod B      |   |      |
|  |   |   10.244.1.5    |     |      |     |   10.244.2.10   |   |      |
|  |   +--------+--------+     |      |     +--------+--------+   |      |
|  |            |              |      |              |            |      |
|  |   +--------+--------+     |      |     +--------+--------+   |      |
|  |   |   cbr0 bridge   |     |      |     |   cbr0 bridge   |   |      |
|  |   |   10.244.1.1    |     |      |     |   10.244.2.1    |   |      |
|  |   +--------+--------+     |      |     +--------+--------+   |      |
|  |            |              |      |              |            |      |
|  |            |              |      |              |            |      |
|  |       +----+----+         |      |         +----+----+       |      |
|  |       |  eth0   |         |      |         |  eth0   |       |      |
|  |       +----+----+         |      |         +----+----+       |      |
|  |            |              |      |              |            |      |
|  +------------+--------------+      +--------------+------------+      |
|               |                                    |                    |
|               +----------+-------------------------+                    |
|                          |                                              |
|                Physical Network / Cloud VPC                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ROUTING REQUIRED:                                                      |
|  Node 1 needs to know: "10.244.2.0/24 is via 192.168.1.11"            |
|  Node 2 needs to know: "10.244.1.0/24 is via 192.168.1.10"            |
|                                                                         |
|  This is what CNI plugins handle!                                      |
|                                                                         |
|  OPTIONS:                                                               |
|  1. L3 Routing (BGP) - Calico                                         |
|  2. Overlay Network (VXLAN) - Flannel, Calico                         |
|  3. Cloud Provider Routes - AWS VPC CNI, GKE                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 3: CONTAINER NETWORK INTERFACE (CNI)

### 3.1 WHAT IS CNI?

```
+-------------------------------------------------------------------------+
|                    CONTAINER NETWORK INTERFACE (CNI)                    |
|                                                                         |
|  CNI is a SPECIFICATION for configuring network interfaces in          |
|  Linux containers.                                                     |
|                                                                         |
|  Kubernetes doesn't implement networking itself.                       |
|  It delegates to CNI plugins.                                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HOW CNI WORKS:                                                         |
|                                                                         |
|  +----------------+                                                    |
|  |    kubelet     |                                                    |
|  |                |                                                    |
|  |  "Create Pod"  |                                                    |
|  +-------+--------+                                                    |
|          |                                                             |
|          | 1. Create pause container                                  |
|          | 2. Call CNI plugin                                         |
|          v                                                             |
|  +----------------+                                                    |
|  |   CNI Plugin   |                                                    |
|  |   (Calico,     |                                                    |
|  |    Flannel)    |                                                    |
|  +-------+--------+                                                    |
|          |                                                             |
|          | 3. Create veth pair                                        |
|          | 4. Attach to Pod namespace                                 |
|          | 5. Assign IP address                                       |
|          | 6. Set up routes                                           |
|          v                                                             |
|  +----------------+                                                    |
|  |   Pod Ready    |                                                    |
|  |   with IP      |                                                    |
|  +----------------+                                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CNI PLUGIN OPERATIONS:                                                 |
|  * ADD: Configure network for new container                           |
|  * DEL: Clean up network when container deleted                       |
|  * CHECK: Verify configuration                                        |
|  * VERSION: Report supported versions                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.2 POPULAR CNI PLUGINS

```
+-------------------------------------------------------------------------+
|                    CNI PLUGIN COMPARISON                                |
|                                                                         |
|  +---------------+------------------------------------------------+    |
|  | Plugin        | Description                                    |    |
|  +---------------+------------------------------------------------+    |
|  | Calico        | L3 networking with BGP. Network policies.     |    |
|  |               | Most popular. Production-ready.               |    |
|  +---------------+------------------------------------------------+    |
|  | Flannel       | Simple overlay (VXLAN). Easy setup.           |    |
|  |               | No network policies. Good for learning.       |    |
|  +---------------+------------------------------------------------+    |
|  | Cilium        | eBPF-based. Advanced security & observability.|    |
|  |               | L7 network policies. High performance.        |    |
|  +---------------+------------------------------------------------+    |
|  | Weave Net     | Encrypted overlay. Easy multi-cloud.          |    |
|  |               | Built-in network policies.                    |    |
|  +---------------+------------------------------------------------+    |
|  | AWS VPC CNI   | Native AWS VPC networking.                    |    |
|  |               | Pods get VPC IPs. Best for EKS.              |    |
|  +---------------+------------------------------------------------+    |
|  | Azure CNI     | Native Azure VNet. Pods get VNet IPs.        |    |
|  |               | Best for AKS.                                 |    |
|  +---------------+------------------------------------------------+    |
|  | GKE (native)  | Google's built-in. Dataplane V2 uses Cilium. |    |
|  +---------------+------------------------------------------------+    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CHOOSING A CNI:                                                        |
|                                                                         |
|  * Learning/Dev: Flannel (simple)                                      |
|  * Production (on-prem): Calico or Cilium                             |
|  * AWS EKS: AWS VPC CNI                                                |
|  * Azure AKS: Azure CNI                                                |
|  * Need L7 policies: Cilium                                            |
|  * Need encryption: Weave or Cilium                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.3 CNI: OVERLAY VS ROUTED NETWORKING

```
+-------------------------------------------------------------------------+
|                    OVERLAY NETWORKING (VXLAN)                           |
|                                                                         |
|  Encapsulates Pod traffic inside Node-to-Node packets.                 |
|                                                                         |
|  +---------------------------+      +---------------------------+      |
|  |         NODE 1            |      |         NODE 2            |      |
|  |                           |      |                           |      |
|  |   Pod A > Pod B packet:   |      |                           |      |
|  |   Src: 10.244.1.5         |      |                           |      |
|  |   Dst: 10.244.2.10        |      |                           |      |
|  |           |               |      |                           |      |
|  |           v               |      |                           |      |
|  |   +---------------+       |      |                           |      |
|  |   | VXLAN Encap   |       |      |                           |      |
|  |   |               |       |      |       +---------------+   |      |
|  |   | Outer:        |-------+------+------>| VXLAN Decap   |   |      |
|  |   | Src: 192.168.1.10     |      |       |               |   |      |
|  |   | Dst: 192.168.1.11     |      |       | Extract inner |   |      |
|  |   |               |       |      |       | packet        |   |      |
|  |   | Inner:        |       |      |       +-------+-------+   |      |
|  |   | Src: 10.244.1.5       |      |               |           |      |
|  |   | Dst: 10.244.2.10      |      |               v           |      |
|  |   +---------------+       |      |           Pod B           |      |
|  |                           |      |                           |      |
|  +---------------------------+      +---------------------------+      |
|                                                                         |
|  PROS:                                                                  |
|  * Works anywhere (no special network setup)                           |
|  * Easy to set up                                                      |
|                                                                         |
|  CONS:                                                                  |
|  * Encapsulation overhead (~50 bytes per packet)                      |
|  * Slightly higher latency                                            |
|  * MTU issues (need to account for encap header)                      |
|                                                                         |
|  USED BY: Flannel (VXLAN mode), Calico (VXLAN mode), Weave            |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    ROUTED NETWORKING (BGP/L3)                           |
|                                                                         |
|  No encapsulation. Pod IPs are directly routable.                      |
|                                                                         |
|  +---------------------------+      +---------------------------+      |
|  |         NODE 1            |      |         NODE 2            |      |
|  |     10.244.1.0/24         |      |     10.244.2.0/24         |      |
|  |                           |      |                           |      |
|  |   Pod A > Pod B packet:   |      |                           |      |
|  |   Src: 10.244.1.5         |      |                           |      |
|  |   Dst: 10.244.2.10        |      |                           |      |
|  |           |               |      |                           |      |
|  |           v               |      |                           |      |
|  |   Routing table:          |      |                           |      |
|  |   10.244.2.0/24 via       |      |                           |      |
|  |   192.168.1.11    --------+------+------>  Pod B             |      |
|  |                           |      |                           |      |
|  +---------------------------+      +---------------------------+      |
|                                                                         |
|  HOW ROUTES ARE DISTRIBUTED:                                           |
|  * BGP: Nodes peer with each other or with router                     |
|  * Cloud routes: AWS/GCP/Azure route tables                           |
|                                                                         |
|  PROS:                                                                  |
|  * No encapsulation overhead                                          |
|  * Better performance                                                  |
|  * Easier debugging (standard IP routing)                             |
|                                                                         |
|  CONS:                                                                  |
|  * Requires BGP or cloud-specific integration                         |
|  * May need router configuration                                       |
|                                                                         |
|  USED BY: Calico (BGP mode), AWS VPC CNI, GKE                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 4: SERVICES — THE HEART OF KUBERNETES NETWORKING

### 4.1 WHY SERVICES?

```
+-------------------------------------------------------------------------+
|                    THE PROBLEM WITH POD IPS                             |
|                                                                         |
|  Pods are EPHEMERAL. They come and go.                                 |
|  Pod IPs change when Pods restart or reschedule.                       |
|                                                                         |
|  PROBLEM:                                                               |
|  ---------                                                              |
|  How does Frontend find Backend if Backend's IP keeps changing?        |
|                                                                         |
|  +-------------+          +-------------+                              |
|  |  Frontend   |----?---->|  Backend    |                              |
|  |             |          | 10.244.1.5  |                              |
|  +-------------+          +-------------+                              |
|                                  |                                      |
|                           Pod crashes!                                  |
|                           Rescheduled!                                  |
|                                  |                                      |
|                                  v                                      |
|                           +-------------+                              |
|                           |  Backend    |                              |
|                           | 10.244.2.8  |  < NEW IP!                   |
|                           +-------------+                              |
|                                                                         |
|  SOLUTION: SERVICES                                                     |
|  ------------------                                                     |
|  Service provides:                                                      |
|  * Stable IP (doesn't change)                                         |
|  * Stable DNS name                                                     |
|  * Load balancing across Pods                                         |
|                                                                         |
|  +-------------+          +-------------+          +-------------+    |
|  |  Frontend   |-------->|   Service   |-------->|  Backend    |    |
|  |             |          | backend-svc |          | (any IP)    |    |
|  |             |          | 10.96.10.5  |          |             |    |
|  +-------------+          +-------------+          +-------------+    |
|                                                                         |
|  Frontend connects to "backend-svc" or 10.96.10.5                     |
|  Service routes to healthy Backend Pods                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 4.2 CLUSTERIP SERVICE (Default)

```
+-------------------------------------------------------------------------+
|                    CLUSTERIP SERVICE                                    |
|                                                                         |
|  * Internal-only IP address                                            |
|  * Only accessible from INSIDE the cluster                             |
|  * Default Service type                                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                    KUBERNETES CLUSTER                           |   |
|  |                                                                  |   |
|  |  +-------------+                                                |   |
|  |  |  Client Pod |                                                |   |
|  |  +------+------+                                                |   |
|  |         |                                                       |   |
|  |         | request to 10.96.10.5:80                             |   |
|  |         v                                                       |   |
|  |  +----------------------------------+                          |   |
|  |  |     Service: my-service          |                          |   |
|  |  |     Type: ClusterIP              |                          |   |
|  |  |     ClusterIP: 10.96.10.5        |                          |   |
|  |  |     Port: 80                     |                          |   |
|  |  |     Selector: app=backend        |                          |   |
|  |  +--------------+-------------------+                          |   |
|  |                 |                                               |   |
|  |       +---------+---------+                                    |   |
|  |       v         v         v                                    |   |
|  |  +--------++--------++--------+                               |   |
|  |  | Pod 1  || Pod 2  || Pod 3  |                               |   |
|  |  | :8080  || :8080  || :8080  |                               |   |
|  |  |app=back||app=back||app=back|                               |   |
|  |  +--------++--------++--------+                               |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  NOT accessible from outside cluster!                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

**YAML EXAMPLE:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  type: ClusterIP        # Default, can be omitted
  selector:
    app: backend         # Pods with this label
  ports:
    - port: 80           # Service port
      targetPort: 8080   # Pod port
```

### 4.3 NODEPORT SERVICE

```
+-------------------------------------------------------------------------+
|                    NODEPORT SERVICE                                     |
|                                                                         |
|  * Opens a port (30000-32767) on EVERY node                           |
|  * External traffic can reach service via NodeIP:NodePort             |
|  * Also creates ClusterIP automatically                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|              External Client                                           |
|                    |                                                   |
|                    | http://192.168.1.10:30080                        |
|                    | (or any node IP)                                  |
|                    v                                                   |
|  +-----------------------------------------------------------------+   |
|  |                    KUBERNETES CLUSTER                           |   |
|  |                                                                  |   |
|  |  +-----------------+  +-----------------+  +-----------------+  |   |
|  |  |     Node 1      |  |     Node 2      |  |     Node 3      |  |   |
|  |  | 192.168.1.10    |  | 192.168.1.11    |  | 192.168.1.12    |  |   |
|  |  |                 |  |                 |  |                 |  |   |
|  |  |    :30080  -----+--+-----:30080 -----+--+-----:30080      |  |   |
|  |  |       |         |  |       |         |  |       |         |  |   |
|  |  +-------+---------+  +-------+---------+  +-------+---------+  |   |
|  |          |                    |                    |            |   |
|  |          +--------------------+--------------------+            |   |
|  |                               |                                  |   |
|  |                               v                                  |   |
|  |                 +--------------------------+                    |   |
|  |                 |   Service: my-service    |                    |   |
|  |                 |   Type: NodePort         |                    |   |
|  |                 |   ClusterIP: 10.96.10.5  |                    |   |
|  |                 |   NodePort: 30080        |                    |   |
|  |                 +------------+-------------+                    |   |
|  |                              |                                   |   |
|  |                    +---------+---------+                        |   |
|  |                    v         v         v                        |   |
|  |               +--------++--------++--------+                   |   |
|  |               | Pod 1  || Pod 2  || Pod 3  |                   |   |
|  |               +--------++--------++--------+                   |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  NOTE: Traffic can enter any node, even if Pod isn't on that node     |
|        kube-proxy routes to correct Pod                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

**YAML EXAMPLE:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  type: NodePort
  selector:
    app: backend
  ports:
    - port: 80           # ClusterIP port
      targetPort: 8080   # Pod port
      nodePort: 30080    # External port (optional, auto-assigned if omitted)
```

### 4.4 LOADBALANCER SERVICE

```
+-------------------------------------------------------------------------+
|                    LOADBALANCER SERVICE                                 |
|                                                                         |
|  * Provisions external load balancer (cloud provider)                  |
|  * Gets external IP from cloud (AWS ELB, GCP LB, Azure LB)            |
|  * Also creates NodePort and ClusterIP                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|              External Client                                           |
|                    |                                                   |
|                    | http://52.23.181.42                              |
|                    v                                                   |
|  +--------------------------------------------+                       |
|  |        Cloud Load Balancer                  |                       |
|  |        (AWS ELB / GCP LB)                   |                       |
|  |        External IP: 52.23.181.42            |                       |
|  +-------------------+------------------------+                       |
|                      |                                                 |
|                      v                                                 |
|  +-----------------------------------------------------------------+   |
|  |                    KUBERNETES CLUSTER                           |   |
|  |                                                                  |   |
|  |  +-------------+  +-------------+  +-------------+              |   |
|  |  |   Node 1    |  |   Node 2    |  |   Node 3    |              |   |
|  |  |   :30080    |  |   :30080    |  |   :30080    |              |   |
|  |  +------+------+  +------+------+  +------+------+              |   |
|  |         |                |                |                      |   |
|  |         +----------------+----------------+                      |   |
|  |                          |                                       |   |
|  |                          v                                       |   |
|  |            +--------------------------+                         |   |
|  |            |   Service: my-service    |                         |   |
|  |            |   Type: LoadBalancer     |                         |   |
|  |            |   External: 52.23.181.42 |                         |   |
|  |            +------------+-------------+                         |   |
|  |                         |                                        |   |
|  |                         v                                        |   |
|  |                    Backend Pods                                  |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  NOTE: Each LoadBalancer Service gets its own external IP              |
|        Can be expensive with many services!                            |
|        Use Ingress for HTTP(S) traffic instead.                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

**YAML EXAMPLE:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  type: LoadBalancer
  selector:
    app: backend
  ports:
    - port: 80
      targetPort: 8080
```

### 4.5 HEADLESS SERVICE

```
+-------------------------------------------------------------------------+
|                    HEADLESS SERVICE                                     |
|                                                                         |
|  * No ClusterIP (clusterIP: None)                                      |
|  * DNS returns Pod IPs directly                                        |
|  * Used for stateful applications (databases, etc.)                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REGULAR SERVICE:                                                       |
|                                                                         |
|  DNS query: my-service.default.svc.cluster.local                       |
|  Returns:   10.96.10.5 (Service ClusterIP)                            |
|                                                                         |
|  HEADLESS SERVICE:                                                      |
|                                                                         |
|  DNS query: my-service.default.svc.cluster.local                       |
|  Returns:   10.244.1.5, 10.244.2.3, 10.244.3.8 (Pod IPs directly!)    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USE CASES:                                                             |
|                                                                         |
|  * StatefulSets (each Pod needs to be addressable)                    |
|    - mysql-0.mysql.default.svc.cluster.local                          |
|    - mysql-1.mysql.default.svc.cluster.local                          |
|                                                                         |
|  * Client-side load balancing                                         |
|    - Client gets all Pod IPs, decides which to use                    |
|                                                                         |
|  * Service discovery without load balancing                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

**YAML EXAMPLE:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql
spec:
  clusterIP: None        # This makes it headless
  selector:
    app: mysql
  ports:
    - port: 3306
```

## PART 5: SERVICE DISCOVERY & DNS

### 5.1 DNS IN KUBERNETES

```
+-------------------------------------------------------------------------+
|                    KUBERNETES DNS                                       |
|                                                                         |
|  Kubernetes runs a DNS server (CoreDNS) in the cluster.                |
|  Every Service and Pod gets a DNS name.                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SERVICE DNS NAMES:                                                     |
|                                                                         |
|  Full name:                                                             |
|  <service-name>.<namespace>.svc.cluster.local                          |
|                                                                         |
|  Examples:                                                              |
|  * my-service.default.svc.cluster.local                               |
|  * backend.production.svc.cluster.local                               |
|                                                                         |
|  Short names (from same namespace):                                    |
|  * my-service (resolves to my-service.default.svc.cluster.local)      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  POD DNS NAMES (with hostname/subdomain):                              |
|                                                                         |
|  <hostname>.<subdomain>.<namespace>.svc.cluster.local                  |
|                                                                         |
|  StatefulSet Pods:                                                      |
|  <pod-name>.<service-name>.<namespace>.svc.cluster.local              |
|  * mysql-0.mysql.default.svc.cluster.local                            |
|  * mysql-1.mysql.default.svc.cluster.local                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DNS RESOLUTION FLOW:                                                   |
|                                                                         |
|  +---------+                     +---------+                           |
|  |   Pod   |--DNS query-------->| CoreDNS |                           |
|  |         |  "my-service"       | (kube-  |                           |
|  |         |                     |  dns)   |                           |
|  |         |<--10.96.10.5--------|         |                           |
|  +---------+                     +---------+                           |
|                                                                         |
|  Pod's /etc/resolv.conf:                                               |
|  nameserver 10.96.0.10  (CoreDNS ClusterIP)                           |
|  search default.svc.cluster.local svc.cluster.local cluster.local     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 5.2 DNS RECORD TYPES

```
+-------------------------------------------------------------------------+
|                    DNS RECORDS CREATED BY KUBERNETES                    |
|                                                                         |
|  A RECORD (Service):                                                    |
|  --------------------                                                   |
|  my-service.default.svc.cluster.local > 10.96.10.5                    |
|                                                                         |
|  A RECORD (Headless Service):                                          |
|  ----------------------------                                           |
|  my-service.default.svc.cluster.local > 10.244.1.5, 10.244.2.3       |
|  (Returns all Pod IPs)                                                 |
|                                                                         |
|  A RECORD (StatefulSet Pods):                                          |
|  -----------------------------                                          |
|  mysql-0.mysql.default.svc.cluster.local > 10.244.1.5                 |
|  mysql-1.mysql.default.svc.cluster.local > 10.244.2.3                 |
|                                                                         |
|  SRV RECORD (Named Ports):                                             |
|  --------------------------                                             |
|  _http._tcp.my-service.default.svc.cluster.local                      |
|  > 0 0 80 my-service.default.svc.cluster.local                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 6: KUBE-PROXY AND SERVICE IMPLEMENTATION

### 6.1 WHAT IS KUBE-PROXY?

```
+-------------------------------------------------------------------------+
|                    KUBE-PROXY                                           |
|                                                                         |
|  kube-proxy runs on every node.                                        |
|  It implements Services by programming network rules.                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HOW IT WORKS:                                                          |
|                                                                         |
|  1. Watches Kubernetes API for Services and Endpoints                  |
|  2. When Service created/updated:                                      |
|     - Programs iptables rules (or IPVS)                               |
|     - Rules redirect Service IP > Pod IPs                             |
|                                                                         |
|  +---------------------------------------------------------------+     |
|  |                         NODE                                   |     |
|  |                                                                |     |
|  |   +-------------+                                             |     |
|  |   | kube-proxy  |<-------- Watch API Server                   |     |
|  |   +------+------+                                             |     |
|  |          |                                                    |     |
|  |          | Programs rules                                     |     |
|  |          v                                                    |     |
|  |   +-------------+                                             |     |
|  |   |  iptables   |                                             |     |
|  |   |  (or IPVS)  |                                             |     |
|  |   +-------------+                                             |     |
|  |                                                                |     |
|  |   Traffic to 10.96.10.5 (Service)                            |     |
|  |          |                                                    |     |
|  |          v (iptables DNAT)                                   |     |
|  |   Redirected to 10.244.1.5 (Pod)                             |     |
|  |                                                                |     |
|  +---------------------------------------------------------------+     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.2 IPTABLES MODE

```
+-------------------------------------------------------------------------+
|                    IPTABLES MODE (Default)                              |
|                                                                         |
|  kube-proxy creates iptables rules for each Service.                   |
|                                                                         |
|  EXAMPLE: Service with 3 backend Pods                                  |
|                                                                         |
|  Traffic to 10.96.10.5:80                                              |
|        |                                                               |
|        v                                                               |
|  +-----------------------------------------------------------------+   |
|  |  KUBE-SERVICES chain                                            |   |
|  |                                                                  |   |
|  |  -A KUBE-SERVICES -d 10.96.10.5/32 -p tcp --dport 80           |   |
|  |     -j KUBE-SVC-XXXXX                                           |   |
|  +--------------------------+--------------------------------------+   |
|                             |                                          |
|                             v                                          |
|  +-----------------------------------------------------------------+   |
|  |  KUBE-SVC-XXXXX chain (Load Balancing)                          |   |
|  |                                                                  |   |
|  |  -A KUBE-SVC-XXXXX -m statistic --probability 0.33             |   |
|  |     -j KUBE-SEP-AAAA                                            |   |
|  |  -A KUBE-SVC-XXXXX -m statistic --probability 0.50             |   |
|  |     -j KUBE-SEP-BBBB                                            |   |
|  |  -A KUBE-SVC-XXXXX                                              |   |
|  |     -j KUBE-SEP-CCCC                                            |   |
|  +--------------------------+--------------------------------------+   |
|           |                 |                 |                        |
|           v                 v                 v                        |
|  +--------------+  +--------------+  +--------------+                 |
|  |KUBE-SEP-AAAA |  |KUBE-SEP-BBBB |  |KUBE-SEP-CCCC |                 |
|  |              |  |              |  |              |                 |
|  | DNAT to      |  | DNAT to      |  | DNAT to      |                 |
|  | 10.244.1.5   |  | 10.244.2.3   |  | 10.244.3.8   |                 |
|  +--------------+  +--------------+  +--------------+                 |
|                                                                         |
|  NOTE: With many Services/Pods, iptables rules can get huge            |
|        (linear lookup time)                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.3 IPVS MODE

```
+-------------------------------------------------------------------------+
|                    IPVS MODE (Better for Large Clusters)                |
|                                                                         |
|  IPVS (IP Virtual Server) is a Linux kernel load balancer.            |
|  Uses hash tables instead of linear chain (O(1) vs O(n)).             |
|                                                                         |
|  ADVANTAGES OVER IPTABLES:                                              |
|  * Better performance at scale (1000s of Services)                    |
|  * More load balancing algorithms:                                     |
|    - Round Robin (rr)                                                 |
|    - Least Connections (lc)                                           |
|    - Destination Hashing (dh)                                         |
|    - Source Hashing (sh)                                              |
|    - Shortest Expected Delay (sed)                                    |
|    - Never Queue (nq)                                                 |
|                                                                         |
|  ENABLE IPVS:                                                           |
|  -------------                                                          |
|  # In kube-proxy ConfigMap                                            |
|  mode: ipvs                                                            |
|  ipvs:                                                                  |
|    scheduler: rr                                                       |
|                                                                         |
|  VIEW IPVS RULES:                                                       |
|  ----------------                                                       |
|  ipvsadm -Ln                                                           |
|                                                                         |
|  OUTPUT:                                                                |
|  TCP  10.96.10.5:80 rr                                                |
|    -> 10.244.1.5:8080    Masq    1      0      0                      |
|    -> 10.244.2.3:8080    Masq    1      0      0                      |
|    -> 10.244.3.8:8080    Masq    1      0      0                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 7: INGRESS

### 7.1 WHAT IS INGRESS?

```
+-------------------------------------------------------------------------+
|                    INGRESS                                              |
|                                                                         |
|  Ingress manages external HTTP(S) access to Services.                  |
|  Like a reverse proxy (Nginx) with Kubernetes integration.             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WITHOUT INGRESS (Multiple LoadBalancers):                             |
|                                                                         |
|  app1.com --> LoadBalancer ($) --> Service A                          |
|  app2.com --> LoadBalancer ($) --> Service B                          |
|  app3.com --> LoadBalancer ($) --> Service C                          |
|                                                                         |
|  3 external IPs, 3x the cost!                                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WITH INGRESS (Single Entry Point):                                    |
|                                                                         |
|  app1.com -+                    +--> Service A                         |
|  app2.com -+--> Ingress --------+--> Service B                         |
|  app3.com -+   (1 LB)          +--> Service C                         |
|                                                                         |
|  1 external IP, routes based on hostname/path!                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  INGRESS FEATURES:                                                      |
|  * Host-based routing (app1.com > Service A)                          |
|  * Path-based routing (/api > API Service, /web > Web Service)        |
|  * TLS termination (HTTPS)                                             |
|  * Load balancing                                                      |
|  * SSL certificate management                                          |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    INGRESS ARCHITECTURE                                 |
|                                                                         |
|                      Internet                                           |
|                          |                                              |
|                          v                                              |
|              +-----------------------+                                 |
|              |  Cloud Load Balancer  |                                 |
|              |     (External IP)     |                                 |
|              +-----------+-----------+                                 |
|                          |                                              |
|  +-----------------------+---------------------------------------+     |
|  |                       |                CLUSTER                |     |
|  |                       v                                       |     |
|  |           +-----------------------+                          |     |
|  |           |   Ingress Controller  |                          |     |
|  |           |   (Nginx Pod)         |                          |     |
|  |           |                       |                          |     |
|  |           | Reads Ingress rules   |                          |     |
|  |           | Configures proxy      |                          |     |
|  |           +-----------+-----------+                          |     |
|  |                       |                                       |     |
|  |         +-------------+-------------+                        |     |
|  |         |             |             |                        |     |
|  |         v             v             v                        |     |
|  |    +---------+   +---------+   +---------+                  |     |
|  |    |Service A|   |Service B|   |Service C|                  |     |
|  |    |(app1)   |   |(app2)   |   |(app3)   |                  |     |
|  |    +---------+   +---------+   +---------+                  |     |
|  |                                                               |     |
|  +---------------------------------------------------------------+     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 7.2 INGRESS RULES

**HOST-BASED ROUTING:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-host-ingress
spec:
  rules:
  - host: app1.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app1-service
            port:
              number: 80
  - host: app2.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app2-service
            port:
              number: 80
```

**PATH-BASED ROUTING:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-based-ingress
spec:
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /web
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
```

**TLS/HTTPS:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
spec:
  tls:
  - hosts:
    - myapp.example.com
    secretName: myapp-tls-secret    # Contains TLS cert and key
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: myapp-service
            port:
              number: 80
```

### 7.3 POPULAR INGRESS CONTROLLERS

```
+-------------------------------------------------------------------------+
|                    INGRESS CONTROLLERS                                  |
|                                                                         |
|  Kubernetes doesn't include an Ingress controller.                     |
|  You must install one.                                                 |
|                                                                         |
|  +--------------------+---------------------------------------------+  |
|  | Controller         | Notes                                       |  |
|  +--------------------+---------------------------------------------+  |
|  | NGINX Ingress      | Most popular. Community & commercial.      |  |
|  |                    | Good default choice.                        |  |
|  +--------------------+---------------------------------------------+  |
|  | Traefik            | Cloud-native, auto-discovery.              |  |
|  |                    | Good for dynamic environments.             |  |
|  +--------------------+---------------------------------------------+  |
|  | HAProxy            | High performance, battle-tested.           |  |
|  +--------------------+---------------------------------------------+  |
|  | AWS ALB Ingress    | Uses AWS Application Load Balancer.        |  |
|  |                    | Best for EKS.                               |  |
|  +--------------------+---------------------------------------------+  |
|  | GKE Ingress        | Uses Google Cloud Load Balancer.           |  |
|  +--------------------+---------------------------------------------+  |
|  | Istio Gateway      | Part of Istio service mesh.                |  |
|  |                    | Advanced traffic management.               |  |
|  +--------------------+---------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 8: NETWORK POLICIES

### 8.1 WHAT ARE NETWORK POLICIES?

```
+-------------------------------------------------------------------------+
|                    NETWORK POLICIES                                     |
|                                                                         |
|  Network Policies are like firewall rules for Pods.                    |
|  Control which Pods can talk to which.                                 |
|                                                                         |
|  DEFAULT BEHAVIOR:                                                      |
|  ------------------                                                     |
|  Without Network Policies: ALL Pods can talk to ALL Pods               |
|  (Fully open network)                                                  |
|                                                                         |
|  With Network Policies: Only explicitly allowed traffic passes         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REQUIREMENTS:                                                          |
|  * CNI plugin must support Network Policies                           |
|  * Supported: Calico, Cilium, Weave Net                               |
|  * NOT supported: Flannel (basic)                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  POLICY TYPES:                                                          |
|                                                                         |
|  Ingress: Control incoming traffic TO Pods                             |
|  Egress:  Control outgoing traffic FROM Pods                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 8.2 NETWORK POLICY EXAMPLES

DENY ALL INGRESS (Default Deny):

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
  namespace: production
spec:
  podSelector: {}          # Applies to all Pods in namespace
  policyTypes:
  - Ingress                # Only affects ingress
  # No ingress rules = deny all incoming traffic
```

**ALLOW SPECIFIC PODS:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend         # Apply to backend Pods
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend    # Only allow from frontend Pods
    ports:
    - protocol: TCP
      port: 8080
```

**ALLOW FROM SPECIFIC NAMESPACE:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-monitoring
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring    # Allow from monitoring namespace
    ports:
    - protocol: TCP
      port: 9090
```

EGRESS POLICY (Restrict Outbound):

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-egress
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
  - to:                    # Allow DNS
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
```

## PART 9: TROUBLESHOOTING

### 9.1 COMMON NETWORKING ISSUES

```
+-------------------------------------------------------------------------+
| Problem                          | Solution                            |
+----------------------------------+-------------------------------------+
| Pod can't reach Service          | Check Service selector matches      |
|                                  | Pod labels. Check Endpoints.        |
+----------------------------------+-------------------------------------+
| DNS not resolving                | Check CoreDNS is running.           |
|                                  | Check /etc/resolv.conf in Pod.      |
+----------------------------------+-------------------------------------+
| Can't reach external services    | Check egress Network Policies.      |
|                                  | Check node's internet connectivity. |
+----------------------------------+-------------------------------------+
| NodePort not accessible          | Check firewall on nodes.            |
|                                  | Check kube-proxy is running.        |
+----------------------------------+-------------------------------------+
| Pod-to-Pod fails across nodes    | Check CNI plugin. Check node        |
|                                  | routes. Check overlay network.      |
+----------------------------------+-------------------------------------+
```

### 9.2 DEBUGGING COMMANDS

```bash
# Check Service and Endpoints
kubectl get svc my-service
kubectl get endpoints my-service
kubectl describe svc my-service

# Check DNS from Pod
kubectl exec -it my-pod -- nslookup my-service
kubectl exec -it my-pod -- cat /etc/resolv.conf

# Check Pod connectivity
kubectl exec -it my-pod -- ping other-pod-ip
kubectl exec -it my-pod -- curl http://my-service:80

# Check kube-proxy
kubectl get pods -n kube-system | grep kube-proxy
kubectl logs -n kube-system kube-proxy-xxxxx

# Check CoreDNS
kubectl get pods -n kube-system | grep coredns
kubectl logs -n kube-system coredns-xxxxx

# Check iptables rules (on node)
iptables -t nat -L | grep my-service
ipvsadm -Ln  # If using IPVS mode

# Check CNI
ls /etc/cni/net.d/
cat /etc/cni/net.d/10-calico.conflist

# Network debugging Pod
kubectl run debug --image=nicolaka/netshoot -it --rm -- /bin/bash
```

## PART 10: SUMMARY & CHEAT SHEET

```
+-------------------------------------------------------------------------+
|                    KUBERNETES NETWORKING CHEAT SHEET                    |
|                                                                         |
|  POD NETWORKING:                                                        |
|  * Each Pod gets unique IP                                             |
|  * Containers in Pod share network namespace (localhost)              |
|  * Pod-to-Pod: Direct IP routing, no NAT                              |
|                                                                         |
|  SERVICES:                                                              |
|  * ClusterIP: Internal only (default)                                 |
|  * NodePort: External via node ports (30000-32767)                    |
|  * LoadBalancer: External via cloud LB                                |
|  * Headless: Direct Pod IPs (clusterIP: None)                        |
|                                                                         |
|  DNS:                                                                   |
|  * <service>.<namespace>.svc.cluster.local                            |
|  * Short: <service> (same namespace)                                  |
|  * StatefulSet: <pod>.<service>.<namespace>.svc.cluster.local        |
|                                                                         |
|  INGRESS:                                                               |
|  * L7 routing (HTTP/HTTPS)                                            |
|  * Host-based and path-based routing                                  |
|  * TLS termination                                                    |
|  * Requires Ingress Controller                                        |
|                                                                         |
|  NETWORK POLICIES:                                                      |
|  * Firewall rules for Pods                                            |
|  * Default: Allow all (no policies)                                   |
|  * Requires supporting CNI (Calico, Cilium)                          |
|                                                                         |
|  CNI PLUGINS:                                                           |
|  * Calico: BGP/VXLAN, Network Policies                               |
|  * Flannel: Simple overlay                                            |
|  * Cilium: eBPF, L7 policies                                         |
|  * AWS VPC CNI: Native VPC IPs                                       |
|                                                                         |
|  KUBE-PROXY MODES:                                                      |
|  * iptables: Default, linear lookup                                   |
|  * IPVS: Better for large clusters, O(1) lookup                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF DOCUMENT

