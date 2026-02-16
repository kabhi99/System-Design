# CHAPTER 2: DOCKER NETWORKING INTERNALS
*Understanding How Docker Implements Container Networking*

Now that we understand the Linux networking primitives, let's see how Docker
combines them into a cohesive networking system. This chapter covers Docker's
architecture, the Container Network Model (CNM), and how the different network
drivers work under the hood.

## SECTION 2.1: THE CONTAINER NETWORK MODEL (CNM)

### WHAT IS CNM?

The Container Network Model is Docker's specification for container networking.
It defines three fundamental components:

1. SANDBOX
2. ENDPOINT
3. NETWORK

Think of CNM as the "blueprint" that Docker follows to create networks.

### THE THREE BUILDING BLOCKS

```
+-------------------------------------------------------------------------+
|                                                                         |
|                    CONTAINER NETWORK MODEL (CNM)                        |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  SANDBOX                                                                |
|  --------                                                               |
|  A Sandbox contains the configuration of a container's network stack.   |
|                                                                         |
|  In practice, a Sandbox IS a Linux network namespace. It includes:      |
|  * Network interfaces                                                   |
|  * Routing table                                                        |
|  * DNS settings (/etc/resolv.conf)                                      |
|  * Firewall rules                                                       |
|                                                                         |
|  Each container has exactly ONE sandbox.                                |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  ENDPOINT                                                               |
|  ---------                                                              |
|  An Endpoint connects a Sandbox to a Network.                           |
|                                                                         |
|  In practice, an Endpoint is one end of a veth pair:                    |
|  * One end inside the container's namespace (eth0)                      |
|  * Other end attached to a network (bridge, overlay, etc.)              |
|                                                                         |
|  A sandbox can have MULTIPLE endpoints (connected to multiple networks) |
|                                                                         |
|  ===================================================================    |
|                                                                         |
|  NETWORK                                                                |
|  --------                                                               |
|  A Network is a group of Endpoints that can communicate directly.       |
|                                                                         |
|  In practice, a Network is implemented by a network driver:             |
|  * Bridge network: Linux bridge                                         |
|  * Overlay network: VXLAN                                               |
|  * Host network: Host's network namespace                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### VISUALIZING CNM

```
+-------------------------------------------------------------------------+
|                                                                         |
|                         NETWORK A                                       |
|   +------------------------------------------------------------------+  |
|   |                                                                  |  |
|   |  +---------------+    +---------------+    +-----------------+   |  |
|   |  |   SANDBOX 1   |    |   SANDBOX 2   |    |   SANDBOX 3     |   |  |
|   |  |  (Container)  |    |  (Container)  |    |  (Container)    |   |  |
|   |  |               |    |               |    |                 |   |  |
|   |  |  +---------+  |    |  +---------+  |    |  +-----------+  |   |  |
|   |  |  |Endpoint |  |    |  |Endpoint |  |    |  |Endpoint   |  |   |  |
|   |  |  |  (eth0) |  |    |  |  (eth0) |  |    |  |  (eth0)   |  |   |  |
|   |  |  +----+----+  |    |  +----+----+  |    |  +----+------+  |   |  |
|   |  +-------+-------+    +-------+-------+    +-------+---------+   |  |
|   |          |                    |                    |             |  |
|   |          |                    |                    |             |  |
|   |          +--------------------+--------------------+             |  |
|   |                               |                                  |  |
|   |                    +----------+----------+                       |  |
|   |                    |   Network Driver    |                       |  |
|   |                    |   (Bridge, etc.)    |                       |  |
|   |                    +---------------------+                       |  |
|   |                                                                  |  |
|   +------------------------------------------------------------------+  |
|                                                                         |
|   All three sandboxes share the same network and can communicate.       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MULTI-NETWORK CONTAINERS

A container can be connected to multiple networks simultaneously:

```
+-------------------------------------------------------------------------+
|                                                                         |
|      NETWORK A (Frontend)              NETWORK B (Backend)              |
|  +-----------------------------+   +-------------------------------+    |
|  |                             |   |                               |    |
|  |  +-----------+              |   |              +-------------+  |    |
|  |  | Web Server|              |   |              | Database    |  |    |
|  |  |           |              |   |              |             |  |    |
|  |  |  +-----+  |              |   |              |  +-------+  |  |    |
|  |  |  |EP A |  |              |   |              |  |EP B   |  |  |    |
|  |  +--+--+--+--+              |   |              +--+--+--+----+  |    |
|  |        |                    |   |                   |           |    |
|  |        |    +---------------+---+---------------+   |           |    |
|  |        |    |    API Server |   |               |   |           |    |
|  |        |    |               |   |               |   |           |    |
|  |        |    |  +-----+  +-----+ |               |   |           |    |
|  |        |    |  |EP A |  |EP B | |               |   |           |    |
|  |        |    +--+--+--+--+--+--+-+               |   |           |    |
|  |        |          |        |                    |   |           |    |
|  |  ------+----------+--------+--------------------+---+-----------|    |
|  |       Bridge A             |      Bridge B      |               |    |
|  |                            |                    |               |    |
|  +----------------------------+    +---------------+---------------+    |
|                                                                         |
|  The API Server has TWO endpoints:                                      |
|  * EP A on Network A (can talk to Web Server)                           |
|  * EP B on Network B (can talk to Database)                             |
|                                                                         |
|  Web Server CANNOT reach Database (different networks, no shared EP)    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### PRACTICAL EXAMPLE

```bash
# Create two networks                             
docker network create frontend                    
docker network create backend                     

# Run database (only on backend)                  
docker run -d --name db --network backend postgres

# Run API server (connected to BOTH networks)     
docker run -d --name api --network backend my-api 
docker network connect frontend api               

# Run web server (only on frontend)               
docker run -d --name web --network frontend nginx 

# Now:                                            
# - web can reach api (both on frontend)          
# - api can reach db (both on backend)            
# - web CANNOT reach db (no shared network)       
```

## SECTION 2.2: LIBNETWORK - DOCKER'S NETWORKING LIBRARY

### WHAT IS LIBNETWORK?

libnetwork is the actual Go library that implements the Container Network Model.
When Docker creates a network or connects a container, libnetwork does the work.

```
Docker CLI/API                                                             
                                                                          |
     v                                                                     
Docker Daemon                                                              
                                                                          |
     v                                                                     
+-------------------------------------------------------------------------+
|                          libnetwork                                     |
|                                                                         |
|   +-------------------------------------------------------------------+ |
|   |                    Network Controller                             | |
|   |                                                                   | |
|   |  Manages networks, endpoints, and drivers                         | |
|   |  Stores state (network configs, IP allocations)                   | |
|   |  Coordinates between different drivers                            | |
|   |                                                                   | |
|   +-------------------------------------------------------------------+ |
|                            |                                            |
|            +---------------+---------------+                            |
|            v               v               v                            |
|   +--------------+ +--------------+ +--------------+                    |
|   |   Bridge     | |   Overlay    | |   Macvlan    |                    |
|   |   Driver     | |   Driver     | |   Driver     |                    |
|   +--------------+ +--------------+ +--------------+                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DRIVER ARCHITECTURE

Network drivers in Docker follow a plugin architecture:

BUILT-IN DRIVERS (compiled into Docker):
- bridge   - Linux bridge-based networks
- host     - Container uses host's network
- none     - No networking
- overlay  - Multi-host overlay networks
- macvlan  - Direct MAC address assignment

REMOTE/PLUGIN DRIVERS (separate processes):
- Weave
- Calico
- Flannel
- Third-party plugins

Each driver must implement a standard interface:

```
type Driver interface {                                        
    CreateNetwork(...)    // Create a new network              
    DeleteNetwork(...)    // Remove a network                  
    CreateEndpoint(...)   // Create endpoint in network        
    DeleteEndpoint(...)   // Remove endpoint                   
    Join(...)             // Connect container to endpoint     
    Leave(...)            // Disconnect container from endpoint
}                                                              
```

## SECTION 2.3: THE BRIDGE DRIVER - DEEP DIVE

### WHEN DOCKER CREATES A BRIDGE NETWORK

Let's trace exactly what happens when you create a bridge network:

```
docker network create my-bridge                      

STEP 1: Docker calls libnetwork                      
+--> libnetwork calls bridge driver's CreateNetwork()

STEP 2: Bridge driver creates Linux bridge           
+--> ip link add br-<network-id> type bridge         
+--> ip link set br-<network-id> up                  

STEP 3: Assign IP to bridge (becomes gateway)        
+--> ip addr add 172.18.0.1/16 dev br-<network-id>   

STEP 4: Configure iptables rules                     
+--> NAT rules for outbound traffic                  
+--> Isolation rules between networks                

STEP 5: Store network metadata                       
+--> Save to /var/lib/docker/network/files/...       
```

Verify it:

```bash
# Create network                                        
docker network create my-bridge                         

# See the Linux bridge created                          
ip link | grep br-                                      
# br-a1b2c3d4e5f6: <BROADCAST,MULTICAST,UP,LOWER_UP> ...

# See its IP address                                    
docker network inspect my-bridge | grep Gateway         
# "Gateway": "172.18.0.1"                               
```

### WHEN A CONTAINER JOINS A BRIDGE NETWORK

```
docker run -d --name web --network my-bridge nginx        

STEP 1: Create network namespace for container            
+--> Container gets its own isolated network stack        

STEP 2: Create veth pair                                  
+--> ip link add veth-xxx type veth peer name eth0        

STEP 3: Move one end into container's namespace           
+--> ip link set eth0 netns <container-ns>                

STEP 4: Attach other end to bridge                        
+--> ip link set veth-xxx master br-<network-id>          

STEP 5: Allocate IP address (IPAM)                        
+--> Container gets next available IP (172.18.0.2)        

STEP 6: Configure container's network                     
+--> ip addr add 172.18.0.2/16 dev eth0 (inside container)
+--> ip route add default via 172.18.0.1 (set gateway)    

STEP 7: Bring interfaces up                               
+--> ip link set veth-xxx up                              
+--> ip link set eth0 up (inside container)               
```

### THE RESULT: COMPLETE BRIDGE ARCHITECTURE

After running three containers on my-bridge:

```
+-------------------------------------------------------------------------+
|                              HOST                                       |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                 Docker Network: my-bridge                        |   |
|  |                                                                  |   |
|  |  +----------------+ +----------------+ +----------------+        |   |
|  |  |  Container 1   | |  Container 2   | |  Container 3   |        |   |
|  |  |  "web"         | |  "api"         | |  "db"          |        |   |
|  |  |  172.18.0.2    | |  172.18.0.3    | |  172.18.0.4    |        |   |
|  |  |                | |                | |                |        |   |
|  |  |  +----------+  | |  +----------+  | |  +----------+  |        |   |
|  |  |  |   eth0   |  | |  |   eth0   |  | |  |   eth0   |  |        |   |
|  |  |  +----+-----+  | |  +----+-----+  | |  +----+-----+  |        |   |
|  |  |       |        | |       |        | |       |        |        |   |
|  |  +-------+--------+ +-------+--------+ +-------+--------+        |   |
|  |          |                  |                  |                 |   |
|  |          | veth-aaa         | veth-bbb         | veth-ccc        |   |
|  |          |                  |                  |                 |   |
|  |  +-------+------------------+------------------+-------+         |   |
|  |  |               br-a1b2c3d4e5f6 (Linux Bridge)        |         |   |
|  |  |                    172.18.0.1 (gateway)             |         |   |
|  |  +-------------------------+---------------------------+         |   |
|  |                            |                                     |   |
|  +----------------------------+-------------------------------------+   |
|                               |                                         |
|                        +------+------+                                  |
|                        |  iptables   |                                  |
|                        | MASQUERADE  |                                  |
|                        +------+------+                                  |
|                               |                                         |
|                          +----+----+                                    |
|                          |  eth0   | (Host's physical NIC)              |
|                          +---------+                                    |
|                               |                                         |
+-------------------------------+-----------------------------------------+
                                                                          |
                           Internet                                        
```

