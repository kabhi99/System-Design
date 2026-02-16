# CHAPTER 2: IMAGES AND CONTAINERS
*The Two Fundamental Docker Concepts*

Understanding the difference between images and containers is fundamental to
mastering Docker. This chapter provides a deep dive into both concepts.

## SECTION 2.1: IMAGES vs CONTAINERS - THE FUNDAMENTAL DIFFERENCE

### THE BLUEPRINT ANALOGY

Think of Docker images and containers like a house blueprint and actual houses:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IMAGE vs CONTAINER                                                     |
|                                                                         |
|                                                                         |
|  IMAGE (Blueprint)                CONTAINER (House)                     |
|  ==================               ================                      |
|                                                                         |
|  +-------------------+           +-------------------+                  |
|  |                   |           |                   |                  |
|  |  +-------------+  |           |  +=============+  |                  |
|  |  | nginx:1.21  |  |  ----->   |  | Container 1 |  |                  |
|  |  |             |  |  create   |  | (web-1)     |  |                  |
|  |  | - nginx     |  |           |  +=============+  |                  |
|  |  | - config    |  |           |                   |                  |
|  |  | - html      |  |           |  +=============+  |                  |
|  |  +-------------+  |  ----->   |  | Container 2 |  |                  |
|  |                   |  create   |  | (web-2)     |  |                  |
|  |  READ-ONLY        |           |  +=============+  |                  |
|  |  Template         |           |                   |                  |
|  |                   |           |  +=============+  |                  |
|  |                   |  ----->   |  | Container 3 |  |                  |
|  |                   |  create   |  | (web-3)     |  |                  |
|  |                   |           |  +=============+  |                  |
|  |                   |           |                   |                  |
|  |                   |           |  RUNNING INSTANCES|                  |
|  |                   |           |  (read-write)     |                  |
|  +-------------------+           +-------------------+                  |
|                                                                         |
|  KEY DIFFERENCES:                                                       |
|                                                                         |
|  IMAGE:                          CONTAINER:                             |
|  * Read-only                     * Read-write layer on top              |
|  * Template/blueprint            * Running instance                     |
|  * Stored in registry            * Runs on a host                       |
|  * Shared between containers     * Isolated from others                 |
|  * Has layers                    * Has runtime state (PIDs, network)    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### FORMAL DEFINITIONS

IMAGE:
An image is a read-only template containing a set of instructions for
creating a Docker container. It includes the application code, runtime,
libraries, environment variables, and configuration files needed to run
an application.

CONTAINER:
A container is a runnable instance of an image. It's a lightweight,
isolated environment that shares the host kernel but has its own
filesystem, networking, and process space.

## SECTION 2.2: DOCKER IMAGES IN DEPTH

### IMAGE STRUCTURE

Every Docker image consists of:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IMAGE STRUCTURE                                                        |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                       Image Manifest                             |   |
|  |  * List of layers                                                |   |
|  |  * Platform info (linux/amd64)                                   |   |
|  |  * Configuration reference                                       |   |
|  +------------------------------------------------------------------+   |
|                              |                                          |
|                              v                                          |
|  +------------------------------------------------------------------+   |
|  |                       Image Config                               |   |
|  |  * Default environment variables                                 |   |
|  |  * Default command (CMD)                                         |   |
|  |  * Default entrypoint (ENTRYPOINT)                               |   |
|  |  * Exposed ports                                                 |   |
|  |  * Working directory                                             |   |
|  |  * User to run as                                                |   |
|  +------------------------------------------------------------------+   |
|                              |                                          |
|                              v                                          |
|  +------------------------------------------------------------------+   |
|  |                       Layers (Filesystem)                        |   |
|  |                                                                  |   |
|  |  +-----------------------------------------------------------+   |   |
|  |  |  Layer 4: COPY app.js /app/  (your application)           |   |   |
|  |  +-----------------------------------------------------------+   |   |
|  |  |  Layer 3: RUN npm install    (dependencies)               |   |   |
|  |  +-----------------------------------------------------------+   |   |
|  |  |  Layer 2: RUN apt-get update (system packages)            |   |   |
|  |  +-----------------------------------------------------------+   |   |
|  |  |  Layer 1: FROM ubuntu:20.04  (base OS)                    |   |   |
|  |  +-----------------------------------------------------------+   |   |
|  |                                                                  |   |
|  |  Each layer is a tarball of filesystem changes                   |   |
|  |  Layers are identified by SHA256 hash                            |   |
|  |  Layers are reused across images                                 |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### IMAGE IDENTIFICATION

