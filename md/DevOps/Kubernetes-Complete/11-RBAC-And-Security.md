# KUBERNETES RBAC & SECURITY
*Chapter 11: Access Control and Security*

RBAC (Role-Based Access Control) controls who can do what in Kubernetes.

## SECTION 11.1: WHY RBAC? (The Security Problem)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM: UNRESTRICTED ACCESS                                     |
|  =================================                                      |
|                                                                         |
|  Without RBAC, anyone with kubectl access can:                        |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |   Junior Developer with kubectl:                               |   |
|  |                                                                 |   |
|  |   kubectl delete deployment production-api     < Oops!        |   |
|  |   kubectl delete pvc database-storage          < Data gone!   |   |
|  |   kubectl exec -it prod-db -- mysql            < Sees secrets |   |
|  |   kubectl get secrets --all-namespaces         < All passwords|   |
|  |   kubectl create deployment bitcoin-miner...   < Crypto mining|   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  PROBLEMS:                                                             |
|                                                                         |
|  1. ACCIDENTAL DAMAGE                                                  |
|     * Dev deletes production resources by mistake                    |
|     * Wrong namespace, wrong context                                 |
|                                                                         |
|  2. SECURITY BREACH                                                    |
|     * Everyone can read all secrets                                  |
|     * Database passwords visible to all                              |
|                                                                         |
|  3. COMPLIANCE VIOLATIONS                                             |
|     * No audit trail of who did what                                 |
|     * Can't prove separation of duties                               |
|                                                                         |
|  4. RESOURCE ABUSE                                                     |
|     * Anyone can create unlimited resources                          |
|     * No control over cluster usage                                  |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  THE SOLUTION: RBAC (Role-Based Access Control)                       |
|  ===============================================                        |
|                                                                         |
|  Define WHO can do WHAT on WHICH resources:                           |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |   Junior Developer:                                            |   |
|  |   Y Can view pods in dev namespace                            |   |
|  |   Y Can view logs                                              |   |
|  |   X Cannot delete anything                                     |   |
|  |   X Cannot access prod namespace                               |   |
|  |   X Cannot read secrets                                        |   |
|  |                                                                 |   |
|  |   Senior Developer:                                            |   |
|  |   Y Can create/delete in dev namespace                        |   |
|  |   Y Can view prod (read-only)                                  |   |
|  |   X Cannot delete in prod                                      |   |
|  |                                                                 |   |
|  |   Ops Team:                                                    |   |
|  |   Y Full access to prod                                       |   |
|  |   Y Can manage nodes                                           |   |
|  |   Y Can read secrets                                           |   |
|  |                                                                 |   |
|  |   CI/CD Pipeline (ServiceAccount):                            |   |
|  |   Y Can create/update deployments                             |   |
|  |   X Cannot delete PVCs                                         |   |
|  |   X Cannot access other namespaces                            |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  REAL-WORLD RBAC SCENARIOS                                            |
|  ==========================                                             |
|                                                                         |
|  SCENARIO 1: Multi-Team Cluster                                       |
|  -------------------------------                                       |
|  * Team A: Full access to namespace team-a                           |
|  * Team B: Full access to namespace team-b                           |
|  * Neither team can see each other's resources                       |
|                                                                         |
|  SCENARIO 2: Dev/Staging/Prod Environments                            |
|  -----------------------------------------                             |
|  * Developers: Full access to dev, read-only to staging/prod        |
|  * QA: Full access to staging, read-only to prod                    |
|  * Ops: Full access everywhere                                       |
|                                                                         |
|  SCENARIO 3: CI/CD Pipeline                                           |
|  ---------------------------                                           |
|  * ServiceAccount for Jenkins/GitHub Actions                         |
|  * Can deploy apps (create/update deployments)                       |
|  * Cannot delete persistent volumes (protect data)                  |
|  * Cannot modify RBAC (can't escalate privileges)                   |
|                                                                         |
|  SCENARIO 4: Monitoring Tools                                         |
|  -----------------------------                                         |
|  * Prometheus ServiceAccount                                          |
|  * Read-only access to pods, nodes, services                        |
|  * Cannot modify anything                                            |
|                                                                         |
|  SCENARIO 5: Application Pods                                         |
|  -----------------------------                                         |
|  * Pod needs to read ConfigMaps                                      |
|  * Pod needs to list other pods (service discovery)                 |
|  * Minimal permissions - only what app needs                        |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  PRINCIPLE OF LEAST PRIVILEGE                                         |
|  =============================                                          |
|                                                                         |
|  Give each user/service ONLY the permissions they NEED.              |
|  Nothing more.                                                        |
|                                                                         |
|  BAD:  "Give developers admin access, it's easier"                   |
|  GOOD: "Developers can view logs and exec into dev pods only"       |
|                                                                         |
|  BAD:  "CI/CD pipeline has cluster-admin"                            |
|  GOOD: "CI/CD can only update deployments in specific namespace"    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11.2: RBAC CONCEPTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RBAC COMPONENTS                                                       |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |   WHO              WHAT                    WHERE               |  |
|  |   (Subject)        (Role)                  (Binding)           |  |
|  |                                                                 |  |
|  |   +---------+      +-----------------+     +----------------+  |  |
|  |   |  User   |      |  Role           |     | RoleBinding    |  |  |
|  |   |  Group  | <----|  (namespace)    |<----| (namespace)    |  |  |
|  |   | Service |      |                 |     |                |  |  |
|  |   | Account |      |  ClusterRole    |     | ClusterRole    |  |  |
|  |   +---------+      |  (cluster-wide) |<----| Binding        |  |  |
|  |                    +-----------------+     | (cluster-wide) |  |  |
|  |                                            +----------------+  |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  * Role: What actions are allowed on what resources                  |
|  * RoleBinding: Links Role to Subject                                |
|  * ClusterRole: Cluster-wide permissions                             |
|  * ClusterRoleBinding: Cluster-wide binding                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11.2: ROLES AND ROLEBINDINGS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ROLE (Namespace-scoped)                                              |
|  ========================                                               |
|                                                                         |
|  apiVersion: rbac.authorization.k8s.io/v1                             |
|  kind: Role                                                             |
|  metadata:                                                              |
|    name: pod-reader                                                    |
|    namespace: dev                                                      |
|  rules:                                                                 |
|    - apiGroups: [""]        # "" = core API                          |
|      resources: ["pods"]                                               |
|      verbs: ["get", "list", "watch"]                                  |
|    - apiGroups: [""]                                                   |
|      resources: ["pods/log"]                                          |
|      verbs: ["get"]                                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ROLEBINDING                                                           |
|  ===========                                                            |
|                                                                         |
|  apiVersion: rbac.authorization.k8s.io/v1                             |
|  kind: RoleBinding                                                      |
|  metadata:                                                              |
|    name: read-pods                                                     |
|    namespace: dev                                                      |
|  subjects:                                                              |
|    - kind: User                                                        |
|      name: jane                                                        |
|      apiGroup: rbac.authorization.k8s.io                              |
|    - kind: ServiceAccount                                              |
|      name: my-app                                                      |
|      namespace: dev                                                    |
|  roleRef:                                                               |
|    kind: Role                                                           |
|    name: pod-reader                                                    |
|    apiGroup: rbac.authorization.k8s.io                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  COMMON VERBS                                                          |
|                                                                         |
|  * get, list, watch (read)                                            |
|  * create, update, patch, delete (write)                             |
|  * * (all verbs)                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11.3: CLUSTERROLES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CLUSTERROLE (Cluster-wide)                                           |
|  ===========================                                            |
|                                                                         |
|  apiVersion: rbac.authorization.k8s.io/v1                             |
|  kind: ClusterRole                                                      |
|  metadata:                                                              |
|    name: secret-reader                                                 |
|  rules:                                                                 |
|    - apiGroups: [""]                                                   |
|      resources: ["secrets"]                                            |
|      verbs: ["get", "list"]                                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CLUSTERROLEBINDING                                                    |
|  ===================                                                    |
|                                                                         |
|  apiVersion: rbac.authorization.k8s.io/v1                             |
|  kind: ClusterRoleBinding                                               |
|  metadata:                                                              |
|    name: read-secrets-global                                          |
|  subjects:                                                              |
|    - kind: Group                                                       |
|      name: security-team                                               |
|      apiGroup: rbac.authorization.k8s.io                              |
|  roleRef:                                                               |
|    kind: ClusterRole                                                    |
|    name: secret-reader                                                 |
|    apiGroup: rbac.authorization.k8s.io                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BUILT-IN CLUSTERROLES                                                 |
|                                                                         |
|  * cluster-admin: Full access to everything                          |
|  * admin: Full access within namespace                               |
|  * edit: Read/write to most resources                                |
|  * view: Read-only access                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11.4: SERVICE ACCOUNTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICE ACCOUNTS                                                      |
|  ================                                                       |
|                                                                         |
|  Identity for pods to access Kubernetes API.                         |
|                                                                         |
|  # Create ServiceAccount                                               |
|  apiVersion: v1                                                        |
|  kind: ServiceAccount                                                   |
|  metadata:                                                              |
|    name: my-app                                                        |
|    namespace: dev                                                      |
|                                                                         |
|  # Use in Pod                                                          |
|  spec:                                                                  |
|    serviceAccountName: my-app                                         |
|    containers:                                                          |
|      - name: app                                                       |
|        image: myapp                                                    |
|                                                                         |
|  # Token mounted at /var/run/secrets/kubernetes.io/serviceaccount    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 11.5: SECURITY CONTEXTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  POD SECURITY CONTEXT                                                  |
|  =====================                                                  |
|                                                                         |
|  spec:                                                                  |
|    securityContext:                                                     |
|      runAsNonRoot: true                                                |
|      runAsUser: 1000                                                   |
|      fsGroup: 2000                                                     |
|    containers:                                                          |
|      - name: app                                                       |
|        image: myapp                                                    |
|        securityContext:                                                |
|          allowPrivilegeEscalation: false                              |
|          readOnlyRootFilesystem: true                                 |
|          capabilities:                                                  |
|            drop: ["ALL"]                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RBAC - KEY TAKEAWAYS                                                 |
|                                                                         |
|  COMPONENTS                                                            |
|  ----------                                                            |
|  * Role/ClusterRole: Define permissions                              |
|  * RoleBinding/ClusterRoleBinding: Assign to users                  |
|  * ServiceAccount: Pod identity                                      |
|                                                                         |
|  PRINCIPLE OF LEAST PRIVILEGE                                         |
|  ----------------------------                                          |
|  * Grant minimum required permissions                                |
|  * Use namespace-scoped roles when possible                         |
|  * Avoid cluster-admin                                               |
|                                                                         |
|  COMMANDS                                                              |
|  --------                                                              |
|  kubectl auth can-i <verb> <resource>                                |
|  kubectl auth can-i --list                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 11

