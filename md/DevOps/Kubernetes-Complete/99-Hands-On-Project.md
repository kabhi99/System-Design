# KUBERNETES HANDS-ON PROJECT
*Learn All Topics with One Complete Project*

This project builds a simple "Task Manager" application with multiple
microservices. By completing it, you'll learn ALL core Kubernetes concepts.

## COMPLETE ARCHITECTURE DIAGRAM

```
+-------------------------------------------------------------------------+
|                                                                         |
|                         FINAL ARCHITECTURE                              |
|                    (What you'll build by the end)                       |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                        INTERNET                                    | |
|  +-------------------------------+-----------------------------------+ |
|                                  |                                      |
|                                  v                                      |
|  +-------------------------------------------------------------------+ |
|  |                    INGRESS CONTROLLER                              | |
|  |            taskmanager.local (Step 9)                             | |
|  |                                                                    | |
|  |     /  ------------------>  frontend-service                      | |
|  |     /api ---------------->  backend-service                       | |
|  +-------------------------------------------------------------------+ |
|                     |                        |                          |
|                     v                        v                          |
|  +-------------------------+  +-------------------------------------+ |
|  |                         |  |                                      | |
|  |   FRONTEND SERVICE      |  |     BACKEND SERVICE                  | |
|  |   (NodePort :30080)     |  |     (ClusterIP)                      | |
|  |        Step 8           |  |         Step 7                       | |
|  |                         |  |                                      | |
|  |   +-----------------+   |  |   +-----------------+               | |
|  |   |   Deployment    |   |  |   |   Deployment    |<-- HPA        | |
|  |   |   replicas: 2   |   |  |   |   replicas: 2   |   (Step 10)   | |
|  |   |                 |   |  |   |                 |               | |
|  |   |  +-----++-----+ |   |  |   |  +-----++-----+ |               | |
|  |   |  |nginx||nginx| |   |  |   |  | api || api | |               | |
|  |   |  | pod || pod | |   |  |   |  | pod || pod | |               | |
|  |   |  +-----++-----+ |   |  |   |  +-----++-----+ |               | |
|  |   +-----------------+   |  |   +--------+--------+               | |
|  |                         |  |            |                         | |
|  +-------------------------+  +------------+-------------------------+ |
|                                            |                            |
|               +----------------------------+------------------------+  |
|               |                            |                        |  |
|               v                            v                        |  |
|  +-------------------------+  +-------------------------+          |  |
|  |                         |  |                         |          |  |
|  |    REDIS SERVICE        |  |   POSTGRES SERVICE      |          |  |
|  |    (ClusterIP)          |  |   (Headless)            |          |  |
|  |       Step 6            |  |      Step 5             |          |  |
|  |                         |  |                         |          |  |
|  |   +-----------------+   |  |   +-----------------+   |          |  |
|  |   |   Deployment    |   |  |   |  StatefulSet    |   |          |  |
|  |   |                 |   |  |   |                 |   |          |  |
|  |   |    +-------+    |   |  |   |    +-------+    |   |          |  |
|  |   |    | redis |    |   |  |   |    |  pg   |    |   |          |  |
|  |   |    |  pod  |    |   |  |   |    |  pod  |    |   |          |  |
|  |   |    +---+---+    |   |  |   |    +---+---+    |   |          |  |
|  |   +--------+--------+   |  |   +--------+--------+   |          |  |
|  |            |            |  |            |            |          |  |
|  |       +----v----+       |  |       +----v----+       |          |  |
|  |       |   PVC   |       |  |       |   PVC   |       |          |  |
|  |       | 500Mi   |       |  |       |   1Gi   |       |          |  |
|  |       +---------+       |  |       +---------+       |          |  |
|  |         Step 4          |  |         Step 4          |          |  |
|  +-------------------------+  +-------------------------+          |  |
|                                                                     |  |
|  +--------------------------------------------------------------+  |  |
|  |                                                               |  |  |
|  |   CRONJOB: cleanup-job (Step 11)                             |  |  |
|  |   Schedule: */5 * * * *                                      |  |  |
|  |                                                               |  |  |
|  |   +---------+                                                |  |  |
|  |   |  Job    |---> Runs every 5 minutes                       |  |  |
|  |   +---------+                                                |  |  |
|  |                                                               |  |  |
|  +--------------------------------------------------------------+  |  |
|                                                                     |  |
|  +--------------------------------------------------------------+  |  |
|  |                       SHARED RESOURCES                        |  |  |
|  |                                                               |  |  |
|  |  ConfigMap (Step 2)     Secret (Step 3)      RBAC (Step 12)  |  |  |
|  |  +-------------+       +-------------+      +-------------+  |  |  |
|  |  | app-config  |       |db-credentials|      | backend-sa  |  |  |  |
|  |  | * APP_NAME  |       |* DB_USER    |      | backend-role|  |  |  |
|  |  | * LOG_LEVEL |       |* DB_PASSWORD|      |             |  |  |  |
|  |  | * nginx.conf|       |             |      |             |  |  |  |
|  |  +-------------+       +-------------+      +-------------+  |  |  |
|  |                                                               |  |  |
|  +--------------------------------------------------------------+  |  |
|                                                                         |
|  ALL IN NAMESPACE: task-manager (Step 1)                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## STEP-BY-STEP PROGRESS DIAGRAMS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STEP 0-1: Setup & Namespace                                           |
|  ---------------------------                                           |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                    MINIKUBE CLUSTER                              |   |
|  |                                                                  |   |
|  |    +------------------------------------------------------+    |   |
|  |    |           Namespace: task-manager                     |    |   |
|  |    |                                                       |    |   |
|  |    |                    (empty)                            |    |   |
|  |    |                                                       |    |   |
|  |    +------------------------------------------------------+    |   |
|  |                                                                  |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  STEP 2-3: ConfigMaps & Secrets                                        |
|  ------------------------------                                        |
|                                                                         |
|    Namespace: task-manager                                             |
|    +-------------------------------------------------------------+    |
|    |                                                              |    |
|    |   +--------------+          +--------------+                |    |
|    |   |  ConfigMap   |          |    Secret    |                |    |
|    |   |  app-config  |          |db-credentials|                |    |
|    |   |              |          |              |                |    |
|    |   | APP_NAME     |          | DB_USER ●●●● |                |    |
|    |   | LOG_LEVEL    |          | DB_PASS ●●●● |                |    |
|    |   | nginx.conf   |          |              |                |    |
|    |   +--------------+          +--------------+                |    |
|    |                                                              |    |
|    |   These will be mounted into pods later                     |    |
|    |                                                              |    |
|    +-------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  STEP 4: Persistent Storage                                            |
|  --------------------------                                            |
|                                                                         |
|    Namespace: task-manager                                             |
|    +-------------------------------------------------------------+    |
|    |                                                              |    |
|    |   +--------------------+    +--------------------+          |    |
|    |   |        PVC         |    |        PVC         |          |    |
|    |   |    postgres-pvc    |    |     redis-pvc      |          |    |
|    |   |      1Gi           |    |      500Mi         |          |    |
|    |   |                    |    |                    |          |    |
|    |   |    +----------+    |    |    +----------+    |          |    |
|    |   |    |    PV    |    |    |    |    PV    |    |          |    |
|    |   |    | (auto)   |    |    |    | (auto)   |    |          |    |
|    |   |    +----------+    |    |    +----------+    |          |    |
|    |   +--------------------+    +--------------------+          |    |
|    |                                                              |    |
|    |   PV created automatically by minikube storage-provisioner  |    |
|    |                                                              |    |
|    +-------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  STEP 5: PostgreSQL (StatefulSet)                                      |
|  --------------------------------                                      |
|                                                                         |
|    Namespace: task-manager                                             |
|    +-------------------------------------------------------------+    |
|    |                                                              |    |
|    |        +------------------------------------------+         |    |
|    |        |         Service: postgres                |         |    |
|    |        |         (Headless - clusterIP: None)     |         |    |
|    |        |         DNS: postgres.task-manager       |         |    |
|    |        +---------------------+--------------------+         |    |
|    |                              |                               |    |
|    |                              v                               |    |
|    |        +------------------------------------------+         |    |
|    |        |          StatefulSet: postgres           |         |    |
|    |        |                                          |         |    |
|    |        |    +---------------------------------+   |         |    |
|    |        |    |         Pod: postgres-0         |   |         |    |
|    |        |    |                                 |   |         |    |
|    |        |    |  +----------------------------+ |   |         |    |
|    |        |    |  |   Container: postgres      | |   |         |    |
|    |        |    |  |   Image: postgres:15       | |   |         |    |
|    |        |    |  |   Port: 5432               | |   |         |    |
|    |        |    |  |                            | |   |         |    |
|    |        |    |  |   env: from Secret --------+-+---+-> db-credentials
|    |        |    |  |   volume: postgres-pvc ----+-+---+-> PVC
|    |        |    |  |                            | |   |         |    |
|    |        |    |  |   [x] Liveness Probe         | |   |         |    |
|    |        |    |  |   [x] Readiness Probe        | |   |         |    |
|    |        |    |  +----------------------------+ |   |         |    |
|    |        |    +---------------------------------+   |         |    |
|    |        +------------------------------------------+         |    |
|    |                                                              |    |
|    +-------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  STEP 6: Redis (Deployment)                                            |
|  --------------------------                                            |
|                                                                         |
|    +--------------------------------------------------------------+    |
|    |         Service: redis                                        |    |
|    |         (ClusterIP - internal only)                           |    |
|    |         DNS: redis.task-manager                               |    |
|    +---------------------------+----------------------------------+    |
|                                |                                        |
|                                v                                        |
|    +--------------------------------------------------------------+    |
|    |              Deployment: redis                                |    |
|    |                                                               |    |
|    |    +---------------------------------------------------+     |    |
|    |    |              ReplicaSet                            |     |    |
|    |    |                                                    |     |    |
|    |    |    +-----------------------------------------+    |     |    |
|    |    |    |            Pod: redis-xxx               |    |     |    |
|    |    |    |                                         |    |     |    |
|    |    |    |   Container: redis                      |    |     |    |
|    |    |    |   Image: redis:7-alpine                 |    |     |    |
|    |    |    |   Port: 6379                            |    |     |    |
|    |    |    |   env: REDIS_PASSWORD from Secret       |    |     |    |
|    |    |    |   volume: redis-pvc                     |    |     |    |
|    |    |    |                                         |    |     |    |
|    |    |    +-----------------------------------------+    |     |    |
|    |    +---------------------------------------------------+     |    |
|    +--------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  STEP 7: Backend API (Deployment with 2 replicas)                      |
|  ------------------------------------------------                      |
|                                                                         |
|    +--------------------------------------------------------------+    |
|    |         Service: backend-service                              |    |
|    |         (ClusterIP)                                           |    |
|    |         Port: 5000                                            |    |
|    +---------------------------+----------------------------------+    |
|                                |                                        |
|                    +-----------+-----------+                           |
|                    |                       |                            |
|                    v                       v                            |
|    +--------------------------------------------------------------+    |
|    |              Deployment: backend (replicas: 2)                |    |
|    |                                                               |    |
|    |   +---------------------+    +---------------------+         |    |
|    |   |  Pod: backend-xxx   |    |  Pod: backend-yyy   |         |    |
|    |   |                     |    |                     |         |    |
|    |   |  Port: 5000         |    |  Port: 5000         |         |    |
|    |   |                     |    |                     |         |    |
|    |   |  env:               |    |  env:               |         |    |
|    |   |  +- ConfigMap ------+----+---> app-config      |         |    |
|    |   |  +- Secret ---------+----+---> db-credentials  |         |    |
|    |   |  +- Secret ---------+----+---> redis-creds     |         |    |
|    |   |                     |    |                     |         |    |
|    |   |  ServiceAccount:    |    |  ServiceAccount:    |         |    |
|    |   |  backend-sa --------+----+---> RBAC            |         |    |
|    |   |                     |    |                     |         |    |
|    |   +---------------------+    +---------------------+         |    |
|    |                                                               |    |
|    |   Connects to: postgres:5432, redis:6379                     |    |
|    |                                                               |    |
|    +--------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  STEP 8: Frontend (Deployment + NodePort)                              |
|  ----------------------------------------                              |
|                                                                         |
|                          EXTERNAL ACCESS                                |
|                               |                                         |
|                               | http://minikube-ip:30080                |
|                               v                                         |
|    +--------------------------------------------------------------+    |
|    |         Service: frontend-service                             |    |
|    |         Type: NodePort                                        |    |
|    |         Port: 80 -> NodePort: 30080                           |    |
|    +---------------------------+----------------------------------+    |
|                                |                                        |
|                    +-----------+-----------+                           |
|                    v                       v                            |
|    +--------------------------------------------------------------+    |
|    |              Deployment: frontend (replicas: 2)               |    |
|    |                                                               |    |
|    |   +---------------------+    +---------------------+         |    |
|    |   |  Pod: frontend-xxx  |    |  Pod: frontend-yyy  |         |    |
|    |   |                     |    |                     |         |    |
|    |   |  nginx container    |    |  nginx container    |         |    |
|    |   |  Port: 80           |    |  Port: 80           |         |    |
|    |   |                     |    |                     |         |    |
|    |   |  ConfigMap mounted: |    |  ConfigMap mounted: |         |    |
|    |   |  nginx.conf --------+----+---> /etc/nginx/...  |         |    |
|    |   |                     |    |                     |         |    |
|    |   +---------------------+    +---------------------+         |    |
|    |                                                               |    |
|    |   nginx.conf proxies /api to backend-service:5000            |    |
|    |                                                               |    |
|    +--------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  STEP 9: Ingress (HTTP Routing)                                        |
|  ------------------------------                                        |
|                                                                         |
|                          INTERNET                                       |
|                              |                                          |
|                              | http://taskmanager.local                 |
|                              v                                          |
|    +--------------------------------------------------------------+    |
|    |                    INGRESS CONTROLLER                         |    |
|    |                    (nginx-ingress)                            |    |
|    |                                                               |    |
|    |    Rules:                                                     |    |
|    |    +-----------------------------------------------------+   |    |
|    |    |  Host: taskmanager.local                            |   |    |
|    |    |                                                      |   |    |
|    |    |  /      ------------>  frontend-service:80          |   |    |
|    |    |  /api   ------------>  backend-service:5000         |   |    |
|    |    |                                                      |   |    |
|    |    +-----------------------------------------------------+   |    |
|    |                                                               |    |
|    +--------------------------------------------------------------+    |
|                     |                        |                          |
|                     v                        v                          |
|              frontend-service          backend-service                  |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  STEP 10: HPA (Autoscaling)                                            |
|  --------------------------                                            |
|                                                                         |
|    +--------------------------------------------------------------+    |
|    |                                                               |    |
|    |     HorizontalPodAutoscaler: backend-hpa                     |    |
|    |                                                               |    |
|    |     Target: Deployment/backend                               |    |
|    |     Min Replicas: 2                                          |    |
|    |     Max Replicas: 10                                         |    |
|    |                                                               |    |
|    |     Scale when:                                              |    |
|    |     * CPU > 50%                                              |    |
|    |     * Memory > 70%                                           |    |
|    |                                                               |    |
|    |                      +-----------+                           |    |
|    |                      |    HPA    |                           |    |
|    |                      |  watches  |                           |    |
|    |                      +-----+-----+                           |    |
|    |                            |                                 |    |
|    |                            v                                 |    |
|    |     Low Load          Normal           High Load             |    |
|    |     +-----+          +-----++-----+   +-----++-----+...     |    |
|    |     | pod |    ->     | pod || pod | -> | pod || pod |        |    |
|    |     +-----+          +-----++-----+   +-----++-----+        |    |
|    |     1 replica        2 replicas       up to 10 replicas     |    |
|    |                                                               |    |
|    +--------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  STEP 11: CronJob (Scheduled Tasks)                                    |
|  ----------------------------------                                    |
|                                                                         |
|    +--------------------------------------------------------------+    |
|    |                                                               |    |
|    |     CronJob: cleanup-job                                     |    |
|    |     Schedule: */5 * * * * (every 5 minutes)                  |    |
|    |                                                               |    |
|    |     Timeline:                                                |    |
|    |     ----------------------------------------------------     |    |
|    |                                                               |    |
|    |     :00        :05        :10        :15        :20          |    |
|    |      |          |          |          |          |           |    |
|    |      v          v          v          v          v           |    |
|    |     Job        Job        Job        Job        Job          |    |
|    |   +-----+    +-----+    +-----+    +-----+    +-----+       |    |
|    |   | pod |    | pod |    | pod |    | pod |    | pod |       |    |
|    |   |runs |    |runs |    |runs |    |runs |    |runs |       |    |
|    |   +--+--+    +--+--+    +--+--+    +--+--+    +--+--+       |    |
|    |      |          |          |          |          |           |    |
|    |      v          v          v          v          v           |    |
|    |   Complete   Complete   Complete   Complete   Complete       |    |
|    |                                                               |    |
|    +--------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  STEP 12: RBAC (Security)                                              |
|  ------------------------                                              |
|                                                                         |
|    +--------------------------------------------------------------+    |
|    |                                                               |    |
|    |     ServiceAccount          Role              RoleBinding    |    |
|    |     +--------------+    +--------------+    +------------+  |    |
|    |     |  backend-sa  |    | backend-role |    |  binding   |  |    |
|    |     |              |    |              |    |            |  |    |
|    |     |  Used by:    |    | Permissions: |    | Connects:  |  |    |
|    |     |  backend     |<---+ * get pods   |<---+ SA ↔ Role  |  |    |
|    |     |  pods        |    | * get secrets|    |            |  |    |
|    |     |              |    | * get configs|    |            |  |    |
|    |     +--------------+    +--------------+    +------------+  |    |
|    |                                                               |    |
|    |     Pod tries to access Kubernetes API:                      |    |
|    |                                                               |    |
|    |     Pod --> "Can I get secrets?" --> API Server              |    |
|    |                                           |                  |    |
|    |                                           v                  |    |
|    |                                    Check RBAC rules          |    |
|    |                                           |                  |    |
|    |                          +----------------+----------------+ |    |
|    |                          |                                 | |    |
|    |                          v                                 v |    |
|    |                    ✅ ALLOWED                        ❌ DENIED|    |
|    |                 (has permission)               (no permission)    |
|    |                                                               |    |
|    +--------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## TOPICS COVERED CHECKLIST

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Step | Topic              | K8s Object        | Concept               |
|  -----+--------------------+-------------------+---------------------  |
|   1   | Namespace          | Namespace         | Resource isolation    |
|   2   | ConfigMaps         | ConfigMap         | Non-sensitive config  |
|   3   | Secrets            | Secret            | Sensitive data        |
|   4   | Storage            | PVC, PV           | Persistent data       |
|   5   | StatefulSet        | StatefulSet       | Stateful apps (DB)    |
|   6   | Deployment         | Deployment        | Stateless apps        |
|   7   | Full Deployment    | Deployment        | Env, probes, limits   |
|   8   | Services           | Service           | NodePort exposure     |
|   9   | Ingress            | Ingress           | HTTP routing          |
|  10   | Autoscaling        | HPA               | Auto scale pods       |
|  11   | CronJob            | CronJob           | Scheduled tasks       |
|  12   | RBAC               | SA, Role, Binding | Security              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## STEP 0: SETUP MINIKUBE

```
+-------------------------------------------------------------------------+
|  🎯 LEARNING OBJECTIVE                                                  |
|  ====================                                                    |
|  * Understand what Minikube is and why we need it                      |
|  * Learn about cluster addons                                          |
|  * Verify your local Kubernetes environment                            |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|  📚 CONCEPT: What is Minikube?                                         |
|  ==============================                                         |
|                                                                         |
|  Minikube = Local Kubernetes cluster running in a VM/container        |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |  Your Laptop                                                    |   |
|  |  +-----------------------------------------------------------+ |   |
|  |  |  Minikube (Docker/VM)                                     | |   |
|  |  |  +-----------------------------------------------------+  | |   |
|  |  |  |           Single-Node Kubernetes Cluster            |  | |   |
|  |  |  |                                                      |  | |   |
|  |  |  |  Control Plane + Worker Node (combined)             |  | |   |
|  |  |  |  * API Server, etcd, scheduler                     |  | |   |
|  |  |  |  * kubelet, kube-proxy                             |  | |   |
|  |  |  |  * Your pods will run here                         |  | |   |
|  |  |  |                                                      |  | |   |
|  |  |  +-----------------------------------------------------+  | |   |
|  |  +-----------------------------------------------------------+ |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  WHY 4 CPUs and 4GB RAM?                                              |
|  * Kubernetes itself needs resources                                  |
|  * We'll run multiple pods (Postgres, Redis, Backend, Frontend)      |
|  * Ingress controller needs resources too                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMMANDS (Run each and UNDERSTAND what happens):

