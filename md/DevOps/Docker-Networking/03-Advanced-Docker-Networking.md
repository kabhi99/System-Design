# CHAPTER 3: ADVANCED DOCKER NETWORKING
*Practical Scenarios, Troubleshooting, and Production Patterns*

This chapter covers advanced Docker networking topics including:
- Macvlan and IPvlan networks
- Docker Compose networking
- Network security and isolation
- Port publishing deep dive
- Troubleshooting common issues
- Production networking patterns

## SECTION 3.1: MACVLAN - CONTAINERS WITH REAL IPs

### THE PROBLEM WITH NAT

Bridge networks use NAT, which has limitations:

LIMITATIONS OF NAT-BASED NETWORKING:

1. Port Conflicts
Two containers can't both expose port 80 on the host

2. Performance Overhead
NAT translation adds latency and CPU overhead

3. Service Discovery Complexity
External systems see host IP, not container IP

4. Some Protocols Don't Work
Protocols that embed IP addresses (SIP, FTP active mode) break

### WHAT IS MACVLAN?

Macvlan allows you to assign a MAC address directly to a container, making
it appear as a physical device on your network.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BRIDGE NETWORKING:                                                     |
|  ------------------                                                     |
|                                                                         |
|      Container 1           Container 2                                  |
|      172.17.0.2            172.17.0.3                                   |
|           |                     |                                       |
|           +---------+-----------+                                       |
|                     |                                                   |
|                 docker0              < NAT Layer                        |
|                 172.17.0.1                                              |
|                     |                                                   |
|                   eth0               < Single MAC, Single IP            |
|              192.168.1.100                                              |
|                     |                                                   |
|              Physical Network                                           |
|                                                                         |
|  External world sees: 192.168.1.100 (host IP)                           |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  MACVLAN NETWORKING:                                                    |
|  -------------------                                                    |
|                                                                         |
|      Container 1           Container 2                                  |
|      192.168.1.101         192.168.1.102                                |
|      MAC: aa:bb:...        MAC: cc:dd:...                               |
|           |                     |                                       |
|           |                     |                                       |
|           |    eth0             |                                       |
|           |  192.168.1.100      |                                       |
|           |  MAC: original      |                                       |
|           |         |           |                                       |
|           +---------+-----------+                                       |
|                     |                                                   |
|              Physical Network                                           |
|                                                                         |
|  External world sees EACH container as separate device!                 |
|  192.168.1.101 (container 1)                                            |
|  192.168.1.102 (container 2)                                            |
|  192.168.1.100 (host)                                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HOW MACVLAN WORKS

Macvlan creates virtual network interfaces that:
- Have their own unique MAC addresses
- Appear as separate physical devices to the network
- Get IP addresses from your real network (via DHCP or static)
- Bypass Docker's NAT completely

MACVLAN MODES:

1. BRIDGE MODE (default)
Containers can talk to each other and external network
Most commonly used mode

2. VEPA MODE (Virtual Ethernet Port Aggregator)
All traffic goes to external switch first
Requires switch support for VEPA/802.1Qbg

3. PRIVATE MODE
Containers isolated from each other
Can only talk to external network

4. PASSTHRU MODE
Single container gets direct access to parent interface
Used for specialized applications

### CREATING A MACVLAN NETWORK

```bash
# First, identify your physical network details:                         
# - Parent interface: eth0                                               
# - Network subnet: 192.168.1.0/24                                       
# - Gateway: 192.168.1.1                                                 
# - Range for containers: 192.168.1.200-192.168.1.220                    

docker network create -d macvlan \                                       
    --subnet=192.168.1.0/24 \                                            
    --gateway=192.168.1.1 \                                              
    --ip-range=192.168.1.200/28 \                                        
    -o parent=eth0 \                                                     
    my-macvlan                                                           

# Run container with real network IP                                     
docker run -d --name web \                                               
    --network my-macvlan \                                               
    --ip 192.168.1.201 \                                                 
    nginx                                                                

# Now external devices can reach the container directly at 192.168.1.201!
```

### THE HOST-TO-CONTAINER PROBLEM

IMPORTANT: With Macvlan, the HOST cannot communicate with its containers!

