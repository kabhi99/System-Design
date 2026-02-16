# KUBERNETES AUTOSCALING
*Chapter 15: Automatic Resource Scaling*

Kubernetes provides multiple levels of autoscaling: pods, nodes, and
vertical scaling.

## SECTION 15.1: HORIZONTAL POD AUTOSCALER (HPA)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS HPA?                                                          |
|                                                                         |
|  Automatically scales pod replicas based on metrics.                  |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |   CPU Usage 80%                  CPU Usage 40%                 |  |
|  |                                                                 |  |
|  |   +---++---++---+               +---++---++---++---++---+     |  |
|  |   |Pod||Pod||Pod|   ------>     |Pod||Pod||Pod||Pod||Pod|     |  |
|  |   +---++---++---+               +---++---++---++---++---+     |  |
|  |                                                                 |  |
|  |   3 replicas > HPA scales to > 5 replicas                     |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BASIC HPA                                                             |
|  =========                                                              |
|                                                                         |
|  # Command                                                              |
|  kubectl autoscale deployment myapp \                                 |
|    --cpu-percent=50 \                                                   |
|    --min=2 \                                                            |
|    --max=10                                                             |
|                                                                         |
|  # YAML                                                                |
|  apiVersion: autoscaling/v2                                           |
|  kind: HorizontalPodAutoscaler                                        |
|  metadata:                                                              |
|    name: myapp-hpa                                                     |
|  spec:                                                                  |
|    scaleTargetRef:                                                      |
|      apiVersion: apps/v1                                               |
|      kind: Deployment                                                   |
|      name: myapp                                                       |
|    minReplicas: 2                                                      |
|    maxReplicas: 10                                                     |
|    metrics:                                                             |
|      - type: Resource                                                  |
|        resource:                                                        |
|          name: cpu                                                     |
|          target:                                                        |
|            type: Utilization                                           |
|            averageUtilization: 50                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  MULTIPLE METRICS                                                      |
|  =================                                                      |
|                                                                         |
|  spec:                                                                  |
|    metrics:                                                             |
|      - type: Resource                                                  |
|        resource:                                                        |
|          name: cpu                                                     |
|          target:                                                        |
|            type: Utilization                                           |
|            averageUtilization: 50                                     |
|      - type: Resource                                                  |
|        resource:                                                        |
|          name: memory                                                  |
|          target:                                                        |
|            type: Utilization                                           |
|            averageUtilization: 70                                     |
|      - type: Pods                                                      |
|        pods:                                                            |
|          metric:                                                        |
|            name: packets-per-second                                   |
|          target:                                                        |
|            type: AverageValue                                          |
|            averageValue: 1k                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 15.2: VERTICAL POD AUTOSCALER (VPA)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS VPA?                                                          |
|                                                                         |
|  Automatically adjusts CPU/memory requests and limits.               |
|                                                                         |
|  apiVersion: autoscaling.k8s.io/v1                                    |
|  kind: VerticalPodAutoscaler                                           |
|  metadata:                                                              |
|    name: myapp-vpa                                                     |
|  spec:                                                                  |
|    targetRef:                                                           |
|      apiVersion: apps/v1                                               |
|      kind: Deployment                                                   |
|      name: myapp                                                       |
|    updatePolicy:                                                        |
|      updateMode: "Auto"       # Off, Initial, Recreate, Auto         |
|    resourcePolicy:                                                      |
|      containerPolicies:                                                |
|        - containerName: "*"                                            |
|          minAllowed:                                                    |
|            cpu: 100m                                                   |
|            memory: 50Mi                                                |
|          maxAllowed:                                                    |
|            cpu: 2                                                      |
|            memory: 2Gi                                                 |
|                                                                         |
|  NOTE: VPA requires installation (not built-in)                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 15.3: CLUSTER AUTOSCALER

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS CLUSTER AUTOSCALER?                                          |
|                                                                         |
|  Automatically adjusts cluster size (nodes).                          |
|                                                                         |
|  SCALE UP when:                                                        |
|  * Pods can't be scheduled due to insufficient resources             |
|                                                                         |
|  SCALE DOWN when:                                                      |
|  * Nodes are underutilized                                            |
|  * Pods can be moved to other nodes                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CLOUD PROVIDER SETUP                                                  |
|                                                                         |
|  # AWS EKS                                                             |
|  eksctl create cluster --nodes-min=2 --nodes-max=10                  |
|                                                                         |
|  # GKE                                                                 |
|  gcloud container clusters create mycluster \                         |
|    --enable-autoscaling \                                              |
|    --min-nodes=2 \                                                      |
|    --max-nodes=10                                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 15.4: PREREQUISITES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HPA REQUIRES RESOURCE REQUESTS                                       |
|                                                                         |
|  # Deployment must specify resources                                  |
|  spec:                                                                  |
|    containers:                                                          |
|      - name: app                                                       |
|        resources:                                                       |
|          requests:                                                      |
|            cpu: 100m          # Required for HPA!                     |
|            memory: 128Mi                                               |
|          limits:                                                        |
|            cpu: 500m                                                   |
|            memory: 512Mi                                               |
|                                                                         |
|  # Metrics Server must be installed                                   |
|  kubectl apply -f \                                                     |
|    https://github.com/kubernetes-sigs/metrics-server/releases/\       |
|    latest/download/components.yaml                                    |
|                                                                         |
|  # Check metrics                                                       |
|  kubectl top pods                                                       |
|  kubectl top nodes                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  AUTOSCALING - KEY TAKEAWAYS                                          |
|                                                                         |
|  THREE TYPES                                                           |
|  -----------                                                           |
|  * HPA: Scale pod replicas (horizontal)                              |
|  * VPA: Scale pod resources (vertical)                               |
|  * Cluster Autoscaler: Scale nodes                                   |
|                                                                         |
|  HPA REQUIREMENTS                                                      |
|  -----------------                                                     |
|  * Metrics Server installed                                          |
|  * Resource requests defined on pods                                 |
|                                                                         |
|  COMMANDS                                                              |
|  --------                                                              |
|  kubectl autoscale deployment <name> --cpu-percent=50 --min=2 --max=10|
|  kubectl get hpa                                                       |
|  kubectl top pods/nodes                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 15

