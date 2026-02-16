# CHAPTER 1: KUBERNETES ARCHITECTURE
*Understanding the Components That Make Orchestration Work*

Kubernetes is a complex distributed system. To master it, you need to
understand how its components work together. This chapter provides a deep
dive into Kubernetes architecture.

## GETTING STARTED: MINIKUBE SETUP (For Practice)

Minikube runs a single-node Kubernetes cluster on your local machine.
Perfect for learning and testing!

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MINIKUBE vs PRODUCTION CLUSTER                                        |
|                                                                         |
|  +-------------------------+      +-------------------------+          |
|  |      MINIKUBE           |      |      EKS / GKE          |          |
|  |   (Your Laptop)         |      |   (Production)          |          |
|  |                         |      |                         |          |
|  |  +-------------------+  |      |  +-----------------+    |          |
|  |  |  Single Node      |  |      |  |  Control Plane  |    |          |
|  |  |  (All-in-one)     |  |      |  |  (Managed)      |    |          |
|  |  |                   |  |      |  +-----------------+    |          |
|  |  |  * Control Plane  |  |      |  +------++------++------+|         |
|  |  |  * Worker         |  |      |  |Node 1||Node 2||Node N||         |
|  |  |  * Your Pods      |  |      |  +------++------++------+|         |
|  |  +-------------------+  |      |                         |          |
|  +-------------------------+      +-------------------------+          |
|                                                                         |
|  Good for: Learning, testing      Good for: Production workloads       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### INSTALL MINIKUBE

```bash
# macOS (using Homebrew)
brew install minikube

# Linux
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Windows (using Chocolatey)
choco install minikube

# Verify installation
minikube version
```

### PREREQUISITES

```bash
# Docker must be installed (minikube uses it as driver)
docker --version

# kubectl must be installed
kubectl version --client

# Install kubectl if needed (macOS)
brew install kubectl
```

### START YOUR CLUSTER

```bash
# Start minikube (creates single-node cluster)
minikube start

# Start with specific resources
minikube start --cpus=4 --memory=8192

# Start with specific Kubernetes version
minikube start --kubernetes-version=v1.28.0
```

### VERIFY CLUSTER IS RUNNING

```bash
# Check minikube status
minikube status

# Expected output:
# minikube
# type: Control Plane
# host: Running
# kubelet: Running
# apiserver: Running
# kubeconfig: Configured

# Check cluster info
kubectl cluster-info

# Check nodes (you'll see 1 node)
kubectl get nodes

# Example output:
# NAME       STATUS   ROLES           AGE   VERSION
# minikube   Ready    control-plane   1m    v1.28.0
```

### ESSENTIAL MINIKUBE COMMANDS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LIFECYCLE                                                              |
|  ---------                                                              |
|  minikube start              # Start cluster                           |
|  minikube stop               # Stop cluster (preserves state)          |
|  minikube delete             # Delete cluster completely               |
|  minikube status             # Check status                            |
|                                                                         |
|  ACCESS                                                                 |
|  ------                                                                 |
|  minikube dashboard          # Open Kubernetes Dashboard (Web UI)      |
|  minikube ssh                # SSH into minikube node                  |
|  minikube ip                 # Get minikube IP address                 |
|                                                                         |
|  SERVICES                                                               |
|  --------                                                               |
|  minikube service <name>     # Open service in browser                 |
|  minikube service list       # List all services with URLs             |
|  minikube tunnel             # Create tunnel for LoadBalancer services |
|                                                                         |
|  ADDONS                                                                 |
|  ------                                                                 |
|  minikube addons list        # List available addons                   |
|  minikube addons enable metrics-server   # Enable metrics             |
|  minikube addons enable ingress          # Enable ingress controller  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### FIRST PRACTICE: DEPLOY AN APP

```bash
# 1. Start minikube
minikube start

# 2. Create a deployment
kubectl create deployment hello --image=nginx

# 3. Check pod is running
kubectl get pods

# 4. Expose it as a service
kubectl expose deployment hello --type=NodePort --port=80

# 5. Open in browser
minikube service hello

# 6. Clean up
kubectl delete deployment hello
kubectl delete service hello
```

### TIPS FOR PRACTICING

- Always check: kubectl get pods -A (see all pods running)
- Use: kubectl describe pod <name> (when things go wrong)
- Use: kubectl logs <pod-name> (see container output)
- Dashboard: minikube dashboard (visual way to explore)
- Reset everything: minikube delete && minikube start