This is a Linux kernel limitation. Traffic from host to its own Macvlan
interfaces is dropped.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HOST                         Container (Macvlan)                       |
|  192.168.1.100                192.168.1.201                             |
|        |                            |                                   |
|        | ------- BLOCKED ------- X |                                    |
|        |                            |                                   |
|  Cannot ping 192.168.1.201 from the host!                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

SOLUTION: Create a Macvlan interface on the host:

```bash
# Create a macvlan interface on the host           
ip link add mac0 link eth0 type macvlan mode bridge
ip addr add 192.168.1.199/32 dev mac0              
ip link set mac0 up                                

# Add route to container subnet via this interface 
ip route add 192.168.1.200/28 dev mac0             

# Now host can communicate with containers!        
```

### WHEN TO USE MACVLAN

**USE MACVLAN WHEN:**
- Legacy applications expect to be on the "real" network
- You need containers to have routable IPs
- Performance is critical (no NAT overhead)
- Network policies require per-container visibility
- Running network appliances in containers

**AVOID MACVLAN WHEN:**
- Your switch limits MAC addresses per port (common!)
- You don't control the network (cloud, managed infra)
- You need many containers (each needs unique MAC)
- Simple port forwarding is sufficient

## SECTION 3.2: IPVLAN - SINGLE MAC, MULTIPLE IPs

### THE MAC ADDRESS LIMITATION

Macvlan creates unique MAC addresses for each container. But:
- Some switches limit MAC addresses per port
- MAC learning tables have size limits
- Cloud providers often restrict MAC addresses

IPvlan solves this by sharing the parent interface's MAC address.

### HOW IPVLAN DIFFERS FROM MACVLAN

MACVLAN:
- Each container: Unique MAC, Unique IP
- Operates at Layer 2
- Multiple MACs visible on network

