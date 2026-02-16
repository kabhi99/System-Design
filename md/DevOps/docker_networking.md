# DOCKER NETWORKING — FROM ZERO TO HERO
*Complete Guide: Basics to Advanced*

### Table of Contents

Part 1: Linux Networking Fundamentals (Prerequisites)
1.1 Network Namespaces
1.2 Virtual Ethernet (veth) Pairs
1.3 Linux Bridge
1.4 iptables and NAT
1.5 Network Address Translation (NAT)

Part 2: Docker Networking Basics
2.1 How Docker Networking Works
2.2 Docker Network Drivers Overview
2.3 Default Bridge Network
2.4 Container-to-Container Communication

Part 3: Docker Network Drivers Deep Dive
3.1 Bridge Network (Default)
3.2 Host Network
3.3 None Network
3.4 Overlay Network
3.5 Macvlan Network
3.6 IPvlan Network

Part 4: Docker DNS and Service Discovery
4.1 Embedded DNS Server
4.2 Container Name Resolution
4.3 Custom DNS Configuration

Part 5: Docker Compose Networking
5.1 Default Network in Compose
5.2 Custom Networks in Compose
5.3 Network Aliases

Part 6: Advanced Topics
6.1 Container Network Model (CNM)
6.2 Network Plugins (libnetwork)
6.3 Multi-Host Networking
6.4 Network Security and Isolation
6.5 Network Troubleshooting

Part 7: Hands-On Labs
7.1 Lab Exercises
7.2 Common Commands Reference

## PART 1: LINUX NETWORKING FUNDAMENTALS (PREREQUISITES)

Before understanding Docker networking, you MUST understand these Linux concepts.
Docker networking is built entirely on top of Linux kernel features.

### 1.1 NETWORK NAMESPACES

```
+-------------------------------------------------------------------------+
|                    WHAT IS A NETWORK NAMESPACE?                         |
|                                                                         |
|  A network namespace is an ISOLATED network stack.                     |
|                                                                         |
|  Each namespace has its own:                                           |
|  * Network interfaces (eth0, lo, etc.)                                |
|  * Routing tables                                                      |
|  * iptables rules                                                      |
|  * Sockets                                                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WITHOUT NAMESPACES (Single Network Stack):                            |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                      HOST                                       |   |
|  |   Process A    Process B    Process C                          |   |
|  |       |            |            |                               |   |
|  |       +------------+------------+                               |   |
|  |                    |                                             |   |
|  |              +-----+-----+                                       |   |
|  |              |   eth0    |  <- All processes share same network  |   |
|  |              +-----------+                                       |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  WITH NAMESPACES (Isolated Network Stacks):                            |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                      HOST                                       |   |
|  |                                                                 |   |
|  |  +-------------+  +-------------+  +-------------+             |   |
|  |  | Namespace A |  | Namespace B |  | Namespace C |             |   |
|  |  |  Process A  |  |  Process B  |  |  Process C  |             |   |
|  |  |    eth0     |  |    eth0     |  |    eth0     |             |   |
|  |  |  10.0.0.1   |  |  10.0.0.2   |  |  10.0.0.3   |             |   |
|  |  +-------------+  +-------------+  +-------------+             |   |
|  |         |               |               |                       |   |
|  |         +---------------+---------------+                       |   |
|  |                         |                                       |   |
|  |  +----------------------+-----------------------+              |   |
|  |  |              Linux Bridge (docker0)          |              |   |
|  |  +----------------------+-----------------------+              |   |
|  |                         |                                       |   |
|  |                    +----+----+                                  |   |
|  |                    |  eth0   |  <- Host's physical interface    |   |
|  |                    +---------+                                  |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  THIS IS EXACTLY HOW DOCKER CONTAINERS WORK!                           |
|  Each container = One network namespace                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

HANDS-ON: Creating Network Namespaces

```bash
# Create a network namespace
sudo ip netns add red
sudo ip netns add blue

# List namespaces
ip netns list

# Execute command inside namespace
sudo ip netns exec red ip link
# Output: Only loopback (lo) interface exists

# Each namespace is completely isolated!
sudo ip netns exec red ping 8.8.8.8
# FAILS - no connectivity to outside world yet
```

### 1.2 VIRTUAL ETHERNET (veth) PAIRS

```
+-------------------------------------------------------------------------+
|                    WHAT IS A VETH PAIR?                                 |
|                                                                         |
|  A veth pair is like a virtual network cable with two ends.            |
|  Whatever enters one end comes out the other.                          |
|                                                                         |
|  +-----------------+                    +-----------------+            |
|  |   Namespace A   |                    |   Namespace B   |            |
|  |                 |                    |                 |            |
|  |   +---------+   |                    |   +---------+   |            |
|  |   | veth-a  |---+--------------------+---| veth-b  |   |            |
|  |   +---------+   |   Virtual Cable    |   +---------+   |            |
|  |                 |                    |                 |            |
|  +-----------------+                    +-----------------+            |
|                                                                         |
|  Packets sent to veth-a appear at veth-b (and vice versa)              |
|                                                                         |
+-------------------------------------------------------------------------+
```

HANDS-ON: Creating veth Pairs

```bash
# Create a veth pair
sudo ip link add veth-red type veth peer name veth-blue