## SECTION 1.1: THE BIG PICTURE

### WHAT IS KUBERNETES?

Kubernetes (K8s) is a container orchestration platform that:

- Deploys containerized applications across clusters of machines
- Scales applications up and down automatically
- Manages the lifecycle of containers
- Provides service discovery and load balancing
- Handles storage orchestration
- Automates rollouts and rollbacks

### CLUSTER ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|                    KUBERNETES CLUSTER ARCHITECTURE                     |
|                                                                         |
|  +--------------------------------------------------------------------+|
|  |                       CONTROL PLANE                                ||
|  |  (Master Node(s) - The Brain)                                     ||
|  |                                                                    ||
|  |  +----------------+  +----------------+  +----------------+      ||
|  |  |   API Server   |  |   Scheduler    |  | Controller     |      ||
|  |  | (kube-apiserver)|  |(kube-scheduler)|  | Manager        |      ||
|  |  |                |  |                |  |                |      ||
|  |  | * REST API     |  | * Pod placement|  | * Node         |      ||
|  |  | * Auth         |  | * Resource     |  | * Replication  |      ||
|  |  | * Validation   |  |   awareness    |  | * Endpoints    |      ||
|  |  +----------------+  +----------------+  | * Service Acct |      ||
|  |          |                               +----------------+      ||
|  |          |                                                        ||
|  |  +-------v--------+  +----------------+                          ||
|  |  |     etcd       |  | Cloud Controller|                          ||
|  |  |                |  | Manager (cloud) |                          ||
|  |  | * Cluster      |  |                |                          ||
|  |  |   state        |  | * Cloud LB     |                          ||
|  |  | * Config       |  | * Routes       |                          ||
|  |  | * Secrets      |  | * Nodes        |                          ||
|  |  +----------------+  +----------------+                          ||
|  |                                                                    ||
|  +--------------------------------------------------------------------+|
|                                    |                                   |
|                                    | API Calls                         |
|                                    v                                   |
|  +--------------------------------------------------------------------+|
|  |                         WORKER NODES                               ||
|  |  (Where your applications run)                                    ||
|  |                                                                    ||
|  |  +--------------------------+  +--------------------------+      ||
|  |  |        Node 1            |  |        Node 2            |      ||
|  |  |                          |  |                          |      ||
|  |  |  +---------------------+ |  |  +---------------------+ |      ||
|  |  |  |      kubelet        | |  |  |      kubelet        | |      ||
|  |  |  | (Node agent)        | |  |  |                     | |      ||
|  |  |  +---------------------+ |  |  +---------------------+ |      ||
|  |  |  +---------------------+ |  |  +---------------------+ |      ||
|  |  |  |    kube-proxy       | |  |  |    kube-proxy       | |      ||
|  |  |  | (Network proxy)     | |  |  |                     | |      ||
|  |  |  +---------------------+ |  |  +---------------------+ |      ||
|  |  |  +---------------------+ |  |  +---------------------+ |      ||
|  |  |  | Container Runtime   | |  |  | Container Runtime   | |      ||
|  |  |  | (containerd/CRI-O)  | |  |  |                     | |      ||
|  |  |  +---------------------+ |  |  +---------------------+ |      ||
|  |  |                          |  |                          |      ||
|  |  |  +-----+ +-----+ +-----+|  |  +-----+ +-----+        |      ||
|  |  |  | Pod | | Pod | | Pod ||  |  | Pod | | Pod |        |      ||
|  |  |  +-----+ +-----+ +-----+|  |  +-----+ +-----+        |      ||
|  |  +--------------------------+  +--------------------------+      ||
|  |                                                                    ||
|  +--------------------------------------------------------------------+|
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMMANDS: CLUSTER OVERVIEW

```bash
kubectl cluster-info                     # Cluster endpoints
kubectl get nodes -o wide                # All nodes with details
kubectl get all -A                       # All resources, all namespaces
kubectl get pods -n kube-system          # Control plane pods
```

### KUBERNETES OBJECTS

