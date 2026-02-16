================================================================================
         CHAPTER 4: INGRESS AND EXTERNAL ACCESS
         Exposing Applications to the Outside World
================================================================================

This chapter covers how to expose Kubernetes applications to external traffic,
including Ingress controllers, Gateway API, and best practices for production.


================================================================================
SECTION 4.1: THE PROBLEM WITH SERVICES
================================================================================

LIMITATIONS OF NODEPORT AND LOADBALANCER
────────────────────────────────────────

While NodePort and LoadBalancer services work, they have issues:

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  NODEPORT LIMITATIONS                                                  │
    │                                                                         │
    │  • Exposes high port (30000-32767) - not standard HTTP/HTTPS ports    │
    │  • Clients must use node-ip:nodeport format                           │
    │  • No TLS termination                                                 │
    │  • No path-based routing                                              │
    │  • No virtual hosting                                                 │
    │                                                                         │
    │  LOADBALANCER LIMITATIONS                                              │
    │                                                                         │
    │  • One LoadBalancer per service = EXPENSIVE!                          │
    │    - 10 services = 10 load balancers = 10× the cost                  │
    │    - Each LB has its own public IP                                   │
    │                                                                         │
    │  • No path-based routing                                              │
    │    - Can't route /api to api-service and /web to web-service         │
    │                                                                         │
    │  • No host-based routing                                              │
    │    - Can't route api.example.com and web.example.com to different    │
    │      services with same LoadBalancer                                 │
    │                                                                         │
    │  • Cloud-only                                                         │
    │    - Doesn't work on bare-metal without MetalLB or similar           │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


THE INGRESS SOLUTION
────────────────────

Ingress provides HTTP/HTTPS routing at Layer 7:

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  WITHOUT INGRESS:                                                      │
    │                                                                         │
    │   api.example.com ──► LoadBalancer ──► api-service                    │
    │   web.example.com ──► LoadBalancer ──► web-service                    │
    │   admin.example.com ──► LoadBalancer ──► admin-service                │
    │                                                                         │
    │   3 external LoadBalancers = 3 public IPs = $$$                       │
    │                                                                         │
    │  ════════════════════════════════════════════════════════════════════ │
    │                                                                         │
    │  WITH INGRESS:                                                         │
    │                                                                         │
    │   api.example.com    ─┐                                                │
    │   web.example.com    ─┼──► Single LB ──► Ingress Controller           │
    │   admin.example.com  ─┘                         │                      │
    │                                                 │                      │
    │                                    ┌────────────┼────────────┐         │
    │                                    │            │            │         │
    │                                    ▼            ▼            ▼         │
    │                              api-service  web-service  admin-service  │
    │                                                                         │
    │   1 external LoadBalancer = 1 public IP = $                           │
    │   Ingress Controller handles routing internally                       │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4.2: INGRESS ARCHITECTURE
================================================================================

TWO COMPONENTS OF INGRESS
─────────────────────────

    1. INGRESS RESOURCE
       • Kubernetes API object
       • Declares routing rules (host, path → service)
       • Just configuration—doesn't do anything by itself

    2. INGRESS CONTROLLER
       • Software that implements Ingress rules
       • Watches for Ingress resources and configures routing
       • Many options: NGINX, Traefik, HAProxy, AWS ALB, etc.

    IMPORTANT: Kubernetes doesn't include an Ingress Controller!
    You must install one separately.


HOW INGRESS WORKS
─────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  INGRESS FLOW                                                          │
    │                                                                         │
    │  1. You create Ingress resource:                                       │
    │     "Route api.example.com/v1/* to api-service:80"                    │
    │                │                                                        │
    │                ▼                                                        │
    │  2. Ingress Controller watches Ingress resources                       │
    │     (using Kubernetes API)                                             │
    │                │                                                        │
    │                ▼                                                        │
    │  3. Controller updates its configuration                               │
    │     (e.g., generates nginx.conf)                                      │
    │                │                                                        │
    │                ▼                                                        │
    │  4. Traffic arrives at Controller (via LoadBalancer/NodePort)         │
    │                │                                                        │
    │                ▼                                                        │
    │  5. Controller inspects Host header and path                          │
    │     "Host: api.example.com, Path: /v1/users"                          │
    │                │                                                        │
    │                ▼                                                        │
    │  6. Controller forwards to appropriate service                        │
    │     api-service:80                                                    │
    │                │                                                        │
    │                ▼                                                        │
    │  7. kube-proxy routes to pod                                          │
    │     10.244.1.5:8080                                                   │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


