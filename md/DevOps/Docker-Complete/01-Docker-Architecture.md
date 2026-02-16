# CHAPTER 1: DOCKER ARCHITECTURE
*Understanding How Docker Actually Works Under the Hood*

To truly master Docker, you need to understand how it works internally. This
chapter explains Docker's architecture, its components, and how they interact.

## SECTION 1.1: THE BIG PICTURE

### DOCKER'S CLIENT-SERVER ARCHITECTURE

Docker uses a client-server architecture:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HIGH-LEVEL DOCKER ARCHITECTURE                                         |
|                                                                         |
|  +-----------------+          +-------------------------------------+   |
|  |                 |          |                                     |   |
|  |  DOCKER CLIENT  |          |          DOCKER HOST                |   |
|  |  (docker CLI)   |          |                                     |   |
|  |                 |          |  +-------------------------------+  |   |
|  |  Commands:      |   REST   |  |       DOCKER DAEMON           |  |   |
|  |  * docker run   |   API    |  |       (dockerd)               |  |   |
|  |  * docker build | ------>  |  |                               |  |   |
|  |  * docker pull  |          |  |  * Manages containers        |  |    |
|  |  * docker push  |          |  |  * Manages images            |  |    |
|  |                 |          |  |  * Manages networks          |  |    |
|  +-----------------+          |  |  * Manages volumes           |  |    |
|                               |  |                               |  |   |
|                               |  +-------------------------------+  |   |
|                               |                |                    |   |
|                               |                v                    |   |
|                               |  +-------------------------------+  |   |
|                               |  |        CONTAINERD            |  |    |
|                               |  |  (container runtime)          |  |   |
|                               |  +-------------------------------+  |   |
|                               |                |                    |   |
|                               |                v                    |   |
|                               |  +-------------------------------+  |   |
|                               |  |           runc               |  |    |
|                               |  |  (creates containers)         |  |   |
|                               |  +-------------------------------+  |   |
|                               |                                     |   |
|                               +-------------------------------------+   |
|                                                                         |
|  +-----------------+                                                    |
|  | DOCKER REGISTRY | <---- Docker Host pulls/pushes images              |
|  | (Docker Hub)    |                                                    |
|  +-----------------+                                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

KEY COMPONENTS EXPLAINED
### 1. DOCKER CLIENT (docker)

- The command-line interface you interact with
- Sends commands to Docker daemon via REST API
- Can connect to local or remote Docker daemons
- Example: docker run, docker build, docker pull

2. DOCKER DAEMON (dockerd)
------------------------
- The "brain" of Docker
- Listens for API requests
- Manages Docker objects (images, containers, networks, volumes)
- Communicates with other Docker daemons (Swarm)

3. CONTAINERD
----------
- Industry-standard container runtime
- Manages the complete container lifecycle
- Handles image transfers and storage
- Supervises container execution

4. runc
----
- Lightweight container runtime
- Actually creates and runs containers
- Uses Linux kernel features (namespaces, cgroups)
- OCI (Open Container Initiative) compliant

## SECTION 1.2: THE EVOLUTION OF DOCKER ARCHITECTURE

### UNDERSTANDING WHY DOCKER IS STRUCTURED THIS WAY

Docker's architecture evolved over time. Understanding this history helps
you understand why it's structured the way it is.

### ORIGINAL DOCKER (Pre-1.11)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MONOLITHIC DOCKER (OLD)                                                |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                       Docker Daemon                              |   |
|  |                                                                  |   |
|  |  Everything in ONE process:                                     |    |
|  |  * API server                                                   |    |
|  |  * Image management                                             |    |
|  |  * Container runtime                                            |    |
|  |  * Networking                                                   |    |
|  |  * Volumes                                                      |    |
|  |                                                                  |   |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  PROBLEMS:                                                              |
|  * Daemon restart = ALL containers restart                              |
|  * Tightly coupled components                                           |
|  * Difficult to innovate on specific parts                              |
|  * Not suitable for Kubernetes (needed alternative runtimes)            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### MODERN DOCKER (Post-1.11)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MODULAR DOCKER (CURRENT)                                               |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |  Docker Daemon (dockerd)                                        |    |
|  |  * API server                                                   |    |
|  |  * Image management (build, push, pull)                        |     |
|  |  * High-level orchestration                                    |     |
|  +--------------------------+--------------------------------------+    |
|                             | gRPC                                      |
|                             v                                           |
|  +-----------------------------------------------------------------+    |
|  |  containerd                                                      |   |
|  |  * Container lifecycle (create, start, stop, delete)           |     |
|  |  * Image pulling and pushing                                   |     |
|  |  * Network and storage management                              |     |
|  +--------------------------+--------------------------------------+    |
|                             |                                           |
|                             v                                           |
|  +-----------------------------------------------------------------+    |
|  |  containerd-shim                                                |    |
|  |  * Decouples container from containerd                         |     |
|  |  * Keeps STDIO and fds open                                    |     |
|  |  * Reports exit status to containerd                           |     |
|  +--------------------------+--------------------------------------+    |
|                             |                                           |
|                             v                                           |
|  +-----------------------------------------------------------------+    |
|  |  runc                                                            |   |
|  |  * Creates container                                            |    |
|  |  * Exits after container starts (daemonless)                   |     |
|  +-----------------------------------------------------------------+    |
|                                                                         |
|  BENEFITS:                                                              |
|  Y Daemon restart doesn't affect running containers                     |
|  Y Components can be upgraded independently                             |
|  Y containerd can be used without Docker (Kubernetes)                   |
|  Y Follows Unix philosophy (do one thing well)                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.3: DEEP DIVE INTO EACH COMPONENT