Everything in Kubernetes is an **Object** (also called Resource).
Objects are persistent entities stored in etcd that represent the cluster state.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS A KUBERNETES OBJECT?                                          |
|                                                                         |
|  * A "record of intent" - you declare what you want                   |
|  * Stored in etcd as JSON/YAML                                        |
|  * Has: apiVersion, kind, metadata, spec, status                      |
|  * Controllers watch objects and make reality match intent            |
|                                                                         |
|  EXAMPLE:                                                              |
|    apiVersion: v1           < API version                             |
|    kind: Pod                < Object type                             |
|    metadata:                                                           |
|      name: nginx            < Object name                             |
|      namespace: default     < Where it lives                          |
|    spec:                    < Desired state (you define)              |
|      containers:                                                       |
|      - name: nginx                                                     |
|        image: nginx:1.21                                              |
|    status:                  < Current state (Kubernetes fills)        |
|      phase: Running                                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MAIN KUBERNETES OBJECTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WORKLOADS - Run your applications                                     |
|  ---------------------------------                                     |
|                                                                         |
|  Pod              Smallest unit, runs 1+ containers                   |
|  Deployment       Manages Pods with rolling updates (most common!)    |
|  ReplicaSet       Ensures N pods are running (used by Deployment)     |
|  StatefulSet      For stateful apps (databases) - stable identity     |
|  DaemonSet        Runs 1 pod per node (logging, monitoring agents)    |
|  Job              Run-to-completion task (batch processing)           |
|  CronJob          Scheduled Jobs (like cron)                          |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  NETWORKING - Expose and connect applications                          |
|  --------------------------------------------                          |
|                                                                         |
|  Service          Stable IP/DNS to access Pods (load balancer)        |
|  Ingress          HTTP/HTTPS routing (like nginx reverse proxy)       |
|  NetworkPolicy    Firewall rules between Pods                         |
|  Endpoints        IP addresses backing a Service                       |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  CONFIGURATION - App settings and secrets                              |
|  ----------------------------------------                              |
|                                                                         |
|  ConfigMap        Store non-sensitive config (env vars, files)        |
|  Secret           Store sensitive data (passwords, tokens, keys)      |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  STORAGE - Persistent data                                             |
|  -------------------------                                             |
|                                                                         |
|  PersistentVolume (PV)        Actual storage (EBS, NFS, etc.)        |
|  PersistentVolumeClaim (PVC)  Request for storage by Pod              |
|  StorageClass                 Template for dynamic provisioning       |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  CLUSTER - Organize and secure                                         |
|  -----------------------------                                         |
|                                                                         |
|  Namespace        Virtual cluster (isolate environments)              |
|  Node             Worker machine (EC2 instance in your case)          |
|  ServiceAccount   Identity for Pods to access API                     |
|  Role/ClusterRole RBAC permissions                                    |
|  RoleBinding      Assign Role to user/ServiceAccount                  |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALING - Auto-adjust resources                                       |
|  -------------------------------                                       |
|                                                                         |
|  HorizontalPodAutoscaler (HPA)  Scale pods based on CPU/memory       |
|  VerticalPodAutoscaler (VPA)    Adjust pod CPU/memory requests       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHICH OBJECT TO USE?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  I want to...                          Use...                          |
|  -------------------------------------------------------------------   |
|                                                                         |
|  Run a web app                         Deployment + Service            |
|  Run a database (MySQL, Postgres)      StatefulSet + Service + PVC     |
|  Run logging agent on every node       DaemonSet                       |
|  Run a one-time batch job              Job                             |
|  Run a scheduled task                  CronJob                         |
|  Store app config                      ConfigMap                       |
|  Store passwords/API keys              Secret                          |
|  Expose app to internet                Service (LoadBalancer) + Ingress|
|  Isolate team environments             Namespace                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMMANDS: LIST ALL OBJECT TYPES

```bash
kubectl api-resources                    # All object types in cluster
kubectl api-resources --namespaced=true  # Only namespaced objects
kubectl explain pod                      # Describe an object type
kubectl explain pod.spec.containers      # Drill into fields
```

### WHAT IS A NAMESPACE?

A Namespace is a virtual cluster inside your physical cluster -
it's a way to isolate and organize resources.

