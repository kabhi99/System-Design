# CHAPTER 2: CNI PLUGINS - DEEP DIVE
*How the Flat Network is Actually Implemented*

The Container Network Interface (CNI) is the specification that defines how
container networking is configured. This chapter explains CNI in depth and
compares major CNI plugins used in production.

## SECTION 2.1: WHAT IS CNI?

### CNI EXPLAINED

CNI (Container Network Interface) is:

1. A SPECIFICATION
Defines the JSON format for network configuration
Defines the operations plugins must support

2. A SET OF LIBRARIES
Go libraries for writing CNI plugins

3. A COLLECTION OF PLUGINS
Reference implementations (bridge, host-local, etc.)

**CNI IS NOT:**
- A daemon or service
- A specific networking solution
- Kubernetes-specific (used by others too)

### THE CNI CONTRACT

A CNI plugin must support these operations:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CNI OPERATIONS                                                         |
|                                                                         |
|  ADD                                                                    |
|  ---                                                                    |
|  "Set up networking for this container"                                 |
|                                                                         |
|  Input:                                                                 |
|  * Container ID                                                         |
|  * Network namespace path                                               |
|  * Network configuration (JSON)                                         |
|                                                                         |
|  Output:                                                                |
|  * IP address assigned                                                  |
|  * Gateway                                                              |
|  * DNS servers                                                          |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  DEL                                                                    |
|  ---                                                                    |
|  "Tear down networking for this container"                              |
|                                                                         |
|  Input:                                                                 |
|  * Container ID                                                         |
|  * Network namespace path                                               |
|  * Network configuration (JSON)                                         |
|                                                                         |
|  Output:                                                                |
|  * Success/failure                                                      |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  CHECK                                                                  |
|  -----                                                                  |
|  "Verify networking is still correctly configured"                      |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  VERSION                                                                |
|  -------                                                                |
|  "Report supported CNI specification versions"                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HOW CNI IS INVOKED

When kubelet creates a pod, here's what happens:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KUBELET                                                                |
|    |                                                                    |
|    | 1. Create pod sandbox (pause container)                            |
|    |                                                                    |
|    v                                                                    |
|  CONTAINER RUNTIME (containerd/CRI-O)                                   |
|    |                                                                    |
|    | 2. Read CNI config from /etc/cni/net.d/                            |
|    |    (picks first file alphabetically)                               |
|    |                                                                    |
|    | 3. Execute CNI binary from /opt/cni/bin/                           |
|    |    with network namespace path as argument                         |
|    |                                                                    |
|    v                                                                    |
|  CNI PLUGIN BINARY                                                      |
|    |                                                                    |
|    | 4. Create veth pair                                                |
|    | 5. Move one end to pod namespace                                   |
|    | 6. Configure IP, routes                                            |
|    | 7. Return result (IP address) to runtime                           |
|    |                                                                    |
|    v                                                                    |
|  POD IS NOW NETWORKED                                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CNI CONFIGURATION FILE

CNI configuration lives in /etc/cni/net.d/:

```bash
# /etc/cni/net.d/10-mynet.conflist                          
{                                                           
  "cniVersion": "0.4.0",                                    
  "name": "mynet",                                          
  "plugins": [                                              
    {                                                       
      "type": "bridge",              < Main network plugin  
      "bridge": "cni0",                                     
      "isGateway": true,                                    
      "ipMasq": true,                                       
      "ipam": {                                             
        "type": "host-local",        < IP address allocation
        "subnet": "10.244.0.0/16",                          
        "routes": [                                         
          {"dst": "0.0.0.0/0"}                              
        ]                                                   
      }                                                     
    },                                                      
    {                                                       
      "type": "portmap",             < Port mapping plugin  
      "capabilities": {                                     
        "portMappings": true                                
      }                                                     
    }                                                       
  ]                                                         
}                                                           
```

**PLUGIN CHAINING:**
Notice the "plugins" array-CNI supports chaining multiple plugins!
Each plugin does one thing well, and they're composed together.

