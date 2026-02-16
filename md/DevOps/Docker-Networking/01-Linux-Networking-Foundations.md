# CHAPTER 1: LINUX NETWORKING FOUNDATIONS
*The Building Blocks That Make Container Networking Possible*

Before we can understand how Docker networking works, we must first understand
the Linux kernel features that make it possible. Docker doesn't invent new
networking technology-it cleverly combines existing Linux kernel features to
create isolated network environments for containers.

This chapter covers the fundamental Linux concepts you absolutely must understand:
- Network Namespaces
- Virtual Ethernet (veth) Pairs
- Linux Bridges
- iptables and Netfilter
- Network Address Translation (NAT)

By the end of this chapter, you'll be able to build your own container networking
from scratch using only Linux commands-which is essentially what Docker does.

## SECTION 1.1: UNDERSTANDING NETWORK NAMESPACES

### WHAT PROBLEM DO NAMESPACES SOLVE?

Imagine you have a single Linux server running multiple applications. Traditionally,
all these applications share the same network stack:

- They see the same network interfaces (eth0, lo)
- They share the same routing table
- They share the same firewall rules
- They compete for the same ports

This creates several problems:

PROBLEM 1: PORT CONFLICTS
If Application A wants to listen on port 80, Application B cannot also use
port 80. In a world where you might run dozens of web servers, this is a
significant limitation.

PROBLEM 2: NO ISOLATION
Any application can see traffic destined for any other application. There's
no network-level separation between workloads.

PROBLEM 3: SECURITY CONCERNS
A compromised application can potentially interfere with the network
configuration of other applications.

### THE SOLUTION: NETWORK NAMESPACES

A network namespace is a completely isolated copy of the network stack. When you
create a new network namespace, you get:

Y Its own set of network interfaces
Y Its own routing table
Y Its own iptables rules
Y Its own socket namespace
Y Its own /proc/net directory

Think of it like this: A network namespace is like giving each application its
own private computer, at least from a networking perspective. Each namespace
thinks it has complete control over the network, unaware that other namespaces
exist.

### ANALOGY: THE APARTMENT BUILDING

Consider an apartment building:

```sql
WITHOUT NAMESPACES (Shared House):
* Everyone shares the same living room, kitchen, bathroom
* If one person is using the TV, others can't watch something different
* Everyone hears everyone else's conversations
* No privacy, constant conflicts

WITH NAMESPACES (Separate Apartments):
* Each apartment has its own living room, kitchen, bathroom
* Each resident has complete privacy
* No conflicts over shared resources
* Each apartment operates independently
```

Network namespaces give each container its own "apartment" in terms of networking.

### HANDS-ON: CREATING YOUR FIRST NAMESPACE

Let's create a network namespace and explore it:

```bash
# Step 1: Create a new network namespace called "red"
sudo ip netns add red

# Step 2: List all network namespaces
ip netns list
# Output: red

# Step 3: See what's inside the namespace
sudo ip netns exec red ip link
# Output:
# 1: lo: <LOOPBACK> mtu 65536 qdisc noop state DOWN mode DEFAULT
#    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
```

Notice that the new namespace only has a loopback interface (lo), and it's DOWN.
This namespace is completely isolated-it has no connection to the outside world.

```bash
# Step 4: Try to reach the internet from inside the namespace
sudo ip netns exec red ping 8.8.8.8
# Output: connect: Network is unreachable
```

The ping fails because:
1. The loopback interface is down
2. There's no eth0 or any other interface to reach external networks
3. There are no routes configured

### WHAT HAPPENS WHEN YOU CREATE A CONTAINER?

When Docker creates a container, one of the first things it does is create a
new network namespace for that container. This is why:

- Each container can bind to port 80 without conflicts
- Containers can't see each other's network traffic (by default)
- Each container has its own IP address
- Each container has its own routing table

But wait-if namespaces are isolated, how do containers communicate with each
other or the outside world? That's where veth pairs come in.

## SECTION 1.2: VIRTUAL ETHERNET (VETH) PAIRS

### THE ISOLATION PROBLEM

We just learned that network namespaces are isolated. But complete isolation
isn't useful-containers need to communicate! We need a way to connect namespaces
together or to the host network.

