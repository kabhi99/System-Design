# CHAPTER 5: NETWORK POLICIES
*Securing Pod-to-Pod Communication*

By default, all pods in Kubernetes can communicate with all other pods.
Network Policies let you control this traffic, implementing microsegmentation
and defense-in-depth. This chapter covers Network Policies in depth.

## SECTION 5.1: WHY NETWORK POLICIES?

### THE DEFAULT: ALLOW ALL

Without Network Policies, Kubernetes is completely open:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DEFAULT KUBERNETES NETWORKING                                         |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                         CLUSTER                                  |   |
|  |                                                                  |   |
|  |  +---------+    +---------+    +---------+    +---------+      |   |
|  |  | Frontend|<-->|   API   |<-->| Database|<-->|  Cache  |      |   |
|  |  +---------+    +---------+    +---------+    +---------+      |   |
|  |       |              |              |              |           |   |
|  |       |              |              |              |           |   |
|  |       +--------------+--------------+--------------+           |   |
|  |                      |              |                          |   |
|  |  +---------+    +---------+    +---------+                    |   |
|  |  |  Debug  |<-->| Attacker|<-->| Logging |                    |   |
|  |  |   Pod   |    |   Pod   |    |   Pod   |                    |   |
|  |  +---------+    +---------+    +---------+                    |   |
|  |                                                                  |   |
|  |  EVERYONE CAN TALK TO EVERYONE!                                 |   |
|  |                                                                  |   |
|  |  Problems:                                                       |   |
|  |  * Compromised pod can reach database directly                  |   |
|  |  * No isolation between namespaces                              |   |
|  |  * No east-west traffic control                                 |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WITH NETWORK POLICIES

Network Policies implement the principle of least privilege:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WITH NETWORK POLICIES                                                 |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                         CLUSTER                                  |   |
|  |                                                                  |   |
|  |  +---------+    +---------+    +---------+    +---------+      |   |
|  |  | Frontend|--->|   API   |--->| Database|    |  Cache  |      |   |
|  |  +---------+    +----+----+    +---------+    +----^----+      |   |
|  |                      |                              |           |   |
|  |                      +------------------------------+           |   |
|  |                                                                  |   |
|  |  +---------+    +---------+    +---------+                    |   |
|  |  |  Debug  |    | Attacker|    | Logging |<---- (metrics only) |   |
|  |  |   Pod   |    |   Pod   |    |   Pod   |                    |   |
|  |  +---------+    +----+----+    +---------+                    |   |
|  |                      |                                          |   |
|  |                      [ ] BLOCKED!                                |   |
|  |                                                                  |   |
|  |  CONTROLLED COMMUNICATION:                                      |   |
|  |  [x] Frontend -> API (allowed)                                    |   |
|  |  [x] API -> Database (allowed)                                    |   |
|  |  [x] API -> Cache (allowed)                                       |   |
|  |  [ ] Attacker -> Database (blocked!)                              |   |
|  |  [ ] Frontend -> Database (blocked!)                              |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.2: HOW NETWORK POLICIES WORK

### THE NETWORK POLICY SPEC

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: my-policy
  namespace: production  # Policies are namespaced!
spec:
  # 1. Which pods does this policy apply to?
  podSelector:
    matchLabels:
      app: database

  # 2. What traffic types are affected?
  policyTypes:
  - Ingress  # Incoming traffic to selected pods
  - Egress   # Outgoing traffic from selected pods

  # 3. What traffic is ALLOWED?
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 5432

  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 9100
