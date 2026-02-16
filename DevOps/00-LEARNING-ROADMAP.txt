================================================================================
              DOCKER & KUBERNETES LEARNING ROADMAP
              A Complete Guide from Zero to Production
================================================================================

This roadmap provides a structured learning path for mastering containerization
and orchestration. Follow the sequence for optimal understanding—each section
builds on previous knowledge.

ESTIMATED TOTAL TIME: 8-12 weeks (2-3 hours/day)


================================================================================
                         LEARNING PATH OVERVIEW
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │                    THE COMPLETE LEARNING JOURNEY                        │
    │                                                                         │
    │  PHASE 1: FOUNDATIONS (Week 1-2)                                       │
    │  ════════════════════════════════                                       │
    │  ├── Linux Fundamentals (if needed)                                    │
    │  ├── Virtualization vs Containerization                                │
    │  └── Why Containers? The Problem They Solve                            │
    │                                                                         │
    │                          ▼                                              │
    │                                                                         │
    │  PHASE 2: DOCKER FUNDAMENTALS (Week 2-4)                               │
    │  ════════════════════════════════════════                               │
    │  ├── Docker Architecture                                               │
    │  ├── Images & Containers                                               │
    │  ├── Dockerfile & Building Images                                      │
    │  ├── Docker Volumes & Persistence                                      │
    │  ├── Docker Networking (Basic)                                         │
    │  └── Docker Compose                                                    │
    │                                                                         │
    │                          ▼                                              │
    │                                                                         │
    │  PHASE 3: DOCKER ADVANCED (Week 4-5)                                   │
    │  ════════════════════════════════════                                   │
    │  ├── Multi-Stage Builds                                                │
    │  ├── Image Optimization                                                │
    │  ├── Security Best Practices                                           │
    │  ├── Docker Networking (Advanced)                                      │
    │  ├── Docker in CI/CD                                                   │
    │  └── Docker Registry & Distribution                                    │
    │                                                                         │
    │                          ▼                                              │
    │                                                                         │
    │  PHASE 4: KUBERNETES FUNDAMENTALS (Week 5-7)                           │
    │  ════════════════════════════════════════════                           │
    │  ├── Why Kubernetes? The Orchestration Problem                         │
    │  ├── Kubernetes Architecture                                           │
    │  ├── Pods, ReplicaSets, Deployments                                    │
    │  ├── Services & Service Discovery                                      │
    │  ├── ConfigMaps & Secrets                                              │
    │  └── Namespaces & Resource Quotas                                      │
    │                                                                         │
    │                          ▼                                              │
    │                                                                         │
    │  PHASE 5: KUBERNETES INTERMEDIATE (Week 7-9)                           │
    │  ════════════════════════════════════════════                           │
    │  ├── Storage: PV, PVC, StorageClasses                                  │
    │  ├── Ingress & External Access                                         │
    │  ├── StatefulSets & DaemonSets                                         │
    │  ├── Jobs & CronJobs                                                   │
    │  ├── RBAC & Security                                                   │
    │  └── Helm Package Manager                                              │
    │                                                                         │
    │                          ▼                                              │
    │                                                                         │
    │  PHASE 6: KUBERNETES ADVANCED (Week 9-11)                              │
    │  ═════════════════════════════════════════                              │
    │  ├── Networking Deep Dive (CNI, Network Policies)                      │
    │  ├── Custom Resource Definitions (CRDs)                                │
    │  ├── Operators                                                         │
    │  ├── Auto-scaling (HPA, VPA, Cluster Autoscaler)                      │
    │  ├── Multi-cluster & Federation                                        │
    │  └── Service Mesh (Istio/Linkerd)                                      │
    │                                                                         │
    │                          ▼                                              │
    │                                                                         │
    │  PHASE 7: PRODUCTION OPERATIONS (Week 11-12)                           │
    │  ════════════════════════════════════════════                           │
    │  ├── Monitoring & Observability                                        │
    │  ├── Logging & Tracing                                                 │
    │  ├── CI/CD with Kubernetes                                             │
    │  ├── GitOps (ArgoCD, Flux)                                             │
    │  ├── Disaster Recovery                                                 │
    │  └── Cost Optimization                                                 │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
                    PHASE 1: FOUNDATIONS (Week 1-2)
================================================================================

PREREQUISITES CHECK
───────────────────