```bash
# 1. START MINIKUBE
minikube start --cpus=4 --memory=4096

# WHAT HAPPENS BEHIND THE SCENES:
# * Minikube creates a VM/container
# * Installs Kubernetes components
# * Configures kubectl to point to this cluster
# * Sets up networking
```

```bash
# 2. ENABLE ADDONS
minikube addons enable ingress          # For HTTP routing (Chapter 8)
minikube addons enable metrics-server   # For HPA autoscaling (Chapter 15)
minikube addons enable storage-provisioner  # For PVCs (Chapter 7)

# WHAT ARE ADDONS?
# Extra features not enabled by default:
# * ingress: NGINX Ingress Controller (routes HTTP traffic)
# * metrics-server: Collects CPU/memory metrics (needed for HPA)
# * storage-provisioner: Auto-creates PVs when you create PVC
```

```bash
# 3. VERIFY CLUSTER
minikube status
kubectl get nodes
```

```
+-------------------------------------------------------------------------+
|  ✅ EXPECTED OUTPUT                                                     |
|  ==================                                                      |
|                                                                         |
|  $ minikube status                                                      |
|  minikube                                                               |
|  type: Control Plane                                                    |
|  host: Running          <- VM/container is running                      |
|  kubelet: Running       <- Node agent is running                        |
|  apiserver: Running     <- API Server is accepting requests             |
|  kubeconfig: Configured <- kubectl can talk to cluster                  |
|                                                                         |
|  $ kubectl get nodes                                                    |
|  NAME       STATUS   ROLES           AGE   VERSION                     |
|  minikube   Ready    control-plane   5m    v1.28.0                     |
|             ^                                                           |
|             Must be "Ready" to proceed!                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

```bash
# 4. CREATE PROJECT DIRECTORY
mkdir -p ~/k8s-project
cd ~/k8s-project
```

```
+-------------------------------------------------------------------------+
|  🔧 TROUBLESHOOTING                                                     |
|  ===================                                                     |
|                                                                         |
|  NODE NOT READY?                                                        |
|  * Wait a minute, Kubernetes is starting                               |
|  * Run: kubectl get nodes --watch                                      |
|                                                                         |
|  MINIKUBE WON'T START?                                                 |
|  * Check Docker is running: docker ps                                  |
|  * Try: minikube delete && minikube start                             |
|                                                                         |
|  NOT ENOUGH RESOURCES?                                                  |
|  * Reduce: minikube start --cpus=2 --memory=2048                      |
|  * Close other applications                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## STEP 1: CREATE NAMESPACE