```

### KEY CONCEPTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NETWORK POLICY COMPONENTS                                             |
|                                                                         |
|  1. POD SELECTOR                                                       |
|     * Selects which pods the policy applies TO                        |
|     * Empty selector {} = all pods in namespace                       |
|     * Uses standard label selectors                                   |
|                                                                         |
|  2. POLICY TYPES                                                       |
|     * Ingress: Controls incoming traffic                              |
|     * Egress: Controls outgoing traffic                               |
|     * Must specify which you want to control                          |
|                                                                         |
|  3. INGRESS RULES                                                      |
|     * Define ALLOWED incoming traffic                                 |
|     * from: Sources allowed to send traffic                           |
|     * ports: Which ports/protocols are allowed                        |
|                                                                         |
|  4. EGRESS RULES                                                       |
|     * Define ALLOWED outgoing traffic                                 |
|     * to: Destinations allowed to receive traffic                     |
|     * ports: Which ports/protocols are allowed                        |
|                                                                         |
|  IMPORTANT:                                                            |
|  * Policies are ADDITIVE (allow, not deny)                            |
|  * If ANY policy selects a pod, traffic must match some rule         |
|  * Unselected pods have NO restrictions                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DEFAULT DENY BEHAVIOR

The first step in securing a namespace is creating "default deny" policies:

```bash
# Default deny ALL ingress traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}  # Applies to ALL pods
  policyTypes:
  - Ingress
  # No ingress rules = deny all ingress

---
# Default deny ALL egress traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
  namespace: production
spec:
  podSelector: {}  # Applies to ALL pods
  policyTypes:
  - Egress
  # No egress rules = deny all egress

---
# Default deny BOTH
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

## SECTION 5.3: SELECTOR TYPES

### UNDERSTANDING SELECTORS

Network Policies use three types of selectors in ingress/egress rules:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. podSelector                                                        |
|     Selects pods in the SAME namespace                                |
|                                                                         |
|     ingress:                                                           |
|     - from:                                                            |
|       - podSelector:                                                   |
|           matchLabels:                                                 |
|             app: frontend                                             |
|                                                                         |
|     Meaning: Allow traffic FROM pods with label app=frontend          |
|              in the SAME namespace as this policy                     |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  2. namespaceSelector                                                  |
|     Selects all pods in matching namespaces                           |
|                                                                         |
|     ingress:                                                           |
|     - from:                                                            |
|       - namespaceSelector:                                            |
|           matchLabels:                                                 |
|             env: staging                                              |
|                                                                         |
|     Meaning: Allow traffic FROM ALL pods in namespaces               |
|              with label env=staging                                   |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  3. ipBlock                                                            |
|     Selects IP CIDR ranges (external traffic)                        |
|                                                                         |
|     ingress:                                                           |
|     - from:                                                            |
|       - ipBlock:                                                       |
|           cidr: 10.0.0.0/8                                           |
|           except:                                                     |
|           - 10.10.0.0/16                                             |
|                                                                         |
|     Meaning: Allow traffic FROM 10.0.0.0/8                           |
|              EXCEPT 10.10.0.0/16                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COMBINING SELECTORS

The way you combine selectors matters A LOT!

```
+-------------------------------------------------------------------------+
|                                                                         |
|  AND vs OR LOGIC                                                       |
|                                                                         |
|  SEPARATE ITEMS = OR                                                   |
|  ------------------                                                    |
|  ingress:                                                              |
|  - from:                                                               |
|    - podSelector:                # +                                   |
|        matchLabels:              # |                                   |
|          app: frontend           # | OR                                |
|    - namespaceSelector:          # |                                   |
|        matchLabels:              # |                                   |
|          env: staging            # +                                   |
|                                                                         |
|  Meaning: Allow from (frontend pods in same namespace)                |
|           OR (ANY pod in staging namespace)                           |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  SAME ITEM = AND                                                       |
|  ----------------                                                      |
|  ingress:                                                              |
|  - from:                                                               |
|    - podSelector:                # +                                   |
|        matchLabels:              # |                                   |
|          app: frontend           # | AND                               |
|      namespaceSelector:          # |                                   |
|        matchLabels:              # |                                   |
|          env: staging            # +                                   |
|                                                                         |
|  Meaning: Allow from (frontend pods) AND (in staging namespace)       |
|           = frontend pods in staging namespace only                   |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  THIS IS A COMMON MISTAKE!                                             |
|                                                                         |
|  The position of the "-" (list item indicator) determines AND/OR:    |
|                                                                         |
|  - item1       ]                                                       |
|  - item2       ] = OR between items                                   |
|                                                                         |
|  - item1       ]                                                       |
|    item2       ] = AND within single item                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.4: PRACTICAL EXAMPLES

### EXAMPLE 1: ALLOW ONLY API TO DATABASE

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 5432

# Result:
# [x] API pods can reach database on port 5432
# [ ] All other pods cannot reach database
```