```
+-------------------------------------------------------------------------+
|                         YOUR CLUSTER                                    |
|                                                                         |
|   +---------------+  +---------------+  +---------------+              |
|   | ns: default   |  | ns: kube-sys  |  | ns: prod      |              |
|   |               |  |               |  |               |              |
|   | * test pods   |  | * coredns     |  | * api-svc     |              |
|   |               |  | * kube-proxy  |  | * web-app     |              |
|   |               |  | * aws-node    |  | * payment-svc |              |
|   +---------------+  +---------------+  +---------------+              |
|                                                                         |
|   +---------------+  +---------------+  +---------------+              |
|   | ns: dev       |  | ns: staging   |  | ns: logging   |              |
|   |               |  |               |  |               |              |
|   | * api-svc     |  | * api-svc     |  | * fluentd     |              |
|   | * web-app     |  | * web-app     |  | * kibana      |              |
|   | (dev version) |  | (test version)|  |               |              |
|   +---------------+  +---------------+  +---------------+              |
|                                                                         |
|   Same name "api-svc" can exist in dev, staging, prod - they're       |
|   completely separate resources!                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

WHY USE NAMESPACES?
-------------------
- Environment isolation (dev, staging, prod)
- Team isolation (team-a, team-b)
- Resource quotas per namespace
- Different RBAC permissions per namespace

DEFAULT NAMESPACES:
-------------------
default         > Where resources go if you don't specify
kube-system     > Kubernetes system components
kube-public     > Publicly readable (rarely used)
kube-node-lease > Node heartbeats

NOT NAMESPACED (Cluster-wide):
------------------------------
Nodes, PersistentVolumes, Namespaces, ClusterRoles, StorageClasses

### COMMANDS: NAMESPACES

```bash
kubectl get namespaces               # List all
kubectl get ns                       # Short form

kubectl get pods -n kube-system      # Pods in specific namespace
kubectl get pods -A                  # ALL namespaces

kubectl create namespace dev         # Create namespace

# Set default namespace
kubectl config set-context --current --namespace=prod
```

## SECTION 1.2: CONTROL PLANE COMPONENTS

### API SERVER (kube-apiserver)

The API server is the front door to Kubernetes:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  API SERVER RESPONSIBILITIES                                           |
|                                                                         |
|  WHAT IT DOES:                                                         |
|  * Exposes the Kubernetes API (REST)                                  |
|  * Front-end to the control plane                                     |
|  * All components communicate through it                              |
|  * Only component that talks to etcd                                  |
|                                                                         |
|  PROCESS:                                                              |
|                                                                         |
|  kubectl apply -f pod.yaml                                            |
|         |                                                              |
|         v                                                              |
|  +-----------------------------------------------------------------+  |
|  |                      API SERVER                                  |  |
|  |                                                                  |  |
|  |  1. AUTHENTICATION                                              |  |
|  |     Who are you? (certificates, tokens, etc.)                  |  |
|  |                          v                                      |  |
|  |  2. AUTHORIZATION                                               |  |
|  |     Can you do this? (RBAC)                                    |  |
|  |                          v                                      |  |
|  |  3. ADMISSION CONTROL                                           |  |
|  |     Should we allow this? (mutating & validating webhooks)     |  |
|  |                          v                                      |  |
|  |  4. VALIDATION                                                  |  |
|  |     Is the request valid?                                      |  |
|  |                          v                                      |  |
|  |  5. PERSIST TO ETCD                                             |  |
|  |     Store the desired state                                    |  |
|  |                                                                  |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  API SERVER IS STATELESS                                               |
|  * Can run multiple instances for HA                                  |
|  * State stored in etcd                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMMANDS: API SERVER

```bash
kubectl auth whoami                      # Check current user
kubectl auth can-i create pods           # Check permission
kubectl api-resources                    # List all resource types
```

ETCD
----

etcd is the cluster's database:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ETCD - THE SOURCE OF TRUTH                                            |
|                                                                         |
|  WHAT IS ETCD?                                                         |
|  * Distributed key-value store                                        |
|  * Stores ALL cluster state                                           |
|  * Uses Raft consensus algorithm                                      |
|  * Highly available (odd number of nodes: 3, 5, 7)                   |
|                                                                         |
|  WHAT IT STORES:                                                       |
|  * Cluster configuration                                              |
|  * Resource definitions (Pods, Services, etc.)                       |
|  * Secrets and ConfigMaps                                             |
|  * Resource status                                                    |
|  * RBAC policies                                                      |
|                                                                         |
|  KEY-VALUE STRUCTURE:                                                  |
|                                                                         |
|  /registry/                                                           |
|  +-- pods/                                                            |
|  |   +-- default/                                                     |
|  |   |   +-- nginx-pod                                               |
|  |   |   +-- api-pod                                                 |
|  |   +-- kube-system/                                                |
|  |       +-- coredns-xxx                                             |
|  +-- services/                                                        |
|  |   +-- default/                                                     |
|  |       +-- my-service                                              |
|  +-- secrets/                                                         |
|      +-- default/                                                     |
|          +-- my-secret                                               |
|                                                                         |
|  CRITICAL:                                                             |
|  * Backup etcd regularly!                                             |
|  * If etcd is lost, cluster state is lost                            |
|  * etcd is the ONLY stateful component                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMMANDS: ETCD BACKUP (Important!)

```bash
# Backup etcd (run with proper certs)
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key
```

### HOW COMPONENTS COMMUNICATE (Watch Mechanism)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IMPORTANT: etcd does NOT push updates to API Server!                  |
|                                                                         |
|  * API Server is the ONLY component that talks to etcd                |
|  * Controllers WATCH the API Server (not etcd directly)               |
|  * etcd is just a database - it stores data, doesn't push             |
|  * API Server notifies watchers when data changes                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
DATA FLOW:
----------

+-------------------------------------------------------------------------+
|                                                                         |
|    Controllers              API Server                etcd             |
|    (watch)                  (gateway)                 (database)       |
|                                                                         |
|        |                        |                        |             |
|        |  1. "Watch for         |                        |             |
|        |      changes"          |                        |             |
|        |----------------------->|                        |             |
|        |                        |                        |             |
|        |                        |  2. Read/Write         |             |
|        |                        |<---------------------->|             |
|        |                        |                        |             |
|        |  3. "Here's an         |                        |             |
|        |      update!"          |                        |             |
|        |<-----------------------|                        |             |
|        |                        |                        |             |
|                                                                         |
+-------------------------------------------------------------------------+
```

