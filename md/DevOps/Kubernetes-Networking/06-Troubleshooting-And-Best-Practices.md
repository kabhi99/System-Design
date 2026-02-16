# CHAPTER 6: TROUBLESHOOTING AND PRODUCTION BEST PRACTICES
*Real-World Kubernetes Networking Operations*

This final chapter covers practical troubleshooting techniques and production
best practices for Kubernetes networking.

## SECTION 6.1: SYSTEMATIC TROUBLESHOOTING APPROACH

### THE NETWORKING TROUBLESHOOTING FRAMEWORK

When debugging networking issues, work through layers systematically:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KUBERNETES NETWORKING TROUBLESHOOTING LAYERS                          |
|                                                                         |
|  Layer 1: POD NETWORKING                                               |
|  -----------------------------                                         |
|  * Does the pod have an IP?                                           |
|  * Is the pod's network namespace correct?                            |
|  * Can the pod reach its gateway?                                     |
|                                                                         |
|  Layer 2: POD-TO-POD                                                   |
|  ---------------------                                                 |
|  * Can pod A ping pod B's IP directly?                                |
|  * Are there Network Policies blocking traffic?                       |
|  * Is the CNI plugin functioning?                                     |
|                                                                         |
|  Layer 3: SERVICE                                                      |
|  ----------------                                                      |
|  * Is the Service created correctly?                                  |
|  * Does the Service have Endpoints?                                   |
|  * Are kube-proxy/IPVS rules correct?                                |
|                                                                         |
|  Layer 4: DNS                                                          |
|  ----------                                                            |
|  * Can pods resolve DNS?                                              |
|  * Is CoreDNS running?                                                |
|  * Is the Service name correct?                                       |
|                                                                         |
|  Layer 5: EXTERNAL ACCESS                                              |
|  -------------------------                                             |
|  * Is Ingress configured correctly?                                   |
|  * Is the LoadBalancer provisioned?                                   |
|  * Are NodePorts open on firewall?                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6.2: LAYER-BY-LAYER TROUBLESHOOTING

### LAYER 1: POD NETWORKING ISSUES

SYMPTOM: Pod stuck in "ContainerCreating"

```bash
# Check pod events
kubectl describe pod <pod-name>

Events:
  Warning  FailedCreatePodSandBox  Failed to create pod sandbox: 
           ... error adding pod to network ...

COMMON CAUSES:
1. CNI plugin not installed or crashed
2. IP address exhaustion
3. CNI configuration error

DIAGNOSIS:
# Check CNI pods
kubectl get pods -n kube-system | grep -E 'calico|flannel|weave|cilium'

# Check CNI logs
kubectl logs -n kube-system <cni-pod-name>

# Check CNI config
ls -la /etc/cni/net.d/
cat /etc/cni/net.d/*.conf

# Check IP allocation
kubectl get nodes -o wide  # See pod CIDR per node
```

SYMPTOM: Pod has IP but can't reach anything

```bash
# Enter pod and check networking
kubectl exec -it <pod-name> -- sh

# Inside pod:
ip addr          # Check interface exists
ip route         # Check default gateway
ping <gateway>   # Test gateway connectivity
```

### LAYER 2: POD-TO-POD ISSUES

SYMPTOM: Pods can't communicate directly

```bash
# Get pod IPs
kubectl get pods -o wide

# Test direct connectivity
kubectl exec -it <pod-a> -- ping <pod-b-ip>

# If ping fails:

# 1. Check Network Policies
kubectl get networkpolicy -n <namespace>

# 2. Check CNI routes on node
# SSH to node
ip route | grep <pod-ip-range>

# 3. Check iptables (for Calico)
iptables -L -n | grep DROP

# 4. Check node connectivity
# From node running pod A, ping pod B's IP
ping <pod-b-ip>
```

### LAYER 3: SERVICE ISSUES

SYMPTOM: Service IP doesn't respond