```
+-------------------------------------------------------------------------+
|  🎯 LEARNING OBJECTIVE                                                  |
|  ====================                                                    |
|  * Understand why namespaces exist                                     |
|  * Create your first Kubernetes object                                 |
|  * Learn to set default namespace                                      |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|  📚 CONCEPT: What is a Namespace?                                      |
|  ================================                                       |
|                                                                         |
|  Namespace = Virtual cluster inside your cluster                       |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                    Kubernetes Cluster                           |   |
|  |                                                                 |   |
|  |  +---------------+ +---------------+ +---------------+        |   |
|  |  |    default    | |  kube-system  | | task-manager  |        |   |
|  |  |   namespace   | |   namespace   | |  namespace    |        |   |
|  |  |               | |               | |  (WE CREATE)  |        |   |
|  |  | (your stuff   | | (K8s system   | |               |        |   |
|  |  |  if you don't | |  components)  | | Our app lives |        |   |
|  |  |  specify)     | |               | | here!         |        |   |
|  |  +---------------+ +---------------+ +---------------+        |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  WHY USE A NAMESPACE?                                                  |
|  * Isolation: Our resources don't mix with others                     |
|  * Organization: Easy to see all project resources                    |
|  * Easy cleanup: Delete namespace = delete everything in it           |
|  * Resource quotas: Limit CPU/memory per namespace                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

```bash
# File: 01-namespace.yaml
-------------------------

