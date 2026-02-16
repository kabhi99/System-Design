# KUBERNETES SERVICES
*Chapter 4: Service Discovery and Load Balancing*

Services provide stable networking for ephemeral Pods. This chapter
covers service types, discovery, and load balancing.

## SECTION 4.1: WHY SERVICES?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM                                                           |
|                                                                         |
|  Pods are ephemeral:                                                   |
|  * IPs change when pods restart                                      |
|  * Multiple replicas have different IPs                              |
|  * Pods can be created/destroyed at any time                        |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |   Before restart:           After restart:                     |  |
|  |   Pod: 10.0.1.5             Pod: 10.0.1.99 (NEW IP!)          |  |
|  |                                                                 |  |
|  |   Client hardcodes          Client can't find pod!          |  |
|  |   10.0.1.5                                                      |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  THE SOLUTION: SERVICES                                               |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |   Client ------> Service ------> Pod 1 (10.0.1.5)             |  |
|  |                  (stable IP)  +-> Pod 2 (10.0.1.6)             |  |
|  |                  10.96.0.100  +-> Pod 3 (10.0.1.7)             |  |
|  |                                                                 |  |
|  |   Pods change, Service IP stays the same                       |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.2: SERVICE NETWORKING (Deep Dive)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HOW DOES A SERVICE GET ITS IP? (ClusterIP)                           |
|  ===========================================                            |
|                                                                         |
|  When you create a Service:                                           |
|                                                                         |
|  1. API Server assigns a ClusterIP from service CIDR (10.96.0.0/12)  |
|  2. This IP is VIRTUAL - no network interface has this IP            |
|  3. kube-proxy on every node creates iptables/IPVS rules             |
|  4. Rules translate ClusterIP > actual pod IPs                       |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |   kubectl create service clusterip web --tcp=80:8080           |   |
|  |                                                                 |   |
|  |                      |                                          |   |
|  |                      v                                          |   |
|  |   +---------------------------------------------------------+  |   |
|  |   |                  API SERVER                              |  |   |
|  |   |                                                          |  |   |
|  |   |  1. Picks IP from 10.96.0.0/12 > 10.96.45.100          |  |   |
|  |   |  2. Creates Service object                               |  |   |
|  |   |  3. Endpoints Controller watches for matching pods       |  |   |
|  |   |                                                          |  |   |
|  |   +---------------------------------------------------------+  |   |
|  |                      |                                          |   |
|  |                      | kube-proxy watches API server           |   |
|  |                      v                                          |   |
|  |   +----------+  +----------+  +----------+                    |   |
|  |   |kube-proxy|  |kube-proxy|  |kube-proxy|                    |   |
|  |   | (Node 1) |  | (Node 2) |  | (Node 3) |                    |   |
|  |   |          |  |          |  |          |                    |   |
|  |   | Creates  |  | Creates  |  | Creates  |                    |   |
|  |   | iptables |  | iptables |  | iptables |                    |   |
|  |   +----------+  +----------+  +----------+                    |   |
|  |                                                                 |   |
|  |   Every node now knows: 10.96.45.100 > pod endpoints          |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  KEY INSIGHT:                                                         |
|  * ClusterIP is VIRTUAL (doesn't exist on any interface)            |
|  * iptables INTERCEPTS packets to ClusterIP                         |
|  * iptables REWRITES destination to real pod IP (DNAT)              |
|  * This happens at EVERY node independently                          |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  HOW DOES SERVICE KNOW POD IPS? (Endpoints)                           |
|  ===========================================                            |
|                                                                         |
|  Endpoints Controller (in controller-manager) automatically           |
|  maintains list of pod IPs for each service:                          |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |   SERVICE: web-service                                         |   |
|  |   selector: app=web                                            |   |
|  |                                                                 |   |
|  |                      |                                          |   |
|  |                      v                                          |   |
|  |   +---------------------------------------------------------+  |   |
|  |   |            ENDPOINTS CONTROLLER                          |  |   |
|  |   |                                                          |  |   |
|  |   |  "Find all pods with label app=web"                     |  |   |
|  |   |                                                          |  |   |
|  |   |  Found:                                                  |  |   |
|  |   |    Pod-1: 10.244.1.5:8080  (Ready Y)                   |  |   |
|  |   |    Pod-2: 10.244.2.10:8080 (Ready Y)                   |  |   |
|  |   |    Pod-3: 10.244.1.20:8080 (NotReady X) < excluded    |  |   |
|  |   |                                                          |  |   |
|  |   +---------------------------------------------------------+  |   |
|  |                      |                                          |   |
|  |                      v                                          |   |
|  |   +---------------------------------------------------------+  |   |
|  |   |            ENDPOINTS OBJECT                              |  |   |
|  |   |                                                          |  |   |
|  |   |  Name: web-service                                      |  |   |
|  |   |  Subsets:                                                |  |   |
|  |   |    - Addresses:                                         |  |   |
|  |   |        - ip: 10.244.1.5                                 |  |   |
|  |   |        - ip: 10.244.2.10                                |  |   |
|  |   |      Ports:                                              |  |   |
|  |   |        - port: 8080                                     |  |   |
|  |   |                                                          |  |   |
|  |   +---------------------------------------------------------+  |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  AUTOMATIC UPDATES:                                                   |
|  * Pod becomes Ready > added to Endpoints                            |
|  * Pod becomes NotReady > removed from Endpoints                     |
|  * Pod deleted > removed from Endpoints                              |
|  * New pod created > added when Ready                                |
|                                                                         |
|  kube-proxy watches Endpoints and updates iptables rules!            |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT HAPPENS WHEN PODS SCALE? (Dynamic IP Management)                |
|  =====================================================                  |
|                                                                         |
|  BEFORE SCALING (2 replicas):                                         |
|  -----------------------------                                         |
|                                                                         |
|  Service: web-svc (10.96.45.100)                                      |
|  Endpoints: 10.244.1.5:8080, 10.244.2.10:8080                        |
|                                                                         |
|  iptables rules on every node:                                        |
|  IF dest=10.96.45.100:80 THEN DNAT to:                               |
|    - 10.244.1.5:8080  (50% probability)                              |
|    - 10.244.2.10:8080 (50% probability)                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SCALE UP TO 5 REPLICAS:                                              |
|  -------------------------                                             |
|                                                                         |
|  kubectl scale deployment web --replicas=5                            |
|                                                                         |
|  1. 3 new pods created with NEW IPs:                                  |
|     Pod-3: 10.244.3.5:8080                                           |
|     Pod-4: 10.244.1.15:8080                                          |
|     Pod-5: 10.244.2.20:8080                                          |
|                                                                         |
|  2. Pods pass readiness probe > become Ready                         |
|                                                                         |
|  3. Endpoints Controller detects new pods (label app=web)            |
|     Updates Endpoints object with 5 IPs                               |
|                                                                         |
|  4. kube-proxy on EVERY node sees Endpoints change                   |
|     Updates iptables rules:                                           |
|                                                                         |
|  iptables rules on every node (UPDATED):                             |
|  IF dest=10.96.45.100:80 THEN DNAT to:                               |
|    - 10.244.1.5:8080   (20% probability)                             |
|    - 10.244.2.10:8080  (20% probability)                             |
|    - 10.244.3.5:8080   (20% probability)  < NEW                      |
|    - 10.244.1.15:8080  (20% probability)  < NEW                      |
|    - 10.244.2.20:8080  (20% probability)  < NEW                      |
|                                                                         |
|  5. New requests automatically distributed to all 5 pods!            |
|     NO client changes needed - same Service IP works                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SCALE DOWN TO 2 REPLICAS:                                            |
|  -------------------------                                             |
|                                                                         |
|  1. Kubernetes terminates 3 pods (highest ordinal first)             |
|  2. Endpoints Controller removes those IPs                           |
|  3. kube-proxy updates iptables (only 2 entries now)                 |
|  4. Traffic automatically goes to remaining 2 pods                   |
|                                                                         |
|  ALL AUTOMATIC! Client just uses stable Service IP.                  |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  HOW CLUSTERIP LOAD BALANCING WORKS (iptables)                        |
|  ==============================================                         |
|                                                                         |
|  When pod sends request to ClusterIP:                                 |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                         NODE 1                                  |   |
|  |                                                                 |   |
|  |  +----------------+                                            |   |
|  |  |   Client Pod   |                                            |   |
|  |  |                |                                            |   |
|  |  | curl http://   |                                            |   |
|  |  | 10.96.45.100:80| < ClusterIP of web-service                |   |
|  |  |                |                                            |   |
|  |  +-------+--------+                                            |   |
|  |          |                                                      |   |
|  |          | Packet: src=10.244.1.5 dst=10.96.45.100:80         |   |
|  |          v                                                      |   |
|  |  +---------------------------------------------------------+   |   |
|  |  |              IPTABLES (kube-proxy rules)                |   |   |
|  |  |                                                         |   |   |
|  |  |  Chain KUBE-SERVICES:                                  |   |   |
|  |  |    Match: dst=10.96.45.100 port=80                     |   |   |
|  |  |    Action: Jump to KUBE-SVC-XXXX                       |   |   |
|  |  |                                                         |   |   |
|  |  |  Chain KUBE-SVC-XXXX (web-service):                    |   |   |
|  |  |    - 33% > KUBE-SEP-AAA (pod 10.244.1.5)              |   |   |
|  |  |    - 33% > KUBE-SEP-BBB (pod 10.244.2.10)             |   |   |
|  |  |    - 33% > KUBE-SEP-CCC (pod 10.244.3.5) < selected   |   |   |
|  |  |                                                         |   |   |
|  |  |  Chain KUBE-SEP-CCC:                                   |   |   |
|  |  |    Action: DNAT to 10.244.3.5:8080                    |   |   |
|  |  |                                                         |   |   |
|  |  +---------------------------------------------------------+   |   |
|  |          |                                                      |   |
|  |          | Packet REWRITTEN:                                   |   |
|  |          | src=10.244.1.5 dst=10.244.3.5:8080                 |   |
|  |          v                                                      |   |
|  |                                                                 |   |
|  |          > Routes to Node 3 (where 10.244.3.5 is)             |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  KEY CONCEPTS:                                                        |
|  * DNAT: Destination Network Address Translation                     |
|  * iptables probability rules distribute load randomly              |
|  * Connection tracking (conntrack) ensures responses return         |
|    to original sender                                                |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  SESSION AFFINITY (Sticky Sessions)                                   |
|  ===================================                                    |
|                                                                         |
|  By default, each request can go to different pod.                    |
|  Sometimes you need requests from same client > same pod.             |
|                                                                         |
|  spec:                                                                 |
|    sessionAffinity: ClientIP        # Sticky by client IP            |
|    sessionAffinityConfig:                                             |
|      clientIP:                                                         |
|        timeoutSeconds: 10800        # 3 hours                        |
|                                                                         |
|  HOW IT WORKS:                                                        |
|  1. First request from 192.168.1.50 > routed to Pod-2               |
|  2. iptables remembers: 192.168.1.50 > Pod-2                        |
|  3. Next requests from same IP > same Pod-2                         |
|  4. After timeout, can go to different pod                          |
|                                                                         |
|  USE CASES:                                                           |
|  * WebSocket connections (need same backend)                         |
|  * In-memory session storage                                         |
|  * File upload in chunks (same server)                               |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICE VS POD PORT MAPPING (Complete Picture)                       |
|  ===============================================                        |
|                                                                         |
|      EXTERNAL                  KUBERNETES CLUSTER                      |
|      ========                  ==================                       |
|                                                                         |
|      Internet                                                          |
|          |                                                              |
|          |  User: curl http://a]4d7.elb.amazonaws.com:443             |
|          v                                                              |
|  +------------------+                                                  |
|  |  Cloud LB        |  < LoadBalancer Service creates this            |
|  |  Port: 443       |                                                  |
|  +--------+---------+                                                  |
|           |                                                             |
|           |  Forwards to NodePort                                      |
|           v                                                             |
|  +-----------------------------------------------------------------+   |
|  |                     ANY NODE                                    |   |
|  |                                                                 |   |
|  |  +---------------------------------------------------------+   |   |
|  |  |  nodePort: 31234                                        |   |   |
|  |  |                                                         |   |   |
|  |  |  iptables: port 31234 > Service ClusterIP:port         |   |   |
|  |  +---------------------------------------------------------+   |   |
|  |           |                                                     |   |
|  |           v                                                     |   |
|  |  +---------------------------------------------------------+   |   |
|  |  |  ClusterIP: 10.96.45.100                                |   |   |
|  |  |  port: 443 (service port)                               |   |   |
|  |  |                                                         |   |   |
|  |  |  iptables: ClusterIP:443 > Endpoints                   |   |   |
|  |  +---------------------------------------------------------+   |   |
|  |           |                                                     |   |
|  |           |  Load balance to one of:                           |   |
|  |           v                                                     |   |
|  |  +---------------------------------------------------------+   |   |
|  |  |  Endpoints (pod IPs):                                   |   |   |
|  |  |    10.244.1.5:8080  < targetPort (container port)      |   |   |
|  |  |    10.244.2.10:8080                                     |   |   |
|  |  |    10.244.3.5:8080                                      |   |   |
|  |  +---------------------------------------------------------+   |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  PORT MAPPING SUMMARY:                                                |
|  ---------------------                                                 |
|  CloudLB:443 > NodePort:31234 > ClusterIP:443 > Pod:8080             |
|                                                                         |
|  YAML:                                                                 |
|  spec:                                                                 |
|    type: LoadBalancer                                                 |
|    ports:                                                              |
|      - port: 443          # ClusterIP port (internal access)         |
|        targetPort: 8080   # Pod/container port                       |
|        nodePort: 31234    # Node port (auto-assigned if not set)     |
|                                                                         |
+-------------------------------------------------------------------------+
```

```bash
NETWORKING VERIFICATION COMMANDS:
---------------------------------

# See service ClusterIP
kubectl get svc <service>

# See endpoints (actual pod IPs)
kubectl get endpoints <service>

# Describe shows all networking details
kubectl describe svc <service>

# Test service from inside cluster
kubectl run test --rm -it --image=busybox -- wget -qO- http://<clusterip>:<port>

# See iptables rules (on node - requires SSH)
sudo iptables -t nat -L KUBE-SERVICES -n
sudo iptables -t nat -L KUBE-NODEPORTS -n
```

## SECTION 4.3: SERVICE TYPES (Detailed)

There are 4 service types. Think of them as "how do I want to access my pods?"

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICE TYPES OVERVIEW                                                |
|                                                                         |
|  +---------------+---------------------+----------------------------+  |
|  | Type          | Access From         | Use When                   |  |
|  +---------------+---------------------+----------------------------+  |
|  | ClusterIP     | Inside cluster only | Internal microservices     |  |
|  | NodePort      | Outside via node IP | Dev/testing, bare metal    |  |
|  | LoadBalancer  | Outside via cloud LB| Production on cloud        |  |
|  | ExternalName  | DNS alias           | External databases         |  |
|  +---------------+---------------------+----------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TYPE 1: ClusterIP (Default) - INTERNAL ONLY

```
WHO CAN ACCESS: Only pods INSIDE the cluster
USE CASE: Backend services, databases, internal APIs

+-------------------------------------------------------------------------+
|                                                                         |
|  CLUSTERIP - HOW IT WORKS                                              |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                    KUBERNETES CLUSTER                            |   |
|  |                                                                  |   |
|  |    +---------------+                                            |   |
|  |    |   Frontend    |                                            |   |
|  |    |   Pod         |                                            |   |
|  |    |               |                                            |   |
|  |    |  curl http:// |                                            |   |
|  |    |  backend-svc  |                                            |   |
|  |    |  :5000        |                                            |   |
|  |    +-------+-------+                                            |   |
|  |            |                                                     |   |
|  |            | Request to backend-svc:5000                        |   |
|  |            v                                                     |   |
|  |    +-----------------------------------------------+            |   |
|  |    |          SERVICE: backend-svc                  |            |   |
|  |    |          Type: ClusterIP                       |            |   |
|  |    |          ClusterIP: 10.96.45.123              |            |   |
|  |    |          Port: 5000                           |            |   |
|  |    |                                                |            |   |
|  |    |  DNS: backend-svc.default.svc.cluster.local   |            |   |
|  |    +-------------------+---------------------------+            |   |
|  |                        |                                         |   |
|  |            +-----------+-----------+                            |   |
|  |            |           |           |  Load balances             |   |
|  |            v           v           v                            |   |
|  |    +-----------+ +-----------+ +-----------+                   |   |
|  |    |  Backend  | |  Backend  | |  Backend  |                   |   |
|  |    |  Pod 1    | |  Pod 2    | |  Pod 3    |                   |   |
|  |    | 10.0.1.5  | | 10.0.1.6  | | 10.0.1.7  |                   |   |
|  |    | :5000     | | :5000     | | :5000     |                   |   |
|  |    +-----------+ +-----------+ +-----------+                   |   |
|  |                                                                  |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|   INTERNET CANNOT ACCESS (no external IP)                           |
|                                                                         |
+-------------------------------------------------------------------------+

YAML:
------
apiVersion: v1
kind: Service
metadata:
  name: backend-svc
spec:
  type: ClusterIP              # Default, can be omitted
  selector:
    app: backend               # Matches pod labels
  ports:
    - port: 5000               # Service port (what clients use)
      targetPort: 5000         # Pod port (where app listens)
```

### TYPE 2: NodePort - EXTERNAL VIA NODE IP

```
WHO CAN ACCESS: Anyone who can reach any node's IP
USE CASE: Development, testing, bare metal clusters (no cloud LB)

+-------------------------------------------------------------------------+
|                                                                         |
|  NODEPORT - HOW IT WORKS                                               |
|                                                                         |
|                         INTERNET / USER                                |
|                              |                                          |
|                              | http://192.168.1.10:30080               |
|                              | (any node IP works!)                     |
|                              v                                          |
|  +-----------------------------------------------------------------+   |
|  |                    KUBERNETES CLUSTER                            |   |
|  |                                                                  |   |
|  |   +------------------+  +------------------+  +----------------+|   |
|  |   |     NODE 1       |  |     NODE 2       |  |    NODE 3      ||   |
|  |   |   192.168.1.10   |  |   192.168.1.11   |  |  192.168.1.12  ||   |
|  |   |                  |  |                  |  |                ||   |
|  |   |  Port 30080 OPEN |  |  Port 30080 OPEN |  | Port 30080 OPEN||   |
|  |   |        |         |  |        |         |  |       |        ||   |
|  |   +--------+---------+  +--------+---------+  +-------+--------+|   |
|  |            |                     |                    |          |   |
|  |            +----------+----------+--------------------+          |   |
|  |                       |                                          |   |
|  |                       v                                          |   |
|  |    +-----------------------------------------------+            |   |
|  |    |          SERVICE: web-svc                      |            |   |
|  |    |          Type: NodePort                        |            |   |
|  |    |          ClusterIP: 10.96.50.100              |            |   |
|  |    |          Port: 80                              |            |   |
|  |    |          NodePort: 30080 <-- Opens on ALL nodes|            |   |
|  |    +-------------------+---------------------------+            |   |
|  |                        |                                         |   |
|  |            +-----------+-----------+                            |   |
|  |            v           v           v                            |   |
|  |    +-----------+ +-----------+ +-----------+                   |   |
|  |    |   Web     | |   Web     | |   Web     |                   |   |
|  |    |   Pod 1   | |   Pod 2   | |   Pod 3   |                   |   |
|  |    |   :80     | |   :80     | |   :80     |                   |   |
|  |    +-----------+ +-----------+ +-----------+                   |   |
|  |                                                                  |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  ACCESS OPTIONS:                                                       |
|  * http://192.168.1.10:30080  (Node 1)                               |
|  * http://192.168.1.11:30080  (Node 2)                               |
|  * http://192.168.1.12:30080  (Node 3) < Any node works!            |
|                                                                         |
+-------------------------------------------------------------------------+

YAML:
------
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  type: NodePort
  selector:
    app: web
  ports:
    - port: 80                 # ClusterIP port (internal)
      targetPort: 80           # Pod port
      nodePort: 30080          # External port (30000-32767)
                               # Auto-assigned if omitted

PORT RANGE: 30000 - 32767 (configurable)
```

### TYPE 3: LoadBalancer - EXTERNAL VIA CLOUD LOAD BALANCER

```
WHO CAN ACCESS: Anyone on the internet
USE CASE: Production apps on AWS/GCP/Azure
REQUIREMENT: Cloud provider (creates actual LB like AWS ELB/ALB)

+-------------------------------------------------------------------------+
|                                                                         |
|  LOADBALANCER - HOW IT WORKS                                           |
|                                                                         |
|                         INTERNET / USER                                |
|                              |                                          |
|                              | http://a]4d7f8e9.elb.amazonaws.com     |
|                              | (External IP/DNS from cloud)            |
|                              v                                          |
|  +-------------------------------------------------------------------+ |
|  |                 CLOUD LOAD BALANCER                                | |
|  |               (AWS ELB / GCP LB / Azure LB)                       | |
|  |                                                                    | |
|  |              Created automatically by Kubernetes!                 | |
|  |              External IP: 52.14.xxx.xxx                          | |
|  +-------------------------------+-----------------------------------+ |
|                                  |                                      |
|                                  v                                      |
|  +-----------------------------------------------------------------+   |
|  |                    KUBERNETES CLUSTER                            |   |
|  |                                                                  |   |
|  |   +------------------+  +------------------+                    |   |
|  |   |     NODE 1       |  |     NODE 2       |                    |   |
|  |   |                  |  |                  |                    |   |
|  |   |  NodePort: 31234 |  |  NodePort: 31234 | < LB sends here   |   |
|  |   |        |         |  |        |         |                    |   |
|  |   +--------+---------+  +--------+---------+                    |   |
|  |            |                     |                               |   |
|  |            +----------+----------+                               |   |
|  |                       v                                          |   |
|  |    +-----------------------------------------------+            |   |
|  |    |          SERVICE: api-svc                      |            |   |
|  |    |          Type: LoadBalancer                    |            |   |
|  |    |          External IP: 52.14.xxx.xxx           |            |   |
|  |    |          Port: 443                             |            |   |
|  |    +-------------------+---------------------------+            |   |
|  |                        |                                         |   |
|  |            +-----------+-----------+                            |   |
|  |            v           v           v                            |   |
|  |    +-----------+ +-----------+ +-----------+                   |   |
|  |    |   API     | |   API     | |   API     |                   |   |
|  |    |   Pod 1   | |   Pod 2   | |   Pod 3   |                   |   |
|  |    |   :8080   | |   :8080   | |   :8080   |                   |   |
|  |    +-----------+ +-----------+ +-----------+                   |   |
|  |                                                                  |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  NOTE: LoadBalancer includes NodePort + ClusterIP automatically!      |
|                                                                         |
|  YOUR EKS CLUSTER USES THIS TYPE!                                     |
|                                                                         |
+-------------------------------------------------------------------------+

YAML:
------
apiVersion: v1
kind: Service
metadata:
  name: api-svc
spec:
  type: LoadBalancer
  selector:
    app: api
  ports:
    - port: 443                # External port
      targetPort: 8080         # Pod port

CHECK EXTERNAL IP:
------------------
kubectl get svc api-svc
# NAME     TYPE           CLUSTER-IP    EXTERNAL-IP         PORT(S)
# api-svc  LoadBalancer   10.96.0.100   52.14.xxx.xxx      443:31234/TCP
```

### TYPE 4: ExternalName - DNS ALIAS

```
WHO CAN ACCESS: Pods inside cluster (for reaching external services)
USE CASE: Connect to external databases, third-party APIs
NO PROXYING: Just a DNS CNAME record

+-------------------------------------------------------------------------+
|                                                                         |
|  EXTERNALNAME - HOW IT WORKS                                           |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                    KUBERNETES CLUSTER                            |   |
|  |                                                                  |   |
|  |   +---------------+                                             |   |
|  |   |   Your Pod    |                                             |   |
|  |   |               |                                             |   |
|  |   |  curl http:// |                                             |   |
|  |   |  my-database  |                                             |   |
|  |   |               |                                             |   |
|  |   +-------+-------+                                             |   |
|  |           |                                                      |   |
|  |           | DNS lookup: my-database                             |   |
|  |           v                                                      |   |
|  |   +--------------------------------------------+                |   |
|  |   |    SERVICE: my-database                    |                |   |
|  |   |    Type: ExternalName                      |                |   |
|  |   |                                            |                |   |
|  |   |    Returns CNAME:                          |                |   |
|  |   |    db.rds.amazonaws.com                    |                |   |
|  |   |                                            |                |   |
|  |   |    (No ClusterIP, no pods!)               |                |   |
|  |   +--------------------+-----------------------+                |   |
|  |                        |                                         |   |
|  +------------------------+-----------------------------------------+   |
|                           |                                             |
|                           | Resolves to external DNS                   |
|                           v                                             |
|  +-----------------------------------------------------------------+   |
|  |              EXTERNAL SERVICE (Outside Cluster)                  |   |
|  |                                                                  |   |
|  |     AWS RDS Database: db.rds.amazonaws.com                      |   |
|  |                                                                  |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  BENEFIT: If database URL changes, just update Service                |
|           (pods don't need to know the real URL)                      |
|                                                                         |
+-------------------------------------------------------------------------+

YAML:
------
apiVersion: v1
kind: Service
metadata:
  name: my-database
spec:
  type: ExternalName
  externalName: db.rds.amazonaws.com     # No selector, no ports!
```

### BONUS: HEADLESS SERVICE (clusterIP: None)

```
NOT A TYPE, but a special configuration of ClusterIP
USE CASE: StatefulSets, when you need to reach specific pods

+-------------------------------------------------------------------------+
|                                                                         |
|  HEADLESS SERVICE - NO CLUSTER IP                                      |
|                                                                         |
|  NORMAL SERVICE:           HEADLESS SERVICE:                           |
|  ---------------           -----------------                           |
|                                                                         |
|  DNS: my-svc               DNS: my-svc                                 |
|       v                         v                                      |
|  Returns: 10.96.0.100      Returns: 10.0.1.5                          |
|  (single ClusterIP)                 10.0.1.6                          |
|                                     10.0.1.7                          |
|                            (all pod IPs!)                              |
|                                                                         |
|  Client > Service > Pod    Client can pick specific pod               |
|  (random pod)              postgres-0.postgres-svc                     |
|                            postgres-1.postgres-svc                     |
|                                                                         |
+-------------------------------------------------------------------------+

YAML:
------
apiVersion: v1
kind: Service
metadata:
  name: postgres-svc
spec:
  clusterIP: None            # < This makes it headless!
  selector:
    app: postgres
  ports:
    - port: 5432
```

### COMPARISON: WHICH SERVICE TYPE TO USE?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DECISION TREE                                                         |
|                                                                         |
|  Need external access?                                                 |
|       |                                                                |
|       +-- NO ---------------> ClusterIP                               |
|       |                       (internal microservices)                |
|       |                                                                |
|       +-- YES                                                          |
|            |                                                           |
|            +-- On cloud (AWS/GCP/Azure)?                              |
|            |        |                                                  |
|            |        +-- YES --> LoadBalancer (production)             |
|            |        |                                                  |
|            |        +-- NO ---> NodePort (dev, bare metal)            |
|            |                                                           |
|            +-- Just need DNS alias to external service?               |
|                     |                                                  |
|                     +-- YES --> ExternalName                          |
|                                                                         |
|  -------------------------------------------------------------------   |
|                                                                         |
|  REAL WORLD EXAMPLES:                                                  |
|                                                                         |
|  * Backend API > calls > Database Service (ClusterIP)                |
|  * Frontend > exposed via > LoadBalancer (users access)              |
|  * Testing locally > NodePort (minikube)                             |
|  * Connect to AWS RDS > ExternalName                                 |
|  * PostgreSQL StatefulSet > Headless Service                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

**COMMANDS:**
---------

```bash
# Create services
kubectl expose deployment <deploy> --port=80 --type=ClusterIP
kubectl expose deployment <deploy> --port=80 --type=NodePort
kubectl expose deployment <deploy> --port=80 --type=LoadBalancer

# View services
kubectl get svc
kubectl get svc -o wide
kubectl describe svc <service-name>

# See which pods service routes to
kubectl get endpoints <service-name>

# Test service from inside cluster
kubectl run test --rm -it --image=busybox -- wget -qO- http://<service>:<port>
```

### HOW DOES TRAFFIC FORWARDING WORK? (kube-proxy + iptables)

QUESTION: If request arrives at Node 1, but Pod is on Node 2,
how does Node 1 know where to forward the traffic?

ANSWER: kube-proxy on EVERY node maintains iptables rules
that know ALL pod locations!

```
STEP 1: SERVICE CREATED > KUBE-PROXY NOTIFIED
---------------------------------------------

+-------------------------------------------------------------------------+
|                                                                         |
|    kubectl apply -f service.yaml                                       |
|              |                                                          |
|              v                                                          |
|    +------------------+                                                |
|    |    API Server    |                                                |
|    |                  |                                                |
|    |  Stores:         |                                                |
|    |  - Service       |                                                |
|    |  - Endpoints     |<-- Endpoints Controller updates this          |
|    |    (pod IPs)     |    whenever pods are added/removed            |
|    |                  |                                                |
|    +--------+---------+                                                |
|             |                                                          |
|             |  kube-proxy WATCHES for changes                         |
|             v                                                          |
|    +--------------+  +--------------+  +--------------+              |
|    |  kube-proxy  |  |  kube-proxy  |  |  kube-proxy  |              |
|    |   (Node 1)   |  |   (Node 2)   |  |   (Node 3)   |              |
|    |              |  |              |  |              |              |
|    | Creates      |  | Creates      |  | Creates      |              |
|    | iptables!    |  | iptables!    |  | iptables!    |              |
|    +--------------+  +--------------+  +--------------+              |
|                                                                         |
|    ALL nodes now have iptables rules:                                 |
|    "Port 30080 > forward to 10.0.2.5 OR 10.0.2.6"                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
STEP 2: REQUEST ARRIVES AT NODE WITHOUT POD
--------------------------------------------

+-------------------------------------------------------------------------+
|                                                                         |
|    Client Request: http://192.168.1.10:30080                          |
|                              |                                          |
|                              v                                          |
|    +----------------------------------------------------------------+  |
|    |                        NODE 1                                   |  |
|    |                   192.168.1.10                                 |  |
|    |                                                                 |  |
|    |    +--------------------------------------------------------+  |  |
|    |    |                    IPTABLES                             |  |  |
|    |    |              (created by kube-proxy)                    |  |  |
|    |    |                                                         |  |  |
|    |    |  Rule: If port = 30080, DNAT to one of:                |  |  |
|    |    |        - 10.0.2.5:80  (Pod on Node 2) <-- Selected!   |  |  |
|    |    |        - 10.0.2.6:80  (Pod on Node 3)                  |  |  |
|    |    |                                                         |  |  |
|    |    +--------------------------------------------------------+  |  |
|    |                         |                                       |  |
|    |    NO POD HERE!         | Packet rewritten:                    |  |
|    |    Just forwards        | Dest: 10.0.2.5:80                    |  |
|    |                         |                                       |  |
|    +-------------------------+---------------------------------------+  |
|                              |                                          |
|                              | Cluster network                         |
|                              v                                          |
|    +----------------------------------------------------------------+  |
|    |                        NODE 2                                   |  |
|    |                                                                 |  |
|    |    +--------------------------------------------------------+  |  |
|    |    |                      POD                                |  |  |
|    |    |                 IP: 10.0.2.5:80                         |  |  |
|    |    |                                                         |  |  |
|    |    |           <---- Request arrives here!                  |  |  |
|    |    |                                                         |  |  |
|    |    +--------------------------------------------------------+  |  |
|    |                                                                 |  |
|    +----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
KEY COMPONENTS:
---------------

+-------------------------------------------------------------------------+
|                                                                         |
|  COMPONENT        | ROLE                                               |
|  -----------------+-------------------------------------------------   |
|                   |                                                    |
|  Endpoints        | List of pod IPs backing a service                 |
|  Controller       | Updates when pods added/removed                   |
|                   |                                                    |
|  kube-proxy       | Runs on EVERY node                                |
|                   | Watches API server for service/endpoint changes   |
|                   | Creates iptables/IPVS rules                       |
|                   |                                                    |
|  iptables         | Linux kernel packet filtering                     |
|                   | Does actual packet forwarding (DNAT)              |
|                   | Selects backend randomly or round-robin           |
|                   |                                                    |
+-------------------------------------------------------------------------+
```

```bash
VERIFY WITH COMMANDS:
---------------------

# See endpoints (pod IPs) for a service
kubectl get endpoints <service-name>
# Output: NAME      ENDPOINTS                    AGE
#         web-svc   10.0.2.5:80,10.0.2.6:80     5m

# View kube-proxy pods
kubectl get pods -n kube-system -l k8s-app=kube-proxy

# On a node, see iptables rules (SSH into node)
sudo iptables -t nat -L KUBE-SERVICES -n | grep <service-name>
```

### PORT MAPPING EXPLAINED: nodePort vs port vs targetPort

```
THREE TYPES OF PORTS IN A SERVICE:
----------------------------------

+-------------------------------------------------------------------------+
|                                                                         |
|  PORT             | WHAT IT IS                                         |
|  -----------------+---------------------------------------------------  |
|                   |                                                    |
|  nodePort         | Port OPENED on ALL nodes (30000-32767)            |
|                   | External users access via: <NodeIP>:<nodePort>    |
|                   |                                                    |
|  port             | Port on the SERVICE (ClusterIP)                   |
|                   | Pods inside cluster access via: <ServiceIP>:<port>|
|                   |                                                    |
|  targetPort       | Port on the POD where container listens           |
|                   | This is where traffic finally arrives             |
|                   |                                                    |
+-------------------------------------------------------------------------+
```

```yaml
CONCRETE EXAMPLE:
-----------------

apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  type: NodePort
  selector:
    app: web
  ports:
    - nodePort: 30080      # External: http://<node-ip>:30080
      port: 80             # Internal: http://web-svc:80
      targetPort: 8080     # Container listens on 8080
```

```
VISUAL MAPPING:
---------------

+-------------------------------------------------------------------------+
|                                                                         |
|   EXTERNAL USER                                                         |
|        |                                                                |
|        |  http://192.168.1.10:30080                                    |
|        |                     ^                                          |
|        |                     |                                          |
|        |                 nodePort: 30080                               |
|        v                                                                |
|   +-----------------------------------------------------------------+  |
|   |                    ANY NODE                                      |  |
|   |             (192.168.1.10, 192.168.1.11, etc.)                  |  |
|   |                                                                  |  |
|   |   Port 30080 is OPEN on ALL nodes in cluster                   |  |
|   |                                                                  |  |
|   +-------------------------+---------------------------------------+  |
|                             |                                          |
|                             | iptables DNAT                            |
|                             v                                          |
|   +-----------------------------------------------------------------+  |
|   |              SERVICE: web-svc                                    |  |
|   |              ClusterIP: 10.96.0.100                             |  |
|   |              Port: 80                                            |  |
|   |                       ^                                          |  |
|   |                       |                                          |
|   |              Internal pods use: http://web-svc:80               |  |
|   |              Or: http://10.96.0.100:80                          |  |
|   |                                                                  |  |
|   +-------------------------+---------------------------------------+  |
|                             |                                          |
|                             | Load balance to endpoints                |
|                             v                                          |
|   +-----------------------------------------------------------------+  |
|   |                    PODS (endpoints)                              |  |
|   |                                                                  |  |
|   |   10.0.2.5:8080    10.0.2.6:8080    10.0.2.7:8080              |  |
|   |       ^                 ^                 ^                      |  |
|   |       |                 |                 |                      |  |
|   |       +-----------------+-----------------+                      |  |
|   |                         |                                        |  |
|   |                   targetPort: 8080                              |  |
|   |              (container port in pod)                            |  |
|   |                                                                  |  |
|   +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
STEP-BY-STEP: USER HITS NODE1, POD ON NODE2
--------------------------------------------

SETUP:
* Node 1 IP: 192.168.1.10 (NO pods here)
* Node 2 IP: 192.168.1.11 (Pod is here: 10.0.2.5)
* Node 3 IP: 192.168.1.12 (NO pods here)
* Service: nodePort=30080, port=80, targetPort=8080

+-------------------------------------------------------------------------+
|                                                                         |
|  USER REQUEST: curl http://192.168.1.10:30080                         |
|  (hitting Node 1, but pod is on Node 2!)                              |
|                                                                         |
|  ===================================================================   |
|                                                                         |
|  STEP 1: Packet arrives at Node 1                                     |
|  ---------------------------------                                     |
|                                                                         |
|     Source IP: Client (203.0.113.50)                                  |
|     Dest IP:   192.168.1.10 (Node 1)                                  |
|     Dest Port: 30080 (nodePort)                                       |
|                                                                         |
|  ===================================================================   |
|                                                                         |
|  STEP 2: iptables on Node 1 matches the packet                        |
|  -----------------------------------------------                       |
|                                                                         |
|     kube-proxy has installed these rules on EVERY node:               |
|                                                                         |
|     Rule: IF dest_port == 30080                                       |
|           THEN DNAT to one of: 10.0.2.5:8080                         |
|           (randomly selected from endpoints)                          |
|                                                                         |
|  ===================================================================   |
|                                                                         |
|  STEP 3: Packet is REWRITTEN (DNAT)                                   |
|  ----------------------------------                                    |
|                                                                         |
|     BEFORE:                       AFTER:                              |
|     Dest: 192.168.1.10:30080  >  Dest: 10.0.2.5:8080                |
|     (Node 1 IP:nodePort)          (Pod IP:targetPort)                 |
|                                                                         |
|     Source IP remains: 203.0.113.50 (client)                         |
|                                                                         |
|  ===================================================================   |
|                                                                         |
|  STEP 4: Packet forwarded via cluster network                         |
|  ---------------------------------------------                         |
|                                                                         |
|     Node 1 > CNI network (flannel/calico) > Node 2                   |
|                                                                         |
|     Packet reaches pod at 10.0.2.5:8080                              |
|                                                                         |
|  ===================================================================   |
|                                                                         |
|  STEP 5: Response flows back (reverse NAT)                            |
|  ------------------------------------------                            |
|                                                                         |
|     Pod 10.0.2.5 > Node 2 > Node 1 > Client                          |
|                                                                         |
|     iptables connection tracking (conntrack) remembers                |
|     the original request and reverses the NAT                         |
|                                                                         |
|     Response to client: Source appears as 192.168.1.10:30080         |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
KEY INSIGHT: WHY THIS WORKS
---------------------------

+-------------------------------------------------------------------------+
|                                                                         |
|  1. nodePort IS UNIQUE CLUSTER-WIDE                                   |
|     If service uses 30080, NO other service can use 30080            |
|     This is enforced by Kubernetes                                    |
|                                                                         |
|  2. EVERY NODE LISTENS ON THE SAME nodePort                           |
|     Node 1:30080, Node 2:30080, Node 3:30080 - ALL work!            |
|     User can hit ANY node, they all forward correctly                |
|                                                                         |
|  3. kube-proxy KNOWS ALL POD LOCATIONS                                |
|     Watches API server for endpoint updates                          |
|     Creates iptables rules with ALL pod IPs                          |
|                                                                         |
|  4. POD CAN BE ANYWHERE                                               |
|     Doesn't matter if pod is on same node or different node          |
|     iptables + cluster network handles routing                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
COMMON SCENARIOS:
-----------------

+-------------------------------------------------------------------------+
|                                                                         |
|  SCENARIO 1: User hits Node 1, Pod on Node 2                          |
|  ---------------------------------------------                         |
|  * iptables on Node 1 rewrites dest to pod IP                        |
|  * Forwards across cluster network to Node 2                         |
|  * Works perfectly! Y                                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SCENARIO 2: User hits Node 2, Pod also on Node 2                     |
|  --------------------------------------------------                    |
|  * iptables on Node 2 rewrites dest to pod IP                        |
|  * Pod is local, traffic stays on Node 2                             |
|  * Works perfectly! Y                                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SCENARIO 3: Multiple pods, spread across nodes                       |
|  ------------------------------------------------                      |
|  * iptables randomly selects one pod from endpoints                  |
|  * Could be local or remote - doesn't matter                         |
|  * Built-in load balancing! Y                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
PORTS CAN BE SAME OR DIFFERENT:
-------------------------------

+-------------------------------------------------------------------------+
|                                                                         |
|  EXAMPLE 1: All ports different (common)                              |
|                                                                         |
|     nodePort: 30080   > Service port: 80   > targetPort: 8080        |
|                                                                         |
|     curl http://node-ip:30080                                         |
|       > iptables > 10.96.0.100:80 (clusterIP)                        |
|       > endpoints > 10.0.2.5:8080 (pod)                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXAMPLE 2: All ports same (also valid)                               |
|                                                                         |
|     nodePort: 30080   > Service port: 30080 > targetPort: 30080      |
|                                                                         |
|     Less common, but works fine                                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXAMPLE 3: Service port = targetPort (very common for ClusterIP)    |
|                                                                         |
|     Service port: 80 > targetPort: 80                                |
|                                                                         |
|     If ports match, you can omit targetPort:                         |
|     ports:                                                            |
|       - port: 80      # targetPort defaults to same value            |
|                                                                         |
+-------------------------------------------------------------------------+
```

```bash
QUICK REFERENCE:
----------------

# See all three ports in service
kubectl get svc <service> -o wide

# See endpoints (where traffic actually goes)
kubectl get endpoints <service>

# Describe shows full port mapping
kubectl describe svc <service>

# Example output:
# Port:                     <unset>  80/TCP
# TargetPort:               8080/TCP
# NodePort:                 <unset>  30080/TCP
# Endpoints:                10.0.2.5:8080,10.0.2.6:8080
```

## SECTION 4.3: SERVICE DISCOVERY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DNS-BASED DISCOVERY                                                   |
|  ====================                                                   |
|                                                                         |
|  Every Service gets a DNS entry automatically.                        |
|                                                                         |
|  DNS FORMAT:                                                           |
|  <service>.<namespace>.svc.cluster.local                              |
|                                                                         |
|  EXAMPLES:                                                             |
|  my-service.default.svc.cluster.local                                 |
|  my-service.default.svc                                               |
|  my-service.default                                                    |
|  my-service  (if in same namespace)                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ENVIRONMENT VARIABLES                                                 |
|  =====================                                                  |
|                                                                         |
|  Kubernetes injects env vars for each Service:                       |
|                                                                         |
|  MY_SERVICE_SERVICE_HOST=10.96.0.100                                  |
|  MY_SERVICE_SERVICE_PORT=80                                           |
|                                                                         |
|  Note: Only for services that exist when pod starts.                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HEADLESS SERVICE                                                      |
|  =================                                                      |
|                                                                         |
|  No cluster IP. DNS returns pod IPs directly.                        |
|  Useful for StatefulSets.                                             |
|                                                                         |
|  spec:                                                                  |
|    clusterIP: None                                                     |
|    selector:                                                            |
|      app: myapp                                                        |
|    ports:                                                               |
|      - port: 80                                                        |
|                                                                         |
|  DNS returns: 10.0.1.5, 10.0.1.6, 10.0.1.7 (all pod IPs)            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4.4: PRACTICAL EXAMPLES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMPLETE DEPLOYMENT + SERVICE                                        |
|                                                                         |
|  apiVersion: apps/v1                                                   |
|  kind: Deployment                                                       |
|  metadata:                                                              |
|    name: web-app                                                       |
|  spec:                                                                  |
|    replicas: 3                                                         |
|    selector:                                                            |
|      matchLabels:                                                       |
|        app: web                                                        |
|    template:                                                            |
|      metadata:                                                          |
|        labels:                                                          |
|          app: web                                                      |
|      spec:                                                              |
|        containers:                                                      |
|          - name: web                                                   |
|            image: nginx:1.25                                           |
|            ports:                                                       |
|              - containerPort: 80                                       |
|  ---                                                                    |
|  apiVersion: v1                                                        |
|  kind: Service                                                          |
|  metadata:                                                              |
|    name: web-service                                                   |
|  spec:                                                                  |
|    selector:                                                            |
|      app: web        # Matches pod labels                             |
|    ports:                                                               |
|      - port: 80                                                        |
|        targetPort: 80                                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  COMMANDS                                                              |
|                                                                         |
|  kubectl get svc                                                       |
|  kubectl describe svc web-service                                     |
|  kubectl get endpoints web-service                                    |
|                                                                         |
|  # Expose deployment quickly                                          |
|  kubectl expose deployment web-app --port=80 --type=LoadBalancer     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICES - KEY TAKEAWAYS                                             |
|                                                                         |
|  SERVICE TYPES                                                         |
|  -------------                                                         |
|  * ClusterIP: Internal only (default)                                |
|  * NodePort: External via node port                                  |
|  * LoadBalancer: External via cloud LB                              |
|  * ExternalName: DNS alias                                           |
|                                                                         |
|  DISCOVERY                                                             |
|  ---------                                                             |
|  * DNS: service.namespace.svc.cluster.local                         |
|  * Environment variables                                             |
|  * Headless: clusterIP: None                                        |
|                                                                         |
|  SELECTOR                                                              |
|  --------                                                              |
|  Service selector must match pod labels                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 4