```bash
# Check Service exists with correct selector
kubectl describe service <svc-name>

# CHECK ENDPOINTS - Most common issue!
kubectl get endpoints <svc-name>

# If endpoints is empty:
# - Selector doesn't match any pods
# - Pods exist but aren't Ready
# - Pods are in different namespace

# Verify selector matches pods
kubectl get pods -l <selector-from-service>

# Check pod readiness
kubectl get pods -o wide
kubectl describe pod <pod-name> | grep -A 5 "Conditions"
```

SYMPTOM: Endpoints exist but Service doesn't work

```bash
# Check kube-proxy is running
kubectl get pods -n kube-system | grep kube-proxy

# Check iptables rules (iptables mode)
iptables -t nat -L KUBE-SERVICES | grep <svc-ip>

# Check IPVS rules (ipvs mode)
ipvsadm -Ln | grep <svc-ip>

# Test directly hitting endpoints
kubectl exec -it <test-pod> -- curl <endpoint-ip>:<port>
```

### LAYER 4: DNS ISSUES

SYMPTOM: Pods can't resolve service names

```bash
# Test DNS resolution inside pod
kubectl exec -it <pod> -- nslookup <service-name>
kubectl exec -it <pod> -- nslookup <service-name>.<namespace>
kubectl exec -it <pod> -- nslookup kubernetes.default

# If DNS fails:

# 1. Check CoreDNS is running
kubectl get pods -n kube-system -l k8s-app=kube-dns

# 2. Check CoreDNS logs
kubectl logs -n kube-system -l k8s-app=kube-dns

# 3. Check CoreDNS service
kubectl get svc -n kube-system kube-dns

# 4. Check pod's DNS config
kubectl exec -it <pod> -- cat /etc/resolv.conf

# 5. Test reaching CoreDNS directly
kubectl exec -it <pod> -- nslookup kubernetes.default 10.96.0.10
```

### LAYER 5: EXTERNAL ACCESS ISSUES

SYMPTOM: Can't reach service externally via NodePort

```bash
# Check NodePort is assigned
kubectl get svc <service-name>

# Test from outside cluster
curl <node-ip>:<nodeport>

# Check node firewall
# On node:
iptables -L INPUT | grep <nodeport>

# Check cloud security groups (AWS/GCP/Azure)
```

SYMPTOM: LoadBalancer stuck in "Pending"

```bash
# Check service status
kubectl describe svc <service-name>

# Common causes:
# - Cloud controller not configured
# - Quota exceeded
# - No cloud provider (bare metal)

# Check cloud-controller-manager logs
kubectl logs -n kube-system -l component=cloud-controller-manager
```

SYMPTOM: Ingress not routing traffic

```bash
# Check Ingress resource
kubectl describe ingress <ingress-name>

# Check Ingress Controller pods
kubectl get pods -n ingress-nginx
kubectl logs -n ingress-nginx <controller-pod>

# Check if Ingress has ADDRESS assigned
kubectl get ingress
# ADDRESS column should have IP

# Check backend service endpoints
kubectl get endpoints <backend-service>

# Test from Ingress Controller pod
kubectl exec -it -n ingress-nginx <controller> -- curl localhost:80
```

## SECTION 6.3: ESSENTIAL DEBUGGING TOOLS AND COMMANDS