apiVersion: v1
kind: Namespace
metadata:
  name: task-manager
  labels:
    project: task-manager
    environment: development
```

```
+-------------------------------------------------------------------------+
|  🔍 UNDERSTAND THE YAML                                                 |
|  ======================                                                  |
|                                                                         |
|  apiVersion: v1        <- API version (v1 = core/stable)               |
|  kind: Namespace       <- Type of object we're creating                |
|  metadata:                                                              |
|    name: task-manager  <- Name of the namespace                        |
|    labels:             <- Key-value tags for organization              |
|      project: task-manager                                             |
|      environment: development                                          |
|                                                                         |
|  Labels are optional but useful for:                                   |
|  * Filtering: kubectl get ns -l project=task-manager                  |
|  * Organization: See what resources belong to what                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMMANDS (Run each and UNDERSTAND what happens):

```bash
# 1. CREATE THE YAML FILE
cat > 01-namespace.yaml << 'EOF'
apiVersion: v1
kind: Namespace
metadata:
  name: task-manager
  labels:
    project: task-manager
    environment: development
EOF
```

```bash
# 2. APPLY THE YAML
kubectl apply -f 01-namespace.yaml

# WHAT HAPPENS:
# 1. kubectl sends YAML to API Server
# 2. API Server validates the YAML
# 3. API Server stores namespace in etcd
# 4. Namespace is now available for use
```

```bash
# 3. VERIFY NAMESPACE WAS CREATED
kubectl get namespaces

# Look for 'task-manager' in the list
```

```bash
# 4. SEE NAMESPACE DETAILS
kubectl describe namespace task-manager

# Shows labels, status, resource quotas (if any)
```

```bash
# 5. SET AS DEFAULT NAMESPACE (IMPORTANT!)
kubectl config set-context --current --namespace=task-manager

# WHY DO THIS?
# Without this: kubectl get pods -n task-manager (every time!)
# With this:    kubectl get pods (automatically uses task-manager)
```

```bash
# 6. VERIFY DEFAULT NAMESPACE
kubectl config view --minify | grep namespace
```

