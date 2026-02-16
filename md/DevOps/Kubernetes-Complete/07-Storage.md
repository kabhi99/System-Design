# KUBERNETES STORAGE
*Chapter 7: Persistent Volumes and Storage Classes*

Kubernetes provides a powerful abstraction for storage that separates
storage provisioning from consumption.

## SECTION 7.1: WHY PERSISTENT STORAGE?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM: PODS ARE EPHEMERAL                                        |
|  ================================                                       |
|                                                                         |
|  Without persistent storage:                                            |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |   MySQL Pod                                                      |   |
|  |   +-----------------------------------------------------------+  |   |
|  |   |                                                           |  |   |
|  |   |  Container filesystem                                     |  |   |
|  |   |  /var/lib/mysql (data stored here)                        |  |   |
|  |   |                                                           |  |   |
|  |   |  users table: 10,000 records                              |  |   |
|  |   |  orders table: 50,000 records                             |  |   |
|  |   |                                                           |  |   |
|  |   +-----------------------------------------------------------+  |   |
|  |                                                                  |   |
|  |   Pod crashes or gets rescheduled...                             |   |
|  |                                                                  |   |
|  |                         POD DIES                                 |   |
|  |                                                                  |   |
|  |   ALL DATA LOST! Container filesystem is GONE.                   |   |
|  |   New pod starts with EMPTY database!                            |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  PROBLEMS:                                                              |
|                                                                         |
|  1. DATA LOSS ON RESTART                                                |
|     * Container storage is temporary                                    |
|     * When pod dies, data dies with it                                  |
|                                                                         |
|  2. NO SHARING BETWEEN CONTAINERS                                       |
|     * Each container has isolated filesystem                            |
|     * Can't share data between containers in pod                        |
|                                                                         |
|  3. NO DATA PERSISTENCE ACROSS RESCHEDULING                             |
|     * Pod moves to different node > data stays on old node              |
|     * New pod can't access the old data                                 |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  THE SOLUTION: PERSISTENT VOLUMES                                       |
|  =================================                                      |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |   MySQL Pod                                                      |   |
|  |   +-----------------------------------------------------------+  |   |
|  |   |                                                           |  |   |
|  |   |  Container mounts external volume:                        |  |   |
|  |   |  /var/lib/mysql > PersistentVolume                        |  |   |
|  |   |                         |                                 |  |   |
|  |   +-------------------------+---------------------------------+  |   |
|  |                             |                                    |   |
|  |   Pod crashes...            |                                    |   |
|  |                             |                                    |   |
|  |                           |                                      |   |
|  |                             |                                    |   |
|  |   New pod created...        |                                    |   |
|  |                             |                                    |   |
|  |   +-------------------------+---------------------------------+  |   |
|  |   |  Container remounts:    |                                 |  |   |
|  |   |  /var/lib/mysql > PersistentVolume                        |  |   |
|  |   +-------------------------+---------------------------------+  |   |
|  |                             |                                    |   |
|  |                             v                                    |   |
|  |   +-----------------------------------------------------------+  |   |
|  |   |           PERSISTENT VOLUME (AWS EBS)                     |  |   |
|  |   |                                                           |  |   |
|  |   |   Data SURVIVES pod restarts!                             |  |   |
|  |   |   users: 10,000 records Y                                 |  |   |
|  |   |   orders: 50,000 records Y                                |  |   |
|  |   |                                                           |  |   |
|  |   +-----------------------------------------------------------+  |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  WHY PV + PVC SEPARATION? (Two-Layer Abstraction)                       |
|  =================================================                      |
|                                                                         |
|  PROBLEM: Different roles, different concerns                           |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |   DEVELOPER (app team):              ADMIN (ops team):           |   |
|  |   "I need 10Gi storage"              "I'll create AWS EBS        |   |
|  |   "I don't care HOW"                  with encryption,           |   |
|  |                                       IOPS, backup policy"       |   |
|  |                                                                  |   |
|  |   Creates: PVC                       Creates: PV                 |   |
|  |   (what I need)                      (how to provide it)         |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  BENEFITS:                                                              |
|                                                                         |
|  1. SEPARATION OF CONCERNS                                              |
|     * Dev doesn't need to know storage details                          |
|     * Admin manages storage infrastructure                              |
|                                                                         |
|  2. PORTABILITY                                                         |
|     * Same PVC works on AWS, GCP, on-prem                               |
|     * Admin provides different PVs per environment                      |
|                                                                         |
|  3. REUSABILITY                                                         |
|     * Admin creates storage once                                        |
|     * Multiple apps can claim it                                        |
|                                                                         |
|  4. SECURITY                                                            |
|     * Dev doesn't need AWS/cloud credentials                            |
|     * Admin controls storage policies                                   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  WHEN TO USE PERSISTENT STORAGE                                         |
|  ===============================                                        |
|                                                                         |
|  USE PERSISTENT VOLUMES FOR:                                            |
|  ----------------------------                                           |
|  * Databases (MySQL, PostgreSQL, MongoDB)                               |
|  * Message queues (Kafka, RabbitMQ)                                     |
|  * File uploads (user content)                                          |
|  * Application logs (if persisting to disk)                             |
|  * Cache that needs to survive restarts (Redis with persistence)        |
|  * Stateful applications (Elasticsearch, Cassandra)                     |
|                                                                         |
|  DON'T NEED PERSISTENT VOLUMES FOR:                                     |
|  -----------------------------------                                    |
|  * Stateless web servers                                                |
|  * API services (state in external DB)                                  |
|  * Temporary processing (data discarded after)                          |
|  * Cache that can be rebuilt (Redis as pure cache)                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.2: STORAGE CONCEPTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE STORAGE ABSTRACTION                                                |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |   Pod                                                             |  |
|  |    |                                                              |  |
|  |    | "I need 10Gi of storage"                                     |  |
|  |    v                                                              |  |
|  |   PersistentVolumeClaim (PVC)  < Developer creates                |  |
|  |    |                                                              |  |
|  |    | Binds to                                                     |  |
|  |    v                                                              |  |
|  |   PersistentVolume (PV)        < Admin creates (or dynamic)       |  |
|  |    |                                                              |  |
|  |    | Backed by                                                    |  |
|  |    v                                                              |  |
|  |   Actual Storage (AWS EBS, GCE PD, NFS, etc.)                     |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  PV: The actual storage resource (created by admin)                     |
|  PVC: A request for storage (created by developer)                      |
|  StorageClass: Template for DYNAMIC provisioning (auto-create PV)       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.2: PERSISTENT VOLUMES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PERSISTENT VOLUME (Admin creates)                                      |
|  ==================================                                     |
|                                                                         |
|  apiVersion: v1                                                         |
|  kind: PersistentVolume                                                 |
|  metadata:                                                              |
|    name: my-pv                                                          |
|  spec:                                                                  |
|    capacity:                                                            |
|      storage: 10Gi                                                      |
|    accessModes:                                                         |
|      - ReadWriteOnce                                                    |
|    persistentVolumeReclaimPolicy: Retain                                |
|    storageClassName: standard                                           |
|    hostPath:                     # For testing only                     |
|      path: /data/my-pv                                                  |
|                                                                         |
|  # Or with cloud storage                                                |
|  spec:                                                                  |
|    awsElasticBlockStore:                                                |
|      volumeID: vol-12345678                                             |
|      fsType: ext4                                                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ACCESS MODES                                                           |
|  ============                                                           |
|                                                                         |
|  * ReadWriteOnce (RWO): Single node read-write                          |
|  * ReadOnlyMany (ROX): Multiple nodes read-only                         |
|  * ReadWriteMany (RWX): Multiple nodes read-write                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  RECLAIM POLICIES                                                       |
|  ================                                                       |
|                                                                         |
|  * Retain: Keep data after PVC deleted (manual cleanup)                 |
|  * Delete: Delete storage when PVC deleted                              |
|  * Recycle: Basic scrub (deprecated)                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.3: PERSISTENT VOLUME CLAIMS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PVC (User requests)                                                    |
|  ====================                                                   |
|                                                                         |
|  apiVersion: v1                                                         |
|  kind: PersistentVolumeClaim                                            |
|  metadata:                                                              |
|    name: my-pvc                                                         |
|  spec:                                                                  |
|    accessModes:                                                         |
|      - ReadWriteOnce                                                    |
|    resources:                                                           |
|      requests:                                                          |
|        storage: 5Gi                                                     |
|    storageClassName: standard                                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USING PVC IN POD                                                       |
|  =================                                                      |
|                                                                         |
|  apiVersion: v1                                                         |
|  kind: Pod                                                              |
|  metadata:                                                              |
|    name: my-pod                                                         |
|  spec:                                                                  |
|    containers:                                                          |
|      - name: app                                                        |
|        image: nginx                                                     |
|        volumeMounts:                                                    |
|          - mountPath: /data                                             |
|            name: my-storage                                             |
|    volumes:                                                             |
|      - name: my-storage                                                 |
|        persistentVolumeClaim:                                           |
|          claimName: my-pvc                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.4: STORAGE CLASSES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DYNAMIC PROVISIONING                                                   |
|  =====================                                                  |
|                                                                         |
|  StorageClass lets Kubernetes create PVs automatically.                 |
|                                                                         |
|  apiVersion: storage.k8s.io/v1                                          |
|  kind: StorageClass                                                     |
|  metadata:                                                              |
|    name: fast-ssd                                                       |
|  provisioner: kubernetes.io/aws-ebs                                     |
|  parameters:                                                            |
|    type: gp3                                                            |
|    iopsPerGB: "50"                                                      |
|  reclaimPolicy: Delete                                                  |
|  volumeBindingMode: WaitForFirstConsumer                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PVC WITH STORAGECLASS                                                  |
|  ======================                                                 |
|                                                                         |
|  apiVersion: v1                                                         |
|  kind: PersistentVolumeClaim                                            |
|  metadata:                                                              |
|    name: fast-storage                                                   |
|  spec:                                                                  |
|    accessModes:                                                         |
|      - ReadWriteOnce                                                    |
|    storageClassName: fast-ssd    # Use StorageClass                     |
|    resources:                                                           |
|      requests:                                                          |
|        storage: 100Gi                                                   |
|                                                                         |
|  Kubernetes automatically provisions the volume!                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  COMMON PROVISIONERS                                                    |
|                                                                         |
|  * kubernetes.io/aws-ebs (AWS EBS)                                      |
|  * kubernetes.io/gce-pd (GCP Persistent Disk)                           |
|  * kubernetes.io/azure-disk (Azure Disk)                                |
|  * rancher.io/local-path (Local path)                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STORAGE - KEY TAKEAWAYS                                                |
|                                                                         |
|  COMPONENTS                                                             |
|  ----------                                                             |
|  * PV: Actual storage resource                                          |
|  * PVC: Request for storage                                             |
|  * StorageClass: Template for dynamic provisioning                      |
|                                                                         |
|  ACCESS MODES                                                           |
|  ------------                                                           |
|  * RWO: Single node read-write                                          |
|  * ROX: Multiple nodes read-only                                        |
|  * RWX: Multiple nodes read-write                                       |
|                                                                         |
|  DYNAMIC PROVISIONING                                                   |
|  ---------------------                                                  |
|  StorageClass + PVC = automatic PV creation                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 7