This is where Virtual Ethernet pairs (veth pairs) come in.

### WHAT IS A VETH PAIR?

A veth pair is like a virtual network cable with two ends. Whatever goes into
one end comes out the other end, and vice versa. The two ends are called "peers."

```
+-------------------------------------------------------------------------+
|                                                                         |
|                        VETH PAIR                                        |
|                                                                         |
|    +-------------+                              +-------------+        |
|    |   veth-A    |<============================>|   veth-B    |        |
|    |   (peer 0)  |       Virtual Cable          |   (peer 1)  |        |
|    +-------------+                              +-------------+        |
|                                                                         |
|    Any packet sent         --------------->    Appears here            |
|    into veth-A                                                         |
|                                                                         |
|    Appears here            <---------------    Any packet sent         |
|                                                 into veth-B            |
|                                                                         |
+-------------------------------------------------------------------------+
```

Key characteristics:

1. ALWAYS CREATED IN PAIRS
You can't create just one end; they always come as a pair.

2. BIDIRECTIONAL
Traffic flows both ways through the virtual cable.

3. CAN SPAN NAMESPACES
One end can be in one namespace, the other end in a different namespace.
This is the key feature that allows namespace connectivity!

4. BEHAVE LIKE REAL ETHERNET INTERFACES
They have MAC addresses, can be assigned IP addresses, and participate
in routing just like physical NICs.

### ANALOGY: THE TIN CAN TELEPHONE

Remember the tin can telephone you might have made as a kid?

- Two tin cans connected by a string
- You speak into one can
- Sound travels through the string
- Your friend hears it on the other can

A veth pair works the same way:
- Two virtual interfaces connected internally
- You send packets into one interface
- Packets travel through the virtual connection
- They appear on the other interface

### HANDS-ON: CONNECTING TWO NAMESPACES

Let's create two namespaces and connect them with a veth pair:

```bash
# Step 1: Create two namespaces
sudo ip netns add red
sudo ip netns add blue

# Step 2: Create a veth pair
# This creates veth-red and veth-blue, connected to each other
sudo ip link add veth-red type veth peer name veth-blue

# At this point, both ends exist in the ROOT (host) namespace
ip link | grep veth
# veth-blue@veth-red: ...
# veth-red@veth-blue: ...

# Step 3: Move each end to its respective namespace
sudo ip link set veth-red netns red
sudo ip link set veth-blue netns blue

# Now if you check the host, the veth interfaces are gone
ip link | grep veth
# (nothing - they've moved to the namespaces)

# Verify they're in the namespaces
sudo ip netns exec red ip link
# Shows veth-red

sudo ip netns exec blue ip link
# Shows veth-blue

# Step 4: Assign IP addresses
sudo ip netns exec red ip addr add 192.168.1.1/24 dev veth-red
sudo ip netns exec blue ip addr add 192.168.1.2/24 dev veth-blue

# Step 5: Bring the interfaces UP
sudo ip netns exec red ip link set veth-red up
sudo ip netns exec blue ip link set veth-blue up

# Don't forget the loopback!
sudo ip netns exec red ip link set lo up
sudo ip netns exec blue ip link set lo up

# Step 6: Test connectivity!
sudo ip netns exec red ping 192.168.1.2
# PING 192.168.1.2 (192.168.1.2) 56(84) bytes of data.
# 64 bytes from 192.168.1.2: icmp_seq=1 ttl=64 time=0.050 ms

SUCCESS! The two namespaces can now communicate!
```

### WHAT DID WE JUST BUILD?

We created the simplest possible container network:

```
+-----------------------+          +-----------------------+
|     Red Namespace     |          |    Blue Namespace     |
|                       |          |                       |
|   +---------------+   |          |   +---------------+   |
|   |   veth-red    |   |          |   |   veth-blue   |   |
|   |  192.168.1.1  |---+----------+---|  192.168.1.2  |   |
|   +---------------+   |  veth    |   +---------------+   |
|                       |  pair    |                       |
+-----------------------+          +-----------------------+
```

This is exactly how Docker connects containers-with veth pairs!

### THE LIMITATION OF VETH PAIRS