### THE DOCKER CLIENT

The docker client is what you interact with:

```bash
$ docker run nginx        
$ docker build -t myapp . 
$ docker push myapp:latest
```

**HOW CLIENT COMMUNICATES WITH DAEMON:**

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DOCKER CLIENT COMMUNICATION                                            |
|                                                                         |
|  LOCAL COMMUNICATION (Default):                                         |
|  --------------------------------                                       |
|  Client --> Unix Socket --> Daemon                                      |
|            /var/run/docker.sock                                         |
|                                                                         |
|  REMOTE COMMUNICATION:                                                  |
|  ----------------------                                                 |
|  Client --> TCP/TLS --> Remote Daemon                                   |
|            tcp://192.168.1.100:2376                                     |
|                                                                         |
|  ENVIRONMENT VARIABLE:                                                  |
|  export DOCKER_HOST=tcp://192.168.1.100:2376                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

```bash
When you run a command:                  

$ docker run nginx                       

1. Client parses command                 
2. Client creates REST API request       
3. Client sends to daemon via Unix socket
4. Daemon processes request              
5. Daemon returns response               
6. Client displays output                
```

### THE DOCKER DAEMON (dockerd)

The daemon is responsible for:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DOCKER DAEMON RESPONSIBILITIES                                         |
|                                                                         |
|  IMAGE OPERATIONS                                                       |
|  * Building images from Dockerfile                                      |
|  * Pulling images from registries                                       |
|  * Pushing images to registries                                         |
|  * Managing local image cache                                           |
|                                                                         |
|  CONTAINER OPERATIONS (via containerd)                                  |
|  * Creating containers                                                  |
|  * Starting/stopping containers                                         |
|  * Attaching to containers                                              |
|  * Executing commands in containers                                     |
|                                                                         |
|  NETWORKING                                                             |
|  * Creating Docker networks                                             |
|  * Managing bridge, overlay networks                                    |
|  * DNS for service discovery                                            |
|                                                                         |
|  STORAGE                                                                |
|  * Managing volumes                                                     |
|  * Managing bind mounts                                                 |
|                                                                         |
|  API SERVER                                                             |
|  * Listening on Unix socket                                             |
|  * Handling REST API requests                                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CONTAINERD

containerd is an industry-standard container runtime:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONTAINERD FEATURES                                                    |
|                                                                         |
|  * CAN BE USED WITHOUT DOCKER!                                          |
|    Kubernetes can use containerd directly                               |
|                                                                         |
|  * Container lifecycle management                                       |
|    create, start, stop, pause, resume, delete                           |
|                                                                         |
|  * Image management                                                     |
|    pull, push, image storage                                            |
|                                                                         |
|  * Snapshot management                                                  |
|    Container filesystem layers                                          |
|                                                                         |
|  * Task execution                                                       |
|    Running processes in containers                                      |
|                                                                         |
|  USED BY:                                                               |
|  * Docker                                                               |
|  * Kubernetes (CRI plugin)                                              |
|  * AWS Fargate                                                          |
|  * Google Cloud Run                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### THE SHIM (containerd-shim)