Before starting, ensure you're comfortable with:

    □ Linux command line basics
      • Navigation (cd, ls, pwd)
      • File operations (cp, mv, rm, cat, less)
      • Process management (ps, top, kill)
      • Text editing (vim/nano)
      • Package management (apt/yum)

    □ Basic networking concepts
      • IP addresses, ports, protocols
      • HTTP/HTTPS basics
      • DNS fundamentals

    □ YAML syntax
      • Indentation, lists, dictionaries
      • Multi-line strings

If you need to brush up, spend the first week on Linux fundamentals.


UNDERSTANDING THE PROBLEM
─────────────────────────

    THE CLASSIC DEPLOYMENT PROBLEM:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  Developer's Machine                Production Server                  │
    │  ┌──────────────────┐              ┌──────────────────┐               │
    │  │                  │              │                  │               │
    │  │  App works       │  ────────►   │  App crashes!    │               │
    │  │  perfectly!      │              │                  │               │
    │  │                  │              │  "But it works   │               │
    │  │  Python 3.9      │              │   on my machine!"│               │
    │  │  Ubuntu 20.04    │              │                  │               │
    │  │  libpq 12        │              │  Python 3.7      │               │
    │  │                  │              │  CentOS 7        │               │
    │  └──────────────────┘              │  libpq 10        │               │
    │                                    └──────────────────┘               │
    │                                                                         │
    │  THE PROBLEM: Environment inconsistency                               │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

    THE CONTAINER SOLUTION:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  Developer's Machine                Production Server                  │
    │  ┌──────────────────┐              ┌──────────────────┐               │
    │  │  ┌────────────┐  │              │  ┌────────────┐  │               │
    │  │  │ Container  │  │  ────────►   │  │ Container  │  │               │
    │  │  │            │  │   Same       │  │            │  │               │
    │  │  │ App        │  │   Image!     │  │ App        │  │               │
    │  │  │ Python 3.9 │  │              │  │ Python 3.9 │  │               │
    │  │  │ All deps   │  │              │  │ All deps   │  │               │
    │  │  └────────────┘  │              │  └────────────┘  │               │
    │  │                  │              │                  │               │
    │  │  Host OS         │              │  Host OS         │               │
    │  └──────────────────┘              └──────────────────┘               │
    │                                                                         │
    │  THE SOLUTION: Package everything together, run anywhere              │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


VIRTUAL MACHINES vs CONTAINERS
──────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  VIRTUAL MACHINES                      CONTAINERS                      │
    │                                                                         │
    │  ┌─────────┐ ┌─────────┐ ┌─────────┐  ┌─────────┐ ┌─────────┐ ┌─────┐ │
    │  │  App A  │ │  App B  │ │  App C  │  │  App A  │ │  App B  │ │App C│ │
    │  ├─────────┤ ├─────────┤ ├─────────┤  ├─────────┤ ├─────────┤ ├─────┤ │
    │  │ Bins/   │ │ Bins/   │ │ Bins/   │  │ Bins/   │ │ Bins/   │ │Bins/│ │
    │  │ Libs    │ │ Libs    │ │ Libs    │  │ Libs    │ │ Libs    │ │Libs │ │
    │  ├─────────┤ ├─────────┤ ├─────────┤  └────┬────┘ └────┬────┘ └──┬──┘ │
    │  │ Guest   │ │ Guest   │ │ Guest   │       │           │         │    │
    │  │   OS    │ │   OS    │ │   OS    │       └───────────┼─────────┘    │
    │  │ (2GB+)  │ │ (2GB+)  │ │ (2GB+)  │                   │              │
    │  └────┬────┘ └────┬────┘ └────┬────┘           ┌───────┴───────┐      │
    │       │           │           │                │  Container    │      │
    │       └───────────┼───────────┘                │  Runtime      │      │
    │                   │                            │  (Docker)     │      │
    │           ┌───────┴───────┐                    └───────┬───────┘      │
    │           │  Hypervisor   │                            │              │
    │           │ (VMware/KVM)  │                    ┌───────┴───────┐      │
    │           └───────┬───────┘                    │   Host OS     │      │
    │                   │                            │ (Shared Kernel)│      │
    │           ┌───────┴───────┐                    └───────┬───────┘      │
    │           │   Host OS     │                            │              │
    │           └───────┬───────┘                    ┌───────┴───────┐      │
    │                   │                            │   Hardware    │      │
    │           ┌───────┴───────┐                    └───────────────┘      │
    │           │   Hardware    │                                          │
    │           └───────────────┘                                          │
    │                                                                         │
    │  VMs: Heavy (GB), Slow boot (mins)    Containers: Light (MB), Fast   │
    │       Strong isolation                            (seconds)           │
    │                                                   Process isolation   │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