# Move each end to different namespace
sudo ip link set veth-red netns red
sudo ip link set veth-blue netns blue

# Assign IP addresses
sudo ip netns exec red ip addr add 192.168.1.1/24 dev veth-red
sudo ip netns exec blue ip addr add 192.168.1.2/24 dev veth-blue

# Bring interfaces up
sudo ip netns exec red ip link set veth-red up
sudo ip netns exec blue ip link set veth-blue up

# Now they can communicate!
sudo ip netns exec red ping 192.168.1.2
# SUCCESS! Packets flow through the veth pair
```

### 1.3 LINUX BRIDGE

```
+-------------------------------------------------------------------------+
|                    WHAT IS A LINUX BRIDGE?                              |
|                                                                         |
|  A bridge is a virtual Layer 2 switch.                                 |
|  It connects multiple network interfaces and forwards frames           |
|  between them based on MAC addresses.                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROBLEM: How do we connect 5 containers?                              |
|  5 containers = 5 namespaces = need 5×4/2 = 10 veth pairs?            |
|  That doesn't scale!                                                   |
|                                                                         |
|  SOLUTION: Use a bridge (virtual switch)                               |
|                                                                         |
|  +----------+ +----------+ +----------+ +----------+ +----------+     |
|  |Container1| |Container2| |Container3| |Container4| |Container5|     |
|  |  veth1   | |  veth2   | |  veth3   | |  veth4   | |  veth5   |     |
|  +----+-----+ +----+-----+ +----+-----+ +----+-----+ +----+-----+     |
|       |            |            |            |            |            |
|       +------------+-----+------+------------+------------+            |
|                          |                                             |
|                +---------+---------+                                   |
|                |   LINUX BRIDGE    | <- Acts like a switch              |
|                |     (docker0)     |                                   |
|                +---------+---------+                                   |
|                          |                                             |
|                     +----+----+                                        |
|                     |  eth0   | <- To outside world                     |
|                     +---------+                                        |
|                                                                         |
|  This is EXACTLY how Docker's default bridge network works!            |
|  docker0 is a Linux bridge created by Docker.                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

HANDS-ON: Creating a Bridge

```bash
# Create a bridge
sudo ip link add br0 type bridge
sudo ip link set br0 up

# Assign IP to bridge (gateway for connected devices)
sudo ip addr add 192.168.1.254/24 dev br0

# Connect namespaces to bridge
# First, create veth pair for each namespace
sudo ip link add veth-red type veth peer name veth-red-br
sudo ip link add veth-blue type veth peer name veth-blue-br

# Move one end to namespace
sudo ip link set veth-red netns red
sudo ip link set veth-blue netns blue

# Connect other end to bridge
sudo ip link set veth-red-br master br0
sudo ip link set veth-blue-br master br0

# Configure IPs inside namespaces
sudo ip netns exec red ip addr add 192.168.1.1/24 dev veth-red
sudo ip netns exec blue ip addr add 192.168.1.2/24 dev veth-blue

# Bring everything up
sudo ip link set veth-red-br up
sudo ip link set veth-blue-br up
sudo ip netns exec red ip link set veth-red up
sudo ip netns exec blue ip link set veth-blue up

# Red and Blue can now communicate through the bridge!
sudo ip netns exec red ping 192.168.1.2
```

### 1.4 IPTABLES AND NAT