### DEBUGGING TOOLKIT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ESSENTIAL DEBUGGING COMMANDS                                          |
|                                                                         |
|  BASIC INFORMATION                                                     |
|  -----------------                                                     |
|  kubectl get pods -o wide              # Pod IPs and nodes            |
|  kubectl get svc                        # Service IPs and ports       |
|  kubectl get endpoints                  # Service backends            |
|  kubectl get nodes -o wide              # Node IPs                    |
|                                                                         |
|  DETAILED INSPECTION                                                   |
|  --------------------                                                  |
|  kubectl describe pod <pod>            # Events, status               |
|  kubectl describe svc <svc>            # Selector, endpoints          |
|  kubectl describe ep <svc>             # Endpoint details             |
|  kubectl describe networkpolicy <np>   # Policy rules                 |
|                                                                         |
|  INSIDE PODS                                                           |
|  -----------                                                           |
|  kubectl exec -it <pod> -- sh          # Shell access                 |
|  kubectl exec <pod> -- ip addr         # Network interfaces           |
|  kubectl exec <pod> -- ip route        # Routing table                |
|  kubectl exec <pod> -- cat /etc/resolv.conf  # DNS config            |
|  kubectl exec <pod> -- nslookup <name> # DNS resolution              |
|  kubectl exec <pod> -- wget -qO- <url> # HTTP test                   |
|  kubectl exec <pod> -- nc -zv <ip> <port>  # TCP connectivity        |
|                                                                         |
|  ON NODES (SSH to node first)                                         |
|  ---------------------------                                           |
|  iptables -t nat -L -n -v              # NAT rules                    |
|  ipvsadm -Ln                            # IPVS rules (if enabled)    |
|  ip route                               # Host routing table          |
|  brctl show                             # Bridge information          |
|  crictl pods                            # Container runtime pods      |
|  journalctl -u kubelet                  # Kubelet logs               |
|                                                                         |
|  LOGS                                                                  |
|  ----                                                                  |
|  kubectl logs <pod>                     # Pod logs                    |
|  kubectl logs -n kube-system -l k8s-app=kube-dns    # CoreDNS       |
|  kubectl logs -n kube-system -l k8s-app=kube-proxy  # kube-proxy    |
|  kubectl logs -n ingress-nginx <ingress-pod>        # Ingress       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### NETWORK DEBUG POD

Create a pod with networking tools for debugging:

```bash
# Quick debug pod
kubectl run debug --rm -it --image=nicolaka/netshoot -- bash

# Or deploy a longer-running debug pod
apiVersion: v1
kind: Pod
metadata:
  name: netdebug
spec:
  containers:
  - name: netshoot
    image: nicolaka/netshoot
    command: ["sleep", "infinity"]

# Tools available in netshoot:
# - curl, wget
# - nslookup, dig, host
# - ping, traceroute, mtr
# - netcat, tcpdump
# - iperf3, iftop
# - ip, ss, netstat
```

### TCPDUMP FOR TRAFFIC ANALYSIS

Capture traffic for deep analysis:

```bash
# Capture on pod's interface
kubectl exec -it <pod> -- tcpdump -i eth0 -nn

# Capture specific traffic
kubectl exec -it <pod> -- tcpdump -i eth0 port 80

# Capture to file
kubectl exec -it <pod> -- tcpdump -i eth0 -w /tmp/capture.pcap

# Copy capture file locally
kubectl cp <pod>:/tmp/capture.pcap ./capture.pcap

# Analyze with wireshark or tshark
tshark -r capture.pcap
```

## SECTION 6.4: PRODUCTION BEST PRACTICES

