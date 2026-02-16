# KUBERNETES PRODUCTION BEST PRACTICES
*Chapter 20: Running Kubernetes in Production*

This chapter covers essential practices for running reliable,
secure, and maintainable Kubernetes clusters in production.

## SECTION 20.1: RESOURCE MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ALWAYS SET RESOURCE REQUESTS AND LIMITS                                |
|  ========================================                               |
|                                                                         |
|  spec:                                                                  |
|    containers:                                                          |
|      - name: app                                                        |
|        resources:                                                       |
|          requests:           # Scheduling guarantee                     |
|            cpu: 100m                                                    |
|            memory: 128Mi                                                |
|          limits:             # Maximum allowed                          |
|            cpu: 500m                                                    |
|            memory: 512Mi                                                |
|                                                                         |
|  WHY?                                                                   |
|  * Requests: Scheduler uses to place pods                               |
|  * Limits: Prevents runaway resource consumption                        |
|  * Without limits: One pod can starve others                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USE LIMITRANGE AND RESOURCEQUOTA                                       |
|  =================================                                      |
|                                                                         |
|  Set namespace-level defaults and limits.                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 20.2: HIGH AVAILABILITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REPLICAS AND ANTI-AFFINITY                                             |
|  ===========================                                            |
|                                                                         |
|  spec:                                                                  |
|    replicas: 3                  # Multiple replicas                     |
|    template:                                                            |
|      spec:                                                              |
|        affinity:                                                        |
|          podAntiAffinity:       # Spread across nodes                   |
|            preferredDuringSchedulingIgnoredDuringExecution:             |
|              - weight: 100                                              |
|                podAffinityTerm:                                         |
|                  labelSelector:                                         |
|                    matchLabels:                                         |
|                      app: myapp                                         |
|                  topologyKey: kubernetes.io/hostname                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  POD DISRUPTION BUDGET                                                  |
|  ======================                                                 |
|                                                                         |
|  Ensure minimum availability during maintenance.                        |
|                                                                         |
|  apiVersion: policy/v1                                                  |
|  kind: PodDisruptionBudget                                              |
|  metadata:                                                              |
|    name: myapp-pdb                                                      |
|  spec:                                                                  |
|    minAvailable: 2      # At least 2 must be running                    |
|    # Or: maxUnavailable: 1                                              |
|    selector:                                                            |
|      matchLabels:                                                       |
|        app: myapp                                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 20.3: HEALTH CHECKS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LIVENESS, READINESS, STARTUP PROBES                                    |
|  ===================================                                    |
|                                                                         |
|  spec:                                                                  |
|    containers:                                                          |
|      - name: app                                                        |
|                                                                         |
|        # Restart if unhealthy                                           |
|        livenessProbe:                                                   |
|          httpGet:                                                       |
|            path: /healthz                                               |
|            port: 8080                                                   |
|          initialDelaySeconds: 10                                        |
|          periodSeconds: 10                                              |
|          failureThreshold: 3                                            |
|                                                                         |
|        # Remove from service if not ready                               |
|        readinessProbe:                                                  |
|          httpGet:                                                       |
|            path: /ready                                                 |
|            port: 8080                                                   |
|          initialDelaySeconds: 5                                         |
|          periodSeconds: 5                                               |
|                                                                         |
|        # For slow-starting apps                                         |
|        startupProbe:                                                    |
|          httpGet:                                                       |
|            path: /healthz                                               |
|            port: 8080                                                   |
|          failureThreshold: 30                                           |
|          periodSeconds: 10                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 20.4: SECURITY BEST PRACTICES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SECURITY CHECKLIST                                                     |
|                                                                         |
|  o Run as non-root                                                      |
|    securityContext:                                                     |
|      runAsNonRoot: true                                                 |
|      runAsUser: 1000                                                    |
|                                                                         |
|  o Read-only filesystem                                                 |
|    securityContext:                                                     |
|      readOnlyRootFilesystem: true                                       |
|                                                                         |
|  o Drop capabilities                                                    |
|    securityContext:                                                     |
|      capabilities:                                                      |
|        drop: ["ALL"]                                                    |
|                                                                         |
|  o No privilege escalation                                              |
|    securityContext:                                                     |
|      allowPrivilegeEscalation: false                                    |
|                                                                         |
|  o Use NetworkPolicies                                                  |
|                                                                         |
|  o Use RBAC with least privilege                                        |
|                                                                         |
|  o Scan images for vulnerabilities                                      |
|                                                                         |
|  o Use specific image tags (not :latest)                                |
|                                                                         |
|  o Store secrets in external secret manager                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 20.5: OPERATIONAL PRACTICES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LABELS AND ANNOTATIONS                                                 |
|  =======================                                                |
|                                                                         |
|  metadata:                                                              |
|    labels:                                                              |
|      app.kubernetes.io/name: myapp                                      |
|      app.kubernetes.io/version: "1.0.0"                                 |
|      app.kubernetes.io/component: backend                               |
|      app.kubernetes.io/part-of: myplatform                              |
|      app.kubernetes.io/managed-by: helm                                 |
|    annotations:                                                         |
|      description: "Backend API service"                                 |
|      owner: "team-backend@company.com"                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  GRACEFUL SHUTDOWN                                                      |
|  ==================                                                     |
|                                                                         |
|  spec:                                                                  |
|    terminationGracePeriodSeconds: 60   # Time to finish work            |
|    containers:                                                          |
|      - name: app                                                        |
|        lifecycle:                                                       |
|          preStop:                                                       |
|            exec:                                                        |
|              command: ["/bin/sh", "-c", "sleep 10"]                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BACKUP AND DISASTER RECOVERY                                           |
|  =============================                                          |
|                                                                         |
|  * Use Velero for cluster backup                                        |
|  * Backup etcd regularly                                                |
|  * Store manifests in Git (GitOps)                                      |
|  * Document recovery procedures                                         |
|  * Test recovery regularly                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 20.6: PRODUCTION CHECKLIST

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PRE-PRODUCTION CHECKLIST                                               |
|                                                                         |
|  RESOURCES                                                              |
|  o Resource requests and limits set                                     |
|  o HPA configured for scaling                                           |
|  o ResourceQuotas per namespace                                         |
|                                                                         |
|  RELIABILITY                                                            |
|  o Multiple replicas                                                    |
|  o Pod anti-affinity configured                                         |
|  o PodDisruptionBudget defined                                          |
|  o All three probes configured                                          |
|                                                                         |
|  SECURITY                                                               |
|  o Non-root containers                                                  |
|  o Read-only filesystem                                                 |
|  o NetworkPolicies in place                                             |
|  o RBAC configured                                                      |
|  o Secrets encrypted at rest                                            |
|                                                                         |
|  OBSERVABILITY                                                          |
|  o Logging configured                                                   |
|  o Metrics exposed                                                      |
|  o Dashboards created                                                   |
|  o Alerts defined                                                       |
|                                                                         |
|  OPERATIONS                                                             |
|  o Standard labels applied                                              |
|  o Graceful shutdown configured                                         |
|  o Backup strategy defined                                              |
|  o Runbooks documented                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PRODUCTION BEST PRACTICES - KEY TAKEAWAYS                              |
|                                                                         |
|  RESOURCES                                                              |
|  ---------                                                              |
|  * Always set requests and limits                                       |
|  * Use LimitRange and ResourceQuota                                     |
|                                                                         |
|  AVAILABILITY                                                           |
|  ------------                                                           |
|  * Multiple replicas                                                    |
|  * Anti-affinity for spread                                             |
|  * PodDisruptionBudget                                                  |
|                                                                         |
|  HEALTH                                                                 |
|  ------                                                                 |
|  * Liveness, Readiness, Startup probes                                  |
|                                                                         |
|  SECURITY                                                               |
|  --------                                                               |
|  * Non-root, read-only, drop capabilities                               |
|  * NetworkPolicies, RBAC                                                |
|                                                                         |
|  OPERATIONS                                                             |
|  ----------                                                             |
|  * Standard labels                                                      |
|  * Graceful shutdown                                                    |
|  * Backup and recovery                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 20