```
+-------------------------------------------------------------------------+
|                    IPTABLES BASICS                                      |
|                                                                         |
|  iptables is the Linux firewall/packet filtering system.               |
|  It decides what happens to network packets.                           |
|                                                                         |
|  TABLES:                                                                |
|  * filter: Accept/drop packets (default firewall)                      |
|  * nat: Network address translation                                    |
|  * mangle: Modify packet headers                                       |
|  * raw: Bypass connection tracking                                     |
|                                                                         |
|  CHAINS (in nat table):                                                 |
|  * PREROUTING: Before routing decision                                 |
|  * POSTROUTING: After routing, before leaving                         |
|  * OUTPUT: Locally generated packets                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PACKET FLOW:                                                           |
|                                                                         |
|  Incoming     +----------+    +----------+    +----------+            |
|  Packet ------|PREROUTING|--->| ROUTING  |--->| FORWARD  |---> Out    |
|               +----------+    +----+-----+    +----------+            |
|                                    |                                   |
|                                    | (local?)                          |
|                                    v                                   |
|                               +---------+                              |
|                               |  INPUT  |                              |
|                               +----+----+                              |
|                                    |                                   |
|                                    v                                   |
|                             Local Process                              |
|                                    |                                   |
|                                    v                                   |
|                               +---------+                              |
|                               | OUTPUT  |                              |
|                               +----+----+                              |
|                                    |                                   |
|                                    v                                   |
|                             +------------+                             |
|                             |POSTROUTING |---> Out                     |
|                             +------------+                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 1.5 NETWORK ADDRESS TRANSLATION (NAT)

```
+-------------------------------------------------------------------------+
|                    SNAT (Source NAT) - MASQUERADE                       |
|                                                                         |
|  Container wants to reach the internet.                                |
|  Problem: Container has private IP (172.17.0.2)                        |
|  Solution: Replace source IP with host's public IP                     |
|                                                                         |
|  +--------------+         +--------------+         +--------------+   |
|  |  Container   |         |     HOST     |         |   Internet   |   |
|  |  172.17.0.2  |-------->|  10.0.0.5    |-------->|   8.8.8.8   |   |
|  +--------------+         |              |         +--------------+   |
|                           |   MASQUERADE |                             |
|  Src: 172.17.0.2          |   Changes    |         Src: 10.0.0.5      |
|  Dst: 8.8.8.8             |   source IP  |         Dst: 8.8.8.8       |
|                           +--------------+                             |
|                                                                         |
|  Command:                                                               |
|  iptables -t nat -A POSTROUTING -s 172.17.0.0/16 -j MASQUERADE        |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    DNAT (Destination NAT) - Port Forwarding             |
|                                                                         |
|  External client wants to reach container's web server.                |
|  Problem: Client can't reach 172.17.0.2 directly                       |
|  Solution: Forward host:8080 -> container:80                            |
|                                                                         |
|  +--------------+         +--------------+         +--------------+   |
|  |   Client     |         |     HOST     |         |  Container   |   |
|  |  (Internet)  |-------->|   :8080      |-------->|    :80       |   |
|  +--------------+         |              |         |  172.17.0.2  |   |
|                           |     DNAT     |         +--------------+   |
|  Dst: host:8080           |   Changes    |         Dst: 172.17.0.2:80 |
|                           |   dest IP    |                             |
|                           +--------------+                             |
|                                                                         |
|  Command:                                                               |
|  iptables -t nat -A PREROUTING -p tcp --dport 8080 \                  |
|           -j DNAT --to-destination 172.17.0.2:80                       |
|                                                                         |
|  THIS IS WHAT docker run -p 8080:80 DOES!                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## PART 2: DOCKER NETWORKING BASICS

### 2.1 HOW DOCKER NETWORKING WORKS

```
+-------------------------------------------------------------------------+
|                    DOCKER NETWORKING = LINUX NETWORKING                 |
|                                                                         |
|  When you run a container, Docker:                                     |
|                                                                         |
|  1. Creates a network namespace for the container                      |
|  2. Creates a veth pair                                                |
|  3. Puts one end in container, other end on bridge (docker0)           |
|  4. Assigns IP address from bridge's subnet                            |
|  5. Sets up NAT rules for external access                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DOCKER'S DEFAULT BRIDGE NETWORK:                                      |
|                                                                         |
|  +----------------------------------------------------------------+    |
|  |                         HOST                                    |    |
|  |                                                                 |    |
|  |  +---------------+  +---------------+  +---------------+       |    |
|  |  |  Container A  |  |  Container B  |  |  Container C  |       |    |
|  |  |  172.17.0.2   |  |  172.17.0.3   |  |  172.17.0.4   |       |    |
|  |  |      |        |  |      |        |  |      |        |       |    |
|  |  |   eth0        |  |   eth0        |  |   eth0        |       |    |
|  |  +------+--------+  +------+--------+  +------+--------+       |    |
|  |         | veth            | veth            | veth            |    |
|  |         |                 |                 |                  |    |
|  |  +------+-----------------+-----------------+------+          |    |
|  |  |              docker0 bridge                     |          |    |
|  |  |              172.17.0.1                         |          |    |
|  |  +------------------------+------------------------+          |    |
|  |                           |                                    |    |
|  |                      +----+----+                               |    |
|  |                      |  eth0   |  Host's physical interface   |    |
|  |                      | 10.0.0.5|                               |    |
|  |                      +---------+                               |    |
|  |                           |                                    |    |
|  |                     +-----+-----+                              |    |
|  |                     |    NAT    |  iptables MASQUERADE        |    |
|  |                     +-----+-----+                              |    |
|  |                           |                                    |    |
|  +---------------------------+------------------------------------+    |
|                              |                                          |
|                         Internet                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

**VERIFY IT YOURSELF:**

```bash
# Start a container
docker run -d --name web nginx

# See the veth pair
docker exec web ip link
# Shows: eth0@if7 (container end)

# On host
ip link | grep veth
# Shows: veth1234567@if6 (host end, connected to docker0)

# See the bridge
brctl show docker0
# Shows: docker0 with veth interfaces attached