Images can be identified in several ways:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IMAGE NAMING CONVENTION                                                |
|                                                                         |
|  Full format: [registry/][repository/]name[:tag][@digest]               |
|                                                                         |
|  EXAMPLES:                                                              |
|                                                                         |
|  nginx                                                                  |
|  -----                                                                  |
|  * Registry: docker.io (default)                                        |
|  * Repository: library (official images)                                |
|  * Name: nginx                                                          |
|  * Tag: latest (default)                                                |
|  * Actual: docker.io/library/nginx:latest                               |
|                                                                         |
|  nginx:1.21                                                             |
|  ----------                                                             |
|  * Explicit tag                                                         |
|  * Actual: docker.io/library/nginx:1.21                                 |
|                                                                         |
|  mycompany/myapp:v2.0.1                                                 |
|  ---------------------                                                  |
|  * User/org repository                                                  |
|  * Custom application                                                   |
|                                                                         |
|  gcr.io/google-samples/hello-app:1.0                                    |
|  -----------------------------------                                    |
|  * Google Container Registry                                            |
|  * Full path specified                                                  |
|                                                                         |
|  nginx@sha256:abc123...                                                 |
|  ---------------------                                                  |
|  * Digest reference                                                     |
|  * Immutable (always same image)                                        |
|  * Used for security/reproducibility                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### IMAGE COMMANDS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMMON IMAGE COMMANDS                                                  |
|                                                                         |
|  LISTING IMAGES                                                         |
|  --------------                                                         |
|  docker images                    # List all local images               |
|  docker images -a                 # Include intermediate layers         |
|  docker images nginx              # Filter by name                      |
|  docker images --format "{{.ID}} {{.Size}}"  # Custom format            |
|                                                                         |
|  PULLING IMAGES                                                         |
|  --------------                                                         |
|  docker pull nginx                # Pull latest                         |
|  docker pull nginx:1.21           # Pull specific tag                   |
|  docker pull nginx@sha256:...     # Pull by digest                      |
|  docker pull --all-tags nginx     # Pull all tags                       |
|                                                                         |
|  INSPECTING IMAGES                                                      |
|  -----------------                                                      |
|  docker inspect nginx             # Full JSON details                   |
|  docker history nginx             # Show layer history                  |
|  docker image inspect nginx --format '{{.Config.Cmd}}'                  |
|                                                                         |
|  REMOVING IMAGES                                                        |
|  ---------------                                                        |
|  docker rmi nginx                 # Remove image                        |
|  docker rmi -f nginx              # Force remove (even if used)         |
|  docker image prune               # Remove unused images                |
|  docker image prune -a            # Remove all unused                   |
|                                                                         |
|  TAGGING IMAGES                                                         |
|  --------------                                                         |
|  docker tag nginx:latest myapp:v1.0                                     |
|  docker tag nginx gcr.io/myproject/nginx:v1                             |
|                                                                         |
|  PUSHING IMAGES                                                         |
|  --------------                                                         |
|  docker push mycompany/myapp:v1.0                                       |
|  docker push gcr.io/myproject/nginx:v1                                  |
|                                                                         |
|  SAVING/LOADING IMAGES                                                  |
|  ---------------------                                                  |
|  docker save nginx > nginx.tar    # Export to file                      |
|  docker load < nginx.tar          # Import from file                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### LAYER CACHING AND SHARING