## SECTION 2.4: DOCKER DNS - AUTOMATIC SERVICE DISCOVERY

### THE PROBLEM: HOW DO CONTAINERS FIND EACH OTHER?

Containers get dynamic IP addresses. You can't hardcode IPs:

```bash
# Don't do this!                                           
database_host = "172.18.0.4"  # IP might change on restart!
```

Docker solves this with automatic DNS.

### DOCKER'S EMBEDDED DNS SERVER

On USER-DEFINED networks (not the default bridge!), Docker runs an embedded
DNS server that automatically resolves container names to their IP addresses.

```
CONTAINER'S /etc/resolv.conf:                                              
+-------------------------------------------------------------------------+
|  nameserver 127.0.0.11                                                  |
|  options ndots:0                                                        |
+-------------------------------------------------------------------------+

127.0.0.11 is Docker's embedded DNS server.                                

When container asks to resolve "db":                                       
1. Container queries 127.0.0.11                                            
2. Docker DNS checks if "db" is a container on the same network            
3. If yes, returns container's IP                                          
4. If no, forwards to host's DNS servers                                   
```

### HOW IT WORKS INTERNALLY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONTAINER "web"                                                        |
|  -----------------                                                      |
|                                                                         |
|  Application code:                                                      |
|  conn = pg.connect("db:5432")                                           |
|            |                                                            |
|            | 1. Resolve "db"                                            |
|            v                                                            |
|  +---------------------+                                                |
|  |   glibc resolver    |                                                |
|  | Reads /etc/resolv.conf                                               |
|  +----------+----------+                                                |
|             | 2. DNS query to 127.0.0.11                                |
|             v                                                           |
|  +------------------------------------------------------------------+   |
|  |                    Docker DNS (127.0.0.11)                       |   |
|  |                                                                  |   |
|  |  Maintains mapping:                                              |   |
|  |  "db"  > 172.18.0.4                                              |   |
|  |  "web" > 172.18.0.2                                              |   |
|  |  "api" > 172.18.0.3                                              |   |
|  |                                                                  |   |
|  +----------+-------------------------------------------------------+   |
|             | 3. Returns 172.18.0.4                                     |
|             v                                                           |
|  Application connects to 172.18.0.4:5432                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### IMPORTANT: DNS ONLY WORKS ON USER-DEFINED NETWORKS!

```bash
# DEFAULT BRIDGE - NO DNS!                                 
docker run -d --name db postgres                           
docker run -d --name web nginx                             
docker exec web ping db                                    
# ERROR: ping: db: Name or service not known               

# USER-DEFINED BRIDGE - DNS WORKS!                         
docker network create my-net                               
docker run -d --name db --network my-net postgres          
docker run -d --name web --network my-net nginx            
docker exec web ping db                                    
# PING db (172.18.0.2): 56 data bytes                      
# 64 bytes from 172.18.0.2: icmp_seq=0 ttl=64 time=0.095 ms
```

### WHY DOESN'T DEFAULT BRIDGE HAVE DNS?

Historical reasons. The default bridge (docker0) predates the embedded DNS
feature. Docker maintains backward compatibility, so the default bridge
uses the legacy --link mechanism instead.

RECOMMENDATION: Always use user-defined networks for:
- Automatic DNS resolution
- Better isolation
- On-the-fly container connect/disconnect