The shim is a small process that acts as a parent for the container:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY THE SHIM EXISTS                                                    |
|                                                                         |
|  WITHOUT SHIM:                                                          |
|                                                                         |
|    containerd                                                           |
|        |                                                                |
|        +-- container process                                            |
|                                                                         |
|    Problem: If containerd restarts, container becomes orphan!           |
|                                                                         |
|  WITH SHIM:                                                             |
|                                                                         |
|    containerd                                                           |
|        |                                                                |
|        +-- containerd-shim (persistent)                                 |
|                |                                                        |
|                +-- container process                                    |
|                                                                         |
|    Solution: Shim keeps container alive even if containerd restarts     |
|                                                                         |
|  SHIM RESPONSIBILITIES:                                                 |
|  * Keeps STDIN/STDOUT/STDERR open                                       |
|  * Reports container exit status                                        |
|  * Allows containerd to be upgraded without killing containers          |
|                                                                         |
+-------------------------------------------------------------------------+
```

RUNC
----

runc is the low-level container runtime:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RUNC: THE CONTAINER CREATOR                                            |
|                                                                         |
|  runc is a CLI tool for spawning and running containers                 |
|  according to the OCI (Open Container Initiative) specification.        |
|                                                                         |
|  WHAT RUNC DOES:                                                        |
|  1. Creates namespaces (process isolation)                              |
|  2. Sets up cgroups (resource limits)                                   |
|  3. Sets up filesystem (root fs, mounts)                                |
|  4. Applies security settings (capabilities, seccomp, AppArmor)         |
|  5. Starts the container process                                        |
|  6. EXITS (daemonless design)                                           |
|                                                                         |
|  PROCESS FLOW:                                                          |
|                                                                         |
|  containerd-shim -----> runc create -----> container running            |
|                              |                                          |
|                              +-- runc exits!                            |
|                                  (not a daemon)                         |
|                                                                         |
|  The container process is now child of containerd-shim, not runc.       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.4: WHAT HAPPENS WHEN YOU RUN A CONTAINER

### COMPLETE FLOW: docker run nginx

```
+-------------------------------------------------------------------------+
|                                                                         |
|  $ docker run -d nginx                                                  |
|                                                                         |
|  STEP 1: Docker Client                                                  |
|  -------------------------                                              |
|  * Parses command                                                       |
|  * Creates API request: POST /containers/create                         |
|  * Sends to daemon via /var/run/docker.sock                             |
|                                                                         |
|  STEP 2: Docker Daemon                                                  |
|  ---------------------                                                  |
|  * Receives API request                                                 |
|  * Checks if nginx image exists locally                                 |
|  * If not: pulls from Docker Hub                                        |
|  * Creates container config                                             |
|  * Calls containerd via gRPC                                            |
|                                                                         |
|  STEP 3: containerd                                                     |
|  ------------------                                                     |
|  * Receives create request                                              |
|  * Prepares container bundle (config + filesystem)                      |
|  * Starts containerd-shim                                               |
|                                                                         |
|  STEP 4: containerd-shim                                                |
|  -----------------------                                                |
|  * Forks itself (to become independent)                                 |
|  * Calls runc to create container                                       |
|                                                                         |
|  STEP 5: runc                                                           |
|  -----------                                                            |
|  * Creates namespaces (pid, net, mnt, uts, ipc)                         |
|  * Sets up cgroups                                                      |
|  * Changes root filesystem to container's rootfs                        |
|  * Executes nginx process                                               |
|  * EXITS (runc is not a daemon!)                                        |
|                                                                         |
|  STEP 6: Container Running                                              |
|  -------------------------                                              |
|  * nginx is now running                                                 |
|  * containerd-shim is parent process                                    |
|  * shim keeps STDIO open                                                |
|  * shim reports status to containerd                                    |
|                                                                         |
|  FINAL STATE:                                                           |
|                                                                         |
|  dockerd                                                                |
|     |                                                                   |
|     +-- containerd                                                      |
|            |                                                            |
|            +-- containerd-shim (PID 1234)                               |
|                    |                                                    |
|                    +-- nginx (PID 5678)                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.5: LINUX KERNEL FEATURES ENABLING CONTAINERS

### NAMESPACES: PROCESS ISOLATION

Namespaces provide isolation for system resources:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LINUX NAMESPACES USED BY DOCKER                                        |
|                                                                         |
|  PID Namespace                                                          |
|  -------------                                                          |
|  * Isolates process IDs                                                 |
|  * Container sees its own PID 1                                         |
|  * Can't see host or other container processes                          |
|                                                                         |
|  Network Namespace                                                      |
|  -----------------                                                      |
|  * Isolates network interfaces, IPs, ports                              |
|  * Container has own eth0, localhost                                    |
|  * Can bind to port 80 without conflicts                                |
|                                                                         |
|  Mount Namespace                                                        |
|  ---------------                                                        |
|  * Isolates filesystem mounts                                           |
|  * Container has own view of filesystem                                 |
|  * Can have different /etc, /var, etc.                                  |
|                                                                         |
|  UTS Namespace                                                          |
|  -------------                                                          |
|  * Isolates hostname and domain name                                    |
|  * Container can have own hostname                                      |
|                                                                         |
|  IPC Namespace                                                          |
|  -------------                                                          |
|  * Isolates inter-process communication                                 |
|  * Message queues, semaphores, shared memory                            |
|                                                                         |
|  User Namespace                                                         |
|  --------------                                                         |
|  * Isolates user and group IDs                                          |
|  * Root in container can be non-root on host                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CGROUPS: RESOURCE LIMITS