Veth pairs are perfect for connecting TWO namespaces. But what if you have
10 containers that all need to communicate with each other?

With just veth pairs, you'd need:
- 10 x 9 / 2 = 45 veth pairs!

This doesn't scale. We need something that acts like a network switch-enter
the Linux Bridge.

## SECTION 1.3: LINUX BRIDGES - THE VIRTUAL SWITCH

### THE PROBLEM WITH MANY-TO-MANY CONNECTIVITY

Suppose you have 5 containers that all need to talk to each other:

WITHOUT A BRIDGE (Mesh of veth pairs):

Container 1
/|\
/ | \
/  |  \
C2 --o   o   o-- C3
\  |  /
\ | /
\|/
Container 4 ------ Container 5

This requires 10 veth pairs! And adding a 6th container means creating
5 more veth pairs. This is O(n2) complexity-it doesn't scale.

```
WITH A BRIDGE (Star topology):

     Container 1
          |
          |
C2 -------+------- C3
          |
     +----+----+
     |  BRIDGE |
     +----+----+
          |
C4 -------+------- C5

Each container needs only ONE veth pair to connect to the bridge.
Adding a 6th container means creating just 1 more veth pair.
This is O(n) complexity-much better!
```

### WHAT IS A LINUX BRIDGE?

A Linux bridge is a software implementation of a network switch. Just like a
physical Ethernet switch:

- It learns MAC addresses of connected devices
- It forwards frames only to the appropriate port
- It operates at Layer 2 (Data Link layer)
- It can have an IP address (making it a Layer 3 bridge)

The key difference: A physical switch has physical ports; a Linux bridge has
virtual interfaces attached to it.

### HOW A BRIDGE WORKS

When a frame arrives at the bridge:

1. LEARNING
The bridge records the source MAC address and the port it came from.
"MAC aa:bb:cc:dd:ee:ff is reachable via port 3"

2. FORWARDING DECISION
The bridge looks up the destination MAC address in its table:
- If found: Forward only to that port (unicast)
- If not found: Flood to all ports except the source (unknown unicast)
- If broadcast: Send to all ports except source

3. FORWARDING
The frame is sent out the appropriate port(s).

This is identical to how a physical switch works-the Linux kernel implements
the switching logic in software.

### DOCKER'S docker0 BRIDGE

When you install Docker, it automatically creates a bridge called "docker0":

```bash
# Check for docker0
ip link show docker0
# docker0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 ...

ip addr show docker0
# inet 172.17.0.1/16 ...

# See what's attached to docker0
brctl show docker0
# bridge name     bridge id               STP enabled     interfaces
# docker0         8000.024216a6c4e2       no
```

The docker0 bridge:
- Has IP address 172.17.0.1 (acts as gateway for containers)
- Uses subnet 172.17.0.0/16 by default
- Containers attach to it via veth pairs

### HANDS-ON: BUILDING YOUR OWN CONTAINER NETWORK

Let's build a network identical to Docker's default bridge:

```bash
# Step 1: Create a bridge
sudo ip link add br0 type bridge
sudo ip link set br0 up

# Step 2: Assign an IP address (this becomes the gateway)
sudo ip addr add 192.168.15.1/24 dev br0

# Step 3: Create two namespaces (simulating containers)
sudo ip netns add container1
sudo ip netns add container2

# Step 4: Create veth pairs for each container
sudo ip link add veth1 type veth peer name veth1-br
sudo ip link add veth2 type veth peer name veth2-br

# Step 5: Move container end to namespace, bridge end to bridge
sudo ip link set veth1 netns container1
sudo ip link set veth1-br master br0

sudo ip link set veth2 netns container2
sudo ip link set veth2-br master br0

# Step 6: Configure IPs inside namespaces
sudo ip netns exec container1 ip addr add 192.168.15.2/24 dev veth1
sudo ip netns exec container2 ip addr add 192.168.15.3/24 dev veth2

# Step 7: Set default gateway (the bridge IP)
sudo ip netns exec container1 ip route add default via 192.168.15.1
sudo ip netns exec container2 ip route add default via 192.168.15.1

# Step 8: Bring everything up
sudo ip link set veth1-br up
sudo ip link set veth2-br up
sudo ip netns exec container1 ip link set veth1 up
sudo ip netns exec container2 ip link set veth2 up
sudo ip netns exec container1 ip link set lo up
sudo ip netns exec container2 ip link set lo up

# Step 9: Test container-to-container communication
sudo ip netns exec container1 ping 192.168.15.3
# SUCCESS! Packets flow through the bridge.
```