INGRESS CONTROLLER OPTIONS
──────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  POPULAR INGRESS CONTROLLERS                                           │
    │                                                                         │
    │  NGINX Ingress Controller                                              │
    │  ─────────────────────────                                              │
    │  • Most popular, mature                                               │
    │  • Two versions: kubernetes/ingress-nginx and nginx/nginx-ingress     │
    │  • Excellent documentation                                            │
    │  • Basic to advanced features                                         │
    │                                                                         │
    │  Traefik                                                               │
    │  ───────                                                               │
    │  • Modern, automatic configuration                                    │
    │  • Built-in dashboard                                                 │
    │  • Native Let's Encrypt support                                       │
    │  • Good for dynamic environments                                      │
    │                                                                         │
    │  HAProxy Ingress                                                       │
    │  ───────────────                                                       │
    │  • High performance                                                   │
    │  • Advanced load balancing                                            │
    │  • Good for TCP/UDP workloads                                         │
    │                                                                         │
    │  AWS ALB Ingress Controller                                           │
    │  ─────────────────────────                                             │
    │  • Creates actual AWS ALBs                                            │
    │  • Native AWS integration                                             │
    │  • Cost: One ALB per Ingress (or IngressGroup)                       │
    │                                                                         │
    │  Istio Ingress Gateway                                                │
    │  ────────────────────                                                  │
    │  • Part of Istio service mesh                                        │
    │  • Advanced traffic management                                        │
    │  • mTLS, observability built-in                                       │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 4.3: INGRESS RESOURCES — CONFIGURATION
================================================================================

BASIC INGRESS EXAMPLE
─────────────────────

    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: my-ingress
      annotations:
        nginx.ingress.kubernetes.io/rewrite-target: /
    spec:
      ingressClassName: nginx  # Which controller handles this
      rules:
      - host: myapp.example.com
        http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-service
                port:
                  number: 80


HOST-BASED ROUTING
──────────────────

Route different domains to different services:

    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: host-routing
    spec:
      ingressClassName: nginx
      rules:
      # Route api.example.com to api-service
      - host: api.example.com
        http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80

      # Route web.example.com to web-service
      - host: web.example.com
        http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-service
                port:
                  number: 80

      # Route admin.example.com to admin-service
      - host: admin.example.com
        http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: admin-service
                port:
                  number: 80


PATH-BASED ROUTING
──────────────────

Route different paths to different services:

    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: path-routing
    spec:
      ingressClassName: nginx
      rules:
      - host: example.com
        http:
          paths:
          # /api/* goes to api-service
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80

          # /static/* goes to static-service
          - path: /static
            pathType: Prefix
            backend:
              service:
                name: static-service
                port:
                  number: 80

          # Everything else goes to frontend-service
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80


PATH TYPES EXPLAINED
────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  PATH TYPES                                                            │
    │                                                                         │
    │  Prefix                                                                │
    │  ──────                                                                │
    │  Matches based on URL path prefix split by /                          │
    │                                                                         │
    │  path: /api                                                           │
    │  ✓ Matches: /api, /api/, /api/users, /api/v1/users                   │
    │  ✗ No match: /apis, /api-v2                                          │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  Exact                                                                 │
    │  ─────                                                                 │
    │  Matches exact path only                                              │
    │                                                                         │
    │  path: /api                                                           │
    │  ✓ Matches: /api                                                     │
    │  ✗ No match: /api/, /api/users                                       │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  ImplementationSpecific                                                │
    │  ─────────────────────                                                 │
    │  Interpretation depends on IngressClass                               │
    │  Usually treated as Prefix                                            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


TLS/HTTPS CONFIGURATION
───────────────────────

Enable HTTPS with TLS certificates:

    # First, create a TLS secret
    kubectl create secret tls my-tls-secret \
      --cert=tls.crt \
      --key=tls.key

    # Then reference in Ingress
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: tls-ingress
    spec:
      ingressClassName: nginx
      tls:
      - hosts:
        - secure.example.com
        secretName: my-tls-secret  # Reference to TLS secret
      rules:
      - host: secure.example.com
        http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: secure-service
                port:
                  number: 80