```
+-------------------------------------------------------------------------+
|  ✅ EXPECTED OUTPUT                                                     |
|  ==================                                                      |
|                                                                         |
|  $ kubectl get namespaces                                               |
|  NAME              STATUS   AGE                                         |
|  default           Active   10m                                         |
|  kube-node-lease   Active   10m                                         |
|  kube-public       Active   10m                                         |
|  kube-system       Active   10m                                         |
|  task-manager      Active   5s   <- Our new namespace!                  |
|                                                                         |
|  $ kubectl config view --minify | grep namespace                       |
|      namespace: task-manager    <- Default is set!                      |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|  💡 CONCEPT CHECK: Test Your Understanding                             |
|  =========================================                              |
|                                                                         |
|  Q1: What happens to all resources if you delete the namespace?       |
|  A1: They all get deleted! (That's why namespaces are great for       |
|      cleanup: kubectl delete namespace task-manager)                   |
|                                                                         |
|  Q2: Can two namespaces have a service with the same name?            |
|  A2: Yes! Names are unique within a namespace, not across cluster.    |
|      dev/mysql and prod/mysql can both exist.                         |
|                                                                         |
|  Q3: What's in kube-system namespace?                                 |
|  A3: Kubernetes system pods! Run: kubectl get pods -n kube-system    |
|      You'll see coredns, kube-proxy, etc.                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## STEP 2: CONFIGMAPS (Non-sensitive configuration)

```
+-------------------------------------------------------------------------+
|  🎯 LEARNING OBJECTIVE                                                  |
|  ====================                                                    |
|  * Understand why configuration should be external to code             |
|  * Create ConfigMaps with key-value pairs AND files                    |
|  * Learn how pods will consume ConfigMaps later                        |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|  📚 CONCEPT: Why ConfigMaps?                                           |
|  ============================                                           |
|                                                                         |
|  WITHOUT ConfigMap (BAD):                                              |
|  ------------------------                                               |
|  # Hardcoded in Dockerfile                                             |
|  ENV APP_NAME="Task Manager"                                           |
|  ENV LOG_LEVEL="debug"                                                 |
|                                                                         |
|  Problem: Need different image for dev/staging/prod!                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WITH ConfigMap (GOOD):                                                |
|  -----------------------                                                |
|  Same image everywhere, config injected at runtime:                   |
|                                                                         |
|  +--------------+     +--------------+     +--------------+           |
|  |    Image     |  +  |   ConfigMap  |  =  |  Running Pod |           |
|  |   myapp:v1   |     |  (dev config)|     |  with dev    |           |
|  |              |     |              |     |  settings    |           |
|  +--------------+     +--------------+     +--------------+           |
|                                                                         |
|  +--------------+     +--------------+     +--------------+           |
|  |    Image     |  +  |   ConfigMap  |  =  |  Running Pod |           |
|  |   myapp:v1   |     | (prod config)|     |  with prod   |           |
|  |  (SAME!)     |     |              |     |  settings    |           |
|  +--------------+     +--------------+     +--------------+           |
|                                                                         |
+-------------------------------------------------------------------------+
```

CONCEPT: ConfigMaps store non-sensitive config data.

```bash
# File: 02-configmaps.yaml
--------------------------

apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: task-manager
data:
  # Simple key-value pairs (become environment variables)
  APP_NAME: "Task Manager"
  APP_ENV: "development"
  LOG_LEVEL: "debug"

  # Multi-line config file (mounted as file in pod)
  nginx.conf: |
    server {
        listen 80;
        server_name localhost;

        location / {
            root /usr/share/nginx/html;
            index index.html;
        }

        location /api {
            proxy_pass http://backend-service:5000;
        }
    }
```

```
+-------------------------------------------------------------------------+
|  🔍 UNDERSTAND THE YAML                                                 |
|  ======================                                                  |
|                                                                         |
|  data:                                                                   |
|    APP_NAME: "Task Manager"   <- Simple key-value                       |
|                                  Will become env var: APP_NAME          |
|                                                                         |
|    nginx.conf: |              <- Multi-line value (note the |)          |
|      server {                   This is an ENTIRE FILE                  |
|        ...                      Will be mounted as /etc/nginx/nginx.conf|
|      }                                                                   |
|                                                                         |
|  TWO WAYS TO USE ConfigMap:                                            |
|  1. As environment variables (APP_NAME, LOG_LEVEL)                     |
|  2. As mounted files (nginx.conf -> /etc/nginx/nginx.conf)              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMMANDS (Run each and UNDERSTAND what happens):

```bash
# 1. CREATE THE YAML FILE
cat > 02-configmaps.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: task-manager
data:
  APP_NAME: "Task Manager"
  APP_ENV: "development"
  LOG_LEVEL: "debug"
  nginx.conf: |
    server {
        listen 80;
        server_name localhost;
        location / {
            root /usr/share/nginx/html;
            index index.html;
        }
        location /api {
            proxy_pass http://backend-service:5000;
        }
    }
EOF
```

```bash
# 2. APPLY AND VERIFY
kubectl apply -f 02-configmaps.yaml

# WHAT HAPPENS:
# ConfigMap is stored in etcd
# NOT used yet - pods will reference it later
```

```bash
# 3. VIEW THE CONFIGMAP
kubectl get configmap
kubectl get configmap app-config -o yaml

# See all the data we stored
```

```bash
# 4. DESCRIBE FOR DETAILS
kubectl describe configmap app-config
```

```
+-------------------------------------------------------------------------+
|  ✅ EXPECTED OUTPUT                                                     |
|  ==================                                                      |
|                                                                         |
|  $ kubectl get configmap                                                |
|  NAME               DATA   AGE                                          |
|  app-config         4      5s   <- 4 keys (APP_NAME, APP_ENV,           |
|  kube-root-ca.crt   1      10m     LOG_LEVEL, nginx.conf)              |
|                                                                         |
|  $ kubectl describe configmap app-config                               |
|  Name:         app-config                                               |
|  Namespace:    task-manager                                             |
|  Data                                                                   |
|  ====                                                                   |
|  APP_ENV:       <- Can see all the keys                                 |
|  ----                                                                   |
|  development                                                            |
|  ...                                                                    |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|  💡 HOW PODS WILL USE THIS (Preview of Step 7)                         |
|  =============================================                          |
|                                                                         |
|  # As environment variables:                                           |
|  envFrom:                                                               |
|    - configMapRef:                                                      |
|        name: app-config    <- All keys become env vars                 |
|                                                                         |
|  # As mounted file:                                                    |
|  volumes:                                                               |
|    - name: nginx-config                                                |
|      configMap:                                                         |
|        name: app-config                                                |
|        items:                                                           |
|          - key: nginx.conf                                             |
|            path: nginx.conf  <- Mount as /etc/nginx/nginx.conf         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## STEP 3: SECRETS (Sensitive data)

```
+-------------------------------------------------------------------------+
|  🎯 LEARNING OBJECTIVE                                                  |
|  ====================                                                    |
|  * Understand difference between ConfigMap and Secret                  |
|  * Learn about base64 encoding (NOT encryption!)                       |
|  * Create secrets for database passwords                               |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|  📚 CONCEPT: ConfigMap vs Secret                                       |
|  ================================                                       |
|                                                                         |
|  +-------------------+-------------------+---------------------------+ |
|  |                   | ConfigMap         | Secret                    | |
|  +-------------------+-------------------+---------------------------+ |
|  | Use for           | Non-sensitive     | Sensitive data           | |
|  |                   | config            | (passwords, tokens)      | |
|  +-------------------+-------------------+---------------------------+ |
|  | Storage           | Plain text        | Base64 encoded           | |
|  +-------------------+-------------------+---------------------------+ |
|  | In kubectl output | Visible           | Hidden (shows ***)       | |
|  +-------------------+-------------------+---------------------------+ |
|  | Examples          | APP_NAME, LOG     | DB_PASSWORD, API_KEY     | |
|  |                   | nginx.conf        | TLS certificates         | |
|  +-------------------+-------------------+---------------------------+ |
|                                                                         |
|  ⚠️  WARNING: Base64 is NOT encryption!                               |
|  Anyone can decode: echo "c2VjcmV0" | base64 -d                       |
|  For real security, use tools like Vault or Sealed Secrets           |
|                                                                         |
+-------------------------------------------------------------------------+
```

CONCEPT: Secrets store sensitive data (passwords, API keys) base64 encoded.

```bash
# File: 03-secrets.yaml
------------------------

apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
  namespace: task-manager
type: Opaque
stringData:                    # stringData = auto base64 encodes
  POSTGRES_USER: taskuser
  POSTGRES_PASSWORD: secretpass123
  POSTGRES_DB: taskdb

---

apiVersion: v1
kind: Secret
metadata:
  name: redis-credentials
  namespace: task-manager
type: Opaque
stringData:
  REDIS_PASSWORD: redispass456
```

```
+-------------------------------------------------------------------------+
|  🔍 UNDERSTAND THE YAML                                                 |
|  ======================                                                  |
|                                                                         |
|  type: Opaque          <- Generic secret (most common)                  |
|                          Other types: kubernetes.io/tls,               |
|                          kubernetes.io/dockerconfigjson                |
|                                                                         |
|  stringData:           <- PLAIN TEXT here, auto-encoded to base64      |
|    POSTGRES_PASSWORD: secretpass123                                    |
|                                                                         |
|  Alternative (manual encoding):                                        |
|  data:                 <- Already base64 encoded                        |
|    POSTGRES_PASSWORD: c2VjcmV0cGFzczEyMw==                            |
|                                                                         |
|  USE stringData: It's easier! Let Kubernetes encode for you.          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMMANDS (Run each and UNDERSTAND what happens):

```bash
# 1. CREATE THE YAML FILE
cat > 03-secrets.yaml << 'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
  namespace: task-manager
type: Opaque
stringData:
  POSTGRES_USER: taskuser
  POSTGRES_PASSWORD: secretpass123
  POSTGRES_DB: taskdb
---
apiVersion: v1
kind: Secret
metadata:
  name: redis-credentials
  namespace: task-manager
type: Opaque
stringData:
  REDIS_PASSWORD: redispass456
EOF
```

```bash
# 2. APPLY
kubectl apply -f 03-secrets.yaml
```

```bash
# 3. VIEW SECRETS (Notice values are hidden)
kubectl get secrets
kubectl describe secret db-credentials

# Values show as "*** bytes" - not visible!
```

```bash
# 4. SEE BASE64 ENCODED DATA
kubectl get secret db-credentials -o yaml

# You'll see: POSTGRES_PASSWORD: c2VjcmV0cGFzczEyMw==
```

```bash
# 5. DECODE A SECRET VALUE
kubectl get secret db-credentials -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d

# Output: secretpass123
# This proves base64 is NOT secure - just encoding!
```

```
+-------------------------------------------------------------------------+
|  ✅ EXPECTED OUTPUT                                                     |
|  ==================                                                      |
|                                                                         |
|  $ kubectl get secrets                                                  |
|  NAME                  TYPE     DATA   AGE                              |
|  db-credentials        Opaque   3      5s                               |
|  redis-credentials     Opaque   1      5s                               |
|                                                                         |
|  $ kubectl describe secret db-credentials                              |
|  Name:         db-credentials                                           |
|  Type:         Opaque                                                   |
|  Data                                                                   |
|  ====                                                                   |
|  POSTGRES_DB:        6 bytes  <- Values hidden!                         |
|  POSTGRES_PASSWORD:  13 bytes                                          |
|  POSTGRES_USER:      8 bytes                                           |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|  💡 CONCEPT CHECK: Test Your Understanding                             |
|  =========================================                              |
|                                                                         |
|  Q1: Is base64 encoding secure?                                        |
|  A1: NO! It's just encoding, not encryption. Anyone with access       |
|      to the secret can decode it.                                      |
|                                                                         |
|  Q2: Why use Secrets instead of ConfigMap for passwords?              |
|  A2: * Secrets are not shown in kubectl describe                      |
|      * Can be encrypted at rest in etcd                               |
|      * Better access control via RBAC                                 |
|      * Convention: passwords belong in Secrets                        |
|                                                                         |
|  Q3: When would you use 'data:' instead of 'stringData:'?            |
|  A3: When you already have base64 encoded value (e.g., from          |
|      another system or generated by a tool)                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## STEP 4: PERSISTENT STORAGE (PV & PVC)

```
+-------------------------------------------------------------------------+
|  🎯 LEARNING OBJECTIVE                                                  |
|  ====================                                                    |
|  * Understand why pods need persistent storage                         |
|  * Learn PVC (developer) vs PV (admin) separation                      |
|  * Create storage that survives pod restarts                           |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|  📚 CONCEPT: Why Persistent Storage?                                   |
|  ====================================                                   |
|                                                                         |
|  WITHOUT persistent storage:                                           |
|  ----------------------------                                          |
|  +---------------+                                                     |
|  |  PostgreSQL   |  Pod crashes...                                    |
|  |  Pod          |                                                     |
|  |               |         💥                                          |
|  |  /var/lib/    |  ----------->  ALL DATA LOST!                      |
|  |  postgresql/  |                                                     |
|  |  (container   |  New pod starts with EMPTY database               |
|  |   filesystem) |                                                     |
|  +---------------+                                                     |
|                                                                         |
|  WITH persistent storage:                                              |
|  ------------------------                                              |
|  +---------------+        +---------------+                           |
|  |  PostgreSQL   |        |  PersistentVol|                           |
|  |  Pod          |------->|  (external    |                           |
|  |               |        |   storage)    |                           |
|  |  /var/lib/    |        |               |                           |
|  |  postgresql/  |        |  Data stays   |                           |
|  +---------------+        |  here!        |                           |
|        |                  +---------------+                           |
|        | Pod crashes...         |                                     |
|        💥                        |                                     |
|        |                        |                                     |
|  +---------------+              |                                     |
|  |  New Pod      |--------------+                                     |
|  |  (reconnects  |  Data still there! [x]                              |
|  |   to storage) |                                                     |
|  +---------------+                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

CONCEPT: PersistentVolumes provide durable storage for databases.

```bash
# File: 04-storage.yaml
------------------------

# PersistentVolumeClaim for PostgreSQL
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: task-manager
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: standard      # minikube default storage class

---

# PersistentVolumeClaim for Redis
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: task-manager
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 500Mi
  storageClassName: standard
```

