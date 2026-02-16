# CHAPTER 3: WORKLOADS
*Deployments, ReplicaSets, and Application Management*

In production, you never create Pods directly. Instead, you use workload
controllers that manage Pods for you. This chapter covers the essential
workload resources: ReplicaSets and Deployments.

## SECTION 3.1: WHY NOT JUST PODS?

### THE PROBLEM WITH BARE PODS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PODS ARE EPHEMERAL                                                    |
|                                                                         |
|  If you create a Pod directly:                                        |
|                                                                         |
|  kubectl run nginx --image=nginx                                      |
|                                                                         |
|  PROBLEMS:                                                             |
|                                                                         |
|  1. NO AUTO-RESTART                                                    |
|     Pod crashes > Pod gone forever                                    |
|     Node fails > Pod lost                                             |
|                                                                         |
|  2. NO SCALING                                                         |
|     Traffic increases > Can't add more pods easily                    |
|                                                                         |
|  3. NO ROLLING UPDATES                                                 |
|     New version? Delete old pod, create new one                       |
|     = Downtime                                                        |
|                                                                         |
|  4. NO ROLLBACKS                                                       |
|     New version broken? Manually recreate old version                 |
|                                                                         |
|  SOLUTION: Use Controllers (Deployments)                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.2: REPLICASETS

### WHAT IS A REPLICASET?

A ReplicaSet ensures a specified number of pod replicas are running:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REPLICASET FUNCTION                                                   |
|                                                                         |
|  Desired State: 3 replicas                                            |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                        ReplicaSet                                |   |
|  |                                                                  |   |
|  |  Selector: app=nginx                                            |   |
|  |                                                                  |   |
|  |  +---------+    +---------+    +---------+                     |   |
|  |  |  Pod 1  |    |  Pod 2  |    |  Pod 3  |                     |   |
|  |  |app=nginx|    |app=nginx|    |app=nginx|                     |   |
|  |  +---------+    +---------+    +---------+                     |   |
|  |                                                                  |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  SELF-HEALING:                                                         |
|                                                                         |
|  Pod 2 crashes...                                                      |
|  +---------+         X           +---------+                          |
|  |  Pod 1  |                     |  Pod 3  |                          |
|  +---------+                     +---------+                          |
|                                                                         |
|  ReplicaSet detects only 2 pods, creates Pod 4                        |
|  +---------+    +---------+    +---------+                           |
|  |  Pod 1  |    |  Pod 4  |    |  Pod 3  |                           |
|  +---------+    +---------+    +---------+                           |
|                                                                         |
|  Back to 3 replicas!                                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### REPLICASET MANIFEST

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: nginx-replicaset
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:                    # Pod template
    metadata:
      labels:
        app: nginx            # Must match selector!
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
```

IMPORTANT: DON'T USE REPLICASETS DIRECTLY!

Use Deployments instead—they manage ReplicaSets for you and provide
rolling updates, rollbacks, and more.

## SECTION 3.3: DEPLOYMENTS

### WHAT IS A DEPLOYMENT?

A Deployment manages ReplicaSets and provides declarative updates:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DEPLOYMENT HIERARCHY                                                  |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                        DEPLOYMENT                                |   |
|  |                    nginx-deployment                              |   |
|  |                                                                  |   |
|  |  * Manages ReplicaSets                                          |   |
|  |  * Handles rolling updates                                      |   |
|  |  * Enables rollbacks                                            |   |
|  |  * Maintains history                                            |   |
|  |                                                                  |   |
|  |  +------------------------------------------------------------+ |   |
|  |  |                     REPLICASET                             | |   |
|  |  |               nginx-deployment-abc123                      | |   |
|  |  |                                                            | |   |
|  |  |  +---------+    +---------+    +---------+               | |   |
|  |  |  |  Pod 1  |    |  Pod 2  |    |  Pod 3  |               | |   |
|  |  |  +---------+    +---------+    +---------+               | |   |
|  |  |                                                            | |   |
|  |  +------------------------------------------------------------+ |   |
|  |                                                                  |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  YOU > Deployment > ReplicaSet > Pods                                 |
|        (manage)     (manages)    (manages)                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DEPLOYMENT MANIFEST

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "200m"
            memory: "256Mi"
```

