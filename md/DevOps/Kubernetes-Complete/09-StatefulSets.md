# KUBERNETES STATEFULSETS
*Chapter 9: Stateful Applications*

StatefulSets manage stateful applications that require stable network
identities, persistent storage, and ordered deployment.

## SECTION 9.1: STATEFULSET vs DEPLOYMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DEPLOYMENT (Stateless)          STATEFULSET (Stateful)               |
|  ======================          ========================              |
|                                                                         |
|  Pod names: random               Pod names: predictable                |
|  web-abc123                       mysql-0, mysql-1, mysql-2            |
|  web-xyz789                                                             |
|                                                                         |
|  Pods interchangeable            Pods have identity                    |
|                                                                         |
|  Shared storage or none          Each pod gets own storage             |
|                                                                         |
|  Scale in any order              Scale in order (0>1>2)               |
|                                   Delete in reverse (2>1>0)           |
|                                                                         |
|  USE FOR:                        USE FOR:                              |
|  * Web servers                   * Databases (MySQL, Postgres)        |
|  * API services                  * Message queues (Kafka)             |
|  * Microservices                 * Distributed stores (Cassandra)    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9.2: STATEFULSET DEFINITION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  apiVersion: apps/v1                                                   |
|  kind: StatefulSet                                                      |
|  metadata:                                                              |
|    name: mysql                                                         |
|  spec:                                                                  |
|    serviceName: mysql     # Headless service name                     |
|    replicas: 3                                                         |
|    selector:                                                            |
|      matchLabels:                                                       |
|        app: mysql                                                      |
|    template:                                                            |
|      metadata:                                                          |
|        labels:                                                          |
|          app: mysql                                                    |
|      spec:                                                              |
|        containers:                                                      |
|          - name: mysql                                                 |
|            image: mysql:8.0                                            |
|            ports:                                                       |
|              - containerPort: 3306                                    |
|            volumeMounts:                                               |
|              - name: data                                              |
|                mountPath: /var/lib/mysql                              |
|    volumeClaimTemplates:    # Each pod gets own PVC                  |
|      - metadata:                                                        |
|          name: data                                                    |
|        spec:                                                            |
|          accessModes: ["ReadWriteOnce"]                               |
|          resources:                                                     |
|            requests:                                                    |
|              storage: 10Gi                                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HEADLESS SERVICE (Required)                                          |
|  ============================                                           |
|                                                                         |
|  apiVersion: v1                                                        |
|  kind: Service                                                          |
|  metadata:                                                              |
|    name: mysql                                                         |
|  spec:                                                                  |
|    clusterIP: None        # Headless!                                 |
|    selector:                                                            |
|      app: mysql                                                        |
|    ports:                                                               |
|      - port: 3306                                                      |
|                                                                         |
|  DNS records created:                                                  |
|  * mysql-0.mysql.default.svc.cluster.local                           |
|  * mysql-1.mysql.default.svc.cluster.local                           |
|  * mysql-2.mysql.default.svc.cluster.local                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9.3: HEADLESS SERVICE EXPLAINED

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS A HEADLESS SERVICE?                                          |
|  ============================                                           |
|                                                                         |
|  A Service with clusterIP: None                                       |
|  * No ClusterIP assigned                                              |
|  * DNS returns POD IPs directly (not Service IP)                     |
|  * Client can reach SPECIFIC pods by name                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### NORMAL SERVICE vs HEADLESS SERVICE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NORMAL SERVICE (ClusterIP)                                            |
|  ==========================                                             |
|                                                                         |
|      Client                                                             |
|         |                                                               |
|         |  nslookup web-svc                                            |
|         |  > Returns: 10.96.0.100 (Service IP)                        |
|         v                                                               |
|   +-----------------------+                                            |
|   |      SERVICE          |                                            |
|   |   ClusterIP:          |  < Traffic goes HERE first                |
|   |   10.96.0.100         |                                            |
|   |                       |                                            |
|   |   Load balances       |  < Randomly picks a pod                   |
|   +-----------+-----------+                                            |
|               |                                                         |
|       +-------+-------+                                                |
|       v       v       v                                                |
|   +------++------++------+                                            |
|   |Pod 1 ||Pod 2 ||Pod 3 |                                            |
|   +------++------++------+                                            |
|                                                                         |
|   Client CANNOT choose which pod! Service decides randomly.          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HEADLESS SERVICE (clusterIP: None)                                    |
|  ==================================                                     |
|                                                                         |
|      Client                                                             |
|         |                                                               |
|         |  nslookup mysql                                              |
|         |  > Returns: 10.0.2.5, 10.0.2.6, 10.0.2.7 (Pod IPs!)        |
|         |                                                               |
|         |  nslookup mysql-0.mysql                                      |
|         |  > Returns: 10.0.2.5 (Specific Pod!)                        |
|         |                                                               |
|         |          NO Service IP in the middle!                        |
|         |          Goes DIRECTLY to pods                               |
|         |                                                               |
|         +-----------------------------------------+                    |
|         |                    |                    |                    |
|         v                    v                    v                    |
|   +-----------+       +-----------+       +-----------+               |
|   | mysql-0   |       | mysql-1   |       | mysql-2   |               |
|   | 10.0.2.5  |       | 10.0.2.6  |       | 10.0.2.7  |               |
|   +-----------+       +-----------+       +-----------+               |
|                                                                         |
|   Client CAN reach specific pods by name!                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHY STATEFULSET NEEDS HEADLESS SERVICE?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REASON 1: STABLE DNS FOR EACH POD                                    |
|  ===================================                                    |
|                                                                         |
|  Each pod gets its own DNS name that NEVER changes                    |
|                                                                         |
|  mysql-0.mysql.default.svc.cluster.local > always mysql-0            |
|  mysql-1.mysql.default.svc.cluster.local > always mysql-1            |
|  mysql-2.mysql.default.svc.cluster.local > always mysql-2            |
|                                                                         |
|  Even if pod restarts > same DNS > clients can reconnect!            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REASON 2: DATABASE REPLICATION NEEDS DIRECT ACCESS                   |
|  ===================================================                    |
|                                                                         |
|  MySQL/PostgreSQL replication:                                         |
|  * Replica needs to connect to SPECIFIC master                        |
|  * Can't use random load balancing!                                   |
|                                                                         |
|     +--------------+                                                   |
|     |   mysql-0    |  < MASTER                                        |
|     |   (Primary)  |                                                   |
|     +------+-------+                                                   |
|            |                                                            |
|            | Replicas connect to: mysql-0.mysql                       |
|     +------+------+                                                    |
|     |             |                                                    |
|     v             v                                                    |
| +----------+ +----------+                                             |
| | mysql-1  | | mysql-2  |  < REPLICAS                                |
| | (Replica)| | (Replica)|                                             |
| +----------+ +----------+                                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REASON 3: CLIENT CHOOSES WHICH POD TO TALK TO                        |
|  ================================================                       |
|                                                                         |
|  Application can decide:                                               |
|  * Write operations > mysql-0 (master)                                |
|  * Read operations  > mysql-1 or mysql-2 (replicas)                  |
|                                                                         |
|  This is READ/WRITE SPLITTING for performance!                        |
|                                                                         |
|     Application                                                        |
|         |                                                               |
|         +-- INSERT/UPDATE > mysql-0.mysql (master)                   |
|         |                                                               |
|         +-- SELECT        > mysql-1.mysql (replica)                  |
|                            or mysql-2.mysql (replica)                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REASON 4: CLUSTER FORMATION                                          |
|  ============================                                           |
|                                                                         |
|  Distributed systems need to discover each other:                     |
|                                                                         |
|  Kafka brokers:       kafka-0, kafka-1, kafka-2                       |
|  ZooKeeper nodes:     zk-0, zk-1, zk-2                                |
|  Elasticsearch nodes: es-0, es-1, es-2                                |
|                                                                         |
|  Each node must know EXACTLY where other nodes are!                  |
|  Headless Service provides predictable DNS names.                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DNS RECORDS CREATED BY HEADLESS SERVICE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICE-LEVEL DNS (returns ALL pod IPs)                              |
|  =======================================                                |
|                                                                         |
|  mysql.default.svc.cluster.local                                      |
|  +-+-+ +--+--+ +++ +----+----+                                        |
|    |      |     |       |                                              |
|  service  namespace  "svc"  "cluster.local"                            |
|                                                                         |
|  DNS Response: 10.0.2.5, 10.0.2.6, 10.0.2.7 (all pods)               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  POD-LEVEL DNS (returns SPECIFIC pod IP)                              |
|  =======================================                                |
|                                                                         |
|  mysql-0.mysql.default.svc.cluster.local > 10.0.2.5                  |
|  +--+--+ +-+-+                                                         |
|   pod    service                                                        |
|   name   name                                                           |
|                                                                         |
|  mysql-1.mysql.default.svc.cluster.local > 10.0.2.6                  |
|  mysql-2.mysql.default.svc.cluster.local > 10.0.2.7                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SHORTHAND DNS (within same namespace)                                |
|  =====================================                                  |
|                                                                         |
|  mysql-0.mysql   < Short form, works within namespace                |
|  mysql-1.mysql                                                         |
|  mysql-2.mysql                                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMPARISON TABLE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +--------------------+---------------------+------------------------+ |
|  | Feature            | Normal Service      | Headless Service       | |
|  +--------------------+---------------------+------------------------+ |
|  | clusterIP          | 10.96.x.x (assigned)| None                   | |
|  +--------------------+---------------------+------------------------+ |
|  | DNS returns        | Service IP          | All Pod IPs            | |
|  +--------------------+---------------------+------------------------+ |
|  | Load balancing     | Yes (kube-proxy)    | No (client decides)    | |
|  +--------------------+---------------------+------------------------+ |
|  | Access specific pod| X NO               | Y YES (pod-0.svc)     | |
|  +--------------------+---------------------+------------------------+ |
|  | Individual pod DNS | X NO               | Y YES                  | |
|  +--------------------+---------------------+------------------------+ |
|  | Use with           | Deployment          | StatefulSet            | |
|  +--------------------+---------------------+------------------------+ |
|  | Use case           | Stateless apps      | Databases, Kafka, etc  | |
|  |                    | (web servers, APIs) | (stateful apps)        | |
|  +--------------------+---------------------+------------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