Layers are shared between images, saving disk space and network bandwidth:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LAYER SHARING EXAMPLE                                                  |
|                                                                         |
|  Image A (Python app)              Image B (Python app)                 |
|  +---------------------+          +---------------------+               |
|  | Layer 4: COPY app   |          | Layer 4: COPY app   |               |
|  | (unique to A)       |          | (unique to B)       |               |
|  +---------------------+          +---------------------+               |
|  | Layer 3: pip install|<-------->| Layer 3: pip install|               |
|  | (shared!)           |  SAME    | (shared!)           |               |
|  +---------------------+  LAYER   +---------------------+               |
|  | Layer 2: Python     |<-------->| Layer 2: Python     |               |
|  | (shared!)           |          | (shared!)           |               |
|  +---------------------+          +---------------------+               |
|  | Layer 1: Ubuntu     |<-------->| Layer 1: Ubuntu     |               |
|  | (shared!)           |          | (shared!)           |               |
|  +---------------------+          +---------------------+               |
|                                                                         |
|  DISK USAGE:                                                            |
|  * Without sharing: 400MB + 400MB = 800MB                               |
|  * With sharing: 400MB + 50MB (unique part) = 450MB                     |
|                                                                         |
|  NETWORK USAGE (pulling):                                               |
|  * Pull Image A: Downloads all layers                                   |
|  * Pull Image B: Only downloads unique Layer 4!                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.3: DOCKER CONTAINERS IN DEPTH

### CONTAINER LIFECYCLE

A container goes through several states:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONTAINER LIFECYCLE                                                    |
|                                                                         |
|                    docker create                                        |
|                         |                                               |
|                         v                                               |
|  +---------+      +---------+      +---------+                          |
|  |         |      |         |      |         |                          |
|  | (none)  |----->| Created |----->| Running |<------+                  |
|  |         |      |         |      |         |       |                  |
|  +---------+      +----+----+      +----+----+       |                  |
|                        |                |            |                  |
|               docker rm|       docker   |docker start|                  |
|                        |       stop/kill|            |                  |
|                        |                v            |                  |
|                        |          +---------+       |                   |
|                        |          |         |       |                   |
|                        +--------->| Stopped |-------+                   |
|                                   | (Exited)|                           |
|                                   |         |                           |
|                                   +----+----+                           |
|                                        |                                |
|                               docker rm|                                |
|                                        v                                |
|                                   +---------+                           |
|                                   | Removed |                           |
|                                   +---------+                           |
|                                                                         |
|  STATES:                                                                |
|  * Created: Container exists but never started                          |
|  * Running: Container is executing                                      |
|  * Paused: Container processes are suspended (SIGSTOP)                  |
|  * Stopped/Exited: Container has stopped (exit code stored)             |
|  * Removed: Container is deleted                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CONTAINER COMMANDS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RUNNING CONTAINERS                                                     |
|                                                                         |
|  docker run nginx                  # Run in foreground                  |
|  docker run -d nginx               # Run in background (detached)       |
|  docker run -it ubuntu bash        # Interactive with terminal          |
|  docker run --name web nginx       # Assign a name                      |
|  docker run --rm nginx             # Remove when stopped                |
|  docker run -p 8080:80 nginx       # Publish port                       |
|  docker run -v /data:/data nginx   # Mount volume                       |
|  docker run -e KEY=val nginx       # Set environment variable           |
|  docker run --network mynet nginx  # Connect to network                 |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  MANAGING CONTAINERS                                                    |
|                                                                         |
|  docker ps                         # List running containers            |
|  docker ps -a                      # List all containers                |
|  docker start <container>          # Start stopped container            |
|  docker stop <container>           # Stop running container             |
|  docker restart <container>        # Restart container                  |
|  docker kill <container>           # Force stop (SIGKILL)               |
|  docker pause <container>          # Pause container                    |
|  docker unpause <container>        # Unpause container                  |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  INTERACTING WITH CONTAINERS                                            |
|                                                                         |
|  docker exec -it <container> bash  # Execute command in container       |
|  docker attach <container>         # Attach to container STDIO          |
|  docker logs <container>           # View logs                          |
|  docker logs -f <container>        # Follow logs                        |
|  docker logs --tail 100 <c>        # Last 100 lines                     |
|  docker cp <c>:/path ./local       # Copy from container                |
|  docker cp ./local <c>:/path       # Copy to container                  |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  INSPECTING CONTAINERS                                                  |
|                                                                         |
|  docker inspect <container>        # Full JSON details                  |
|  docker stats                      # Live resource usage                |
|  docker top <container>            # Show processes                     |
|  docker diff <container>           # Show filesystem changes            |
|  docker port <container>           # Show port mappings                 |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  REMOVING CONTAINERS                                                    |
|                                                                         |
|  docker rm <container>             # Remove stopped container           |
|  docker rm -f <container>          # Force remove (even running)        |
|  docker container prune            # Remove all stopped                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CONTAINER FILESYSTEM