WATCH = Long-lived connection waiting for updates:
--------------------------------------------------

Deployment Controller:
> "API Server, tell me when a Deployment changes"

ReplicaSet Controller:
> "API Server, tell me when a ReplicaSet changes"

Scheduler:
> "API Server, tell me when an unscheduled Pod appears"

kubelet:
> "API Server, tell me when a Pod is assigned to my node"

```bash
EXAMPLE: Creating a Deployment
-------------------------------

kubectl create deployment nginx --replicas=3

Step 1: kubectl ------> API Server ------> etcd
               "create"            "store Deployment"

Step 2: API Server ------> Deployment Controller
                   "new Deployment created!"
        (Deployment Controller was watching for Deployment changes)

Step 3: Deployment Controller ------> API Server ------> etcd
                              "create ReplicaSet"   "store"

Step 4: API Server ------> ReplicaSet Controller
                   "new ReplicaSet created!"

...and so on (ReplicaSet creates Pods, Scheduler assigns nodes, etc.)
```

### SCHEDULER (kube-scheduler)

The scheduler decides where pods run:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCHEDULER WORKFLOW                                                    |
|                                                                         |
|  New pod created (unscheduled)                                        |
|         |                                                              |
|         v                                                              |
|  +-----------------------------------------------------------------+  |
|  |                      SCHEDULER                                   |  |
|  |                                                                  |  |
|  |  1. FILTERING                                                   |  |
|  |     Which nodes CAN run this pod?                              |  |
|  |     * Has enough CPU/memory?                                   |  |
|  |     * Matches nodeSelector?                                    |  |
|  |     * Tolerates taints?                                        |  |
|  |     * Has required ports available?                            |  |
|  |                                                                  |  |
|  |     Nodes: [A, B, C, D] > Filtered: [A, B, D]                 |  |
|  |                                                                  |  |
|  |  2. SCORING                                                     |  |
|  |     Rank the filtered nodes                                    |  |
|  |     * Balance resource usage                                   |  |
|  |     * Image locality (already has image?)                     |  |
|  |     * Inter-pod affinity/anti-affinity                        |  |
|  |     * Custom priorities                                        |  |
|  |                                                                  |  |
|  |     Scores: A=85, B=70, D=90 > Best: D                        |  |
|  |                                                                  |  |
|  |  3. BINDING                                                     |  |
|  |     Assign pod to node D                                       |  |
|  |     Write binding to API server                                |  |
|  |                                                                  |  |
|  +-----------------------------------------------------------------+  |
|         |                                                              |
|         v                                                              |
|  kubelet on Node D receives pod spec and starts containers            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMMANDS: SCHEDULING

```bash
# Check why pod is pending
kubectl describe pod <pod-name>          # Look at Events section
kubectl get events --field-selector reason=FailedScheduling

# View node resources
kubectl top nodes                        # Resource usage
```

