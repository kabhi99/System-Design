# KUBERNETES SERVICE MESH
*Chapter 16: Advanced Traffic Management*

Service meshes provide advanced networking features like traffic
management, security, and observability.

## SECTION 16.1: WHAT IS A SERVICE MESH?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICE MESH ARCHITECTURE                                            |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |   Without Service Mesh:        With Service Mesh:              |  |
|  |                                                                 |  |
|  |   +---------+                  +---------------------+         |  |
|  |   | Service |                  | Service             |         |  |
|  |   |    A    |-------->         |    A    +---------+ |         |  |
|  |   +---------+                  |         | Sidecar |-+-->      |  |
|  |       |                        |         | (proxy) | |         |  |
|  |       |                        |         +---------+ |         |  |
|  |       v                        +---------------------+         |  |
|  |   +---------+                           |                      |  |
|  |   | Service |                           v                      |  |
|  |   |    B    |                  +---------------------+         |  |
|  |   +---------+                  | Service             |         |  |
|  |                                |    B    +---------+ |         |  |
|  |   Direct communication         |         | Sidecar | |         |  |
|  |                                |         +---------+ |         |  |
|  |                                +---------------------+         |  |
|  |                                                                 |  |
|  |                                Sidecar proxies handle all      |  |
|  |                                traffic between services        |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  KEY FEATURES                                                          |
|  ============                                                          |
|                                                                         |
|  * Traffic Management: Routing, load balancing, retries             |
|  * Security: mTLS, authentication, authorization                    |
|  * Observability: Metrics, tracing, logging                         |
|  * Resilience: Circuit breakers, timeouts, fault injection         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 16.2: POPULAR SERVICE MESHES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ISTIO                                                                 |
|  =====                                                                 |
|                                                                         |
|  Most feature-rich, uses Envoy proxy.                                |
|                                                                         |
|  # Install                                                             |
|  istioctl install --set profile=demo                                  |
|  kubectl label namespace default istio-injection=enabled             |
|                                                                         |
|  # Traffic routing                                                     |
|  apiVersion: networking.istio.io/v1beta1                              |
|  kind: VirtualService                                                  |
|  metadata:                                                              |
|    name: reviews-route                                                |
|  spec:                                                                  |
|    hosts:                                                               |
|      - reviews                                                         |
|    http:                                                                |
|      - match:                                                          |
|          - headers:                                                    |
|              end-user:                                                 |
|                exact: jason                                           |
|        route:                                                          |
|          - destination:                                                |
|              host: reviews                                             |
|              subset: v2                                                |
|      - route:                                                          |
|          - destination:                                                |
|              host: reviews                                             |
|              subset: v1                                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  LINKERD                                                               |
|  =======                                                               |
|                                                                         |
|  Lightweight, easy to use.                                            |
|                                                                         |
|  # Install                                                             |
|  linkerd install | kubectl apply -f -                                 |
|  linkerd viz install | kubectl apply -f -                            |
|                                                                         |
|  # Inject sidecar                                                      |
|  kubectl get deploy -o yaml | linkerd inject - | kubectl apply -f - |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CILIUM                                                                |
|  ======                                                                |
|                                                                         |
|  eBPF-based, high performance, no sidecar needed.                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 16.3: COMMON USE CASES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CANARY DEPLOYMENTS                                                    |
|  ====================                                                   |
|                                                                         |
|  Route 10% traffic to new version:                                    |
|                                                                         |
|  spec:                                                                  |
|    http:                                                                |
|      - route:                                                          |
|          - destination:                                                |
|              host: myapp                                               |
|              subset: v1                                                |
|            weight: 90                                                  |
|          - destination:                                                |
|              host: myapp                                               |
|              subset: v2                                                |
|            weight: 10                                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  MUTUAL TLS (mTLS)                                                    |
|  ==================                                                    |
|                                                                         |
|  Encrypt all service-to-service communication:                       |
|                                                                         |
|  apiVersion: security.istio.io/v1beta1                                |
|  kind: PeerAuthentication                                               |
|  metadata:                                                              |
|    name: default                                                       |
|    namespace: default                                                  |
|  spec:                                                                  |
|    mtls:                                                                |
|      mode: STRICT                                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CIRCUIT BREAKER                                                       |
|  ===============                                                        |
|                                                                         |
|  Prevent cascade failures:                                            |
|                                                                         |
|  apiVersion: networking.istio.io/v1beta1                              |
|  kind: DestinationRule                                                 |
|  metadata:                                                              |
|    name: myapp                                                         |
|  spec:                                                                  |
|    host: myapp                                                         |
|    trafficPolicy:                                                       |
|      connectionPool:                                                    |
|        tcp:                                                             |
|          maxConnections: 100                                          |
|      outlierDetection:                                                 |
|        consecutive5xxErrors: 5                                        |
|        interval: 30s                                                   |
|        baseEjectionTime: 30s                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICE MESH - KEY TAKEAWAYS                                         |
|                                                                         |
|  WHAT                                                                  |
|  ----                                                                  |
|  * Sidecar proxies handle service communication                      |
|  * Advanced traffic management                                       |
|  * Automatic mTLS encryption                                         |
|  * Observability built-in                                            |
|                                                                         |
|  OPTIONS                                                               |
|  -------                                                               |
|  * Istio: Feature-rich                                               |
|  * Linkerd: Lightweight                                              |
|  * Cilium: eBPF-based                                                |
|                                                                         |
|  USE CASES                                                             |
|  ---------                                                             |
|  * Canary/blue-green deployments                                     |
|  * Zero-trust security (mTLS)                                        |
|  * Circuit breakers, retries                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 16