### THE ARCHITECTURE WE BUILT

```
+-------------------------------------------------------------------------+
|                              HOST                                       |
|                                                                         |
|    +------------------+              +------------------+              |
|    |    container1    |              |    container2    |              |
|    |   192.168.15.2   |              |   192.168.15.3   |              |
|    |                  |              |                  |              |
|    |   +----------+   |              |   +----------+   |              |
|    |   |  veth1   |   |              |   |  veth2   |   |              |
|    |   +----+-----+   |              |   +----+-----+   |              |
|    |        |         |              |        |         |              |
|    +--------+---------+              +--------+---------+              |
|             |                                 |                        |
|             | veth1-br                        | veth2-br               |
|             |                                 |                        |
|    +--------+---------------------------------+--------+              |
|    |                    br0 (bridge)                    |              |
|    |                   192.168.15.1                     |              |
|    |              (gateway for containers)              |              |
|    +----------------------------------------------------+              |
|                                                                         |
+-------------------------------------------------------------------------+
```

This is EXACTLY what Docker does when you run containers on the default
bridge network! The only difference is Docker automates all these steps.

### BUT WAIT-CONTAINERS STILL CAN'T REACH THE INTERNET!

Try this:

```bash
sudo ip netns exec container1 ping 8.8.8.8
# Network is unreachable (or no route to host)
```

The containers can reach each other and the bridge, but they can't reach
the outside world. Why?

Because the containers use private IP addresses (192.168.15.0/24) that aren't
routable on the internet. We need NAT (Network Address Translation) to solve
this-which brings us to our next topic.

## SECTION 1.4: IPTABLES AND NETFILTER - THE LINUX FIREWALL

### WHAT IS NETFILTER?

Netfilter is a framework built into the Linux kernel that allows you to:

- Filter packets (firewall)
- Modify packets (NAT, mangling)
- Track connections (stateful inspection)
- Log packets

iptables is the user-space tool used to configure Netfilter rules.

### THE PACKET JOURNEY THROUGH NETFILTER

When a packet enters or leaves a Linux system, it passes through several
"hooks" or checkpoints where Netfilter can inspect and modify it:

```
INCOMING PACKET (from network):

+-------------------------------------------------------------------------+
|                                                                         |
|     Network                                                             |
|        |                                                                |
|        v                                                                |
|   +-------------+                                                      |
|   | PREROUTING  | < First stop for all incoming packets                |
|   +------+------+   NAT/DNAT happens here                              |
|          |                                                              |
|          v                                                              |
|   +-------------+                                                      |
|   |  ROUTING    | < Kernel decides: Is this for me or should I forward?|
|   |  DECISION   |                                                      |
|   +------+------+                                                      |
|          |                                                              |
|     +----+----+                                                        |
|     |         |                                                        |
|     v         v                                                        |
|  (For me)   (Forward)                                                  |
|     |         |                                                        |
|     v         v                                                        |
| +-------+  +---------+                                                |
| | INPUT |  | FORWARD | < Packets being routed through this host       |
| +---+---+  +----+----+                                                |
|     |           |                                                      |
|     v           |                                                      |
| Local Process   |                                                      |
|     |           |                                                      |
|     v           |                                                      |
| +--------+      |                                                      |
| | OUTPUT |      |  < Packets generated locally                        |
| +---+----+      |                                                      |
|     |           |                                                      |
|     +-----+-----+                                                      |
|           |                                                            |
|           v                                                            |
|   +--------------+                                                     |
|   | POSTROUTING  | < Last stop before leaving                         |
|   +------+-------+   SNAT/MASQUERADE happens here                     |
|          |                                                              |
|          v                                                              |
|      Network                                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### IPTABLES TABLES

iptables organizes rules into "tables" based on what they do:

FILTER TABLE (default)
- Purpose: Accept or drop packets (firewall)
- Chains: INPUT, FORWARD, OUTPUT
- Example: Block all incoming SSH from a specific IP

NAT TABLE
- Purpose: Network Address Translation
- Chains: PREROUTING, POSTROUTING, OUTPUT
- Example: Change source IP of outgoing packets

MANGLE TABLE
- Purpose: Modify packet headers
- Chains: All five chains
- Example: Change TTL, mark packets for routing

RAW TABLE
- Purpose: Bypass connection tracking
- Chains: PREROUTING, OUTPUT
- Example: High-performance packet processing

### DOCKER'S USE OF IPTABLES

Docker heavily uses iptables for:

1. NAT (MASQUERADE)
Allows containers to reach the internet using the host's IP

2. Port Forwarding (DNAT)
Maps host ports to container ports (-p 8080:80)

3. Inter-container Communication
Controls whether containers can talk to each other

4. Network Isolation
Prevents traffic between different Docker networks

Let's look at each in detail.

## SECTION 1.5: NETWORK ADDRESS TRANSLATION (NAT)

### WHY DO WE NEED NAT?

Containers use private IP addresses (like 172.17.0.2). These addresses:

- Are not routable on the internet
- Can't be used to reach external servers
- Would be dropped by internet routers

NAT solves this by translating private addresses to public addresses.

### SNAT (SOURCE NAT) - OUTGOING TRAFFIC

When a container wants to reach the internet:

```
BEFORE NAT (packet leaves container):
+-------------------------------------------------------------+
|  Source IP:        172.17.0.2  (container)                  |
|  Destination IP:   8.8.8.8     (Google DNS)                |
|  Source Port:      54321                                    |
|  Destination Port: 53                                       |
+-------------------------------------------------------------+

The internet has no idea how to route back to 172.17.0.2!