COMMON NGINX INGRESS ANNOTATIONS
────────────────────────────────

    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: annotated-ingress
      annotations:
        # Rewrite path
        nginx.ingress.kubernetes.io/rewrite-target: /$2

        # Rate limiting
        nginx.ingress.kubernetes.io/limit-rps: "100"

        # Enable CORS
        nginx.ingress.kubernetes.io/enable-cors: "true"

        # Proxy timeouts
        nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
        nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"

        # WebSocket support
        nginx.ingress.kubernetes.io/proxy-http-version: "1.1"
        nginx.ingress.kubernetes.io/upstream-hash-by: "$remote_addr"

        # SSL redirect
        nginx.ingress.kubernetes.io/ssl-redirect: "true"

        # Body size limit
        nginx.ingress.kubernetes.io/proxy-body-size: "100m"

        # Custom headers
        nginx.ingress.kubernetes.io/configuration-snippet: |
          add_header X-Custom-Header "value";

    spec:
      ...


================================================================================
SECTION 4.4: INGRESS CONTROLLER ARCHITECTURE
================================================================================

NGINX INGRESS CONTROLLER INTERNALS
──────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  NGINX INGRESS CONTROLLER                                              │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐   │
    │  │                                                                 │   │
    │  │   ┌───────────────────┐    ┌───────────────────────────────┐  │   │
    │  │   │  Controller       │    │       NGINX                   │  │   │
    │  │   │  (Go binary)      │    │       (nginx worker)         │  │   │
    │  │   │                   │    │                               │  │   │
    │  │   │  • Watches K8s API│    │  • Actual request handling   │  │   │
    │  │   │  • Ingress        │───►│  • TLS termination           │  │   │
    │  │   │  • Services       │    │  • Load balancing            │  │   │
    │  │   │  • Endpoints      │    │  • Proxying                  │  │   │
    │  │   │  • Secrets (TLS)  │    │                               │  │   │
    │  │   │                   │    │  Config: /etc/nginx/nginx.conf│  │   │
    │  │   │  Generates        │    │                               │  │   │
    │  │   │  nginx.conf      │────►│                               │  │   │
    │  │   │                   │    │                               │  │   │
    │  │   └───────────────────┘    └─────────────┬─────────────────┘  │   │
    │  │                                          │                     │   │
    │  │                                          │                     │   │
    │  └──────────────────────────────────────────┼─────────────────────┘   │
    │                                             │                         │
    │                                             ▼                         │
    │                          ┌─────────────────────────────────┐         │
    │                          │         Backend Pods            │         │
    │                          │  10.244.0.5, 10.244.1.3, ...   │         │
    │                          └─────────────────────────────────┘         │
    │                                                                         │
    │  NOTE: NGINX Ingress proxies directly to POD IPs,                     │
    │        not to ClusterIP service (bypasses kube-proxy)!               │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


GENERATED NGINX CONFIGURATION
─────────────────────────────

You can see what NGINX config is generated:

    # Get NGINX config from controller pod
    kubectl exec -it ingress-nginx-controller-xxx -n ingress-nginx \
      -- cat /etc/nginx/nginx.conf

    # Relevant section for an Ingress:
    server {
        listen 80;
        server_name api.example.com;

        location /api {
            proxy_pass http://upstream_backend;
        }
    }

    upstream upstream_backend {
        server 10.244.0.5:8080;    # Pod IP 1
        server 10.244.1.3:8080;    # Pod IP 2
        server 10.244.2.7:8080;    # Pod IP 3
    }


================================================================================
SECTION 4.5: GATEWAY API — THE FUTURE OF INGRESS
================================================================================

WHY GATEWAY API?
────────────────

Ingress has limitations:
    • Limited to HTTP/HTTPS (no TCP/UDP)
    • Annotations are controller-specific (not portable)
    • Limited role-based configuration
    • Complex to extend