# See NAT rules
iptables -t nat -L -n
# Shows: MASQUERADE rule for 172.17.0.0/16
```

### 2.2 DOCKER NETWORK DRIVERS OVERVIEW

```
+-------------------------------------------------------------------------+
|                    DOCKER NETWORK DRIVERS                               |
|                                                                         |
|  +-------------+----------------------------------------------------+  |
|  | Driver      | Description                                        |  |
|  +-------------+----------------------------------------------------+  |
|  | bridge      | Default. Containers on same host communicate.     |  |
|  |             | Uses Linux bridge + NAT.                          |  |
|  +-------------+----------------------------------------------------+  |
|  | host        | No network isolation. Container uses host's       |  |
|  |             | network stack directly.                           |  |
|  +-------------+----------------------------------------------------+  |
|  | none        | No networking. Container is completely isolated.  |  |
|  +-------------+----------------------------------------------------+  |
|  | overlay     | Multi-host networking. Containers on different    |  |
|  |             | hosts can communicate (Docker Swarm).             |  |
|  +-------------+----------------------------------------------------+  |
|  | macvlan     | Assigns MAC address to container. Container       |  |
|  |             | appears as physical device on network.            |  |
|  +-------------+----------------------------------------------------+  |
|  | ipvlan      | Like macvlan but shares MAC address with host.    |  |
|  |             | Better for environments limiting MACs.            |  |
|  +-------------+----------------------------------------------------+  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WHEN TO USE EACH:                                                      |
|                                                                         |
|  bridge:  Default for single-host. Most common.                        |
|  host:    Maximum network performance needed.                          |
|  none:    Security (no network access needed).                         |
|  overlay: Multi-host communication (Swarm, Kubernetes).                |
|  macvlan: Legacy apps expecting to be on physical network.             |
|                                                                         |
+-------------------------------------------------------------------------+
```

**COMMANDS:**

```bash
# List networks
docker network ls

# Inspect a network
docker network inspect bridge

# Create custom network
docker network create --driver bridge my-network

# Run container on specific network
docker run -d --network my-network --name web nginx

# Connect running container to network
docker network connect my-network existing-container

# Disconnect from network
docker network disconnect my-network existing-container
```

### 2.3 DEFAULT BRIDGE NETWORK

```
+-------------------------------------------------------------------------+
|                    DEFAULT BRIDGE (docker0)                             |
|                                                                         |
|  * Created automatically when Docker starts                            |
|  * Name: "bridge" (confusing, I know)                                  |
|  * Subnet: 172.17.0.0/16 (configurable)                               |
|  * Gateway: 172.17.0.1                                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  LIMITATIONS OF DEFAULT BRIDGE:                                        |
|                                                                         |
|  1. NO AUTOMATIC DNS                                                   |
|     Containers can only reach each other by IP, not by name.          |
|                                                                         |
|     # On default bridge:                                               |
|     docker exec containerA ping containerB   # FAILS!                  |
|     docker exec containerA ping 172.17.0.3   # Works                   |
|                                                                         |
|  2. ALL CONTAINERS CONNECTED BY DEFAULT                                |
|     Less isolation between unrelated containers.                       |
|                                                                         |
|  3. NEED --link FOR NAME RESOLUTION (Deprecated)                       |
|     docker run --link containerB:alias containerA                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  RECOMMENDATION: Always create user-defined bridge networks!           |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                    USER-DEFINED BRIDGE NETWORKS                         |
|                                                                         |
|  ADVANTAGES:                                                            |
|                                                                         |
|  1. AUTOMATIC DNS                                                      |
|     Containers can reach each other by name!                          |
|                                                                         |
|     # Create network                                                   |
|     docker network create my-app                                       |
|                                                                         |
|     # Run containers                                                   |
|     docker run -d --name db --network my-app postgres                 |
|     docker run -d --name web --network my-app nginx                   |
|                                                                         |
|     # Now web can reach db by name                                    |
|     docker exec web ping db   # Works!                                |
|                                                                         |
|  2. BETTER ISOLATION                                                   |
|     Only containers on same network can communicate.                  |
|                                                                         |
|  3. ON-THE-FLY CONNECT/DISCONNECT                                     |
|     docker network connect my-app container3                          |
|     docker network disconnect my-app container3                       |
|                                                                         |
|  4. CONFIGURABLE                                                       |
|     Custom subnet, gateway, IP range.                                 |
|                                                                         |
|     docker network create \                                            |
|       --subnet 10.0.0.0/24 \                                          |
|       --gateway 10.0.0.1 \                                            |
|       my-custom-net                                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2.4 CONTAINER-TO-CONTAINER COMMUNICATION

SCENARIO 1: Same Network (User-Defined Bridge)