LEARNING GOALS FOR PHASE 1
──────────────────────────

By the end of Phase 1, you should be able to:

    ✓ Explain why containers exist and what problems they solve
    ✓ Describe the difference between VMs and containers
    ✓ Understand that containers share the host kernel
    ✓ Know the basic Linux features enabling containers (namespaces, cgroups)


================================================================================
                    PHASE 2: DOCKER FUNDAMENTALS (Week 2-4)
================================================================================

LEARNING SEQUENCE
─────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  DOCKER FUNDAMENTALS - CHAPTER ORDER                                   │
    │                                                                         │
    │  READ IN THIS ORDER:                                                   │
    │                                                                         │
    │  1. Docker-Complete/01-Docker-Architecture.txt                        │
    │     • Docker Engine components                                        │
    │     • Client-Server architecture                                      │
    │     • containerd and runc                                             │
    │                                                                         │
    │  2. Docker-Complete/02-Images-And-Containers.txt                      │
    │     • What are images and containers                                  │
    │     • Image layers and Union FS                                       │
    │     • Container lifecycle                                             │
    │     • Basic commands (run, start, stop, rm)                          │
    │                                                                         │
    │  3. Docker-Complete/03-Dockerfile-Deep-Dive.txt                       │
    │     • Dockerfile syntax                                               │
    │     • All instructions explained                                      │
    │     • Build context                                                   │
    │     • Best practices                                                  │
    │                                                                         │
    │  4. Docker-Complete/04-Data-Persistence.txt                           │
    │     • Volumes vs Bind mounts                                          │
    │     • tmpfs mounts                                                    │
    │     • Volume drivers                                                  │
    │                                                                         │
    │  5. Docker-Networking/01-Linux-Networking-Foundations.txt             │
    │     (Already created - covers networking fundamentals)                │
    │                                                                         │
    │  6. Docker-Complete/05-Docker-Compose.txt                             │
    │     • Multi-container applications                                    │
    │     • docker-compose.yml syntax                                       │
    │     • Service dependencies                                            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


HANDS-ON EXERCISES FOR PHASE 2
──────────────────────────────

    EXERCISE 1: Hello Docker
    ────────────────────────
    docker run hello-world
    docker run -it ubuntu bash
    docker ps -a
    docker images

    EXERCISE 2: Build Your First Image
    ───────────────────────────────────
    Create a simple web app and Dockerfile
    Build with: docker build -t myapp .
    Run with: docker run -p 8080:80 myapp

    EXERCISE 3: Data Persistence
    ────────────────────────────
    Run MySQL with named volume
    Delete container, recreate
    Verify data persists

    EXERCISE 4: Docker Compose
    ──────────────────────────
    Create a compose file for:
    - Web app
    - Database
    - Redis cache
    Run with: docker-compose up


================================================================================
                    PHASE 3: DOCKER ADVANCED (Week 4-5)
================================================================================

LEARNING SEQUENCE
─────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  DOCKER ADVANCED - CHAPTER ORDER                                       │
    │                                                                         │
    │  7. Docker-Complete/06-Multi-Stage-Builds.txt                         │
    │     • Build vs Runtime dependencies                                   │
    │     • Reducing image size                                             │
    │     • Production-optimized images                                     │
    │                                                                         │
    │  8. Docker-Complete/07-Security-Best-Practices.txt                    │
    │     • Running as non-root                                             │
    │     • Image scanning                                                  │
    │     • Secrets management                                              │
    │     • Read-only containers                                            │
    │                                                                         │
    │  9. Docker-Networking/02-Docker-Networking-Internals.txt              │
    │     Docker-Networking/03-Advanced-Docker-Networking.txt               │
    │     (Already created)                                                  │
    │                                                                         │
    │  10. Docker-Complete/08-Registry-And-Distribution.txt                 │
    │      • Docker Hub                                                     │
    │      • Private registries                                             │
    │      • Image tagging strategies                                       │
    │                                                                         │
    │  11. Docker-Complete/09-Docker-In-CI-CD.txt                           │
    │      • Building in pipelines                                          │
    │      • Testing containers                                             │
    │      • Push to registry                                               │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