Gateway API is the next-generation API for traffic management:

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  INGRESS vs GATEWAY API                                                │
    │                                                                         │
    │  INGRESS:                                                              │
    │  ┌──────────────────────────┐                                         │
    │  │        Ingress           │  Single resource                        │
    │  │                          │  Combines infrastructure + routing      │
    │  │  • TLS config           │  Often requires annotations             │
    │  │  • Host routing         │                                         │
    │  │  • Path routing         │                                         │
    │  │  • Backend services     │                                         │
    │  └──────────────────────────┘                                         │
    │                                                                         │
    │  GATEWAY API:                                                          │
    │  ┌──────────────────────────┐                                         │
    │  │     GatewayClass         │  Infrastructure provider (cluster-wide)│
    │  └──────────────────────────┘                                         │
    │              │                                                         │
    │              ▼                                                         │
    │  ┌──────────────────────────┐                                         │
    │  │       Gateway            │  Load balancer config (infra team)     │
    │  │  • Listeners             │                                         │
    │  │  • TLS config           │                                         │
    │  └──────────────────────────┘                                         │
    │              │                                                         │
    │              ▼                                                         │
    │  ┌──────────────────────────┐                                         │
    │  │     HTTPRoute            │  Routing rules (app team)              │
    │  │  • Host matching        │                                         │
    │  │  • Path matching        │                                         │
    │  │  • Backend refs         │                                         │
    │  └──────────────────────────┘                                         │
    │                                                                         │
    │  Separation of concerns!                                               │
    │  • Cluster admin manages GatewayClass                                 │
    │  • Platform team manages Gateway                                      │
    │  • App team manages HTTPRoute                                         │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


GATEWAY API EXAMPLE
───────────────────

    # 1. GatewayClass (cluster admin)
    apiVersion: gateway.networking.k8s.io/v1
    kind: GatewayClass
    metadata:
      name: nginx
    spec:
      controllerName: k8s.io/nginx

    ---
    # 2. Gateway (platform team)
    apiVersion: gateway.networking.k8s.io/v1
    kind: Gateway
    metadata:
      name: prod-gateway
      namespace: infra
    spec:
      gatewayClassName: nginx
      listeners:
      - name: http
        port: 80
        protocol: HTTP
        allowedRoutes:
          namespaces:
            from: All  # Allow routes from any namespace

      - name: https
        port: 443
        protocol: HTTPS
        tls:
          mode: Terminate
          certificateRefs:
          - name: prod-tls-cert
        allowedRoutes:
          namespaces:
            from: All

    ---
    # 3. HTTPRoute (app team)
    apiVersion: gateway.networking.k8s.io/v1
    kind: HTTPRoute
    metadata:
      name: api-route
      namespace: my-app
    spec:
      parentRefs:
      - name: prod-gateway
        namespace: infra
      hostnames:
      - api.example.com
      rules:
      - matches:
        - path:
            type: PathPrefix
            value: /v1
        backendRefs:
        - name: api-v1-service
          port: 80
      - matches:
        - path:
            type: PathPrefix
            value: /v2
        backendRefs:
        - name: api-v2-service
          port: 80


GATEWAY API FEATURES
────────────────────

    • TCP/UDP routing (TCPRoute, UDPRoute)
    • gRPC routing (GRPCRoute)
    • Traffic splitting (canary deployments)
    • Header-based routing
    • Request/Response manipulation
    • Role-based access control


================================================================================
SECTION 4.6: PRODUCTION BEST PRACTICES
================================================================================

ARCHITECTURE PATTERNS
─────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  RECOMMENDED PRODUCTION ARCHITECTURE                                   │
    │                                                                         │
    │   Internet                                                              │
    │       │                                                                │
    │       ▼                                                                │
    │   ┌───────────────────────────────────────────────────────────────┐   │
    │   │              Cloud Load Balancer (L4)                         │   │
    │   │   • Simple TCP/UDP load balancing                            │   │
    │   │   • Health checks                                            │   │
    │   │   • DDoS protection                                          │   │
    │   └───────────────────────────┬───────────────────────────────────┘   │
    │                               │                                        │
    │                               ▼                                        │
    │   ┌───────────────────────────────────────────────────────────────┐   │
    │   │              Ingress Controller (L7)                          │   │
    │   │                                                               │   │
    │   │   • TLS termination                                          │   │
    │   │   • Host/path routing                                        │   │
    │   │   • Rate limiting                                            │   │
    │   │   • Authentication                                           │   │
    │   │   • Logging/metrics                                          │   │
    │   │                                                               │   │
    │   │   Run as Deployment with HPA                                 │   │
    │   │   Multiple replicas for HA                                   │   │
    │   │                                                               │   │
    │   └─────────────────────────────┬─────────────────────────────────┘   │
    │                                 │                                      │
    │                    ┌────────────┼────────────┐                        │
    │                    │            │            │                        │
    │                    ▼            ▼            ▼                        │
    │              ┌───────────┐ ┌───────────┐ ┌───────────┐               │
    │              │ Service A │ │ Service B │ │ Service C │               │
    │              └───────────┘ └───────────┘ └───────────┘               │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