```bash
# Create network
docker network create app-net

# Run database
docker run -d --name postgres --network app-net \
  -e POSTGRES_PASSWORD=secret postgres

# Run app (can connect to postgres by name)
docker run -d --name app --network app-net \
  -e DATABASE_URL=postgres://postgres:secret@postgres:5432/db \
  my-app

# Communication flow:
#   app -> DNS lookup "postgres" -> 172.18.0.2 -> postgres container
```

SCENARIO 2: Different Networks (Isolated)

```bash
# Create two networks
docker network create frontend
docker network create backend

# Run containers
docker run -d --name web --network frontend nginx
docker run -d --name db --network backend postgres

# web CANNOT reach db (different networks)
docker exec web ping db   # FAILS!

# To allow communication, connect to both networks:
docker network connect backend web
# Now web can reach db
```

SCENARIO 3: Expose Ports to Host

```bash
# Container runs web server on port 80
# Expose as port 8080 on host
docker run -d -p 8080:80 --name web nginx

# Access from host or external
curl http://localhost:8080

# What Docker does behind the scenes:
# iptables -t nat -A PREROUTING -p tcp --dport 8080 \
#          -j DNAT --to-destination 172.17.0.2:80
```

## PART 3: DOCKER NETWORK DRIVERS DEEP DIVE

### 3.1 BRIDGE NETWORK (Default)

```
+-------------------------------------------------------------------------+
|                    BRIDGE NETWORK ARCHITECTURE                          |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                         HOST                                     |   |
|  |                                                                  |   |
|  |   +--------------------------------------------------------+    |   |
|  |   |                User-Defined Bridge                      |    |   |
|  |   |                   (my-app-net)                          |    |   |
|  |   |                                                         |    |   |
|  |   |  +---------+  +---------+  +---------+                 |    |   |
|  |   |  | web     |  | api     |  | db      |                 |    |   |
|  |   |  | nginx   |  | node    |  | postgres|                 |    |   |
|  |   |  |.2       |  |.3       |  |.4       |                 |    |   |
|  |   |  +----+----+  +----+----+  +----+----+                 |    |   |
|  |   |       |           |            |                        |    |   |
|  |   |       +-----------+------------+                        |    |   |
|  |   |                   |                                     |    |   |
|  |   |   ----------------+-----------------------              |    |   |
|  |   |   Bridge: 172.18.0.1 (gateway)                         |    |   |
|  |   |   Subnet: 172.18.0.0/16                                |    |   |
|  |   +-------------------+-------------------------------------+    |   |
|  |                       |                                          |   |
|  |                   +---+---+                                      |   |
|  |                   | eth0  |                                      |   |
|  |                   +-------+                                      |   |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

**CREATING CUSTOM BRIDGE:**

```bash
# Basic
docker network create my-net

# With options
docker network create \
  --driver bridge \
  --subnet 10.0.0.0/24 \
  --gateway 10.0.0.1 \
  --ip-range 10.0.0.128/25 \
  --opt "com.docker.network.bridge.name"="my-bridge" \
  my-custom-net