LEARNING GOALS FOR PHASE 2-3
────────────────────────────

By the end of Docker phases, you should be able to:

    ✓ Explain Docker architecture (client, daemon, containerd, runc)
    ✓ Build optimized Docker images with multi-stage builds
    ✓ Write Dockerfiles following best practices
    ✓ Use volumes for data persistence
    ✓ Create multi-container applications with Docker Compose
    ✓ Understand Docker networking modes
    ✓ Implement security best practices
    ✓ Push/pull images from registries


================================================================================
                PHASE 4: KUBERNETES FUNDAMENTALS (Week 5-7)
================================================================================

WHY KUBERNETES AFTER DOCKER?
────────────────────────────

Docker solves: "How do I package and run a single application?"
Kubernetes solves: "How do I run 100+ containers across 50+ servers?"

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  THE ORCHESTRATION PROBLEM                                             │
    │                                                                         │
    │  You have:                                                             │
    │  • 50 microservices                                                   │
    │  • 20 servers                                                         │
    │  • Need high availability                                             │
    │  • Need to scale based on load                                        │
    │  • Need to handle failures                                            │
    │                                                                         │
    │  WITHOUT ORCHESTRATION:                                                │
    │  ┌─────────┐  "Which server has capacity?"                            │
    │  │  You    │  "Server 5 crashed, restart containers manually"        │
    │  │  (SRE)  │  "Traffic spike! Quick, add more containers!"           │
    │  │  😰     │  "Wait, which version is running where?"                │
    │  └─────────┘                                                           │
    │                                                                         │
    │  WITH KUBERNETES:                                                      │
    │  ┌─────────┐                      ┌───────────────────────┐           │
    │  │  You    │  "I want 5 replicas" │     KUBERNETES        │           │
    │  │  (SRE)  │  ─────────────────►  │                       │           │
    │  │  😌     │                      │  • Finds capacity     │           │
    │  └─────────┘                      │  • Schedules pods     │           │
    │                                   │  • Restarts failures  │           │
    │      Declarative                  │  • Scales as needed   │           │
    │      "Desired State"              │  • Load balances      │           │
    │                                   └───────────────────────┘           │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


LEARNING SEQUENCE
─────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  KUBERNETES FUNDAMENTALS - CHAPTER ORDER                               │
    │                                                                         │
    │  1. Kubernetes-Complete/01-Architecture.txt                           │
    │     • Control plane components                                        │
    │     • Worker node components                                          │
    │     • How they communicate                                            │
    │                                                                         │
    │  2. Kubernetes-Complete/02-Pods.txt                                   │
    │     • What is a Pod                                                   │
    │     • Pod lifecycle                                                   │
    │     • Multi-container pods                                            │
    │     • Pod design patterns                                             │
    │                                                                         │
    │  3. Kubernetes-Complete/03-Workloads.txt                              │
    │     • ReplicaSets                                                     │
    │     • Deployments                                                     │
    │     • Rolling updates & Rollbacks                                     │
    │                                                                         │
    │  4. Kubernetes-Complete/04-Services.txt                               │
    │     • Service types                                                   │
    │     • Service discovery                                               │
    │     • DNS in Kubernetes                                               │
    │                                                                         │
    │  5. Kubernetes-Complete/05-Configuration.txt                          │
    │     • ConfigMaps                                                      │
    │     • Secrets                                                         │
    │     • Environment variables                                           │
    │                                                                         │
    │  6. Kubernetes-Complete/06-Namespaces.txt                             │
    │     • Namespace isolation                                             │
    │     • Resource quotas                                                 │
    │     • Limit ranges                                                    │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


HANDS-ON EXERCISES FOR PHASE 4
──────────────────────────────

    SETUP: Install minikube or kind for local practice
    ───────────────────────────────────────────────────
    minikube start
    # or
    kind create cluster

    EXERCISE 1: Deploy Your First Application
    ──────────────────────────────────────────
    kubectl create deployment nginx --image=nginx
    kubectl expose deployment nginx --port=80 --type=NodePort
    kubectl get all

    EXERCISE 2: Scale and Update
    ────────────────────────────
    kubectl scale deployment nginx --replicas=5
    kubectl set image deployment/nginx nginx=nginx:1.21
    kubectl rollout status deployment/nginx
    kubectl rollout undo deployment/nginx

    EXERCISE 3: ConfigMaps and Secrets
    ──────────────────────────────────
    Create ConfigMap with app settings
    Create Secret for database password
    Mount them in a pod