### NETWORK ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PRODUCTION NETWORK DESIGN CHECKLIST                                   |
|                                                                         |
|  IP ADDRESS PLANNING                                                   |
|  --------------------                                                  |
|  □ Plan pod CIDR size for growth (don't use /24 for pod network!)    |
|  □ Ensure no overlap with existing networks                           |
|  □ Reserve ranges for future expansion                                |
|  □ Document all IP ranges                                             |
|                                                                         |
|  Example sizing:                                                       |
|  * 100 nodes × 100 pods/node = 10,000 pods minimum                   |
|  * /16 for pods = 65,536 IPs Y                                       |
|  * /20 for pods = 4,096 IPs X (too small for growth)                |
|                                                                         |
|  CNI SELECTION                                                         |
|  -------------                                                         |
|  □ Network policies required? Don't use Flannel alone                 |
|  □ Performance critical? Consider Cilium (eBPF) or Calico BGP        |
|  □ Multi-cloud/hybrid? Use overlay network                           |
|  □ AWS EKS? Consider VPC CNI for native integration                  |
|                                                                         |
|  INGRESS DESIGN                                                        |
|  --------------                                                        |
|  □ Multiple Ingress Controller replicas for HA                       |
|  □ TLS termination at Ingress (not pods)                             |
|  □ cert-manager for automatic certificate management                 |
|  □ Rate limiting at Ingress level                                    |
|  □ WAF in front of Ingress for public services                       |
|                                                                         |
|  SECURITY                                                              |
|  --------                                                              |
|  □ Default deny Network Policies in all namespaces                   |
|  □ Explicit allow policies for required traffic                      |
|  □ Don't forget DNS egress rules!                                    |
|  □ Namespace isolation (separate networks if needed)                 |
|  □ mTLS between services (consider service mesh)                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HIGH AVAILABILITY PATTERNS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HA NETWORKING COMPONENTS                                              |
|                                                                         |
|  1. COREDNS                                                            |
|     * Deploy at least 2 replicas                                      |
|     * Use Pod Anti-Affinity to spread across nodes                   |
|     * Set appropriate resource requests                               |
|                                                                         |
|     apiVersion: apps/v1                                               |
|     kind: Deployment                                                   |
|     metadata:                                                         |
|       name: coredns                                                   |
|     spec:                                                             |
|       replicas: 3                                                     |
|       template:                                                       |
|         spec:                                                         |
|           affinity:                                                   |
|             podAntiAffinity:                                         |
|               requiredDuringSchedulingIgnoredDuringExecution:        |
|               - topologyKey: kubernetes.io/hostname                  |
|                 labelSelector:                                       |
|                   matchLabels:                                       |
|                     k8s-app: kube-dns                                |
|                                                                         |
|  2. INGRESS CONTROLLER                                                 |
|     * Multiple replicas (3+ for production)                          |
|     * Spread across availability zones                               |
|     * HPA for autoscaling                                            |
|     * PDB to prevent all pods being evicted                          |
|                                                                         |
|  3. LOAD BALANCER                                                      |
|     * Use cloud provider's HA LB                                     |
|     * Multi-AZ deployment                                            |
|     * Health check configuration                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MONITORING AND OBSERVABILITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NETWORKING METRICS TO MONITOR                                         |
|                                                                         |
|  CNI HEALTH                                                            |
|  ----------                                                            |
|  * CNI pod status                                                     |
|  * IP allocation rate / available IPs                                |
|  * CNI error rates                                                    |
|                                                                         |
|  COREDNS                                                               |
|  -------                                                               |
|  * Query rate per second                                              |
|  * Query latency (P50, P99)                                          |
|  * NXDOMAIN rate                                                      |
|  * Forward request errors                                            |
|                                                                         |
|  KUBE-PROXY / SERVICES                                                 |
|  ---------------------                                                 |
|  * Service sync duration                                              |
|  * Endpoint changes                                                   |
|  * iptables/IPVS rule count                                          |
|                                                                         |
|  INGRESS                                                               |
|  -------                                                               |
|  * Request rate                                                       |
|  * Error rate (4xx, 5xx)                                             |
|  * Latency (P50, P99)                                                |
|  * Active connections                                                 |
|  * SSL certificate expiry                                            |
|                                                                         |
|  NETWORK CONNECTIVITY                                                  |
|  --------------------                                                  |
|  * Pod-to-pod latency                                                 |
|  * Cross-node packet loss                                            |
|  * Network policy violations                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CAPACITY PLANNING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NETWORKING CAPACITY CONSIDERATIONS                                    |
|                                                                         |
|  IP ADDRESS CAPACITY                                                   |
|  --------------------                                                  |
|  * Pod CIDR: Calculate max pods × 2 (for rolling deployments)        |
|  * Service CIDR: Usually /12 to /16 is sufficient                    |
|  * For AWS VPC CNI: Consider ENI limits per instance type            |
|                                                                         |
|  IPTABLES SCALING                                                      |
|  -----------------                                                     |
|  * 1,000 services ≈ 10,000 iptables rules                            |
|  * 10,000+ services: Consider IPVS mode                              |
|  * 50,000+ services: Consider Cilium eBPF                            |
|                                                                         |
|  COREDNS SCALING                                                       |
|  ---------------                                                       |
|  * 1 CoreDNS replica per 1,000 pods (rough guideline)                |
|  * Enable node-local DNS cache for high query loads                  |
|  * Consider DNS autoscaling based on cluster size                    |
|                                                                         |
|  INGRESS SCALING                                                       |
|  ---------------                                                       |
|  * Monitor connections per second, memory usage                      |
|  * Set HPA based on request rate or CPU                              |
|  * Consider multiple Ingress Controllers for different workloads    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6.5: COMMON PRODUCTION ISSUES AND SOLUTIONS

### ISSUE: DNS RESOLUTION SLOW OR FAILING

```bash
SYMPTOM: Services take seconds to resolve, intermittent DNS failures

CAUSE 1: CoreDNS overwhelmed
SOLUTION:
* Increase CoreDNS replicas
* Enable node-local DNS cache
* Check CoreDNS memory limits

# Enable node-local DNS
kubectl apply -f https://github.com/kubernetes/kubernetes/raw/master/cluster/addons/dns/nodelocaldns/nodelocaldns.yaml

CAUSE 2: ndots:5 causing unnecessary lookups
SOLUTION: Configure dnsConfig in pods

spec:
  dnsConfig:
    options:
    - name: ndots
      value: "2"  # Reduce from default 5
```

### ISSUE: SERVICE UNAVAILABLE DURING ROLLING UPDATES

```yaml
SYMPTOM: 5xx errors during deployments

SOLUTION: Configure proper termination handling

spec:
  containers:
  - name: app
    lifecycle:
      preStop:
        exec:
          command: ["sh", "-c", "sleep 10"]
    # Give time for endpoints to update
  terminationGracePeriodSeconds: 30

# Also configure readiness probe
readinessProbe:
  httpGet:
    path: /health
    port: 8080
  periodSeconds: 5
```

### ISSUE: NETWORK POLICIES NOT WORKING

```bash
SYMPTOM: Pods can still communicate despite deny policies

CHECK 1: CNI supports Network Policies
kubectl get pods -n kube-system | grep -E 'calico|cilium|weave'
# If only Flannel, policies won't work!

CHECK 2: Policy selects correct pods
kubectl get pods -l <selector-from-policy>

CHECK 3: Namespace labels exist (for namespaceSelector)
kubectl get ns --show-labels
```

### ISSUE: INGRESS CONTROLLER HIGH LATENCY

```bash
SYMPTOM: Slow response times through Ingress

CHECK 1: Ingress Controller resources
kubectl top pods -n ingress-nginx
# CPU/Memory might be saturated

CHECK 2: Backend service health
kubectl get endpoints <backend-service>
# Fewer endpoints = more load per pod

SOLUTION: Tune Ingress Controller

# Increase worker connections
data:
  worker-connections: "65535"
  keep-alive-requests: "10000"
  upstream-keepalive-connections: "1000"
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TROUBLESHOOTING AND BEST PRACTICES - KEY TAKEAWAYS                   |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  TROUBLESHOOTING APPROACH                                        | |
|  |  * Work through layers: Pod > Pod-to-Pod > Service > DNS >      | |
|  |    External                                                      | |
|  |  * Check Endpoints first (most common issue!)                   | |
|  |  * Use netshoot for debugging                                   | |
|  |  * tcpdump for deep packet analysis                            | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  PRODUCTION CHECKLIST                                            | |
|  |  * Plan IP ranges for growth                                    | |
|  |  * Choose CNI based on requirements                             | |
|  |  * Default deny Network Policies                                | |
|  |  * HA for DNS, Ingress, and CNI components                     | |
|  |  * Monitor networking metrics                                   | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|  |                                                                   | |
|  |  COMMON PITFALLS                                                 | |
|  |  * Forgetting DNS in egress policies                            | |
|  |  * Flannel without policy support                               | |
|  |  * Insufficient pod CIDR size                                   | |
|  |  * Missing readiness probes causing traffic to unready pods    | |
|  |                                                                   | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 6
*CONGRATULATIONS! You've completed the Kubernetes*
*Networking deep-dive series.*