## SECTION 2.5: THE HOST AND NONE DRIVERS

### HOST NETWORK: NO ISOLATION

With host networking, the container doesn't get its own network namespace.
It shares the host's network stack directly.

```
docker run -d --network host nginx                                         

WHAT HAPPENS:                                                              
* Container uses host's eth0, lo, etc.                                     
* Container binds directly to host ports                                   
* No NAT, no port mapping needed                                           
* No network isolation!                                                    

+-------------------------------------------------------------------------+
|                              HOST                                       |
|                                                                         |
|      +-----------------------------------------------------------+      |
|      |                    Container "web"                        |      |
|      |                                                           |      |
|      |   nginx listens on port 80                               |       |
|      |   Uses host's network stack directly                     |       |
|      |                                                           |      |
|      +-----------------------------------------------------------+      |
|                              |                                          |
|                         No veth pair!                                   |
|                         No bridge!                                      |
|                         No NAT!                                         |
|                              |                                          |
|                         +----+----+                                     |
|                         |  eth0   |                                     |
|                         |  :80    |  < nginx directly on host:80        |
|                         +---------+                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

**WHEN TO USE HOST NETWORK:**
- Maximum network performance needed
- Application needs to see all host traffic
- Network monitoring/sniffing tools
- When port conflicts aren't a concern

### NONE NETWORK: COMPLETE ISOLATION

With none networking, the container has NO network connectivity.

```
docker run -d --network none my-secure-app                                 

WHAT HAPPENS:                                                              
* Container gets a namespace with only loopback (lo)                       
* No external connectivity whatsoever                                      
* Can't even reach other containers                                        

+-------------------------------------------------------------------------+
|                                                                         |
|      +-----------------------------------------------------------+      |
|      |                    Container                               |     |
|      |                                                           |      |
|      |   Only has loopback interface:                           |       |
|      |   lo: 127.0.0.1                                          |       |
|      |                                                           |      |
|      |   Cannot reach:                                          |       |
|      |   X Other containers                                    |        |
|      |   X The host                                            |        |
|      |   X The internet                                        |        |
|      |                                                           |      |
|      +-----------------------------------------------------------+      |
|                                                                         |
|      Complete network isolation                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

**WHEN TO USE NONE NETWORK:**
- Security-sensitive batch jobs
- Containers that only process local files
- Compliance requirements (air-gapped processing)

## SECTION 2.6: OVERLAY NETWORKS - MULTI-HOST NETWORKING

### THE MULTI-HOST PROBLEM

Bridge networks only work on a single host. But what if you have containers
on multiple hosts that need to communicate?

```
HOST 1                              HOST 2                   
+---------------------+            +------------------------+
|  Container A        |            |  Container B           |
|  172.17.0.2         |            |  172.17.0.2  < Same IP!|
|                     |            |                        |
|  docker0 bridge     |            |  docker0 bridge        |
|  172.17.0.1         |            |  172.17.0.1            |
+----------+----------+            +----------+-------------+
           |                                                |
           |      Physical Network                          |
           +-----------+------------------------------------+
                                                            |
               How can A reach B?                            
               They have overlapping IPs!                    
```

### THE SOLUTION: OVERLAY NETWORKS

Overlay networks create a virtual Layer 2 network that spans multiple hosts.
Containers on different hosts appear to be on the same network.

```
HOST 1                              HOST 2                    
+---------------------+            +-------------------------+
|  Container A        |            |  Container B            |
|  10.0.0.2           |            |  10.0.0.3               |
|         |           |            |         |               |
|  +------+------+    |            |    +----+------------+  |
|  | VXLAN Tunnel|    |            |    |VXLAN Tunnel     |  |
|  | Encapsulate |    |            |    | Decapsulate     |  |
|  +------+------+    |            |    +------+----------+  |
|         |           |            |           |             |
|     eth0 (192.168.1.10)          |       eth0 (192.168.1.11)
+---------+-----------+            +-----------+-------------+
          |                                                  |
          +---------- Physical Network ----------------------+
```