================================================================================
              PHASE 5: KUBERNETES INTERMEDIATE (Week 7-9)
================================================================================

LEARNING SEQUENCE
─────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  KUBERNETES INTERMEDIATE - CHAPTER ORDER                               │
    │                                                                         │
    │  7. Kubernetes-Complete/07-Storage.txt                                │
    │     • Persistent Volumes                                              │
    │     • Persistent Volume Claims                                        │
    │     • Storage Classes                                                 │
    │     • Dynamic provisioning                                            │
    │                                                                         │
    │  8. Kubernetes-Complete/08-Ingress.txt                                │
    │     • Ingress resources                                               │
    │     • Ingress controllers                                             │
    │     • TLS termination                                                 │
    │     (Also see: Kubernetes-Networking/04-Ingress-And-External-Access) │
    │                                                                         │
    │  9. Kubernetes-Complete/09-StatefulSets.txt                           │
    │     • Stateful applications                                           │
    │     • Stable network identities                                       │
    │     • Ordered deployment                                              │
    │                                                                         │
    │  10. Kubernetes-Complete/10-Jobs-And-CronJobs.txt                     │
    │      • Batch processing                                               │
    │      • One-time tasks                                                 │
    │      • Scheduled jobs                                                 │
    │                                                                         │
    │  11. Kubernetes-Complete/11-RBAC-And-Security.txt                     │
    │      • Authentication                                                 │
    │      • Authorization (RBAC)                                           │
    │      • Service accounts                                               │
    │      • Security contexts                                              │
    │                                                                         │
    │  12. Kubernetes-Complete/12-Helm.txt                                  │
    │      • Package management                                             │
    │      • Charts                                                         │
    │      • Values and templating                                          │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
                PHASE 6: KUBERNETES ADVANCED (Week 9-11)
================================================================================

LEARNING SEQUENCE
─────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  KUBERNETES ADVANCED - CHAPTER ORDER                                   │
    │                                                                         │
    │  13. Kubernetes-Networking/ (All 6 chapters - already created)        │
    │      • CNI plugins                                                    │
    │      • Network policies                                               │
    │      • Service mesh introduction                                      │
    │                                                                         │
    │  14. Kubernetes-Complete/13-Custom-Resources.txt                      │
    │      • Custom Resource Definitions (CRDs)                             │
    │      • Extending Kubernetes                                           │
    │                                                                         │
    │  15. Kubernetes-Complete/14-Operators.txt                             │
    │      • Operator pattern                                               │
    │      • Building operators                                             │
    │      • Popular operators                                              │
    │                                                                         │
    │  16. Kubernetes-Complete/15-Autoscaling.txt                           │
    │      • Horizontal Pod Autoscaler                                      │
    │      • Vertical Pod Autoscaler                                        │
    │      • Cluster Autoscaler                                             │
    │                                                                         │
    │  17. Kubernetes-Complete/16-Service-Mesh.txt                          │
    │      • Why service mesh                                               │
    │      • Istio architecture                                             │
    │      • Traffic management                                             │
    │      • Observability                                                  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
              PHASE 7: PRODUCTION OPERATIONS (Week 11-12)
================================================================================

LEARNING SEQUENCE
─────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  PRODUCTION OPERATIONS - CHAPTER ORDER                                 │
    │                                                                         │
    │  18. Kubernetes-Complete/17-Monitoring.txt                            │
    │      • Prometheus                                                     │
    │      • Grafana                                                        │
    │      • Alerting                                                       │
    │                                                                         │
    │  19. Kubernetes-Complete/18-Logging.txt                               │
    │      • Centralized logging                                            │
    │      • EFK/ELK stack                                                  │
    │      • Loki                                                           │
    │                                                                         │
    │  20. Kubernetes-Complete/19-CI-CD.txt                                 │
    │      • GitOps principles                                              │
    │      • ArgoCD                                                         │
    │      • Flux                                                           │
    │                                                                         │
    │  21. Kubernetes-Complete/20-Production-Best-Practices.txt             │
    │      • High availability                                              │
    │      • Disaster recovery                                              │
    │      • Cost optimization                                              │
    │      • Security hardening                                             │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
                         FOLDER STRUCTURE