## SECTION 2.2: NETWORK TOPOLOGIES - HOW PLUGINS CONNECT PODS

CNI plugins implement the flat network requirement using different strategies:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THREE MAIN APPROACHES TO POD NETWORKING                                |
|                                                                         |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  1. OVERLAY NETWORKS                                               | |
|  |  ---------------------                                             | |
|  |  * Encapsulate pod traffic in outer packet                         | |
|  |  * Works regardless of underlay network                            | |
|  |  * Examples: Flannel (VXLAN), Weave, Calico (VXLAN mode)           | |
|  |                                                                    | |
|  |  Pros: Works anywhere, simple setup                                | |
|  |  Cons: Encapsulation overhead, MTU issues, debugging harder        | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  2. ROUTING-BASED                                                  | |
|  |  -------------------                                               | |
|  |  * Pod IPs routed directly (no encapsulation)                      | |
|  |  * Requires underlay network cooperation                           | |
|  |  * Examples: Calico (BGP), Cilium, kube-router                     | |
|  |                                                                    | |
|  |  Pros: No overhead, full MTU, standard networking                  | |
|  |  Cons: Requires infrastructure support, more complex setup         | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  3. CLOUD-NATIVE                                                   | |
|  |  -----------------                                                 | |
|  |  * Use cloud provider's native networking                          | |
|  |  * Pods get real VPC IPs                                           | |
|  |  * Examples: AWS VPC CNI, Azure CNI, GKE VPC-native                | |
|  |                                                                    | |
|  |  Pros: Native performance, security groups work, no overlay        | |
|  |  Cons: Cloud-specific, IP address consumption                      | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

### OVERLAY NETWORK IN DETAIL

Overlay networks create a virtual network "on top of" the physical network:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  OVERLAY NETWORK (VXLAN)                                                |
|                                                                         |
|   NODE 1 (Host IP: 192.168.1.10)       NODE 2 (Host IP: 192.168.1.11)   |
|   +----------------------------+       +-----------------------------+  |
|   |                            |       |                             |  |
|   |   +--------+  +--------+   |       |   +--------+  +---------+   |  |
|   |   | Pod A  |  | Pod B  |   |       |   | Pod C  |  | Pod D   |   |  |
|   |   |10.244  |  |10.244  |   |       |   |10.244  |  |10.244   |   |  |
|   |   |.0.2    |  |.0.3    |   |       |   |.1.2    |  |.1.3     |   |  |
|   |   +---+----+  +---+----+   |       |   +---+----+  +---+-----+   |  |
|   |       |           |        |       |       |           |         |  |
|   |   +---+-----------+----+   |       |   +---+-----------+-----+   |  |
|   |   |       cni0         |   |       |   |       cni0          |   |  |
|   |   |   (Linux bridge)   |   |       |   |   (Linux bridge)    |   |  |
|   |   +---------+----------+   |       |   +---------+-----------+   |  |
|   |             |              |       |             |               |  |
|   |   +---------+----------+   |       |   +---------+-----------+   |  |
|   |   |    VXLAN Device    |   |       |   |    VXLAN Device     |   |  |
|   |   |   (flannel.1)      |   |       |   |   (flannel.1)       |   |  |
|   |   |                    |   |       |   |                     |   |  |
|   |   | Encapsulates pod   |   |       |   | Decapsulates pod    |   |  |
|   |   | traffic in UDP     |<--+-------+-->| traffic from UDP    |   |  |
|   |   | (port 4789)        |   |       |   | (port 4789)         |   |  |
|   |   +---------+----------+   |       |   +---------+-----------+   |  |
|   |             |              |       |             |               |  |
|   |   +---------+----------+   |       |   +---------+-----------+   |  |
|   |   |       eth0         |   |       |   |       eth0          |   |  |
|   |   |   192.168.1.10     |   |       |   |   192.168.1.11      |   |  |
|   |   +---------+----------+   |       |   +---------+-----------+   |  |
|   |             |              |       |             |               |  |
|   +-------------+--------------+       +-------------+---------------+  |
|                 |                                    |                  |
|                 +------------ PHYSICAL --------------+                  |
|                              NETWORK                                    |
|                                                                         |
|  PACKET FROM Pod A (10.244.0.2) TO Pod C (10.244.1.2):                  |
|                                                                         |
|  ORIGINAL:                                                              |
|  +------------------------------------------+                           |
|  | Src: 10.244.0.2  Dst: 10.244.1.2  Data  |                            |
|  +------------------------------------------+                           |
|                                                                         |
|  AFTER ENCAPSULATION:                                                   |
|  +--------------------------------------------------------------------+ |
|  | Outer IP: 192.168.1.10 > 192.168.1.11                              | |
|  | UDP Port: 4789 (VXLAN)                                             | |
|  | +------------------------------------------+                       | |
|  | | Src: 10.244.0.2  Dst: 10.244.1.2  Data  |  (Original packet)     | |
|  | +------------------------------------------+                       | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