# Assign specific IP to container
docker run -d --name web --network my-custom-net --ip 10.0.0.10 nginx
```

### 3.2 HOST NETWORK

```
+-------------------------------------------------------------------------+
|                    HOST NETWORK                                         |
|                                                                         |
|  Container shares the host's network namespace.                        |
|  NO network isolation!                                                 |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                         HOST                                     |   |
|  |                                                                  |   |
|  |       +---------------------------------------------+           |   |
|  |       |              Container                      |           |   |
|  |       |                                             |           |   |
|  |       |   Process (nginx listening on port 80)     |           |   |
|  |       |                                             |           |   |
|  |       |   Uses host's eth0 directly!               |           |   |
|  |       |   No NAT, no port mapping needed           |           |   |
|  |       |                                             |           |   |
|  |       +---------------------------------------------+           |   |
|  |                          |                                       |   |
|  |                      +---+---+                                   |   |
|  |                      | eth0  |  Host IP: 10.0.0.5               |   |
|  |                      | :80   |  nginx accessible on 10.0.0.5:80 |   |
|  |                      +-------+                                   |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USAGE:                                                                 |
|  docker run -d --network host nginx                                    |
|                                                                         |
|  PROS:                                                                  |
|  * No NAT overhead (better performance)                                |
|  * No port mapping needed                                              |
|  * Can bind to low ports (< 1024) if container runs as root           |
|                                                                         |
|  CONS:                                                                  |
|  * No network isolation                                                |
|  * Port conflicts with host services                                   |
|  * Less portable (depends on host's network)                          |
|                                                                         |
|  USE CASE:                                                              |
|  * High-performance networking needs                                   |
|  * Container needs to see all host traffic (monitoring)               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.3 NONE NETWORK

```
+-------------------------------------------------------------------------+
|                    NONE NETWORK                                         |
|                                                                         |
|  Container has NO network connectivity.                                |
|  Only has loopback (lo) interface.                                     |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                      Container                                   |   |
|  |                                                                  |   |
|  |   Process                                                       |   |
|  |      |                                                          |   |
|  |      |                                                          |   |
|  |   +--+--+                                                       |   |
|  |   | lo  |  127.0.0.1 (loopback only)                           |   |
|  |   +-----+                                                       |   |
|  |                                                                  |   |
|  |   No eth0, no external connectivity                             |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  USAGE:                                                                 |
|  docker run -d --network none my-secure-app                           |
|                                                                         |
|  USE CASES:                                                             |
|  * Security-sensitive containers (no network attack surface)          |
|  * Batch processing (read files, write files, no network needed)     |
|  * Testing in complete isolation                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 3.4 OVERLAY NETWORK (Multi-Host)

```
+-------------------------------------------------------------------------+
|                    OVERLAY NETWORK                                      |
|                                                                         |
|  Enables container communication across multiple Docker hosts.         |
|  Used in Docker Swarm and (indirectly) Kubernetes.                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HOW IT WORKS (VXLAN):                                                  |
|                                                                         |
|  +-------------------------+       +-------------------------+        |
|  |         HOST 1          |       |         HOST 2          |        |
|  |                         |       |                         |        |
|  |  +-----------------+   |       |   +-----------------+   |        |
|  |  |   Container A   |   |       |   |   Container B   |   |        |
|  |  |   10.0.0.2      |   |       |   |   10.0.0.3      |   |        |
|  |  +--------+--------+   |       |   +--------+--------+   |        |
|  |           |            |       |            |            |        |
|  |  +--------+--------+   |       |   +--------+--------+   |        |
|  |  |  Overlay Net    |   |       |   |  Overlay Net    |   |        |
|  |  |  (VXLAN tunnel) |   |       |   |  (VXLAN tunnel) |   |        |
|  |  +--------+--------+   |       |   +--------+--------+   |        |
|  |           |            |       |            |            |        |
|  |      +----+----+       |       |       +----+----+       |        |
|  |      |  eth0   |       |       |       |  eth0   |       |        |
|  |      |192.168.1.10     |       |       |192.168.1.11     |        |
|  |      +----+----+       |       |       +----+----+       |        |
|  +-----------+------------+       +------------+------------+        |
|              |                                 |                      |
|              +-----------+---------------------+                      |
|                          |                                            |
|               Physical Network (Underlay)                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  Container A sends packet to 10.0.0.3:                                |
|  1. Packet encapsulated in VXLAN header                               |
|  2. Sent over physical network to HOST 2                              |
|  3. HOST 2 decapsulates, delivers to Container B                      |
|                                                                         |
|  From container's perspective: Same network, no awareness of hosts    |
|                                                                         |
+-------------------------------------------------------------------------+
```

CREATING OVERLAY NETWORK (Docker Swarm):

```bash
# Initialize swarm
docker swarm init

# Create overlay network
docker network create --driver overlay --attachable my-overlay

# Run service on overlay
docker service create --name web --network my-overlay nginx

# Or run standalone container on overlay (with --attachable)
docker run -d --name app --network my-overlay my-app
```

### 3.5 MACVLAN NETWORK

```
+-------------------------------------------------------------------------+
|                    MACVLAN NETWORK                                      |
|                                                                         |
|  Assigns a MAC address to container.                                   |
|  Container appears as a PHYSICAL device on the network.                |
|  No NAT, container has its own IP on the LAN.                         |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                         HOST                                     |   |
|  |                                                                  |   |
|  |  +-----------------+  +-----------------+                       |   |
|  |  |   Container A   |  |   Container B   |                       |   |
|  |  | MAC: aa:bb:cc:01|  | MAC: aa:bb:cc:02|                       |   |
|  |  | IP: 192.168.1.20|  | IP: 192.168.1.21|                       |   |
|  |  +--------+--------+  +--------+--------+                       |   |
|  |           |                    |                                 |   |
|  |           +--------+-----------+                                 |   |
|  |                    | macvlan                                     |   |
|  |               +----+----+                                        |   |
|  |               |  eth0   |  Host: 192.168.1.10                   |   |
|  |               +----+----+                                        |   |
|  +--------------------+---------------------------------------------+   |
|                       |                                                 |
|               +-------+--------+                                        |
|               | Physical Switch|  Sees 3 MAC addresses:               |
|               |                |  - Host: 192.168.1.10                 |
|               |                |  - ContainerA: 192.168.1.20           |
|               |                |  - ContainerB: 192.168.1.21           |
|               +----------------+                                        |
|                                                                         |
|  USE CASES:                                                             |
|  * Legacy apps that need to be on the physical network                |
|  * Apps that need to be reachable directly (no NAT)                   |
|  * Network monitoring/sniffing applications                           |
|                                                                         |
|  LIMITATION:                                                            |
|  * Host cannot directly communicate with macvlan containers!          |
|    (By design - different network namespace)                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

**CREATING MACVLAN:**

```bash
# Create macvlan network
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 \
  my-macvlan

# Run container with specific IP
docker run -d --name web --network my-macvlan \
  --ip 192.168.1.20 \
  nginx

# Container is now directly on the physical network!
```

## PART 4: DOCKER DNS AND SERVICE DISCOVERY

### 4.1 EMBEDDED DNS SERVER

```
+-------------------------------------------------------------------------+
|                    DOCKER'S EMBEDDED DNS (127.0.0.11)                   |
|                                                                         |
|  On user-defined networks, Docker runs an embedded DNS server.         |
|  Containers can resolve each other by name.                            |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                      User-Defined Network                        |   |
|  |                                                                  |   |
|  |   +---------------+              +---------------+              |   |
|  |   |   Container   |              |   Container   |              |   |
|  |   |   "web"       |              |   "db"        |              |   |
|  |   |               |              |               |              |   |
|  |   |  ping db -----+--------------+---> Success!  |              |   |
|  |   |               |              |               |              |   |
|  |   |  /etc/resolv.conf:          |               |              |   |
|  |   |  nameserver 127.0.0.11      |               |              |   |
|  |   +---------------+              +---------------+              |   |
|  |           |                                                      |   |
|  |           | DNS query: "db"                                     |   |
|  |           v                                                      |   |
|  |   +-------------------------------------------------------+     |   |
|  |   |              Docker DNS Server (127.0.0.11)           |     |   |
|  |   |                                                       |     |   |
|  |   |   "db" -> 172.18.0.3                                   |     |   |
|  |   |   "web" -> 172.18.0.2                                  |     |   |
|  |   |                                                       |     |   |
|  |   |   Unknown queries -> Forward to host's DNS            |     |   |
|  |   +-------------------------------------------------------+     |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  NOTE: Default bridge does NOT have embedded DNS!                      |
|        Only user-defined networks get automatic DNS.                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 4.2 NETWORK ALIASES

```bash
# Give container multiple DNS names
docker run -d --name postgres --network my-net \
  --network-alias db \
  --network-alias database \
  postgres

# All of these resolve to the same container:
# - postgres (container name)
# - db (alias)
# - database (alias)
```

```bash
# Use case: Multiple containers behind same alias (load balancing)
docker run -d --name web1 --network my-net --network-alias web nginx
docker run -d --name web2 --network my-net --network-alias web nginx
docker run -d --name web3 --network my-net --network-alias web nginx

# DNS query for "web" returns all 3 IPs (round-robin)
docker run --rm --network my-net busybox nslookup web
# Returns: 172.18.0.2, 172.18.0.3, 172.18.0.4
```

## PART 5: DOCKER COMPOSE NETWORKING

### 5.1 DEFAULT NETWORK IN COMPOSE

```bash
# docker-compose.yml
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "8080:80"

  api:
    image: my-api
    depends_on:
      - db

  db:
    image: postgres

# Docker Compose automatically:
# 1. Creates network: myapp_default
# 2. Connects all services to it
# 3. Services can reach each other by service name
#    - web can ping api
#    - api can connect to db:5432
```

### 5.2 CUSTOM NETWORKS IN COMPOSE

```bash
# docker-compose.yml
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

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No external access

# Network isolation:
# - web can reach api (both on frontend)
# - api can reach db (both on backend)
# - web CANNOT reach db (different networks)
# - db has no internet access (internal: true)
```

### 5.3 EXTERNAL NETWORKS

```bash
# Use existing network created outside compose

# First create network
docker network create shared-network

# docker-compose.yml
version: '3.8'

services:
  web:
    image: nginx
    networks:
      - shared-network

networks:
  shared-network:
    external: true

# Useful for:
# - Connecting services from different compose files
# - Sharing network with standalone containers
```

## PART 6: ADVANCED TOPICS

### 6.1 CONTAINER NETWORK MODEL (CNM)

```
+-------------------------------------------------------------------------+
|                    DOCKER'S CONTAINER NETWORK MODEL                     |
|                                                                         |
|  CNM is Docker's networking architecture specification.                |
|                                                                         |
|  THREE MAIN COMPONENTS:                                                 |
|                                                                         |
|  1. SANDBOX                                                             |
|     Container's network namespace.                                     |
|     Contains: interfaces, routes, DNS config                           |
|                                                                         |
|  2. ENDPOINT                                                            |
|     Connection between Sandbox and Network.                            |
|     Like a veth pair end.                                              |
|                                                                         |
|  3. NETWORK                                                             |
|     Group of endpoints that can communicate.                           |
|     Like a bridge or overlay.                                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  +---------------------------------------------------------------+     |
|  |                        NETWORK A                              |     |
|  |  +---------------------------------------------------------+  |     |
|  |  |                                                         |  |     |
|  |  |  +-------------+  +-------------+  +-------------+     |  |     |
|  |  |  |   SANDBOX   |  |   SANDBOX   |  |   SANDBOX   |     |  |     |
|  |  |  | Container 1 |  | Container 2 |  | Container 3 |     |  |     |
|  |  |  +------+------+  +------+------+  +------+------+     |  |     |
|  |  |         |                |                |             |  |     |
|  |  |     Endpoint         Endpoint         Endpoint          |  |     |
|  |  |         |                |                |             |  |     |
|  |  |         +----------------+----------------+             |  |     |
|  |  |                          |                              |  |     |
|  |  +--------------------------+------------------------------+  |     |
|  |                             |                                 |     |
|  |                    Network Driver                             |     |
|  |                   (bridge, overlay)                           |     |
|  |                                                               |     |
|  +---------------------------------------------------------------+     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 6.2 NETWORK SECURITY AND ISOLATION

**ISOLATION STRATEGIES:**

```bash
# 1. Separate networks for different services
docker network create frontend
docker network create backend
docker network create database --internal

# 2. Internal networks (no external access)
docker network create --internal secure-net

# 3. Restrict inter-container communication
# In daemon.json:
{
  "icc": false  // Disable inter-container communication on default bridge
}

# 4. Use firewall rules
iptables -I DOCKER-USER -s 172.18.0.0/16 -d 172.19.0.0/16 -j DROP
```

### 6.3 NETWORK TROUBLESHOOTING

**USEFUL COMMANDS:**

```bash
# 1. Inspect network
docker network inspect my-network

# 2. See container's network settings
docker inspect --format='{{json .NetworkSettings}}' container-name

# 3. Check connectivity from inside container
docker exec -it container-name /bin/sh
ping other-container
nslookup other-container
curl http://other-container:8080

# 4. See iptables rules
iptables -t nat -L -n -v
iptables -L -n -v

# 5. See bridge and veth pairs
brctl show
ip link

# 6. Trace packets
tcpdump -i docker0 -n

# 7. Check DNS resolution
docker run --rm --network my-net busybox nslookup db
```

**COMMON ISSUES:**

```
+--------------------------------------------------------------------+
| Problem                        | Solution                          |
+--------------------------------+-----------------------------------+
| Container can't reach internet | Check NAT rules (MASQUERADE)     |
|                                | Check ip_forward is enabled       |
+--------------------------------+-----------------------------------+
| Can't resolve container name   | Use user-defined network, not    |
|                                | default bridge                    |
+--------------------------------+-----------------------------------+
| Port not accessible from host  | Check -p flag mapping            |
|                                | Check firewall rules              |
+--------------------------------+-----------------------------------+
| Containers can't communicate   | Check they're on same network    |
|                                | Check ICC settings                |
+--------------------------------+-----------------------------------+
```

## PART 7: HANDS-ON LABS

### 7.1 LAB EXERCISES

LAB 1: Bridge Networking Basics

```bash
# Create a custom network
docker network create lab-net

# Run two containers
docker run -d --name web --network lab-net nginx
docker run -d --name client --network lab-net alpine sleep 3600

# Test DNS resolution
docker exec client ping -c 3 web

# Test HTTP
docker exec client wget -O- http://web

# Cleanup
docker rm -f web client
docker network rm lab-net
```

LAB 2: Multi-Network Setup

```bash
# Create frontend and backend networks
docker network create frontend
docker network create backend --internal

# Run database (backend only)
docker run -d --name db --network backend postgres:alpine

# Run API (both networks)
docker run -d --name api --network backend alpine sleep 3600
docker network connect frontend api

# Run web (frontend only)
docker run -d --name web --network frontend nginx

# Test connectivity
docker exec api ping -c 1 db      # Works
docker exec web ping -c 1 api     # Works
docker exec web ping -c 1 db      # Fails (different network)
docker exec db ping -c 1 google.com  # Fails (internal network)
```

LAB 3: Port Mapping

```bash
# Run nginx with port mapping
docker run -d --name web -p 8080:80 nginx

# Access from host
curl http://localhost:8080

# See NAT rules created by Docker
iptables -t nat -L -n | grep 8080
```

### 7.2 COMMON COMMANDS REFERENCE

```
+--------------------------------------------------------------------+
| Command                           | Description                    |
+-----------------------------------+--------------------------------+
| docker network ls                 | List all networks              |
| docker network inspect <net>      | Show network details           |
| docker network create <net>       | Create network                 |
| docker network rm <net>           | Remove network                 |
| docker network connect <net> <c>  | Connect container to network   |
| docker network disconnect <net> <c>| Disconnect container          |
| docker network prune              | Remove unused networks         |
+-----------------------------------+--------------------------------+
| docker run --network <net>        | Run container on network       |
| docker run -p 8080:80             | Map port 8080->80              |
| docker run --network host         | Use host network               |
| docker run --network none         | No networking                  |
| docker run --ip 10.0.0.5          | Assign specific IP             |
| docker run --network-alias db     | Add DNS alias                  |
+-----------------------------------+--------------------------------+
```

## END OF DOCUMENT