### SCHEDULING CONSTRAINTS (nodeSelector & Taints/Tolerations)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  nodeSelector - "I WANT to run on THIS type of node"                   |
|  -----------------------------------------------------                 |
|  * Simple label-based constraint on Pod                                |
|  * Pod only runs on nodes matching the label                          |
|                                                                         |
|  Example:                                                               |
|    kubectl label node worker-1 disktype=ssd                           |
|                                                                         |
|    spec:                                                                |
|      nodeSelector:                                                      |
|        disktype: ssd    # Only run on SSD nodes                       |
|                                                                         |
|  Use cases: GPU nodes, SSD storage, specific regions                  |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  Taints & Tolerations - "Stay AWAY unless you tolerate me"            |
|  ---------------------------------------------------------             |
|  * Taint = applied to NODE (repels pods)                              |
|  * Toleration = applied to POD (allows scheduling on tainted node)    |
|                                                                         |
|  Taint a node:                                                          |
|    kubectl taint nodes node-1 dedicated=gpu:NoSchedule                |
|                                                                         |
|  Pod tolerates it:                                                      |
|    spec:                                                                |
|      tolerations:                                                       |
|        - key: "dedicated"                                               |
|          value: "gpu"                                                   |
|          effect: "NoSchedule"                                           |
|                                                                         |
|  Taint Effects:                                                         |
|    NoSchedule       > Won't schedule new pods                          |
|    PreferNoSchedule > Soft rule, avoid if possible                     |
|    NoExecute        > Evict existing pods + prevent new               |
|                                                                         |
|  Use cases: GPU-only nodes, master nodes, maintenance draining        |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  SUMMARY:                                                               |
|    nodeSelector = Pod says "I want X"      (PULL)                      |
|    Taint        = Node says "Go away"      (PUSH)                      |
|    Toleration   = Pod says "I don't mind"  (OVERRIDE)                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMMANDS: NODE LABELS & TAINTS

```bash
# Labels
kubectl get nodes --show-labels
kubectl label node <node> disktype=ssd
kubectl label node <node> disktype-              # Remove label

# Taints
kubectl taint nodes <node> key=value:NoSchedule
kubectl taint nodes <node> key=value:NoSchedule- # Remove taint

# Maintenance
kubectl cordon <node>                    # Mark unschedulable
kubectl drain <node> --ignore-daemonsets # Evict pods
kubectl uncordon <node>                  # Make schedulable
```

### CONTROLLER MANAGER (kube-controller-manager)

Controllers maintain the desired state:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONTROLLER MANAGER                                                     |
|                                                                         |
|  A controller is a control loop that:                                  |
|  1. Watches current state                                              |
|  2. Compares to desired state                                          |
|  3. Takes action to reconcile                                          |
|                                                                        |  
|                     +-----------------+                                |
|                     |  Desired State  |                                |
|                     |  (etcd)         |                                |
|                     +--------+--------+                                |
|                              |                                         |
|                     +--------v--------+                                |
|                     |   Controller    |                                |
|                     |   (reconcile)   |                                |
|                     +--------+--------+                                |
|                              |                                         |
|                     +--------v--------+                                |
|                     |  Current State  |                                |
|                     |  (cluster)      |                                |
|                     +-----------------+                                |
|                                                                         |
|  BUILT-IN CONTROLLERS:                                                 |
|                                                                         |
|  Node Controller                                                       |
|  * Monitors node health                                               |
|  * Evicts pods from unhealthy nodes                                  |
|                                                                         |
|  Replication Controller                                                |
|  * Ensures correct number of pod replicas                            |
|                                                                         |
|  Endpoints Controller                                                  |
|  * Populates Endpoints objects                                       |
|  * Links Services to Pods                                            |
|                                                                         |
|  Service Account Controller                                            |
|  * Creates default service accounts                                   |
|                                                                         |
|  Deployment Controller                                                 |
|  * Manages ReplicaSets for Deployments                               |
|                                                                         |
|  And many more...                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHAT IS A DEPLOYMENT?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DEPLOYMENT - The Most Common Way to Run Apps                          |
|                                                                         |
|  A Deployment manages:                                                 |
|  * How many replicas of your app should run                           |
|  * Which container image to use                                       |
|  * Rolling updates and rollbacks                                      |
|  * Self-healing (restarts failed pods)                                |
|                                                                         |
|  HIERARCHY:                                                            |
|                                                                         |
|    Deployment                                                          |
|        |                                                               |
|        | creates & manages                                             |
|        v                                                               |
|    ReplicaSet                                                          |
|        |                                                               |
|        | creates & manages                                             |
|        v                                                               |
|    Pods (your containers)                                             |
|                                                                         |
|  WHY NOT CREATE PODS DIRECTLY?                                        |
|  -----------------------------                                         |
|  * Pod dies > stays dead (no restart)                                 |
|  * No scaling                                                          |
|  * No rolling updates                                                  |
|                                                                         |
|  WHY NOT USE REPLICASET DIRECTLY?                                     |
|  --------------------------------                                      |
|  * No rolling updates (all-or-nothing)                                |
|  * No rollback capability                                             |
|  * No update history                                                  |
|                                                                         |
|  DEPLOYMENT GIVES YOU:                                                 |
|  ---------------------                                                 |
|  Y Declarative updates                                                |
|  Y Rolling updates (zero downtime)                                   |
|  Y Rollback to previous version                                      |
|  Y Scaling up/down                                                   |
|  Y Pause/resume deployments                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