### ROUTING-BASED NETWORK IN DETAIL

Routing-based CNIs advertise pod routes directly:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ROUTING-BASED NETWORK (BGP with Calico)                                |
|                                                                         |
|   NODE 1 (192.168.1.10)                NODE 2 (192.168.1.11)            |
|   +----------------------------+       +-----------------------------+  |
|   |                            |       |                             |  |
|   |   +--------+  +--------+   |       |   +--------+  +---------+   |  |
|   |   | Pod A  |  | Pod B  |   |       |   | Pod C  |  | Pod D   |   |  |
|   |   |10.244  |  |10.244  |   |       |   |10.244  |  |10.244   |   |  |
|   |   |.0.2    |  |.0.3    |   |       |   |.1.2    |  |.1.3     |   |  |
|   |   +---+----+  +---+----+   |       |   +---+----+  +---+-----+   |  |
|   |       |           |        |       |       |           |         |  |
|   |   Routes to pods via      |       |   Routes to pods via         |  |
|   |   direct veth pairs        |       |   direct veth pairs         |  |
|   |                            |       |                             |  |
|   |   ROUTING TABLE:           |       |   ROUTING TABLE:            |  |
|   |   10.244.0.2 > caliXXX     |       |   10.244.1.2 > caliYYY      |  |
|   |   10.244.0.3 > caliZZZ     |       |   10.244.1.3 > caliWWW      |  |
|   |   10.244.1.0/24 >          |       |   10.244.0.0/24 >           |  |
|   |     via 192.168.1.11       |       |     via 192.168.1.10        |  |
|   |                            |       |                             |  |
|   +-------------+--------------+       +-------------+---------------+  |
|                 |                                    |                  |
|                 |      BGP peering between nodes     |                  |
|                 |<------------------------------------>                 |
|                 |    "I have 10.244.0.0/24"          |                  |
|                 |    "I have 10.244.1.0/24"          |                  |
|                 |                                    |                  |
|                 +------------ PHYSICAL --------------+                  |
|                              NETWORK                                    |
|                       (must route pod CIDRs)                            |
|                                                                         |
|  PACKET FROM Pod A (10.244.0.2) TO Pod C (10.244.1.2):                  |
|                                                                         |
|  NO ENCAPSULATION - packet sent directly:                               |
|  +------------------------------------------+                           |
|  | Src: 10.244.0.2  Dst: 10.244.1.2  Data  |                            |
|  +------------------------------------------+                           |
|                                                                         |
|  Physical network routes 10.244.1.0/24 to Node 2                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.3: MAJOR CNI PLUGINS COMPARISON

### FLANNEL - SIMPLE AND RELIABLE

Flannel is the simplest CNI plugin, created by CoreOS:

```
ARCHITECTURE:                                                              
* flanneld daemon runs on each node                                        
* Stores subnet allocation in etcd or Kubernetes API                       
* Supports multiple backends: VXLAN, host-gw, WireGuard                    

+-------------------------------------------------------------------------+
|                                                                         |
|  FLANNEL BACKENDS                                                       |
|                                                                         |
|  VXLAN (default):                                                       |
|  * Overlay network using VXLAN                                          |
|  * Works everywhere, no infrastructure changes                          |
|  * ~10-15% overhead due to encapsulation                                |
|                                                                         |
|  host-gw:                                                               |
|  * Direct routing, no encapsulation                                     |
|  * Requires Layer 2 adjacency between nodes                             |
|  * Best performance                                                     |
|                                                                         |
|  WireGuard:                                                             |
|  * Encrypted overlay using WireGuard VPN                                |
|  * Secure, relatively fast                                              |
|                                                                         |
+-------------------------------------------------------------------------+

PROS:                                                                      
Y Simple-easy to deploy and understand                                     
Y Reliable-mature and battle-tested                                        
Y Low resource usage                                                       

CONS:                                                                      
X No network policies (use with Calico for policies)                       
X No advanced features                                                     
X VXLAN overhead                                                           

BEST FOR:                                                                  
* Simple clusters                                                          
* Getting started with Kubernetes                                          
* When you just need "it to work"                                          
```

### CALICO - FULL-FEATURED NETWORKING

Calico is the most popular CNI for production:

```
ARCHITECTURE:                                                              
* calico-node daemon on each node (runs BIRD BGP daemon)                   
* calico-kube-controllers for sync with Kubernetes                         
* Felix agent for programming routes and policies                          

+-------------------------------------------------------------------------+
|                                                                         |
|  CALICO NETWORKING MODES                                                |
|                                                                         |
|  BGP (default):                                                         |
|  * Pods get routable IPs                                                |
|  * BGP advertises pod routes                                            |
|  * No encapsulation, best performance                                   |
|  * Requires BGP-capable infrastructure or full mesh                     |
|                                                                         |
|  VXLAN:                                                                 |
|  * Overlay when BGP isn't possible                                      |
|  * Works anywhere                                                       |
|  * Slight overhead                                                      |
|                                                                         |
|  IPIP:                                                                  |
|  * IP-in-IP encapsulation                                               |
|  * Less overhead than VXLAN                                             |
|  * Simpler tunneling                                                    |
|                                                                         |
|  CrossSubnet:                                                           |
|  * BGP within subnet, IPIP/VXLAN across subnets                         |
|  * Best of both worlds                                                  |
|                                                                         |
+-------------------------------------------------------------------------+

NETWORK POLICIES:                                                          
Calico implements Kubernetes NetworkPolicy AND extends it:                 

# Kubernetes NetworkPolicy (Calico implements)                             
apiVersion: networking.k8s.io/v1                                           
kind: NetworkPolicy                                                        
...                                                                        

# Calico-specific GlobalNetworkPolicy                                      
apiVersion: projectcalico.org/v3                                           
kind: GlobalNetworkPolicy                                                  
metadata:                                                                  
  name: deny-all-egress                                                    
spec:                                                                      
  selector: all()                                                          
  types:                                                                   
  - Egress                                                                 
  egress: []                                                               

PROS:                                                                      
Y Excellent performance (especially BGP mode)                              
Y Full network policy support                                              
Y Flexible-works in any environment                                        
Y Strong security features                                                 

CONS:                                                                      
X More complex to configure                                                
X BGP requires some networking knowledge                                   
X More resource usage than Flannel                                         

BEST FOR:                                                                  
* Production clusters                                                      
* Security-conscious environments                                          
* When you need network policies                                           
```

### CILIUM - EBPF-POWERED NETWORKING

Cilium uses eBPF for high-performance networking:

```
WHAT IS eBPF?                                                              
eBPF (extended Berkeley Packet Filter) allows running custom code          
in the Linux kernel without modifying kernel source. Cilium uses           
this for networking, security, and observability.                          

+-------------------------------------------------------------------------+
|                                                                         |
|  TRADITIONAL CNI vs CILIUM (eBPF)                                       |
|                                                                         |
|  TRADITIONAL:                                                           |
|  Packet > iptables > routing > bridge > deliver                         |
|           |         |         |                                         |
|           +---------+---------+-- Multiple kernel subsystems            |
|                                   Context switches                      |
|                                   Rule traversal                        |
|                                                                         |
|  CILIUM (eBPF):                                                         |
|  Packet > eBPF program > deliver                                        |
|           |                                                             |
|           +-- Single efficient program in kernel                        |
|               Direct routing decisions                                  |
|               No iptables rules                                         |
|                                                                         |
+-------------------------------------------------------------------------+

CILIUM FEATURES:                                                           

1. KUBE-PROXY REPLACEMENT                                                  
   Cilium can replace kube-proxy entirely, implementing services           
   with eBPF instead of iptables.                                          

2. NETWORK POLICIES ON STEROIDS                                            
   * L3/L4 policies (like Kubernetes NetworkPolicy)                        
   * L7 policies (HTTP, gRPC, Kafka-aware!)                                
   * DNS-based policies                                                    

   Example L7 policy:                                                      
   apiVersion: cilium.io/v2                                                
   kind: CiliumNetworkPolicy                                               
   metadata:                                                               
     name: allow-get-only                                                  
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
           - method: GET         # Only allow GET requests!                
             path: "/api/.*"                                               

3. HUBBLE OBSERVABILITY                                                    
   Built-in network flow visibility:                                       
   * See all connections in cluster                                        
   * Service dependency maps                                               
   * Flow logs without packet capture                                      

PROS:                                                                      
Y Highest performance                                                      
Y L7-aware network policies                                                
Y Built-in observability (Hubble)                                          
Y Can replace kube-proxy                                                   

CONS:                                                                      
X Requires newer kernels (4.9+, 5.10+ for all features)                    
X More complex                                                             
X Heavier resource usage                                                   

BEST FOR:                                                                  
* High-performance requirements                                            
* Advanced security needs (L7 policies)                                    
* When you need observability built-in                                     
```

### AWS VPC CNI - NATIVE AWS NETWORKING

The AWS VPC CNI gives pods real VPC IP addresses:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  AWS VPC CNI ARCHITECTURE                                               |
|                                                                         |
|       +------------------------------------------------+                |
|       |                    AWS VPC                     |                |
|       |                 10.0.0.0/16                    |                |
|       |                                                |                |
|       |   Subnet A               Subnet B              |                |
|       |   10.0.1.0/24            10.0.2.0/24          |                 |
|       |                                                |                |
|       |   Node 1                 Node 2                |                |
|       |   10.0.1.10              10.0.2.20            |                 |
|       |   +------------+        +------------+        |                 |
|       |   | ENI 1      |        | ENI 1      |        |                 |
|       |   | (primary)  |        | (primary)  |        |                 |
|       |   |            |        |            |        |                 |
|       |   | ENI 2      |        | ENI 2      |        |                 |
|       |   | 10.0.1.50 -+---Pod A| 10.0.2.50 -+---Pod C|                 |
|       |   | 10.0.1.51 -+---Pod B| 10.0.2.51 -+---Pod D|                 |
|       |   | ...        |        | ...        |        |                 |
|       |   +------------+        +------------+        |                 |
|       |                                                |                |
|       +------------------------------------------------+                |
|                                                                         |
|   EACH POD GETS A REAL VPC IP!                                          |
|   Pod A: 10.0.1.50 (real VPC IP, not overlay)                           |
|                                                                         |
|   HOW IT WORKS:                                                         |
|   * Each node gets multiple ENIs (Elastic Network Interfaces)           |
|   * Each ENI can have multiple secondary IPs                            |
|   * Pods get assigned these secondary IPs                               |
|   * Traffic routes natively through VPC                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