### EXAMPLE 2: ALLOW INTER-NAMESPACE COMMUNICATION

```bash
# First, label the source namespace
kubectl label namespace frontend-ns team=frontend

---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-namespace
  namespace: backend-ns
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          team: frontend
    ports:
    - protocol: TCP
      port: 8080
```

### EXAMPLE 3: ALLOW DNS (COMMON REQUIREMENT!)

If you deny all egress, pods can't resolve DNS!

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}  # All pods
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

### EXAMPLE 4: ALLOW EXTERNAL INTERNET ACCESS

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-internet
  namespace: production
spec:
  podSelector:
    matchLabels:
      internet-access: "true"
  policyTypes:
  - Egress
  egress:
  # Allow all egress to non-cluster IPs
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
        except:
        - 10.0.0.0/8      # Cluster internal
        - 172.16.0.0/12   # Cluster internal
        - 192.168.0.0/16  # Cluster internal
    ports:
    - protocol: TCP
      port: 443
```

### EXAMPLE 5: COMPLETE APPLICATION POLICY

```bash
# 1. Default deny for namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: myapp
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress

---
# 2. Allow DNS
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: myapp
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - ports:
    - port: 53
      protocol: UDP
    - port: 53
      protocol: TCP

---
# 3. Frontend: Allow ingress from Ingress controller, egress to API
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-policy
  namespace: myapp
spec:
  podSelector:
    matchLabels:
      tier: frontend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          app.kubernetes.io/name: ingress-nginx
    ports:
    - port: 80
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: api
    ports:
    - port: 8080

---
# 4. API: Allow ingress from frontend, egress to database
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-policy
  namespace: myapp
spec:
  podSelector:
    matchLabels:
      tier: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: frontend
    ports:
    - port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: database
    ports:
    - port: 5432

---
# 5. Database: Allow ingress from API only
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-policy
  namespace: myapp
spec:
  podSelector:
    matchLabels:
      tier: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: api
    ports:
    - port: 5432
```

## SECTION 5.5: CNI REQUIREMENTS

IMPORTANT: NOT ALL CNIs SUPPORT NETWORK POLICIES!

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CNI NETWORK POLICY SUPPORT                                            |
|                                                                         |
|  FULL SUPPORT:                                                         |
|  [x] Calico                 Full support + extensions                   |
|  [x] Cilium                 Full support + L7 policies                  |
|  [x] Weave                  Full support                                |
|  [x] Antrea                 Full support                                |
|  [x] Romana                 Full support                                |
|                                                                         |
|  PARTIAL/NO SUPPORT:                                                   |
|  [ ] Flannel                NO network policy support!                  |
|                           (use Flannel + Calico for policies)         |
|  ~ AWS VPC CNI            Limited (use Security Groups instead)       |
|                                                                         |
|  WHAT HAPPENS WITHOUT SUPPORT?                                         |
|  * NetworkPolicy resources are ACCEPTED (API doesn't reject)          |
|  * But policies are NOT ENFORCED!                                     |
|  * You think you're protected, but you're not!                        |
|                                                                         |
|  HOW TO CHECK:                                                         |
|  kubectl get pods -n kube-system                                      |
|  # Look for calico-node, cilium, weave, etc.                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.6: TROUBLESHOOTING NETWORK POLICIES

DEBUGGING WORKFLOW
### STEP 1: Verify CNI supports Network Policies

```bash
kubectl get pods -n kube-system | grep -E 'calico|cilium|weave'

If using Flannel alone, policies won't work!

STEP 2: List policies affecting a pod
-------------------------------------
kubectl get networkpolicy -n <namespace>

kubectl describe networkpolicy <name> -n <namespace>

STEP 3: Check if policy selects the right pods
---------------------------------------------
# Get pods matching the selector
kubectl get pods -n <namespace> -l app=database

STEP 4: Test connectivity
-------------------------
# Create test pod
kubectl run test --rm -it --image=busybox -- sh