### REAL-WORLD EXAMPLE: MySQL MASTER-REPLICA

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HEADLESS SERVICE YAML                                                 |
|  =====================                                                  |
|                                                                         |
|  apiVersion: v1                                                        |
|  kind: Service                                                          |
|  metadata:                                                              |
|    name: mysql                   # Service name                        |
|  spec:                                                                  |
|    clusterIP: None               # < HEADLESS!                        |
|    selector:                                                            |
|      app: mysql                                                        |
|    ports:                                                               |
|      - port: 3306                                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HOW APPLICATION USES IT                                               |
|  ========================                                               |
|                                                                         |
|  # Connect to master for writes                                        |
|  mysql -h mysql-0.mysql -u root -p                                    |
|                                                                         |
|  # Connect to replica for reads                                        |
|  mysql -h mysql-1.mysql -u root -p                                    |
|                                                                         |
|  # Application config                                                  |
|  MYSQL_MASTER_HOST=mysql-0.mysql                                      |
|  MYSQL_REPLICA_HOST=mysql-1.mysql,mysql-2.mysql                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REPLICA CONFIGURATION (in mysql-1, mysql-2)                          |
|  ============================================                           |
|                                                                         |
|  CHANGE MASTER TO                                                      |
|    MASTER_HOST='mysql-0.mysql',   < Uses headless DNS!               |
|    MASTER_USER='repl',                                                 |
|    MASTER_PASSWORD='password';                                        |
|                                                                         |
|  If mysql-0 pod restarts:                                             |
|  * Gets new IP (e.g., 10.0.2.99)                                     |
|  * DNS mysql-0.mysql > 10.0.2.99 (auto-updated!)                    |
|  * Replicas reconnect automatically                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### VERIFY HEADLESS SERVICE