Container A sends packet to 10.0.0.3:
1. Packet: Src: 10.0.0.2, Dst: 10.0.0.3
2. VXLAN encapsulates: Outer: 192.168.1.10 > 192.168.1.11
3. Travels over physical network
4. HOST 2 decapsulates
5. Delivers to Container B

From containers' perspective: They're on the same network!

### VXLAN: VIRTUAL EXTENSIBLE LAN

VXLAN (Virtual Extensible LAN) is the technology Docker uses for overlay networks.

```
VXLAN PACKET STRUCTURE:                                                    
+-------------------------------------------------------------------------+
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                    OUTER PACKET (Physical)                      |    |
|  |  Outer Ethernet | Outer IP | Outer UDP | VXLAN | Inner Packet   |    |
|  |     Header      |  Header  |   Header  | Header|                |    |
|  |                 |          |           |       |                |    |
|  |  Src: Host1 MAC | Src: 192.168.1.10   | Port: | VNI:            |    |
|  |  Dst: Host2 MAC | Dst: 192.168.1.11   | 4789  | Network ID      |    |
|  +-----------------+----------+-----------+-------+----------------+    |
|                                                      |                  |
|                                    +-----------------+                  |
|                                    v                                    |
|  +-----------------------------------------------------------------+    |
|  |                    INNER PACKET (Virtual)                       |    |
|  |                                                                 |    |
|  |     Inner Ethernet    |    Inner IP     |      Payload          |    |
|  |         Header        |     Header      |                       |    |
|  |                       |                 |                       |    |
|  |  Src: Container A MAC | Src: 10.0.0.2  |  Application Data      |    |
|  |  Dst: Container B MAC | Dst: 10.0.0.3  |                        |    |
|  |                       |                 |                       |    |
|  +-----------------------+-----------------+-----------------------+    |
|                                                                         |
|  The inner packet is completely preserved-MAC addresses, IPs, etc.      |
|  This is what makes overlay a "Layer 2" overlay.                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CREATING AN OVERLAY NETWORK

Overlay networks require Docker Swarm (for key-value store coordination):

```bash
# Initialize Swarm on manager node                            
docker swarm init                                             

# Create overlay network                                      
docker network create --driver overlay --attachable my-overlay

# Run containers on overlay                                   
docker run -d --name web --network my-overlay nginx           
docker run -d --name api --network my-overlay my-api          

# On another Swarm node, containers can join the same network 
# and communicate directly with web and api!                  
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DOCKER NETWORKING ARCHITECTURE                                         |
|                                                                         |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  CONTAINER NETWORK MODEL (CNM)                                     | |
|  |  -----------------------------                                     | |
|  |  * Sandbox: Container's network namespace                          | |
|  |  * Endpoint: Connection to a network (veth pair end)               | |
|  |  * Network: Group of communicating endpoints                       | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  NETWORK DRIVERS                                                   | |
|  |  ----------------                                                  | |
|  |  * bridge: Linux bridge, NAT, single-host                          | |
|  |  * host: No isolation, share host network                          | |
|  |  * none: Complete isolation                                        | |
|  |  * overlay: VXLAN, multi-host networking                           | |
|  |  * macvlan: Direct MAC assignment                                  | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  DOCKER DNS                                                        | |
|  |  ----------                                                        | |
|  |  * Embedded DNS at 127.0.0.11                                      | |
|  |  * Automatic name resolution on user-defined networks              | |
|  |  * NOT available on default bridge                                 | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
|  KEY TAKEAWAYS:                                                         |
|  * Always use user-defined bridge networks (DNS, isolation)             |
|  * Default bridge is legacy-avoid for new projects                      |
|  * Overlay networks enable multi-host communication                     |
|  * Understanding CNM helps troubleshoot networking issues               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 2

