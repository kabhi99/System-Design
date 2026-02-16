# KUBERNETES OPERATORS
*Chapter 14: Automated Application Management*

Operators extend Kubernetes to automate complex application lifecycle
management using custom controllers.

## SECTION 14.1: OPERATOR PATTERN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS AN OPERATOR?                                                 |
|                                                                         |
|  Operator = CRD + Custom Controller                                   |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |   User creates:      Operator watches and acts:               |  |
|  |                                                                 |  |
|  |   PostgresCluster    > Create StatefulSet                     |  |
|  |   replicas: 3        > Create Services                         |  |
|  |   version: 14        > Configure replication                   |  |
|  |                      > Handle backups                          |  |
|  |                      > Manage upgrades                         |  |
|  |                      > Self-healing                            |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  RECONCILIATION LOOP                                                   |
|  ====================                                                   |
|                                                                         |
|  +---------+    +--------------+    +-------------+                   |
|  | Observe |--->|   Compare    |--->|    Act      |                   |
|  | Current |    | Desired vs   |    |  Make it    |                   |
|  |  State  |    |   Current    |    |   match     |                   |
|  +---------+    +--------------+    +-------------+                   |
|       ^                                     |                          |
|       +-------------------------------------+                          |
|                   (Continuous loop)                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 14.2: POPULAR OPERATORS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DATABASE OPERATORS                                                    |
|  ==================                                                    |
|                                                                         |
|  * CloudNativePG (PostgreSQL)                                        |
|  * Percona Operator (MySQL, MongoDB, PostgreSQL)                     |
|  * Strimzi (Apache Kafka)                                            |
|  * Redis Operator                                                     |
|                                                                         |
|  INFRASTRUCTURE OPERATORS                                             |
|  =========================                                              |
|                                                                         |
|  * cert-manager (TLS certificates)                                   |
|  * external-dns (DNS management)                                     |
|  * prometheus-operator (Monitoring)                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXAMPLE: CERT-MANAGER                                                |
|                                                                         |
|  # Install                                                             |
|  kubectl apply -f \                                                     |
|    https://github.com/cert-manager/cert-manager/releases/\            |
|    download/v1.13.0/cert-manager.yaml                                 |
|                                                                         |
|  # Create Certificate resource                                        |
|  apiVersion: cert-manager.io/v1                                       |
|  kind: Certificate                                                      |
|  metadata:                                                              |
|    name: my-cert                                                       |
|  spec:                                                                  |
|    secretName: my-tls-secret                                          |
|    issuerRef:                                                           |
|      name: letsencrypt-prod                                           |
|      kind: ClusterIssuer                                               |
|    dnsNames:                                                            |
|      - example.com                                                     |
|      - www.example.com                                                |
|                                                                         |
|  # Operator automatically:                                            |
|  # 1. Requests cert from Let's Encrypt                               |
|  # 2. Handles DNS/HTTP challenge                                     |
|  # 3. Creates TLS secret                                             |
|  # 4. Renews before expiry                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 14.3: OPERATOR FRAMEWORKS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BUILD YOUR OWN OPERATOR                                              |
|                                                                         |
|  FRAMEWORKS:                                                           |
|  * Operator SDK (Go, Ansible, Helm)                                  |
|  * Kubebuilder (Go)                                                   |
|  * KUDO (Declarative)                                                 |
|  * Metacontroller (JavaScript/Python)                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  OPERATOR SDK QUICKSTART                                              |
|                                                                         |
|  # Initialize                                                          |
|  operator-sdk init --domain mycompany.com --repo my-operator         |
|                                                                         |
|  # Create API (CRD + Controller)                                      |
|  operator-sdk create api --group app --version v1 --kind Database   |
|                                                                         |
|  # Implement reconcile logic in controllers/database_controller.go  |
|                                                                         |
|  # Build and deploy                                                   |
|  make docker-build docker-push IMG=myregistry/my-operator:v1        |
|  make deploy IMG=myregistry/my-operator:v1                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OPERATORS - KEY TAKEAWAYS                                            |
|                                                                         |
|  WHAT                                                                  |
|  ----                                                                  |
|  * CRD + Controller = Operator                                       |
|  * Encodes operational knowledge                                     |
|  * Automates Day 2 operations                                        |
|                                                                         |
|  PATTERN                                                               |
|  -------                                                               |
|  * Watch custom resources                                            |
|  * Compare desired vs actual state                                   |
|  * Take action to reconcile                                          |
|                                                                         |
|  POPULAR OPERATORS                                                     |
|  -----------------                                                     |
|  * cert-manager, prometheus-operator                                 |
|  * Database operators (PostgreSQL, MySQL)                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 14