## SECTION 3.4: ROLLING UPDATES

### HOW ROLLING UPDATES WORK

When you update a Deployment, Kubernetes performs a rolling update:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ROLLING UPDATE: nginx:1.21 > nginx:1.22                              |
|                                                                         |
|  STEP 1: Initial State (all v1.21)                                    |
|  ---------------------------------                                     |
|  ReplicaSet-OLD (3 replicas)                                          |
|  +---------+    +---------+    +---------+                           |
|  |  v1.21  |    |  v1.21  |    |  v1.21  |                           |
|  +---------+    +---------+    +---------+                           |
|                                                                         |
|  STEP 2: Create new ReplicaSet, scale up 1                            |
|  ----------------------------------------                              |
|  ReplicaSet-OLD (3)           ReplicaSet-NEW (1)                      |
|  +---------+ +---------+ +---------+    +---------+                 |
|  |  v1.21  | |  v1.21  | |  v1.21  |    |  v1.22  | < New           |
|  +---------+ +---------+ +---------+    +---------+                 |
|                                                                         |
|  STEP 3: Scale down old by 1, scale up new by 1                       |
|  ---------------------------------------------                         |
|  ReplicaSet-OLD (2)           ReplicaSet-NEW (2)                      |
|  +---------+ +---------+         +---------+ +---------+            |
|  |  v1.21  | |  v1.21  |         |  v1.22  | |  v1.22  |            |
|  +---------+ +---------+         +---------+ +---------+            |
|                                                                         |
|  STEP 4: Continue until all updated                                    |
|  ------------------------------------                                  |
|  ReplicaSet-OLD (0)           ReplicaSet-NEW (3)                      |
|                               +---------+ +---------+ +---------+   |
|                               |  v1.22  | |  v1.22  | |  v1.22  |   |
|                               +---------+ +---------+ +---------+   |
|                                                                         |
|  ZERO DOWNTIME! Traffic served throughout update.                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### UPDATE STRATEGIES

```yaml
spec:
  strategy:
    type: RollingUpdate          # or "Recreate"
    rollingUpdate:
      maxUnavailable: 1          # Max pods unavailable during update
      maxSurge: 1                # Max pods over desired count

ROLLINGUPDATE (Default):
* Zero downtime
* Gradual replacement
* Good for stateless apps

RECREATE:
* Kill all old pods first
* Then create new pods
* Has downtime!
* Use for: apps that can't have two versions running
```

### TRIGGERING AN UPDATE

```bash
# Method 1: Edit manifest and apply
kubectl apply -f deployment.yaml

# Method 2: Set image directly
kubectl set image deployment/nginx nginx=nginx:1.22

# Method 3: Edit in-place
kubectl edit deployment nginx
```

### MONITORING UPDATE

```bash
kubectl rollout status deployment/nginx
# Waiting for deployment "nginx" rollout to finish...
# deployment "nginx" successfully rolled out
```

## SECTION 3.5: ROLLBACKS

### DEPLOYMENT REVISION HISTORY

Kubernetes keeps history of Deployment revisions:

```bash
# View history
kubectl rollout history deployment/nginx

REVISION  CHANGE-CAUSE
1         <none>
2         kubectl set image deployment/nginx nginx=nginx:1.22
3         kubectl set image deployment/nginx nginx=nginx:1.23

# View specific revision
kubectl rollout history deployment/nginx --revision=2
```

### PERFORMING A ROLLBACK

```bash
# Rollback to previous revision
kubectl rollout undo deployment/nginx

# Rollback to specific revision
kubectl rollout undo deployment/nginx --to-revision=1

# Check status
kubectl rollout status deployment/nginx
```