```bash
# Check service has no ClusterIP
kubectl get svc mysql
# NAME    TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)    AGE
# mysql   ClusterIP   None         <none>        3306/TCP   5m

# Verify DNS returns pod IPs (from inside a pod)
kubectl run test --rm -it --image=busybox -- nslookup mysql
# Server:    10.96.0.10
# Name:      mysql.default.svc.cluster.local
# Address 1: 10.0.2.5 mysql-0.mysql.default.svc.cluster.local
# Address 2: 10.0.2.6 mysql-1.mysql.default.svc.cluster.local
# Address 3: 10.0.2.7 mysql-2.mysql.default.svc.cluster.local

# Verify individual pod DNS
kubectl run test --rm -it --image=busybox -- nslookup mysql-0.mysql
# Name:      mysql-0.mysql.default.svc.cluster.local
# Address 1: 10.0.2.5
```

## SECTION 9.4: POD IDENTITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STABLE NETWORK IDENTITY                                              |
|  ========================                                               |
|                                                                         |
|  Pod Name: <statefulset-name>-<ordinal>                               |
|  * mysql-0, mysql-1, mysql-2                                          |
|                                                                         |
|  Hostname: Same as pod name                                           |
|  * mysql-0.mysql.default.svc.cluster.local                           |
|                                                                         |
|  Even if pod is deleted and recreated:                               |
|  * Same name (mysql-0)                                                |
|  * Same DNS                                                            |
|  * Same PVC (data preserved)                                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ORDERED OPERATIONS                                                    |
|  ===================                                                    |
|                                                                         |
|  Create: mysql-0 > mysql-1 > mysql-2                                 |
|  (Each pod must be Running before next starts)                       |
|                                                                         |
|  Delete: mysql-2 > mysql-1 > mysql-0                                 |
|  (Reverse order)                                                       |
|                                                                         |
|  Scale up: Add mysql-3, mysql-4...                                   |
|  Scale down: Remove highest ordinals first                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STATEFULSETS - KEY TAKEAWAYS                                         |
|                                                                         |
|  FEATURES                                                              |
|  --------                                                              |
|  * Stable pod names (mysql-0, mysql-1)                               |
|  * Stable DNS (pod-name.service.namespace)                           |
|  * Per-pod persistent storage                                        |
|  * Ordered deployment/scaling                                         |
|                                                                         |
|  REQUIREMENTS                                                          |
|  ------------                                                          |
|  * Headless Service (clusterIP: None)                               |
|  * volumeClaimTemplates for storage                                  |
|                                                                         |
|  USE CASES                                                             |
|  ---------                                                             |
|  * Databases (MySQL, PostgreSQL)                                     |
|  * Distributed systems (Kafka, ZooKeeper)                           |
|  * Any app needing stable identity                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 9