PROS:
Y Native VPC performance
Y Security groups work on pods!
Y No overlay overhead
Y Pods visible in VPC flow logs

CONS:
X IP address exhaustion (pods consume VPC IPs)
X Limited pods per node (based on ENI limits)
X AWS-specific

IP ADDRESS PLANNING:
Instance type limits how many pods can run:

t3.medium:  3 ENIs x 6 IPs each = 17 pods max
m5.large:   3 ENIs x 10 IPs each = 29 pods max
m5.xlarge:  4 ENIs x 15 IPs each = 58 pods max

You need to plan VPC CIDR carefully to have enough IPs!

## SECTION 2.4: CNI PLUGIN COMPARISON TABLE

```
+----------------------------------------------------------------------------------------+
|                                                                                        |
|  CNI PLUGIN COMPARISON                                                                 |
|                                                                                        |
|  +----------+-----------+-----------+-----------+-----------+------------------------+ |
|  | Feature  | Flannel   | Calico    | Cilium    | AWS VPC   | Notes                  | |
|  +----------+-----------+-----------+-----------+-----------+------------------------+ |
|  | Network  | Overlay   | BGP/      | eBPF +    | Native    | Calico most flexible   | |
|  | Mode     | (VXLAN)   | Overlay   | routing   | VPC       |                        | |
|  +----------+-----------+-----------+-----------+-----------+------------------------+ |
|  | Network  | No        | Yes       | Yes +     | Via SGs   | Cilium adds L7         | |
|  | Policies | (use +    | (K8s +    | L7        |           |                        | |
|  |          | Calico)   | extended) |           |           |                        | |
|  +----------+-----------+-----------+-----------+-----------+------------------------+ |
|  | Perf.    | Good      | Excellent | Best      | Excellent | eBPF is fastest        | |
|  +----------+-----------+-----------+-----------+-----------+------------------------+ |
|  | Complex. | Low       | Medium    | High      | Low       | Flannel simplest       | |
|  +----------+-----------+-----------+-----------+-----------+------------------------+ |
|  | Resource | Low       | Medium    | High      | Low       | Cilium needs memory    | |
|  | Usage    |           |           |           |           |                        | |
|  +----------+-----------+-----------+-----------+-----------+------------------------+ |
|  | Encrypt. | WireGuard | WireGuard | WireGuard | VPC       | All support encrypt.   | |
|  |          | backend   | option    | option    | encrypt   |                        | |
|  +----------+-----------+-----------+-----------+-----------+------------------------+ |
|  | Replace  | No        | No        | Yes       | No        | Cilium major feature   | |
|  | kube-    |           |           |           |           |                        | |
|  | proxy    |           |           |           |           |                        | |
|  +----------+-----------+-----------+-----------+-----------+------------------------+ |
|  | Best For | Simple    | Prod      | High-perf | EKS       | Choose based on needs  | |
|  |          | clusters  | clusters  | security  | clusters  |                        | |
|  +----------+-----------+-----------+-----------+-----------+------------------------+ |
|                                                                                        |
+----------------------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CNI PLUGINS - KEY TAKEAWAYS                                            |
|                                                                         |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  CNI IS A SPECIFICATION                                            | |
|  |  * Defines ADD/DEL/CHECK/VERSION operations                        | |
|  |  * Plugins are executables called by container runtime             | |
|  |  * Config in /etc/cni/net.d/                                       | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  THREE APPROACHES                                                  | |
|  |  * Overlay: Encapsulate traffic (Flannel, Weave)                   | |
|  |  * Routing: Direct routes via BGP (Calico)                         | |
|  |  * Cloud-native: Use cloud networking (AWS VPC CNI)                | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  CHOOSING A CNI                                                    | |
|  |  * Just starting? Flannel                                          | |
|  |  * Production? Calico                                              | |
|  |  * Need maximum performance + L7 policies? Cilium                  | |
|  |  * On AWS EKS? AWS VPC CNI                                         | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 2