### PAUSING AND RESUMING

```bash
# Pause (make multiple changes without triggering updates)
kubectl rollout pause deployment/nginx

# Make changes...
kubectl set image deployment/nginx nginx=nginx:1.23
kubectl set resources deployment/nginx -c nginx --limits=memory=256Mi

# Resume (triggers single rolling update)
kubectl rollout resume deployment/nginx
```

## SECTION 3.6: DEPLOYMENT CONFIGURATION

### COMPLETE DEPLOYMENT EXAMPLE

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  labels:
    app: web
spec:
  replicas: 3
  revisionHistoryLimit: 10           # Keep 10 ReplicaSet revisions
  progressDeadlineSeconds: 600       # Fail if update takes > 10 min

  selector:
    matchLabels:
      app: web

  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1              # At most 1 pod unavailable
      maxSurge: 1                    # At most 1 extra pod

  template:
    metadata:
      labels:
        app: web
      annotations:
        prometheus.io/scrape: "true"
    spec:
      containers:
      - name: web
        image: myapp:v1.0.0
        ports:
        - containerPort: 8080

        env:
        - name: DB_HOST
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: database_host

        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"

        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5

        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 15
          periodSeconds: 10

      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: web
              topologyKey: kubernetes.io/hostname
```

## SECTION 3.7: DEPLOYMENT COMMANDS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DEPLOYMENT COMMANDS                                                   |
|                                                                         |
|  CREATE:                                                               |
|  -------                                                               |
|  kubectl create deployment nginx --image=nginx                        |
|  kubectl apply -f deployment.yaml                                     |
|                                                                         |
|  VIEW:                                                                  |
|  -----                                                                  |
|  kubectl get deployments                                              |
|  kubectl describe deployment nginx                                    |
|  kubectl get deployment nginx -o yaml                                 |
|                                                                         |
|  UPDATE:                                                               |
|  -------                                                               |
|  kubectl set image deployment/nginx nginx=nginx:1.22                  |
|  kubectl set resources deployment/nginx -c nginx --limits=cpu=200m   |
|  kubectl edit deployment nginx                                        |
|  kubectl apply -f deployment.yaml                                     |
|                                                                         |
|  SCALE:                                                                |
|  ------                                                                |
|  kubectl scale deployment nginx --replicas=5                          |
|                                                                         |
|  ROLLOUT:                                                              |
|  --------                                                              |
|  kubectl rollout status deployment/nginx                              |
|  kubectl rollout history deployment/nginx                             |
|  kubectl rollout undo deployment/nginx                                |
|  kubectl rollout pause deployment/nginx                               |
|  kubectl rollout resume deployment/nginx                              |
|  kubectl rollout restart deployment/nginx                             |
|                                                                         |
|  DELETE:                                                               |
|  -------                                                               |
|  kubectl delete deployment nginx                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WORKLOADS - KEY TAKEAWAYS                                             |
|                                                                         |
|  REPLICASET                                                            |
|  ----------                                                            |
|  * Ensures specified number of pod replicas                           |
|  * Self-healing (recreates failed pods)                               |
|  * Don't use directly—use Deployments                                 |
|                                                                         |
|  DEPLOYMENT                                                            |
|  ----------                                                            |
|  * Manages ReplicaSets                                                |
|  * Declarative updates                                                |
|  * Rolling updates (zero downtime)                                    |
|  * Rollback capability                                                |
|  * Revision history                                                   |
|                                                                         |
|  ROLLING UPDATE STRATEGIES                                             |
|  -------------------------                                             |
|  * RollingUpdate: Gradual replacement (default)                       |
|  * Recreate: Kill all, then create new                               |
|                                                                         |
|  BEST PRACTICES                                                        |
|  --------------                                                        |
|  * Always use Deployments (not bare Pods or ReplicaSets)             |
|  * Set resource requests and limits                                   |
|  * Configure readiness and liveness probes                           |
|  * Use meaningful revision annotations                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 3