```yaml
DEPLOYMENT EXAMPLE:
-------------------

apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3                    # Run 3 pods
  selector:
    matchLabels:
      app: nginx                 # Manage pods with this label
  template:                      # Pod template
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
```

```
HOW ROLLING UPDATE WORKS:
-------------------------

+-------------------------------------------------------------------------+
|                                                                         |
|  kubectl set image deployment/nginx nginx=nginx:1.22                   |
|                                                                         |
|  STEP 1: New ReplicaSet created (v2)                                   |
|                                                                         |
|    ReplicaSet v1: [Pod] [Pod] [Pod]     < running nginx:1.21          |
|    ReplicaSet v2: (empty)                < new, nginx:1.22             |
|                                                                         |
|  STEP 2: Gradually scale up v2, scale down v1                         |
|                                                                         |
|    ReplicaSet v1: [Pod] [Pod]            < 2 pods                      |
|    ReplicaSet v2: [Pod]                  < 1 pod                       |
|                                                                         |
|  STEP 3: Continue until complete                                       |
|                                                                         |
|    ReplicaSet v1: (empty)                < scaled to 0                 |
|    ReplicaSet v2: [Pod] [Pod] [Pod]     < all traffic here            |
|                                                                         |
|  ROLLBACK: kubectl rollout undo deployment/nginx                       |
|    > Scales v1 back up, v2 back down                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMMANDS: DEPLOYMENTS

```bash
# Create deployment
kubectl create deployment nginx --image=nginx --replicas=3

# View deployment and its children
kubectl get deploy,rs,pods               # See hierarchy
kubectl describe deployment nginx

# Scale
kubectl scale deployment nginx --replicas=5

# Update image (triggers rolling update)
kubectl set image deployment/nginx nginx=nginx:1.22

# Watch rollout
kubectl rollout status deployment/nginx

# Rollout history
kubectl rollout history deployment/nginx

# Rollback
kubectl rollout undo deployment/nginx
kubectl rollout undo deployment/nginx --to-revision=2
```

## SECTION 1.3: WORKER NODE COMPONENTS

KUBELET
-------

kubelet is the node agent:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KUBELET                                                               |
|                                                                         |
|  RESPONSIBILITIES:                                                     |
|  * Registers node with cluster                                        |
|  * Watches API server for pod assignments                            |
|  * Manages pod lifecycle                                              |
|  * Reports node and pod status                                        |
|  * Runs liveness/readiness probes                                     |
|                                                                         |
|  WORKFLOW:                                                              |
|                                                                         |
|  API Server                                                             |
|       |                                                                 |
|       | "Run pod X on this node"                                        |
|       v                                                                 |
|  +-----------------------------------------------------------------+    |
|  |                        KUBELET                                   |   |
|  |                                                                  |   |
|  |  1. Receives PodSpec                                            |    |
|  |  2. Tells container runtime to pull images                     |     |
|  |  3. Tells container runtime to start containers                |     |
|  |  4. Sets up volumes                                            |     |
|  |  5. Sets up networking (via CNI)                               |     |
|  |  6. Monitors containers                                        |     |
|  |  7. Reports status to API server                               |     |
|  |                                                                  |   |
|  +-----------------------------------------------------------------+    |
|       |                                                                 |
|       | CRI (Container Runtime Interface)                               |
|       v                                                                 |
|  +-----------------------------------------------------------------+    |
|  |               Container Runtime                                  |   |
|  |         (containerd, CRI-O, Docker)                             |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMMANDS: NODES & KUBELET

```bash
kubectl get nodes -o wide                # Node info + container runtime
kubectl describe node <node>             # Capacity, allocatable, pods
kubectl top nodes                        # Resource usage

