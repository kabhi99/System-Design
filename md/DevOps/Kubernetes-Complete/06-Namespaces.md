# KUBERNETES NAMESPACES
*Chapter 6: Multi-tenancy and Resource Isolation*

Namespaces provide a way to divide cluster resources between multiple
users, teams, or applications.

## SECTION 6.1: WHY NAMESPACES?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM: EVERYTHING IN ONE PLACE                                   |
|  =====================================                                  |
|                                                                         |
|  Without namespaces, all resources in single "default" namespace:       |
|                                                                         |
|  kubectl get pods                                                       |
|  -----------------------------------------------------------------      |
|  frontend-dev-abc123                                                    |
|  frontend-prod-xyz789                                                   |
|  backend-dev-111aaa                                                     |
|  backend-prod-222bbb                                                    |
|  mysql-dev-333ccc                                                       |
|  mysql-prod-444ddd                                                      |
|  redis-team-a-555eee                                                    |
|  redis-team-b-666fff                                                    |
|  ... 200 more pods ...                                                  |
|                                                                         |
|  PROBLEMS:                                                              |
|                                                                         |
|  1. NAME COLLISIONS                                                     |
|     * Two teams want "mysql" service name                               |
|     * Must use ugly names: mysql-team-a, mysql-team-b                   |
|                                                                         |
|  2. NO ISOLATION                                                        |
|     * Dev team can accidentally delete prod resources                   |
|     * Junior dev has access to everything                               |
|                                                                         |
|  3. NO RESOURCE LIMITS PER TEAM                                         |
|     * One team can consume all CPU/memory                               |
|     * No fair sharing of cluster resources                              |
|                                                                         |
|  4. CHAOS                                                               |
|     * Hard to find your resources                                       |
|     * Hard to clean up a team's resources                               |
|     * No logical grouping                                               |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  THE SOLUTION: NAMESPACES                                               |
|  =========================                                              |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                    KUBERNETES CLUSTER                           |    |
|  |                                                                 |    |
|  |  +-------------+  +-------------+  +-------------+            |      |
|  |  |     dev     |  |   staging   |  |    prod     |            |      |
|  |  |             |  |             |  |             |            |      |
|  |  | * mysql     |  | * mysql     |  | * mysql     | < Same    |       |
|  |  | * redis     |  | * redis     |  | * redis     |   names!  |       |
|  |  | * backend   |  | * backend   |  | * backend   |            |      |
|  |  |             |  |             |  |             |            |      |
|  |  | CPU: 10     |  | CPU: 20     |  | CPU: 100    | < Quotas  |       |
|  |  | Mem: 20Gi   |  | Mem: 40Gi   |  | Mem: 200Gi  |            |      |
|  |  |             |  |             |  |             |            |      |
|  |  | Users:      |  | Users:      |  | Users:      |            |      |
|  |  | dev-team    |  | qa-team     |  | ops-team    | < RBAC    |       |
|  |  +-------------+  +-------------+  +-------------+            |      |
|  |                                                                 |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  BENEFITS:                                                              |
|  * Same names in different namespaces (mysql in dev AND prod)           |
|  * Isolation (dev team can't touch prod)                                |
|  * Resource quotas per namespace                                        |
|  * Easy cleanup (delete namespace = delete everything in it)            |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  WHEN TO USE NAMESPACES                                                 |
|  =======================                                                |
|                                                                         |
|  USE NAMESPACES FOR:                                                    |
|  ---------------------                                                  |
|                                                                         |
|  1. ENVIRONMENT SEPARATION                                              |
|     * dev, staging, production                                          |
|     * Same cluster, different namespaces                                |
|                                                                         |
|  2. TEAM SEPARATION                                                     |
|     * team-a, team-b, team-c                                            |
|     * Each team has their own namespace                                 |
|                                                                         |
|  3. PROJECT/APPLICATION SEPARATION                                      |
|     * ecommerce, analytics, auth-service                                |
|     * Group related resources                                           |
|                                                                         |
|  4. CUSTOMER/TENANT SEPARATION (Multi-tenant)                           |
|     * customer-acme, customer-globex                                    |
|     * SaaS applications                                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DON'T USE NAMESPACES FOR:                                              |
|  --------------------------                                             |
|                                                                         |
|  1. VERSIONING                                                          |
|     * Bad: myapp-v1, myapp-v2 namespaces                                |
|     * Good: Use labels, deployments handle versions                     |
|                                                                         |
|  2. SMALL CLUSTERS                                                      |
|     * < 10 developers, single team                                      |
|     * "default" namespace is fine                                       |
|                                                                         |
|  3. HARD SECURITY BOUNDARIES                                            |
|     * Namespaces provide soft isolation                                 |
|     * For hard isolation, use separate clusters                         |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  NAMESPACE-SCOPED vs CLUSTER-SCOPED RESOURCES                           |
|  =============================================                          |
|                                                                         |
|  NAMESPACE-SCOPED (exist inside a namespace):                           |
|  * Pods, Deployments, Services, ConfigMaps, Secrets                     |
|  * ReplicaSets, StatefulSets, Jobs, CronJobs                            |
|  * Ingress, PersistentVolumeClaims, Roles, RoleBindings                 |
|                                                                         |
|  CLUSTER-SCOPED (exist across entire cluster):                          |
|  * Nodes, PersistentVolumes, Namespaces                                 |
|  * ClusterRoles, ClusterRoleBindings                                    |
|  * StorageClasses, IngressClasses                                       |
|                                                                         |
|  # Check if resource is namespaced                                      |
|  kubectl api-resources --namespaced=true                                |
|  kubectl api-resources --namespaced=false                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6.2: UNDERSTANDING NAMESPACES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT ARE NAMESPACES?                                                   |
|                                                                         |
|  Virtual clusters within a physical cluster.                            |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |   Kubernetes Cluster                                           |     |
|  |   +-----------------------------------------------------------+|     |
|  |   |                                                           ||     |
|  |   |  +-------------+  +-------------+  +-------------+       ||      |
|  |   |  |   default   |  |    dev      |  |    prod     |       ||      |
|  |   |  |             |  |             |  |             |       ||      |
|  |   |  | * pods      |  | * pods      |  | * pods      |       ||      |
|  |   |  | * services  |  | * services  |  | * services  |       ||      |
|  |   |  | * configs   |  | * configs   |  | * configs   |       ||      |
|  |   |  +-------------+  +-------------+  +-------------+       ||      |
|  |   |                                                           ||     |
|  |   +-----------------------------------------------------------+|     |
|  |                                                                 |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DEFAULT NAMESPACES                                                     |
|  ===================                                                    |
|                                                                         |
|  * default: Where resources go if no namespace specified                |
|  * kube-system: Kubernetes system components                            |
|  * kube-public: Publicly readable resources                             |
|  * kube-node-lease: Node heartbeat data                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6.2: WORKING WITH NAMESPACES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CREATING NAMESPACES                                                    |
|  ====================                                                   |
|                                                                         |
|  # Command                                                              |
|  kubectl create namespace dev                                           |
|                                                                         |
|  # YAML                                                                 |
|  apiVersion: v1                                                         |
|  kind: Namespace                                                        |
|  metadata:                                                              |
|    name: dev                                                            |
|    labels:                                                              |
|      environment: development                                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USING NAMESPACES                                                       |
|  =================                                                      |
|                                                                         |
|  # List namespaces                                                      |
|  kubectl get namespaces                                                 |
|  kubectl get ns                                                         |
|                                                                         |
|  # Create resource in namespace                                         |
|  kubectl apply -f pod.yaml -n dev                                       |
|                                                                         |
|  # List resources in namespace                                          |
|  kubectl get pods -n dev                                                |
|  kubectl get all -n dev                                                 |
|                                                                         |
|  # Set default namespace                                                |
|  kubectl config set-context --current --namespace=dev                   |
|                                                                         |
|  # List resources across all namespaces                                 |
|  kubectl get pods --all-namespaces                                      |
|  kubectl get pods -A                                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  NAMESPACE IN YAML                                                      |
|  ==================                                                     |
|                                                                         |
|  apiVersion: v1                                                         |
|  kind: Pod                                                              |
|  metadata:                                                              |
|    name: my-pod                                                         |
|    namespace: dev    # Specify namespace                                |
|  spec:                                                                  |
|    containers:                                                          |
|      - name: app                                                        |
|        image: nginx                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6.3: RESOURCE QUOTAS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LIMIT RESOURCES PER NAMESPACE                                          |
|                                                                         |
|  apiVersion: v1                                                         |
|  kind: ResourceQuota                                                    |
|  metadata:                                                              |
|    name: dev-quota                                                      |
|    namespace: dev                                                       |
|  spec:                                                                  |
|    hard:                                                                |
|      # Compute resources                                                |
|      requests.cpu: "10"                                                 |
|      requests.memory: 20Gi                                              |
|      limits.cpu: "20"                                                   |
|      limits.memory: 40Gi                                                |
|                                                                         |
|      # Object counts                                                    |
|      pods: "100"                                                        |
|      services: "50"                                                     |
|      secrets: "100"                                                     |
|      configmaps: "100"                                                  |
|      persistentvolumeclaims: "20"                                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CHECK QUOTA USAGE                                                      |
|                                                                         |
|  kubectl describe resourcequota dev-quota -n dev                        |
|                                                                         |
|  # Output:                                                              |
|  # Used      Hard                                                       |
|  # ----      ----                                                       |
|  # pods      10        100                                              |
|  # cpu       5         20                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6.4: LIMIT RANGES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DEFAULT LIMITS FOR CONTAINERS                                          |
|                                                                         |
|  apiVersion: v1                                                         |
|  kind: LimitRange                                                       |
|  metadata:                                                              |
|    name: default-limits                                                 |
|    namespace: dev                                                       |
|  spec:                                                                  |
|    limits:                                                              |
|      - type: Container                                                  |
|        default:           # Default limits                              |
|          cpu: 500m                                                      |
|          memory: 256Mi                                                  |
|        defaultRequest:    # Default requests                            |
|          cpu: 100m                                                      |
|          memory: 128Mi                                                  |
|        max:               # Maximum allowed                             |
|          cpu: 2                                                         |
|          memory: 2Gi                                                    |
|        min:               # Minimum required                            |
|          cpu: 50m                                                       |
|          memory: 64Mi                                                   |
|                                                                         |
|  Now pods without explicit limits get defaults applied.                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6.5: CROSS-NAMESPACE COMMUNICATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ACCESSING SERVICES ACROSS NAMESPACES                                   |
|                                                                         |
|  DNS format:                                                            |
|  <service>.<namespace>.svc.cluster.local                                |
|                                                                         |
|  Example:                                                               |
|  # Pod in 'web' namespace accessing DB in 'database' namespace          |
|  mysql.database.svc.cluster.local:3306                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  NAMESPACED vs CLUSTER-SCOPED RESOURCES                                 |
|                                                                         |
|  NAMESPACED (isolated):                                                 |
|  * Pods, Deployments, Services                                          |
|  * ConfigMaps, Secrets                                                  |
|  * ServiceAccounts                                                      |
|                                                                         |
|  CLUSTER-SCOPED (shared):                                               |
|  * Nodes                                                                |
|  * PersistentVolumes                                                    |
|  * ClusterRoles                                                         |
|  * Namespaces themselves                                                |
|                                                                         |
|  # Check if resource is namespaced                                      |
|  kubectl api-resources --namespaced=true                                |
|  kubectl api-resources --namespaced=false                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NAMESPACES - KEY TAKEAWAYS                                             |
|                                                                         |
|  PURPOSE                                                                |
|  -------                                                                |
|  * Divide cluster resources                                             |
|  * Isolate teams/environments                                           |
|  * Apply quotas and limits                                              |
|                                                                         |
|  RESOURCE CONTROL                                                       |
|  ----------------                                                       |
|  * ResourceQuota: Limit total resources                                 |
|  * LimitRange: Default and max for containers                           |
|                                                                         |
|  COMMANDS                                                               |
|  --------                                                               |
|  kubectl create namespace <name>                                        |
|  kubectl get pods -n <namespace>                                        |
|  kubectl get pods -A (all namespaces)                                   |
|  kubectl config set-context --current --namespace=<name>                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 6