**COMMANDS:**
---------

```bash
kubectl apply -f 04-storage.yaml

# View storage
kubectl get pvc
kubectl get pv
kubectl describe pvc postgres-pvc
```

## STEP 5: POSTGRESQL DATABASE (StatefulSet)

CONCEPT: StatefulSet for stateful apps needing stable identity & storage.

```bash
# File: 05-postgres.yaml
-------------------------

apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: task-manager
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
          name: postgres

        # Environment from Secret
        envFrom:
        - secretRef:
            name: db-credentials

        # Resource limits
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi

        # Health checks
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - taskuser
          initialDelaySeconds: 30
          periodSeconds: 10

        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - taskuser
          initialDelaySeconds: 5
          periodSeconds: 5

        # Mount persistent storage
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data

      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc

---

# Service for PostgreSQL (headless for StatefulSet)
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: task-manager
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  clusterIP: None              # Headless service for StatefulSet
```

**COMMANDS:**
---------

```bash
kubectl apply -f 05-postgres.yaml

# Watch pod start
kubectl get pods -w

# Check StatefulSet
kubectl get statefulset
kubectl describe statefulset postgres

# Test database connection
kubectl exec -it postgres-0 -- psql -U taskuser -d taskdb -c "\l"
```

## STEP 6: REDIS CACHE (Deployment)

CONCEPT: Deployment for stateless (or semi-stateful) applications.

```bash
# File: 06-redis.yaml
----------------------

apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: task-manager
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379

        command:
        - redis-server
        - --requirepass
        - $(REDIS_PASSWORD)

        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-credentials
              key: REDIS_PASSWORD

        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 200m
            memory: 128Mi

        livenessProbe:
          tcpSocket:
            port: 6379
          initialDelaySeconds: 10
          periodSeconds: 5

        readinessProbe:
          tcpSocket:
            port: 6379
          initialDelaySeconds: 5
          periodSeconds: 3

        volumeMounts:
        - name: redis-storage
          mountPath: /data

      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc

---

# Service for Redis (ClusterIP - internal only)
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: task-manager
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP
```

**COMMANDS:**
---------

```bash
kubectl apply -f 06-redis.yaml

# Check deployment
kubectl get deployment redis
kubectl get pods -l app=redis

# Test Redis
kubectl exec -it deployment/redis -- redis-cli -a redispass456 PING
```

## STEP 7: BACKEND API (Deployment with full features)

CONCEPT: Full-featured Deployment with all best practices.

```bash
# File: 07-backend.yaml
------------------------

apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: task-manager
  labels:
    app: backend
    version: v1
spec:
  replicas: 2                        # Multiple replicas for HA
  selector:
    matchLabels:
      app: backend

  # Rolling update strategy
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0              # Zero downtime

  template:
    metadata:
      labels:
        app: backend
        version: v1
    spec:
      # Service account for RBAC
      serviceAccountName: backend-sa

      containers:
      - name: backend
        image: hashicorp/http-echo    # Simple echo server for demo
        args:
        - "-text=Task Manager API v1"
        - "-listen=:5000"
        ports:
        - containerPort: 5000
          name: http

        # Environment from ConfigMap
        env:
        - name: APP_NAME
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: APP_NAME
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: LOG_LEVEL

        # Database credentials from Secret
        - name: DB_HOST
          value: postgres
        - name: DB_USER
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: POSTGRES_USER
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: POSTGRES_PASSWORD

        # Redis credentials
        - name: REDIS_HOST
          value: redis
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-credentials
              key: REDIS_PASSWORD

        # Resource management
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi

        # Health checks
        livenessProbe:
          httpGet:
            path: /
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 10
          failureThreshold: 3

        readinessProbe:
          httpGet:
            path: /
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
          failureThreshold: 3

---

# Service for Backend (ClusterIP)
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: task-manager
spec:
  selector:
    app: backend
  ports:
  - port: 5000
    targetPort: 5000
    name: http
  type: ClusterIP
```

**COMMANDS:**
---------

```bash
# First create the service account (needed by deployment)
kubectl create serviceaccount backend-sa -n task-manager

kubectl apply -f 07-backend.yaml

# Check deployment
kubectl get deployment backend
kubectl get pods -l app=backend
kubectl describe deployment backend

# Check service
kubectl get service backend-service
kubectl get endpoints backend-service

# Test backend
kubectl port-forward service/backend-service 5000:5000 &
curl http://localhost:5000
# Kill port-forward: fg then Ctrl+C
```

## STEP 8: FRONTEND (Deployment + NodePort Service)

CONCEPT: Frontend with NodePort for external access (before Ingress).

```bash
# File: 08-frontend.yaml
-------------------------

apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: task-manager
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80

        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 200m
            memory: 128Mi

        # Mount ConfigMap as file
        volumeMounts:
        - name: nginx-config
          mountPath: /etc/nginx/conf.d/default.conf
          subPath: nginx.conf

        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 10

        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 2
          periodSeconds: 5

      volumes:
      - name: nginx-config
        configMap:
          name: app-config

---

# Service for Frontend (NodePort for external access)
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: task-manager
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30080              # Access via minikube IP:30080
  type: NodePort
```

**COMMANDS:**
---------

```bash
kubectl apply -f 08-frontend.yaml

# Check deployment
kubectl get deployment frontend
kubectl get pods -l app=frontend

# Access via NodePort
minikube service frontend-service -n task-manager --url

# Or get minikube IP and access port 30080
minikube ip
# Then visit http://<minikube-ip>:30080
```

## STEP 9: INGRESS (HTTP routing)

CONCEPT: Ingress provides HTTP routing and single entry point.

```bash
# File: 09-ingress.yaml
------------------------

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: task-manager-ingress
  namespace: task-manager
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: taskmanager.local       # Add to /etc/hosts
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 5000
```

**COMMANDS:**
---------

```bash
kubectl apply -f 09-ingress.yaml

# Get minikube IP
minikube ip

# Add to /etc/hosts (replace <minikube-ip> with actual IP)
echo "$(minikube ip) taskmanager.local" | sudo tee -a /etc/hosts

# Verify ingress
kubectl get ingress
kubectl describe ingress task-manager-ingress

# Start minikube tunnel (required for ingress on some systems)
minikube tunnel

# Access (in another terminal)
curl http://taskmanager.local
curl http://taskmanager.local/api
```

## STEP 10: HORIZONTAL POD AUTOSCALER (HPA)

CONCEPT: HPA automatically scales pods based on CPU/memory.

```bash
# File: 10-hpa.yaml
--------------------

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: task-manager
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50      # Scale when CPU > 50%
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70      # Scale when Memory > 70%
```

**COMMANDS:**
---------