When a container runs, it gets a read-write layer on top of the image:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONTAINER FILESYSTEM (Union FS)                                        |
|                                                                         |
|  +--------------------------------------------------------------------+ |
|  |                     Container Layer (R/W)                          | |
|  |                                                                    | |
|  |  Any changes you make go here:                                     | |
|  |  * New files created                                               | |
|  |  * Files modified (copy-on-write)                                  | |
|  |  * Files deleted (marked as deleted)                               | |
|  |                                                                    | |
|  |    EPHEMERAL - Lost when container is removed!                     | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|  |                     Image Layers (R/O)                             | |
|  |                                                                    | |
|  |  +---------------------------------------------------------------+ | |
|  |  |  Layer N: Application files                                   | | |
|  |  +---------------------------------------------------------------+ | |
|  |  |  Layer 2: Dependencies                                        | | |
|  |  +---------------------------------------------------------------+ | |
|  |  |  Layer 1: Base OS                                             | | |
|  |  +---------------------------------------------------------------+ | |
|  |                                                                    | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
|  COPY-ON-WRITE (CoW):                                                   |
|  ----------------------                                                 |
|  When container modifies a file from image layer:                       |
|  1. File is COPIED to container's R/W layer                             |
|  2. Modifications happen on the copy                                    |
|  3. Original file in image layer untouched                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.4: DOCKER RUN IN DEPTH

### UNDERSTANDING docker run

docker run is the most important command. Let's break it down:

```bash
docker run [OPTIONS] IMAGE [COMMAND] [ARG...]      

WHAT HAPPENS:                                      
1. If image not found locally, pulls from registry 
2. Creates a new container                         
3. Allocates filesystem and mounts read-write layer
4. Allocates network interface and IP              
5. Executes specified command (or default CMD)     
```

