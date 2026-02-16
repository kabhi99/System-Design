# KUBERNETES MONITORING
*Chapter 17: Metrics and Alerting*

Monitoring is essential for understanding cluster health and
application performance.

## SECTION 17.1: MONITORING STACK

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TYPICAL MONITORING STACK                                               |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |   +-------------+     +-------------+     +-------------+      |     |
|  |   |  Metrics    |     | Prometheus  |     |  Grafana    |      |     |
|  |   |  Exporters  |---->|   (Store)   |---->|  (Visualize)|      |     |
|  |   +-------------+     +-------------+     +-------------+      |     |
|  |                              |                                  |    |
|  |                              v                                  |    |
|  |                       +-------------+                          |     |
|  |                       | Alertmanager|                          |     |
|  |                       |  (Alerts)   |                          |     |
|  |                       +-------------+                          |     |
|  |                                                                 |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  COMPONENTS                                                             |
|  ==========                                                             |
|                                                                         |
|  * Prometheus: Time-series database for metrics                         |
|  * Grafana: Visualization and dashboards                                |
|  * Alertmanager: Alert routing and notifications                        |
|  * Exporters: Expose metrics (node, kube-state, app)                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 17.2: PROMETHEUS OPERATOR

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INSTALL KUBE-PROMETHEUS-STACK                                          |
|  ==============================                                         |
|                                                                         |
|  # Using Helm                                                           |
|  helm repo add prometheus-community \                                   |
|    https://prometheus-community.github.io/helm-charts                   |
|                                                                         |
|  helm install monitoring prometheus-community/kube-prometheus-stack \   |
|    --namespace monitoring --create-namespace                            |
|                                                                         |
|  Installs:                                                              |
|  * Prometheus                                                           |
|  * Grafana (admin/prom-operator)                                        |
|  * Alertmanager                                                         |
|  * Node exporter                                                        |
|  * kube-state-metrics                                                   |
|  * Pre-built dashboards                                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ACCESS DASHBOARDS                                                      |
|                                                                         |
|  # Grafana                                                              |
|  kubectl port-forward svc/monitoring-grafana 3000:80 -n monitoring      |
|  # Open http://localhost:3000                                           |
|                                                                         |
|  # Prometheus                                                           |
|  kubectl port-forward svc/monitoring-prometheus 9090 -n monitoring      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 17.3: KEY METRICS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CLUSTER METRICS                                                        |
|  ===============                                                        |
|                                                                         |
|  * Node CPU/Memory/Disk usage                                           |
|  * Pod count per node                                                   |
|  * Cluster capacity vs usage                                            |
|                                                                         |
|  APPLICATION METRICS                                                    |
|  ===================                                                    |
|                                                                         |
|  * Pod CPU/Memory usage                                                 |
|  * Request rate, error rate, latency (RED)                              |
|  * Container restarts                                                   |
|                                                                         |
|  KUBERNETES METRICS                                                     |
|  ===================                                                    |
|                                                                         |
|  * Deployment replica status                                            |
|  * Pod phase (Running, Pending, Failed)                                 |
|  * PVC usage                                                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USEFUL PROMQL QUERIES                                                  |
|                                                                         |
|  # CPU usage by pod                                                     |
|  sum(rate(container_cpu_usage_seconds_total{                            |
|    namespace="default"}[5m])) by (pod)                                  |
|                                                                         |
|  # Memory usage by namespace                                            |
|  sum(container_memory_usage_bytes) by (namespace)                       |
|                                                                         |
|  # Pods not ready                                                       |
|  kube_pod_status_ready{condition="false"}                               |
|                                                                         |
|  # Request rate (if app exports metrics)                                |
|  sum(rate(http_requests_total[5m])) by (service)                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 17.4: ALERTING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROMETHEUSRULE                                                         |
|  ===============                                                        |
|                                                                         |
|  apiVersion: monitoring.coreos.com/v1                                   |
|  kind: PrometheusRule                                                   |
|  metadata:                                                              |
|    name: app-alerts                                                     |
|  spec:                                                                  |
|    groups:                                                              |
|      - name: app                                                        |
|        rules:                                                           |
|          - alert: HighErrorRate                                         |
|            expr: |                                                      |
|              sum(rate(http_requests_total{status=~"5.."}[5m]))          |
|              / sum(rate(http_requests_total[5m])) > 0.1                 |
|            for: 5m                                                      |
|            labels:                                                      |
|              severity: critical                                         |
|            annotations:                                                 |
|              summary: "High error rate detected"                        |
|              description: "Error rate > 10% for 5 minutes"              |
|                                                                         |
|          - alert: PodRestarts                                           |
|            expr: |                                                      |
|              increase(kube_pod_container_status_restarts_total          |
|              [1h]) > 5                                                  |
|            labels:                                                      |
|              severity: warning                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MONITORING - KEY TAKEAWAYS                                             |
|                                                                         |
|  STACK                                                                  |
|  -----                                                                  |
|  * Prometheus: Collect and store metrics                                |
|  * Grafana: Visualize with dashboards                                   |
|  * Alertmanager: Handle alerts                                          |
|                                                                         |
|  INSTALLATION                                                           |
|  ------------                                                           |
|  kube-prometheus-stack Helm chart                                       |
|                                                                         |
|  KEY METRICS                                                            |
|  -----------                                                            |
|  * CPU, Memory, Disk                                                    |
|  * Request rate, errors, latency                                        |
|  * Pod status and restarts                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 17