# Try to connect
wget -qO- --timeout=2 http://<pod-ip>:<port>

STEP 5: Check policy is correctly applied (Calico example)
---------------------------------------------------------
# On the node running the pod
calicoctl get workloadendpoint

# Check iptables rules
iptables -L -n -v | grep cali
```

### COMMON MISTAKES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMMON NETWORK POLICY MISTAKES                                        |
|                                                                         |
|  1. FORGETTING DNS                                                     |
|     Symptom: Pods can't resolve hostnames                             |
|     Fix: Add egress rule for DNS (port 53 to kube-dns)               |
|                                                                         |
|  2. AND vs OR CONFUSION                                                |
|     Wrong:                                                             |
|     - from:                                                            |
|       - podSelector: {}     # OR                                      |
|       - namespaceSelector:  # This allows ALL pods!                   |
|           matchLabels: ...                                            |
|                                                                         |
|     Right:                                                             |
|     - from:                                                            |
|       - podSelector: {}     # AND                                     |
|         namespaceSelector:  # Only pods in specific namespace         |
|           matchLabels: ...                                            |
|                                                                         |
|  3. EMPTY SELECTOR MEANS "ALL"                                        |
|     podSelector: {}         # Matches ALL pods in namespace          |
|     namespaceSelector: {}   # Matches ALL namespaces                 |
|                                                                         |
|  4. NAMESPACE LABELS NOT SET                                          |
|     Policy uses namespaceSelector with label that doesn't exist      |
|     Fix: kubectl label namespace <ns> <key>=<value>                  |
|                                                                         |
|  5. CNI DOESN'T ENFORCE POLICIES                                      |
|     Flannel silently ignores NetworkPolicy!                           |
|     Fix: Use Calico, Cilium, or Flannel+Calico                       |
|                                                                         |
|  6. EGRESS TO ENDPOINTS, NOT SERVICES                                 |
|     Egress rules apply to pod IPs, not Service ClusterIPs            |
|     Use podSelector, not service name                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.7: ADVANCED: CALICO AND CILIUM EXTENSIONS

### CALICO GLOBAL NETWORK POLICIES

Calico extends Kubernetes with cluster-wide policies:

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: deny-all-external
spec:
  # Applies to ALL pods in ALL namespaces
  selector: all()
  types:
  - Egress
  egress:
  # Only allow egress to cluster-internal IPs
  - action: Allow
    destination:
      nets:
      - 10.0.0.0/8
      - 172.16.0.0/12
      - 192.168.0.0/16
  # Deny everything else (implicit)
```

### CILIUM L7 POLICIES

Cilium can inspect and filter at Layer 7:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: api-l7-policy
spec:
  endpointSelector:
    matchLabels:
      app: api
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "80"
      rules:
        http:
        # Only allow GET and POST, not DELETE
        - method: GET
        - method: POST
          path: "/api/v1/.*"

# This policy:
# [x] Allows GET requests
# [x] Allows POST to /api/v1/*
# [ ] Blocks DELETE requests!
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NETWORK POLICIES - KEY TAKEAWAYS                                      |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  CORE CONCEPTS                                                   | |
|  |  * Policies are ADDITIVE (allow rules, not deny)                | |
|  |  * Empty selector {} = all pods                                 | |
|  |  * Unselected pods have NO restrictions                         | |
|  |  * Start with "default deny" then allow what's needed          | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  SELECTORS                                                       | |
|  |  * podSelector: Pods in same namespace                          | |
|  |  * namespaceSelector: Pods in matching namespaces               | |
|  |  * ipBlock: External IP ranges                                  | |
|  |  * Separate list items = OR                                     | |
|  |  * Same list item = AND                                         | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  COMMON PATTERNS                                                 | |
|  |  * Default deny ingress + egress                                | |
|  |  * Allow DNS (port 53 to kube-system)                          | |
|  |  * Tier-based policies (frontend->api->database)                 | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  CNI REQUIREMENTS                                                | |
|  |  * Must use CNI that supports policies                          | |
|  |  * Calico, Cilium, Weave = full support                        | |
|  |  * Flannel = NO support (add Calico for policies)              | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 5