```bash
kubectl apply -f 10-hpa.yaml

# Check HPA
kubectl get hpa
kubectl describe hpa backend-hpa

# Watch HPA (in separate terminal)
kubectl get hpa -w

# Generate load to test autoscaling
kubectl run -i --tty load-generator --rm --image=busybox --restart=Never -- \
  /bin/sh -c "while sleep 0.01; do wget -q -O- http://backend-service:5000; done"

# Watch pods scale up
kubectl get pods -l app=backend -w
```

## STEP 11: CRONJOB (Scheduled task)

CONCEPT: CronJob runs scheduled tasks (like cron in Linux).

```bash
# File: 11-cronjob.yaml
------------------------

apiVersion: batch/v1
kind: CronJob
metadata:
  name: cleanup-job
  namespace: task-manager
spec:
  schedule: "*/5 * * * *"          # Every 5 minutes
  concurrencyPolicy: Forbid        # Don't run if previous still running
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: cleanup
            image: busybox
            command:
            - /bin/sh
            - -c
            - |
              echo "Running cleanup at $(date)"
              echo "Cleaning old tasks..."
              sleep 5
              echo "Cleanup complete!"
          restartPolicy: OnFailure
```

**COMMANDS:**
---------

```bash
kubectl apply -f 11-cronjob.yaml

# Check CronJob
kubectl get cronjob
kubectl describe cronjob cleanup-job

# Watch jobs being created
kubectl get jobs -w

# See job pods
kubectl get pods -l job-name

# Check logs of a completed job
kubectl logs -l job-name=cleanup-job-<timestamp>

# Manually trigger a job
kubectl create job --from=cronjob/cleanup-job manual-cleanup
```

## STEP 12: RBAC (Role-Based Access Control)

CONCEPT: RBAC controls who can do what in the cluster.

```bash
# File: 12-rbac.yaml
---------------------

# ServiceAccount for backend
apiVersion: v1
kind: ServiceAccount
metadata:
  name: backend-sa
  namespace: task-manager

---

# Role with limited permissions
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: backend-role
  namespace: task-manager
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]

---

# Bind Role to ServiceAccount
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: backend-rolebinding
  namespace: task-manager
subjects:
- kind: ServiceAccount
  name: backend-sa
  namespace: task-manager
roleRef:
  kind: Role
  name: backend-role
  apiGroup: rbac.authorization.k8s.io
```

**COMMANDS:**
---------

```bash
kubectl apply -f 12-rbac.yaml

# Check RBAC resources
kubectl get serviceaccount
kubectl get role
kubectl get rolebinding

# Test permissions
kubectl auth can-i get pods --as=system:serviceaccount:task-manager:backend-sa
kubectl auth can-i delete pods --as=system:serviceaccount:task-manager:backend-sa
```

## STEP 13: VERIFY EVERYTHING IS RUNNING

```bash
# Check all resources
kubectl get all -n task-manager

# Expected output:
# NAME                            READY   STATUS    RESTARTS   AGE
# pod/backend-xxx                 1/1     Running   0          5m
# pod/backend-yyy                 1/1     Running   0          5m
# pod/frontend-xxx                1/1     Running   0          5m
# pod/frontend-yyy                1/1     Running   0          5m
# pod/postgres-0                  1/1     Running   0          10m
# pod/redis-xxx                   1/1     Running   0          8m
# 
# NAME                      TYPE        CLUSTER-IP      PORT(S)
# service/backend-service   ClusterIP   10.96.x.x       5000/TCP
# service/frontend-service  NodePort    10.96.x.x       80:30080/TCP
# service/postgres          ClusterIP   None            5432/TCP
# service/redis             ClusterIP   10.96.x.x       6379/TCP
# 
# NAME                       READY   UP-TO-DATE   AVAILABLE
# deployment.apps/backend    2/2     2            2
# deployment.apps/frontend   2/2     2            2
# deployment.apps/redis      1/1     1            1
# 
# NAME                                  READY
# statefulset.apps/postgres             1/1
# 
# NAME                          SCHEDULE      SUSPEND   ACTIVE
# cronjob.batch/cleanup-job    */5 * * * *   False     0
```

## STEP 14: USEFUL DEBUGGING COMMANDS

```bash
# View logs
kubectl logs deployment/backend
kubectl logs deployment/frontend
kubectl logs statefulset/postgres

# Shell into pod
kubectl exec -it deployment/backend -- /bin/sh
kubectl exec -it postgres-0 -- bash

# Describe for troubleshooting
kubectl describe pod <pod-name>
kubectl describe deployment backend

# View events
kubectl get events --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods
kubectl top nodes

# Port forward for testing
kubectl port-forward service/backend-service 5000:5000
kubectl port-forward service/postgres 5432:5432
```

## STEP 15: CLEANUP

```bash
# Delete all resources in namespace
kubectl delete namespace task-manager

# Or delete individual resources
kubectl delete -f .

# Stop minikube
minikube stop

# Delete minikube cluster (if needed)
minikube delete
```

## QUICK REFERENCE: ALL FILES TO CREATE

```
~/k8s-project/
+-- 01-namespace.yaml
+-- 02-configmaps.yaml
+-- 03-secrets.yaml
+-- 04-storage.yaml
+-- 05-postgres.yaml
+-- 06-redis.yaml
+-- 07-backend.yaml
+-- 08-frontend.yaml
+-- 09-ingress.yaml
+-- 10-hpa.yaml
+-- 11-cronjob.yaml
+-- 12-rbac.yaml
```

**APPLY ALL AT ONCE:**

```bash
# Apply in order
kubectl apply -f 01-namespace.yaml
kubectl config set-context --current --namespace=task-manager
kubectl apply -f 02-configmaps.yaml
kubectl apply -f 03-secrets.yaml
kubectl apply -f 04-storage.yaml
kubectl apply -f 05-postgres.yaml
kubectl apply -f 06-redis.yaml
kubectl create serviceaccount backend-sa -n task-manager
kubectl apply -f 07-backend.yaml
kubectl apply -f 08-frontend.yaml
kubectl apply -f 09-ingress.yaml
kubectl apply -f 10-hpa.yaml
kubectl apply -f 11-cronjob.yaml
kubectl apply -f 12-rbac.yaml
```

## TOPICS LEARNED CHECKLIST

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ☐ Namespaces           - Isolating resources                         |
|  ☐ ConfigMaps           - Non-sensitive configuration                 |
|  ☐ Secrets              - Sensitive data (passwords)                  |
|  ☐ PV/PVC               - Persistent storage                          |
|  ☐ StatefulSet          - Stateful apps (database)                    |
|  ☐ Deployment           - Stateless apps (backend, frontend)          |
|  ☐ Services             - ClusterIP, NodePort, Headless               |
|  ☐ Ingress              - HTTP routing                                |
|  ☐ Health Checks        - Liveness & Readiness probes                 |
|  ☐ Resource Limits      - CPU/Memory requests & limits                |
|  ☐ HPA                  - Horizontal Pod Autoscaler                   |
|  ☐ CronJob              - Scheduled tasks                             |
|  ☐ RBAC                 - ServiceAccount, Role, RoleBinding           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF PROJECT