# View pods on specific node
kubectl get pods -A --field-selector spec.nodeName=<node>

# Kubelet logs (on node via SSH)
journalctl -u kubelet -f
```

### KUBE-PROXY

kube-proxy implements Services:

(See Kubernetes-Networking/03-Services-And-Kube-Proxy.txt for details)

- Programs iptables or IPVS rules
- Enables Service virtual IPs
- Load balances traffic to pods

### COMMANDS: KUBE-PROXY

```bash
kubectl get pods -n kube-system -l k8s-app=kube-proxy
kubectl logs <kube-proxy-pod> -n kube-system
```

### CONTAINER RUNTIME

The container runtime runs containers:

- containerd (most common)
- CRI-O
- Docker (deprecated as runtime, uses containerd anyway)

## SECTION 1.4: HOW IT ALL WORKS TOGETHER

### CREATING A DEPLOYMENT - END TO END

```
kubectl create deployment nginx --image=nginx --replicas=3

+-------------------------------------------------------------------------+
|                                                                         |
|  STEP 1: kubectl > API Server                                         |
|  -----------------------------                                         |
|  * kubectl sends Deployment spec to API server                        |
|  * API server authenticates, authorizes, validates                   |
|  * Stores Deployment in etcd                                         |
|                                                                         |
|  STEP 2: Deployment Controller                                        |
|  -----------------------------                                         |
|  * Watches API server, sees new Deployment                           |
|  * Creates ReplicaSet object                                         |
|  * Stores ReplicaSet in etcd                                         |
|                                                                         |
|  STEP 3: ReplicaSet Controller                                        |
|  ------------------------------                                        |
|  * Watches API server, sees new ReplicaSet                           |
|  * Sees 0 pods exist, 3 desired                                      |
|  * Creates 3 Pod objects (unscheduled)                               |
|  * Stores Pods in etcd                                               |
|                                                                         |
|  STEP 4: Scheduler                                                     |
|  --------------------                                                  |
|  * Watches API server, sees 3 unscheduled Pods                       |
|  * Filters and scores nodes                                          |
|  * Binds each Pod to a node                                          |
|  * Updates Pod with node assignment                                  |
|                                                                         |
|  STEP 5: kubelet (on each assigned node)                              |
|  ---------------------------------------                               |
|  * Watches API server, sees Pod assigned to this node               |
|  * Tells container runtime to pull nginx image                       |
|  * Tells container runtime to start container                        |
|  * Sets up networking and volumes                                    |
|  * Reports Pod status to API server                                  |
|                                                                         |
|  STEP 6: Endpoint Controller                                          |
|  ----------------------------                                          |
|  * Sees Pods are running                                             |
|  * Updates Endpoints object for Service                              |
|                                                                         |
|  RESULT: 3 nginx pods running, accessible via Service                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMMANDS: TRACE THE FLOW

```bash
# Create and watch
kubectl create deployment nginx --image=nginx --replicas=3
kubectl get deploy,rs,pods -w            # Watch resources being created

# See events (shows full flow)
kubectl get events --sort-by='.lastTimestamp'
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KUBERNETES ARCHITECTURE - KEY TAKEAWAYS                               |
|                                                                         |
|  CONTROL PLANE                                                         |
|  -------------                                                         |
|  * API Server: REST API, authentication, authorization                |
|  * etcd: Cluster state database                                       |
|  * Scheduler: Decides where pods run                                  |
|  * Controller Manager: Maintains desired state                        |
|                                                                         |
|  WORKER NODES                                                          |
|  ------------                                                          |
|  * kubelet: Node agent, manages pods                                  |
|  * kube-proxy: Network proxy, implements Services                    |
|  * Container Runtime: Runs containers                                 |
|                                                                         |
|  KEY CONCEPTS                                                          |
|  ------------                                                          |
|  * Declarative: You declare desired state                            |
|  * Controllers: Watch and reconcile                                  |
|  * API-centric: Everything goes through API server                   |
|  * etcd is the only stateful component                               |
|                                                                         |
|  MOST USED COMMANDS                                                    |
|  ------------------                                                    |
|  kubectl cluster-info                  # Cluster info                 |
|  kubectl get nodes -o wide             # Node status                  |
|  kubectl get pods -n kube-system       # System pods                  |
|  kubectl describe pod <name>           # Debug pod                    |
|  kubectl logs <pod>                    # View logs                    |
|  kubectl get events                    # Recent events                |
|  kubectl top nodes                     # Resource usage               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 1

