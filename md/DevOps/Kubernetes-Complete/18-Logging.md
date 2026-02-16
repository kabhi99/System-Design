# KUBERNETES LOGGING
*Chapter 18: Centralized Log Management*

Centralized logging aggregates logs from all pods for easier
debugging and analysis.

## SECTION 18.1: LOGGING ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LOG COLLECTION PATTERNS                                                |
|                                                                         |
|  1. NODE-LEVEL AGENT (DaemonSet)                                        |
|  -------------------------------                                        |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |   Node                                                            |  |
|  |   +-----------------------------------------------------------+   |  |
|  |   |                                                           |   |  |
|  |   |  Pod A --> /var/log/containers/                           |   |  |
|  |   |  Pod B -->        |                                       |   |  |
|  |   |  Pod C -->        v                                       |   |  |
|  |   |              +----------+                                 |   |  |
|  |   |              | Fluentd  |----> Log Storage                |   |  |
|  |   |              | DaemonSet|     (Elasticsearch)             |   |  |
|  |   |              +----------+                                 |   |  |
|  |   |                                                           |   |  |
|  |   +-----------------------------------------------------------+   |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  2. SIDECAR CONTAINER                                                   |
|  ---------------------                                                  |
|                                                                         |
|  +----------------------------------+                                   |
|  |   Pod                            |                                   |
|  |   +----------+  +----------+    |                                    |
|  |   |   App    |  |  Sidecar |    |                                    |
|  |   |          |--| (Fluent) |----+--> Log Storage                     |
|  |   +----------+  +----------+    |                                    |
|  |        shared volume            |                                    |
|  +----------------------------------+                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 18.2: EFK STACK

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ELASTICSEARCH + FLUENTD + KIBANA                                       |
|  =================================                                      |
|                                                                         |
|  * Elasticsearch: Store and index logs                                  |
|  * Fluentd/Fluent Bit: Collect and forward logs                         |
|  * Kibana: Visualize and search logs                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  FLUENT BIT DAEMONSET                                                   |
|                                                                         |
|  apiVersion: apps/v1                                                    |
|  kind: DaemonSet                                                        |
|  metadata:                                                              |
|    name: fluent-bit                                                     |
|  spec:                                                                  |
|    selector:                                                            |
|      matchLabels:                                                       |
|        app: fluent-bit                                                  |
|    template:                                                            |
|      spec:                                                              |
|        containers:                                                      |
|          - name: fluent-bit                                             |
|            image: fluent/fluent-bit:latest                              |
|            volumeMounts:                                                |
|              - name: varlog                                             |
|                mountPath: /var/log                                      |
|              - name: containers                                         |
|                mountPath: /var/lib/docker/containers                    |
|                readOnly: true                                           |
|        volumes:                                                         |
|          - name: varlog                                                 |
|            hostPath:                                                    |
|              path: /var/log                                             |
|          - name: containers                                             |
|            hostPath:                                                    |
|              path: /var/lib/docker/containers                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 18.3: LOKI STACK

```
+-------------------------------------------------------------------------+
|                                                                         |
|  GRAFANA LOKI (Lightweight Alternative)                                 |
|  =======================================                                |
|                                                                         |
|  * Loki: Like Prometheus, but for logs                                  |
|  * Promtail: Log collector agent                                        |
|  * Grafana: Visualize logs alongside metrics                            |
|                                                                         |
|  Advantages:                                                            |
|  * Lightweight (doesn't index log content)                              |
|  * Cost-effective storage                                               |
|  * Native Grafana integration                                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  INSTALL LOKI-STACK                                                     |
|                                                                         |
|  helm repo add grafana https://grafana.github.io/helm-charts            |
|                                                                         |
|  helm install loki grafana/loki-stack \                                 |
|    --namespace logging --create-namespace \                             |
|    --set grafana.enabled=true                                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  QUERY LOGS (LogQL)                                                     |
|                                                                         |
|  # Filter by label                                                      |
|  {namespace="default", app="myapp"}                                     |
|                                                                         |
|  # Search content                                                       |
|  {app="myapp"} |= "error"                                               |
|                                                                         |
|  # JSON parsing                                                         |
|  {app="myapp"} | json | level="error"                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 18.4: BASIC COMMANDS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KUBECTL LOGS                                                           |
|  =============                                                          |
|                                                                         |
|  # View pod logs                                                        |
|  kubectl logs my-pod                                                    |
|                                                                         |
|  # Follow logs (stream)                                                 |
|  kubectl logs -f my-pod                                                 |
|                                                                         |
|  # Previous container logs (after restart)                              |
|  kubectl logs my-pod --previous                                         |
|                                                                         |
|  # Specific container in multi-container pod                            |
|  kubectl logs my-pod -c my-container                                    |
|                                                                         |
|  # Logs from all pods with label                                        |
|  kubectl logs -l app=myapp                                              |
|                                                                         |
|  # Last 100 lines                                                       |
|  kubectl logs my-pod --tail=100                                         |
|                                                                         |
|  # Since timestamp                                                      |
|  kubectl logs my-pod --since=1h                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LOGGING - KEY TAKEAWAYS                                                |
|                                                                         |
|  PATTERNS                                                               |
|  --------                                                               |
|  * DaemonSet agent (most common)                                        |
|  * Sidecar container                                                    |
|                                                                         |
|  STACKS                                                                 |
|  ------                                                                 |
|  * EFK: Elasticsearch + Fluentd + Kibana                                |
|  * Loki: Lightweight, Grafana-native                                    |
|                                                                         |
|  COMMANDS                                                               |
|  --------                                                               |
|  kubectl logs <pod> [-f] [--tail=N] [--since=1h]                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 18