AFTER NAT (packet leaves host):
+-------------------------------------------------------------+
|  Source IP:        203.0.113.5  (host's public IP)         |
|  Destination IP:   8.8.8.8      (Google DNS)               |
|  Source Port:      34567        (mapped port)              |
|  Destination Port: 53                                       |
+-------------------------------------------------------------+

Now the reply can come back to the host!

RETURN PACKET (response from internet):
+-------------------------------------------------------------+
|  Source IP:        8.8.8.8                                  |
|  Destination IP:   203.0.113.5  (host)                     |
|  Source Port:      53                                       |
|  Destination Port: 34567                                    |
+-------------------------------------------------------------+

AFTER REVERSE NAT (host forwards to container):
+-------------------------------------------------------------+
|  Source IP:        8.8.8.8                                  |
|  Destination IP:   172.17.0.2   (container)                |
|  Source Port:      53                                       |
|  Destination Port: 54321        (original port)            |
+-------------------------------------------------------------+
```

### MASQUERADE - DYNAMIC SNAT

MASQUERADE is a special type of SNAT that automatically uses the outgoing
interface's IP address. This is perfect for situations where the host's IP
might change (DHCP, cloud instances).

iptables -t nat -A POSTROUTING \
-s 172.17.0.0/16 \
-o eth0 \
-j MASQUERADE

Translation:
- Table: nat
- Chain: POSTROUTING (as packets leave)
- Source: 172.17.0.0/16 (Docker containers)
- Out interface: eth0 (external interface)
- Action: MASQUERADE (replace source IP with eth0's IP)

This single rule allows ALL containers to reach the internet!

### DNAT (DESTINATION NAT) - INCOMING TRAFFIC / PORT FORWARDING

When someone wants to reach a container from outside:

```
docker run -p 8080:80 nginx

This creates a DNAT rule:

INCOMING PACKET (to host:8080):
+-------------------------------------------------------------+
|  Source IP:        203.0.113.100  (client on internet)     |
|  Destination IP:   203.0.113.5    (host)                   |
|  Source Port:      45678                                    |
|  Destination Port: 8080                                     |
+-------------------------------------------------------------+

AFTER DNAT (forwarded to container):
+-------------------------------------------------------------+
|  Source IP:        203.0.113.100                           |
|  Destination IP:   172.17.0.2     (container)              |
|  Source Port:      45678                                    |
|  Destination Port: 80             (container's nginx port) |
+-------------------------------------------------------------+
```

The iptables rule Docker creates:

iptables -t nat -A PREROUTING \
-p tcp \
--dport 8080 \
-j DNAT --to-destination 172.17.0.2:80

Translation:
- Table: nat
- Chain: PREROUTING (as packets arrive)
- Protocol: TCP
- Destination port: 8080
- Action: Change destination to 172.17.0.2:80

### HANDS-ON: ENABLING INTERNET FOR OUR CONTAINERS

Remember our bridge network from earlier? Let's enable internet access:

```bash
# Step 1: Enable IP forwarding (allows the host to route packets)
sudo sysctl -w net.ipv4.ip_forward=1

# Step 2: Add MASQUERADE rule for our container subnet
sudo iptables -t nat -A POSTROUTING \
    -s 192.168.15.0/24 \
    -o eth0 \
    -j MASQUERADE

# Step 3: Allow forwarding through the bridge
sudo iptables -A FORWARD \
    -i br0 \
    -o eth0 \
    -j ACCEPT

sudo iptables -A FORWARD \
    -i eth0 \
    -o br0 \
    -m state --state ESTABLISHED,RELATED \
    -j ACCEPT

# Step 4: Test internet access from container!
sudo ip netns exec container1 ping 8.8.8.8
# PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
# 64 bytes from 8.8.8.8: icmp_seq=1 ttl=116 time=12.3 ms

SUCCESS! Our container can now reach the internet!
```

## SECTION 1.6: PUTTING IT ALL TOGETHER

### WHAT WE'VE LEARNED

We've covered all the building blocks Docker uses for networking:

1. NETWORK NAMESPACES
Provide isolated network stacks for containers

2. VETH PAIRS
Connect namespaces to the host network

3. LINUX BRIDGES
Act as virtual switches connecting multiple containers

4. IPTABLES/NETFILTER
Provide firewall functionality and packet modification

5. NAT (MASQUERADE & DNAT)
Enable internet access and port forwarding

### DOCKER'S DEFAULT BRIDGE: THE COMPLETE PICTURE

When you run: docker run -d -p 8080:80 --name web nginx

Docker does ALL of the following automatically:

1. Creates a network namespace for the container
2. Creates a veth pair
3. Moves one end into the container namespace (becomes eth0)
4. Attaches other end to docker0 bridge
5. Assigns IP from 172.17.0.0/16 subnet via DHCP
6. Sets container's default gateway to 172.17.0.1 (docker0)
7. Creates DNAT rule: host:8080 > container:80
8. MASQUERADE rule already exists for outbound traffic

All the complexity we explored manually-Docker handles it in milliseconds!

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LINUX NETWORKING BUILDING BLOCKS FOR CONTAINERS                       |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |   NETWORK NAMESPACE                                             |   |
|  |   * Isolated network stack                                     |   |
|  |   * Own interfaces, routes, iptables                           |   |
|  |   * Foundation of container isolation                          |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |   VETH PAIR                                                     |   |
|  |   * Virtual cable with two ends                                |   |
|  |   * Connects namespaces                                        |   |
|  |   * Always created in pairs                                    |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |   LINUX BRIDGE                                                  |   |
|  |   * Virtual Layer 2 switch                                     |   |
|  |   * Connects multiple containers                               |   |
|  |   * docker0 is Docker's default bridge                         |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |   IPTABLES/NAT                                                  |   |
|  |   * MASQUERADE: Containers reach internet                      |   |
|  |   * DNAT: Port forwarding (host:port > container:port)        |   |
|  |   * Firewall rules for isolation                              |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  These four concepts form the foundation of ALL container networking.  |
|  Docker, Kubernetes, and other container platforms all build on top   |
|  of these Linux kernel features.                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WHAT'S NEXT?

In Chapter 2, we'll dive into Docker's specific networking implementation:
- The Container Network Model (CNM)
- Docker network drivers in detail
- How Docker DNS works
- Docker Compose networking
- Advanced Docker networking scenarios

## END OF CHAPTER 1