Control groups limit and account for resource usage:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CGROUPS RESOURCES CONTROLLED                                           |
|                                                                         |
|  CPU                                                                    |
|  ---                                                                    |
|  docker run --cpus=2 nginx          # Max 2 CPU cores                   |
|  docker run --cpu-shares=512 nginx  # Relative weight                   |
|                                                                         |
|  Memory                                                                 |
|  ------                                                                 |
|  docker run --memory=1g nginx       # Max 1GB RAM                       |
|  docker run --memory-swap=2g nginx  # Max 2GB RAM+swap                  |
|                                                                         |
|  Block I/O                                                              |
|  ---------                                                              |
|  docker run --device-read-bps=/dev/sda:1mb nginx                        |
|  docker run --device-write-bps=/dev/sda:1mb nginx                       |
|                                                                         |
|  Network (via iptables, not cgroups directly)                           |
|  ---------                                                              |
|  Can limit bandwidth through external tools                             |
|                                                                         |
|  PIDs                                                                   |
|  ----                                                                   |
|  docker run --pids-limit=100 nginx  # Max 100 processes                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 1.6: DOCKER STORAGE ARCHITECTURE

### IMAGE LAYERS AND UNION FILESYSTEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DOCKER IMAGE LAYERS                                                    |
|                                                                         |
|  Images are built in layers. Each layer is read-only.                   |
|                                                                         |
|  Dockerfile:                     Image Layers:                          |
|                                                                         |
|  FROM ubuntu:20.04    ----->    +-------------------+  Layer 1          |
|                                 |    Ubuntu base    |  (read-only)      |
|                                 +-------------------+                   |
|                                          |                              |
|  RUN apt-get update   ----->    +-------+-----------+  Layer 2          |
|                                 |  apt cache update |  (read-only)      |
|                                 +-------------------+                   |
|                                          |                              |
|  RUN apt-get install  ----->    +-------+-----------+  Layer 3          |
|      -y nginx                   |   nginx package   |  (read-only)      |
|                                 +-------------------+                   |
|                                          |                              |
|  COPY index.html /var ----->    +-------+-----------+  Layer 4          |
|                                 |   Your HTML file  |  (read-only)      |
|                                 +-------------------+                   |
|                                                                         |
|  When container runs:                                                   |
|                                                                         |
|                                 +-------------------+  Writable         |
|                                 |  Container Layer  |  (read-write)     |
|                                 |  (your changes)   |                   |
|                                 +-------------------+                   |
|                                          |                              |
|                                 +-------------------+                   |
|                                 |   Image Layers    |  (read-only)      |
|                                 +-------------------+                   |
|                                                                         |
|  BENEFITS:                                                              |
|  * Layers are shared between images (saves disk space)                  |
|  * Layers are cached (speeds up builds)                                 |
|  * Only differences are stored                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### STORAGE DRIVERS

Docker supports multiple storage drivers for the Union filesystem:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STORAGE DRIVERS                                                        |
|                                                                         |
|  overlay2 (Recommended)                                                 |
|  ----------------------                                                 |
|  * Default for modern Linux                                             |
|  * Best performance and stability                                       |
|  * Requires Linux kernel 4.0+                                           |
|                                                                         |
|  devicemapper                                                           |
|  ------------                                                           |
|  * Block-level storage                                                  |
|  * Good for CentOS/RHEL older versions                                  |
|  * More complex configuration                                           |
|                                                                         |
|  btrfs                                                                  |
|  -----                                                                  |
|  * Requires btrfs filesystem                                            |
|  * Native snapshot support                                              |
|                                                                         |
|  zfs                                                                    |
|  ---                                                                    |
|  * Requires ZFS filesystem                                              |
|  * Enterprise features                                                  |
|                                                                         |
|  CHECK YOUR DRIVER:                                                     |
|  docker info | grep "Storage Driver"                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DOCKER ARCHITECTURE - KEY TAKEAWAYS                                    |
|                                                                         |
|  COMPONENTS                                                             |
|  ----------                                                             |
|  * Docker Client: CLI tool, sends commands via REST API                 |
|  * Docker Daemon: Manages images, containers, networks, volumes         |
|  * containerd: Container lifecycle management                           |
|  * containerd-shim: Keeps containers running independently              |
|  * runc: Actually creates and runs containers                           |
|                                                                         |
|  LINUX FEATURES                                                         |
|  --------------                                                         |
|  * Namespaces: Process isolation (PID, network, mount, etc.)            |
|  * Cgroups: Resource limits (CPU, memory, I/O)                          |
|  * Union FS: Layered filesystem for images                              |
|                                                                         |
|  KEY INSIGHTS                                                           |
|  ------------                                                           |
|  * Docker daemon restart doesn't kill containers (thanks to shim)       |
|  * runc exits after creating container (daemonless)                     |
|  * Image layers are shared and cached                                   |
|  * Containers share the host kernel (not VMs!)                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 1