IPVLAN:
- All containers: SAME MAC (parent's), Unique IPs
- Can operate at Layer 2 (L2) or Layer 3 (L3)
- Single MAC visible on network

### IPVLAN MODES

```
L2 MODE (Layer 2):                                                         
+-------------------------------------------------------------------------+
|                                                                         |
|  Container 1           Container 2              HOST                    |
|  IP: 192.168.1.101     IP: 192.168.1.102       IP: 192.168.1.100        |
|                                                                         |
|        |                    |                       |                   |
|        +--------------------+-----------------------+                   |
|                             |                                           |
|                           eth0                                          |
|                    MAC: aa:bb:cc:dd:ee:ff                               |
|                                                                         |
|  ALL traffic uses same MAC address                                      |
|  Works like a switch (ARP, broadcasts work)                             |
|                                                                         |
+-------------------------------------------------------------------------+

L3 MODE (Layer 3):                                                         
+-------------------------------------------------------------------------+
|                                                                         |
|  Container 1           Container 2              HOST                    |
|  IP: 10.10.1.2         IP: 10.10.2.2           IP: 192.168.1.100        |
|  Subnet: 10.10.1.0/24  Subnet: 10.10.2.0/24                             |
|                                                                         |
|        |                    |                       |                   |
|        +--------------------+-----------------------+                   |
|                             |                                           |
|                    Host acts as ROUTER                                  |
|                    Routes between subnets                               |
|                    No ARP, no broadcasts                                |
|                                                                         |
|  Each container can be on different subnet                              |
|  Host routes traffic between them                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CREATING IPVLAN NETWORKS

```bash
# L2 Mode                                 
docker network create -d ipvlan \         
    --subnet=192.168.1.0/24 \             
    --gateway=192.168.1.1 \               
    -o parent=eth0 \                      
    -o ipvlan_mode=l2 \                   
    my-ipvlan-l2                          

# L3 Mode                                 
docker network create -d ipvlan \         
    --subnet=10.10.1.0/24 \               
    -o parent=eth0 \                      
    -o ipvlan_mode=l3 \                   
    my-ipvlan-l3                          

# Run containers                          
docker run -d --network my-ipvlan-l2 nginx
```

## SECTION 3.3: DOCKER COMPOSE NETWORKING

### AUTOMATIC NETWORK CREATION

Docker Compose automatically creates a network for your application:

```bash
# docker-compose.yml                                        
version: '3.8'                                              
services:                                                   
  web:                                                      
    image: nginx                                            
    ports:                                                  
      - "80:80"                                             
  api:                                                      
    image: my-api                                           
  db:                                                       
    image: postgres                                         

When you run: docker-compose up                             

Docker creates:                                             
* Network: myproject_default                                
* Container: myproject_web_1                                
* Container: myproject_api_1                                
* Container: myproject_db_1                                 

All containers join myproject_default network automatically.
```

### SERVICE DISCOVERY IN COMPOSE

Containers can reach each other by SERVICE NAME:

```
# Inside 'web' container:                                                  
curl http://api:8080/data    # Reaches 'api' service                       
psql -h db -U postgres        # Reaches 'db' service                       

The service names become DNS hostnames!                                    

+-------------------------------------------------------------------------+
|                                                                         |
|                    myproject_default network                            |
|                                                                         |
|  +---------------+  +---------------+  +---------------+                |
|  |     web       |  |     api       |  |      db       |                |
|  |               |  |               |  |               |                |
|  | DNS: "web"    |  | DNS: "api"    |  | DNS: "db"     |                |
|  | IP: 172.18.0.2|  | IP: 172.18.0.3|  | IP: 172.18.0.4|                |
|  +---------------+  +---------------+  +---------------+                |
|                                                                         |
|  web can resolve "api" > 172.18.0.3                                     |
|  api can resolve "db"  > 172.18.0.4                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CUSTOM NETWORKS IN COMPOSE

For more control, define custom networks:

```
version: '3.8'                                                             

services:                                                                  
  web:                                                                     
    image: nginx                                                           
    networks:                                                              
      - frontend                                                           

  api:                                                                     
    image: my-api                                                          
    networks:                                                              
      - frontend                                                           
      - backend                                                            

  db:                                                                      
    image: postgres                                                        
    networks:                                                              
      - backend                                                            

  cache:                                                                   
    image: redis                                                           
    networks:                                                              
      - backend                                                            

networks:                                                                  
  frontend:                                                                
    driver: bridge                                                         
    ipam:                                                                  
      config:                                                              
        - subnet: 172.20.0.0/24                                            
  backend:                                                                 
    driver: bridge                                                         
    ipam:                                                                  
      config:                                                              
        - subnet: 172.21.0.0/24                                            
    internal: true  # No external access!                                  

This creates:                                                              

+-------------------------------------------------------------------------+
|                                                                         |
|   FRONTEND NETWORK                     BACKEND NETWORK                  |
|   172.20.0.0/24                        172.21.0.0/24                    |
|   (has internet access)                (internal - no internet)         |
|                                                                         |
|   +---------------+                    +---------------+                |
|   |     web       |                    |      db       |                |
|   |  172.20.0.2   |                    |  172.21.0.2   |                |
|   +---------------+                    +---------------+                |
|          |                                    |                         |
|          |                                    |                         |
|   +------+----------------------+-------------+--+                      |
|   |                             |                |                      |
|   |         api                 |                |                      |
|   |    172.20.0.3 (frontend)    |    +---------------+                  |
|   |    172.21.0.3 (backend)     |    |    cache      |                  |
|   |                             |    |  172.21.0.4   |                  |
|   +-----------------------------+    +---------------+                  |
|                                                                         |
|   * web can reach api (both on frontend)                                |
|   * api can reach db and cache (all on backend)                         |
|   * web CANNOT reach db or cache (different networks)                   |
|   * db and cache CANNOT reach internet (internal network)               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### NETWORK ALIASES

Give services multiple DNS names:

```yaml
services:                                         
  database:                                       
    image: postgres                               
    networks:                                     
      backend:                                    
        aliases:                                  
          - db                                    
          - postgres                              
          - primary-db                            

# Other containers can now use any of these names:
# database, db, postgres, primary-db              
```

## SECTION 3.4: PORT PUBLISHING DEEP DIVE

### UNDERSTANDING -p AND --publish

When you publish ports, Docker creates iptables rules to forward traffic:

```bash
docker run -p 8080:80 nginx                            

WHAT HAPPENS:                                          
1. Docker creates DNAT rule in PREROUTING chain        
2. Docker creates ACCEPT rule in FORWARD chain         
3. Docker creates rule in docker-proxy (userland proxy)
```

### THE PORT PUBLISHING OPTIONS

```bash
FORMAT: -p [host_ip:]host_port:container_port[/protocol]

EXAMPLES:                                               

# All interfaces, TCP only (default)                    
-p 8080:80                                              
# Equivalent to: -p 0.0.0.0:8080:80/tcp                 
# Binds to all host IPs on port 8080                    

# Specific interface only                               
-p 127.0.0.1:8080:80                                    
# Only accessible from localhost                        
# External machines CANNOT reach this                   

# Specific interface, all IPs in that range             
-p 192.168.1.100:8080:80                                
# Only accessible via 192.168.1.100                     

# UDP protocol                                          
-p 53:53/udp                                            
# For DNS servers, TFTP, etc.                           

# Both TCP and UDP                                      
-p 53:53/tcp -p 53:53/udp                               

# Random host port                                      
-p 80                                                   
# Docker assigns random high port (e.g., 32768)         
# Use `docker port container_name` to find it           

# Port range                                            
-p 8000-8010:8000-8010                                  
# Maps 11 ports                                         
```

### HOW PORT FORWARDING WORKS INTERNALLY

```
EXTERNAL REQUEST TO HOST:8080                                              

+-------------------------------------------------------------------------+
|                                                                         |
|  1. Packet arrives at host                                              |
|     Dst: 192.168.1.100:8080                                             |
|                                                                         |
|  2. iptables PREROUTING (nat table)                                     |
|     Rule: DNAT to 172.17.0.2:80                                         |
|     Packet modified: Dst: 172.17.0.2:80                                 |
|                                                                         |
|  3. Routing decision                                                    |
|     Destination 172.17.0.2 > forward through docker0                    |
|                                                                         |
|  4. iptables FORWARD (filter table)                                     |
|     Rule: ACCEPT for docker traffic                                     |
|                                                                         |
|  5. Packet delivered to container                                       |
|     Container sees: Dst: 172.17.0.2:80                                  |
|                                                                         |
|  6. Container responds                                                  |
|     Src: 172.17.0.2:80 > 192.168.1.100:8080                             |
|     MASQUERADE translates back                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### THE DOCKER-PROXY (USERLAND PROXY)

Docker also runs a userland proxy process for each published port:

```bash
ps aux | grep docker-proxy                                           
# /usr/bin/docker-proxy -proto tcp -host-ip 0.0.0.0 -host-port 8080 \
#                       -container-ip 172.17.0.2 -container-port 80  
```

WHY TWO MECHANISMS?

iptables (kernel):
- Fast, handles most traffic
- Works for external > container traffic

docker-proxy (userland):
- Handles localhost > container traffic
- Handles hairpin NAT (container > host:port > container)
- Slower but necessary for edge cases

DISABLE USERLAND PROXY (if not needed):

```bash
# In /etc/docker/daemon.json:                                 
{                                                             
    "userland-proxy": false                                   
}                                                             

Only disable if you don't need localhost access to containers.
```

## SECTION 3.5: NETWORK SECURITY AND ISOLATION

### INTER-CONTAINER COMMUNICATION (ICC)

By default, containers on the same bridge can communicate freely.

```bash
# Check if ICC is enabled                                              
docker network inspect bridge | grep EnableICC                         

# Disable ICC on default bridge                                        
# In /etc/docker/daemon.json:                                          
{                                                                      
    "icc": false                                                       
}                                                                      

With ICC disabled, containers can only communicate if explicitly linked
or if there are specific iptables rules.                               
```

### NETWORK ISOLATION STRATEGIES

```bash
STRATEGY 1: SEPARATE NETWORKS                                           

Create different networks for different security zones:                 

docker network create dmz                                               
docker network create internal                                          
docker network create database                                          

# Frontend in DMZ                                                       
docker run -d --network dmz --name web nginx                            

# API in internal                                                       
docker run -d --network internal --name api my-api                      

# Database in database network                                          
docker run -d --network database --name db postgres                     

# Connect API to both internal and database                             
docker network connect database api                                     

------------------------------------------------------------------------

STRATEGY 2: INTERNAL NETWORKS                                           

Networks with no external access:                                       

docker network create --internal secure-backend                         

Containers on this network:                                             
* CAN communicate with each other                                       
* CANNOT reach the internet                                             
* CANNOT be reached from outside Docker                                 
### ```                                                                 

```bash
STRATEGY 3: IPTABLES RULES

Add custom firewall rules:

# Block container-to-container on specific ports
iptables -I DOCKER-USER -p tcp --dport 5432 -j DROP

# Allow only specific source
iptables -I DOCKER-USER -p tcp -s 172.17.0.2 --dport 5432 -j ACCEPT
```

### THE DOCKER-USER CHAIN                                                  

Docker manages its own iptables rules. If you add rules to standard chains,
Docker might overwrite them on restart.                                    

USE DOCKER-USER CHAIN for custom rules:                                    

```bash
# This chain is processed BEFORE Docker's rules
# Your rules here won't be overwritten

# Example: Block all external access to container port 3306
iptables -I DOCKER-USER -i eth0 -p tcp --dport 3306 -j DROP
```

## SECTION 3.6: TROUBLESHOOTING DOCKER NETWORKING

### COMMON ISSUES AND SOLUTIONS                  

ISSUE 1: "CONTAINER CAN'T REACH INTERNET"        

```bash
DIAGNOSIS STEPS:

# 1. Check if container has IP
docker exec container ip addr

# 2. Check default gateway
docker exec container ip route
# Should show: default via 172.17.0.1 dev eth0

# 3. Can container reach gateway?
docker exec container ping 172.17.0.1

# 4. Check host's IP forwarding
cat /proc/sys/net/ipv4/ip_forward
# Should be: 1

# 5. Check iptables NAT rules
iptables -t nat -L POSTROUTING -v
# Should show MASQUERADE rule for Docker subnet

SOLUTIONS:
- Enable IP forwarding: sysctl -w net.ipv4.ip_forward=1
- Restart Docker: systemctl restart docker
- Check if firewall is blocking: iptables -L FORWARD
### ```

ISSUE 2: "CONTAINERS CAN'T REACH EACH OTHER BY NAME"

```bash
CAUSE: Probably using default bridge network                     

# Check network                                                  
docker inspect container --format '{{.NetworkSettings.Networks}}'

# If using default 'bridge' network, DNS won't work!             

SOLUTION: Use user-defined network                               

docker network create my-net                                     
docker network connect my-net container1                         
docker network connect my-net container2                         
### ```                                                          

ISSUE 3: "PORT PUBLISHING NOT WORKING"                           

```bash
DIAGNOSIS:

# 1. Is port actually published?
docker port container_name

# 2. Check if something else is using the port
netstat -tulpn | grep 8080
lsof -i :8080

# 3. Check iptables rules
iptables -t nat -L DOCKER -v

# 4. Check docker-proxy
ps aux | grep docker-proxy

# 5. Check if container is listening
docker exec container netstat -tulpn
### ```

ISSUE 4: "SLOW NETWORK PERFORMANCE"

```bash
POSSIBLE CAUSES:                                        

1. MTU mismatch                                         
   docker network inspect bridge | grep MTU             
   # Default is 1500, might need adjustment for overlays

2. Network driver overhead                              
   # Try host networking for maximum performance        
   docker run --network host ...                        

3. Too many iptables rules                              
   iptables -L | wc -l                                  

4. DNS resolution issues                                
   # Add explicit DNS servers                           
   docker run --dns 8.8.8.8 ...                         
```

### USEFUL TROUBLESHOOTING COMMANDS

```bash
# List all networks                                               
docker network ls                                                 

# Inspect network details                                         
docker network inspect network_name                               

# See container's network settings                                
docker inspect container --format '{{json .NetworkSettings}}' | jq

# Enter container network namespace (advanced)                    
PID=$(docker inspect -f '{{.State.Pid}}' container_name)          
nsenter -t $PID -n ip addr                                        

# See all iptables rules Docker created                           
iptables -L -n -v                                                 
iptables -t nat -L -n -v                                          

# Watch network traffic                                           
docker exec container tcpdump -i eth0                             

# Test DNS resolution                                             
docker exec container nslookup service_name                       

# Check Docker logs for network errors                            
journalctl -u docker | grep -i network                            
```

## SECTION 3.7: PRODUCTION NETWORKING PATTERNS

### PATTERN 1: THREE-TIER ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|                       THREE-TIER NETWORK DESIGN                         |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                         DMZ Network                              |   |
|  |                     (internet-facing)                            |   |
|  |                                                                  |   |
|  |     +---------+      +---------+      +---------+                |   |
|  |     |  nginx  |      |  nginx  |      |  nginx  |                |   |
|  |     |   LB    |      |   LB    |      |   LB    |                |   |
|  |     +----+----+      +----+----+      +----+----+                |   |
|  |          |                |                |                     |   |
|  +----------+----------------+----------------+---------------------+   |
|             |                |                |                         |
|  +----------+----------------+----------------+---------------------+   |
|  |          |      APP Network (internal)     |                     |   |
|  |          |                |                |                     |   |
|  |     +----v----+      +----v----+      +----v----+                |   |
|  |     |   API   |      |   API   |      |   API   |                |   |
|  |     | Server  |      | Server  |      | Server  |                |   |
|  |     +----+----+      +----+----+      +----+----+                |   |
|  |          |                |                |                     |   |
|  +----------+----------------+----------------+---------------------+   |
|             |                |                |                         |
|  +----------+----------------+----------------+---------------------+   |
|  |          |    DATA Network (internal)      |                     |   |
|  |          |                |                |                     |   |
|  |     +----v----+      +----v----+      +----v----+                |   |
|  |     | Postgres|      |  Redis  |      | Elastic |                |   |
|  |     | Primary |      | Cluster |      | Search  |                |   |
|  |     +---------+      +---------+      +---------+                |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  SECURITY RULES:                                                        |
|  * DMZ > APP: Allowed (specific ports)                                  |
|  * APP > DATA: Allowed (specific ports)                                 |
|  * DMZ > DATA: BLOCKED                                                  |
|  * DATA > Internet: BLOCKED                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### PATTERN 2: MICROSERVICES WITH SERVICE MESH

In a microservices architecture, use overlay networks with service mesh:

```yaml
version: '3.8'                                     

services:                                          
  api-gateway:                                     
    image: kong                                    
    networks:                                      
      - frontend                                   
      - mesh                                       
    deploy:                                        
      replicas: 3                                  

  user-service:                                    
    image: my-user-service                         
    networks:                                      
      - mesh                                       
      - data                                       
    deploy:                                        
      replicas: 5                                  

  order-service:                                   
    image: my-order-service                        
    networks:                                      
      - mesh                                       
      - data                                       
    deploy:                                        
      replicas: 5                                  

  payment-service:                                 
    image: my-payment-service                      
    networks:                                      
      - mesh                                       
      - external  # Needs to reach payment gateways
    deploy:                                        
      replicas: 3                                  

networks:                                          
  frontend:                                        
    driver: overlay                                
  mesh:                                            
    driver: overlay                                
    internal: true  # No external access           
  data:                                            
    driver: overlay                                
    internal: true                                 
  external:                                        
    driver: overlay                                
```

### PATTERN 3: HIGH-PERFORMANCE NETWORKING

For latency-sensitive applications:

```bash
# Option 1: Host networking                      
docker run --network host low-latency-app        

# Option 2: Macvlan for native performance       
docker network create -d macvlan \               
    --subnet=192.168.1.0/24 \                    
    --gateway=192.168.1.1 \                      
    -o parent=eth0 \                             
    high-perf-net                                

docker run -d --network high-perf-net trading-app

# Option 3: Tune network settings                
docker run \                                     
    --sysctl net.core.somaxconn=65535 \          
    --sysctl net.ipv4.tcp_max_syn_backlog=65535 \
    high-traffic-app                             
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ADVANCED DOCKER NETWORKING TOPICS                                      |
|                                                                         |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  MACVLAN & IPVLAN                                                  | |
|  |  * Give containers real network IPs                                | |
|  |  * Macvlan: Unique MAC per container                               | |
|  |  * IPvlan: Shared MAC, unique IPs                                  | |
|  |  * Use for legacy apps needing "real" network presence             | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  DOCKER COMPOSE NETWORKING                                         | |
|  |  * Auto-creates network per project                                | |
|  |  * Service names become DNS hostnames                              | |
|  |  * Use multiple networks for isolation                             | |
|  |  * Internal networks block internet access                         | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  NETWORK SECURITY                                                  | |
|  |  * Use separate networks for security zones                        | |
|  |  * DOCKER-USER chain for custom firewall rules                     | |
|  |  * Internal networks for sensitive services                        | |
|  |  * ICC can be disabled for paranoid isolation                      | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|  |                                                                    | |
|  |  TROUBLESHOOTING                                                   | |
|  |  * Check IP forwarding, iptables, DNS                              | |
|  |  * Use nsenter for deep namespace inspection                       | |
|  |  * tcpdump inside containers for traffic analysis                  | |
|  |  * Most issues: wrong network or missing DNS                       | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 3