================================================================================

    /DevOps/
    │
    ├── 00-LEARNING-ROADMAP.txt (This file)
    │
    ├── Docker-Complete/
    │   ├── 01-Docker-Architecture.txt
    │   ├── 02-Images-And-Containers.txt
    │   ├── 03-Dockerfile-Deep-Dive.txt
    │   ├── 04-Data-Persistence.txt
    │   ├── 05-Docker-Compose.txt
    │   ├── 06-Multi-Stage-Builds.txt
    │   ├── 07-Security-Best-Practices.txt
    │   ├── 08-Registry-And-Distribution.txt
    │   └── 09-Docker-In-CI-CD.txt
    │
    ├── Docker-Networking/ (Already exists)
    │   ├── 01-Linux-Networking-Foundations.txt
    │   ├── 02-Docker-Networking-Internals.txt
    │   └── 03-Advanced-Docker-Networking.txt
    │
    ├── Kubernetes-Complete/
    │   ├── 01-Architecture.txt
    │   ├── 02-Pods.txt
    │   ├── 03-Workloads.txt
    │   ├── 04-Services.txt
    │   ├── 05-Configuration.txt
    │   ├── 06-Namespaces.txt
    │   ├── 07-Storage.txt
    │   ├── 08-Ingress.txt
    │   ├── 09-StatefulSets.txt
    │   ├── 10-Jobs-And-CronJobs.txt
    │   ├── 11-RBAC-And-Security.txt
    │   ├── 12-Helm.txt
    │   ├── 13-Custom-Resources.txt
    │   ├── 14-Operators.txt
    │   ├── 15-Autoscaling.txt
    │   ├── 16-Service-Mesh.txt
    │   ├── 17-Monitoring.txt
    │   ├── 18-Logging.txt
    │   ├── 19-CI-CD.txt
    │   └── 20-Production-Best-Practices.txt
    │
    └── Kubernetes-Networking/ (Already exists)
        ├── 01-Kubernetes-Networking-Fundamentals.txt
        ├── 02-CNI-Plugins-Deep-Dive.txt
        ├── 03-Services-And-Kube-Proxy.txt
        ├── 04-Ingress-And-External-Access.txt
        ├── 05-Network-Policies.txt
        └── 06-Troubleshooting-And-Best-Practices.txt


================================================================================
                      CERTIFICATION PATH
================================================================================

If you want to get certified, here's the recommended order:

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CERTIFICATION ROADMAP                                                 │
    │                                                                         │
    │  1. DOCKER CERTIFIED ASSOCIATE (DCA)                                   │
    │     • After completing Docker phases                                  │
    │     • Validates Docker knowledge                                      │
    │                                                                         │
    │  2. CERTIFIED KUBERNETES ADMINISTRATOR (CKA)                           │
    │     • After completing K8s Fundamentals + Intermediate                │
    │     • Focus: Cluster administration                                   │
    │     • Hands-on exam                                                   │
    │                                                                         │
    │  3. CERTIFIED KUBERNETES APPLICATION DEVELOPER (CKAD)                  │
    │     • After completing K8s phases                                     │
    │     • Focus: Application development                                  │
    │     • Hands-on exam                                                   │
    │                                                                         │
    │  4. CERTIFIED KUBERNETES SECURITY SPECIALIST (CKS)                     │
    │     • After CKA                                                       │
    │     • Advanced security topics                                        │
    │     • Requires CKA to attempt                                         │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
                              RESOURCES
================================================================================

PRACTICE ENVIRONMENTS
─────────────────────

    LOCAL:
    • Docker Desktop (Mac/Windows)
    • minikube (local K8s cluster)
    • kind (Kubernetes in Docker)
    • k3d (lightweight K8s)

    CLOUD (FREE TIERS):
    • Google Cloud (GKE) - $300 credit
    • AWS (EKS) - Free tier
    • Azure (AKS) - $200 credit
    • DigitalOcean Kubernetes - $100 credit

    PLAYGROUNDS:
    • Killercoda (free K8s labs)
    • Play with Docker
    • Play with Kubernetes


RECOMMENDED READING ORDER
─────────────────────────

    Start here → Follow the chapter numbers → Complete hands-on exercises
    
    Don't skip ahead! Each chapter builds on previous knowledge.


================================================================================
                          END OF ROADMAP
================================================================================