### COMMON OPTIONS EXPLAINED

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ESSENTIAL docker run OPTIONS                                           |
|                                                                         |
|  -d, --detach                                                           |
|  --------------                                                         |
|  Run container in background                                            |
|  docker run -d nginx                                                    |
|                                                                         |
|  -i, --interactive                                                      |
|  -----------------                                                      |
|  Keep STDIN open                                                        |
|  Usually combined with -t                                               |
|                                                                         |
|  -t, --tty                                                              |
|  ----------                                                             |
|  Allocate pseudo-TTY                                                    |
|  Enables terminal features (colors, ctrl+c, etc.)                       |
|  docker run -it ubuntu bash                                             |
|                                                                         |
|  --name                                                                 |
|  ------                                                                 |
|  Assign name to container                                               |
|  docker run --name webserver nginx                                      |
|                                                                         |
|  --rm                                                                   |
|  ----                                                                   |
|  Remove container when it exits                                         |
|  Useful for one-off commands                                            |
|  docker run --rm -it alpine sh                                          |
|                                                                         |
|  -p, --publish                                                          |
|  ---------------                                                        |
|  Map port from host to container                                        |
|  Format: hostPort:containerPort                                         |
|  docker run -p 8080:80 nginx         # host:8080 > container:80         |
|  docker run -p 80 nginx              # Random host port > 80            |
|  docker run -p 127.0.0.1:8080:80     # Only localhost access            |
|                                                                         |
|  -v, --volume                                                           |
|  -------------                                                          |
|  Mount volume or bind mount                                             |
|  docker run -v myvolume:/data nginx  # Named volume                     |
|  docker run -v /host/path:/container/path nginx  # Bind mount           |
|                                                                         |
|  -e, --env                                                              |
|  ----------                                                             |
|  Set environment variable                                               |
|  docker run -e MYSQL_ROOT_PASSWORD=secret mysql                         |
|  docker run --env-file .env nginx                                       |
|                                                                         |
|  --network                                                              |
|  ---------                                                              |
|  Connect to a network                                                   |
|  docker run --network mybridge nginx                                    |
|                                                                         |
|  --restart                                                              |
|  ---------                                                              |
|  Restart policy                                                         |
|  docker run --restart=always nginx   # Always restart                   |
|  docker run --restart=unless-stopped nginx                              |
|  docker run --restart=on-failure:5 nginx  # Max 5 retries               |
|                                                                         |
|  --memory, --cpus                                                       |
|  -----------------                                                      |
|  Resource limits                                                        |
|  docker run --memory=512m --cpus=1 nginx                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2.5: PRACTICAL EXAMPLES

### EXAMPLE 1: Running a Web Server

```bash
# Run nginx, map port 8080 to 80, detached    
docker run -d -p 8080:80 --name my-nginx nginx

# Access at http://localhost:8080             

# View logs                                   
docker logs my-nginx                          

# Stop and remove                             
docker stop my-nginx                          
docker rm my-nginx                            
```

### EXAMPLE 2: Interactive Development

```bash
# Start Python environment interactively
docker run -it --rm python:3.9 python   

# Or get a shell                        
docker run -it --rm python:3.9 bash     
```

### EXAMPLE 3: Database with Persistence

```bash
# Create volume                              
docker volume create postgres-data           

# Run PostgreSQL with persistent storage     
docker run -d \                              
  --name my-postgres \                       
  -e POSTGRES_PASSWORD=secret \              
  -v postgres-data:/var/lib/postgresql/data \
  -p 5432:5432 \                             
  postgres:14                                
```

### EXAMPLE 4: One-off Commands

```bash
# Run a command and remove container                   
docker run --rm alpine cat /etc/os-release             

# Run tests in a container                             
docker run --rm -v $(pwd):/app -w /app node:16 npm test
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IMAGES AND CONTAINERS - KEY TAKEAWAYS                                  |
|                                                                         |
|  IMAGES                                                                 |
|  ------                                                                 |
|  * Read-only templates                                                  |
|  * Built from layers                                                    |
|  * Layers are shared and cached                                         |
|  * Identified by name:tag or digest                                     |
|  * Stored in registries                                                 |
|                                                                         |
|  CONTAINERS                                                             |
|  ----------                                                             |
|  * Running instances of images                                          |
|  * Have read-write layer (ephemeral!)                                   |
|  * Have lifecycle (created, running, stopped, removed)                  |
|  * Isolated processes with own network, filesystem                      |
|                                                                         |
|  ESSENTIAL COMMANDS                                                     |
|  -----------------                                                      |
|  docker pull/push         # Transfer images                             |
|  docker run               # Create and start container                  |
|  docker ps                # List containers                             |
|  docker exec              # Run command in container                    |
|  docker logs              # View container output                       |
|  docker stop/start/rm     # Manage container lifecycle                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 2