HIGH AVAILABILITY INGRESS
─────────────────────────

    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: ingress-nginx-controller
      namespace: ingress-nginx
    spec:
      replicas: 3  # Multiple replicas
      selector:
        matchLabels:
          app: ingress-nginx
      template:
        metadata:
          labels:
            app: ingress-nginx
        spec:
          # Spread across nodes
          topologySpreadConstraints:
          - maxSkew: 1
            topologyKey: kubernetes.io/hostname
            whenUnsatisfiable: DoNotSchedule
            labelSelector:
              matchLabels:
                app: ingress-nginx

          # Don't run on same node
          affinity:
            podAntiAffinity:
              requiredDuringSchedulingIgnoredDuringExecution:
              - labelSelector:
                  matchLabels:
                    app: ingress-nginx
                topologyKey: kubernetes.io/hostname

          containers:
          - name: controller
            resources:
              requests:
                cpu: 100m
                memory: 90Mi
              limits:
                cpu: 1000m
                memory: 512Mi


CERT-MANAGER FOR TLS
────────────────────

Automate TLS certificate management with cert-manager:

    # Install cert-manager
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

    # Create ClusterIssuer for Let's Encrypt
    apiVersion: cert-manager.io/v1
    kind: ClusterIssuer
    metadata:
      name: letsencrypt-prod
    spec:
      acme:
        server: https://acme-v02.api.letsencrypt.org/directory
        email: admin@example.com
        privateKeySecretRef:
          name: letsencrypt-prod
        solvers:
        - http01:
            ingress:
              class: nginx

    # Ingress with automatic TLS
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: auto-tls-ingress
      annotations:
        cert-manager.io/cluster-issuer: letsencrypt-prod  # Auto-issue cert
    spec:
      ingressClassName: nginx
      tls:
      - hosts:
        - secure.example.com
        secretName: auto-tls-secret  # cert-manager creates this
      rules:
      - host: secure.example.com
        http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-service
                port:
                  number: 80


================================================================================
CHAPTER SUMMARY
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  INGRESS AND EXTERNAL ACCESS - KEY TAKEAWAYS                          │
    │                                                                         │
    │  ┌───────────────────────────────────────────────────────────────────┐ │
    │  │                                                                   │ │
    │  │  INGRESS BENEFITS                                                │ │
    │  │  • Single entry point for multiple services                     │ │
    │  │  • TLS termination                                              │ │
    │  │  • Host and path-based routing                                  │ │
    │  │  • Cost savings (1 LB vs many)                                  │ │
    │  │                                                                   │ │
    │  ├───────────────────────────────────────────────────────────────────┤ │
    │  │                                                                   │ │
    │  │  INGRESS CONTROLLERS                                             │ │
    │  │  • NGINX: Most popular, mature                                  │ │
    │  │  • Traefik: Modern, auto-config                                 │ │
    │  │  • AWS ALB: Native AWS integration                              │ │
    │  │  • Must install separately—K8s doesn't include one             │ │
    │  │                                                                   │ │
    │  ├───────────────────────────────────────────────────────────────────┤ │
    │  │                                                                   │ │
    │  │  GATEWAY API                                                     │ │
    │  │  • Future of Kubernetes ingress                                 │ │
    │  │  • Separates infrastructure from routing                        │ │
    │  │  • Supports TCP/UDP, gRPC, traffic splitting                   │ │
    │  │  • Role-based configuration                                     │ │
    │  │                                                                   │ │
    │  ├───────────────────────────────────────────────────────────────────┤ │
    │  │                                                                   │ │
    │  │  PRODUCTION TIPS                                                 │ │
    │  │  • Multiple Ingress Controller replicas                        │ │
    │  │  • Use cert-manager for TLS automation                         │ │
    │  │  • Cloud LB in front for DDoS protection                       │ │
    │  │  • Monitor and set appropriate resource limits                 │ │
    │  │                                                                   │ │
    │  └───────────────────────────────────────────────────────────────────┘ │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
                              END OF CHAPTER 4
================================================================================

