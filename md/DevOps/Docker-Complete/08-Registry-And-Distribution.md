# DOCKER REGISTRY & DISTRIBUTION
*Chapter 8: Storing and Sharing Images*

Registries are storage and distribution systems for Docker images.
This chapter covers public registries, private registries, and best
practices for image management.

## SECTION 8.1: UNDERSTANDING REGISTRIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS A REGISTRY?                                                   |
|                                                                         |
|  A registry stores Docker images and allows:                          |
|  * Push: Upload images                                               |
|  * Pull: Download images                                             |
|  * Search: Find images                                               |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |                                                                 |  |
|  |   Developer            Registry              Production        |  |
|  |                                                                 |  |
|  |   docker build         +--------------+      docker pull       |  |
|  |       |                |              |           |            |  |
|  |       v                |   myapp:1.0  |           v            |  |
|  |   docker push -------->|   myapp:1.1  |<---- docker run       |  |
|  |                        |   myapp:1.2  |                        |  |
|  |                        |              |                        |  |
|  |                        +--------------+                        |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  IMAGE NAMING CONVENTION                                              |
|  ========================                                               |
|                                                                         |
|  Full image reference:                                                |
|                                                                         |
|  [registry]/[namespace]/[repository]:[tag]                           |
|                                                                         |
|  Examples:                                                             |
|  * nginx                                                              |
|    -> docker.io/library/nginx:latest                                  |
|                                                                         |
|  * myuser/myapp:v1.0                                                  |
|    -> docker.io/myuser/myapp:v1.0                                     |
|                                                                         |
|  * gcr.io/myproject/myapp:v1.0                                       |
|    -> Google Container Registry                                       |
|                                                                         |
|  * 123456789.dkr.ecr.us-east-1.amazonaws.com/myapp:v1.0             |
|    -> AWS ECR                                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8.2: PUBLIC REGISTRIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DOCKER HUB (docker.io)                                               |
|  =======================                                                |
|                                                                         |
|  * Default registry                                                   |
|  * Free public repositories                                          |
|  * 1 free private repo                                               |
|  * Rate limits for anonymous pulls                                   |
|                                                                         |
|  # Login                                                               |
|  docker login                                                          |
|                                                                         |
|  # Push to Docker Hub                                                 |
|  docker tag myapp:v1.0 myusername/myapp:v1.0                         |
|  docker push myusername/myapp:v1.0                                   |
|                                                                         |
|  # Pull from Docker Hub                                               |
|  docker pull myusername/myapp:v1.0                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  OTHER PUBLIC REGISTRIES                                              |
|  ========================                                               |
|                                                                         |
|  GitHub Container Registry (ghcr.io)                                  |
|  -------------------------------------                                  |
|  docker login ghcr.io -u USERNAME -p TOKEN                           |
|  docker push ghcr.io/username/myapp:v1.0                             |
|                                                                         |
|  Google Container Registry (gcr.io)                                   |
|  -------------------------------------                                  |
|  gcloud auth configure-docker                                         |
|  docker push gcr.io/project-id/myapp:v1.0                            |
|                                                                         |
|  AWS ECR                                                               |
|  --------                                                              |
|  aws ecr get-login-password | docker login --username AWS \          |
|    --password-stdin 123456.dkr.ecr.region.amazonaws.com              |
|  docker push 123456.dkr.ecr.region.amazonaws.com/myapp:v1.0         |
|                                                                         |
|  Azure Container Registry                                             |
|  -------------------------                                              |
|  az acr login --name myregistry                                       |
|  docker push myregistry.azurecr.io/myapp:v1.0                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8.3: PRIVATE REGISTRY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RUNNING YOUR OWN REGISTRY                                            |
|  ==========================                                            |
|                                                                         |
|  # Simple local registry                                               |
|  docker run -d -p 5000:5000 --name registry registry:2               |
|                                                                         |
|  # Push to local registry                                             |
|  docker tag myapp:v1.0 localhost:5000/myapp:v1.0                     |
|  docker push localhost:5000/myapp:v1.0                               |
|                                                                         |
|  # Pull from local registry                                           |
|  docker pull localhost:5000/myapp:v1.0                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PRODUCTION REGISTRY WITH STORAGE                                     |
|  =================================                                      |
|                                                                         |
|  # docker-compose.yml                                                  |
|  version: '3.8'                                                        |
|                                                                         |
|  services:                                                              |
|    registry:                                                            |
|      image: registry:2                                                 |
|      ports:                                                             |
|        - "5000:5000"                                                   |
|      volumes:                                                           |
|        - registry-data:/var/lib/registry                              |
|        - ./config.yml:/etc/docker/registry/config.yml                |
|      environment:                                                       |
|        REGISTRY_STORAGE_DELETE_ENABLED: "true"                        |
|                                                                         |
|  volumes:                                                               |
|    registry-data:                                                       |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REGISTRY WITH TLS                                                     |
|  ==================                                                    |
|                                                                         |
|  # Generate self-signed cert (for testing)                            |
|  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \               |
|    -keyout registry.key -out registry.crt                             |
|                                                                         |
|  docker run -d -p 443:443 \                                            |
|    -v $(pwd)/certs:/certs \                                            |
|    -e REGISTRY_HTTP_ADDR=0.0.0.0:443 \                                |
|    -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/registry.crt \            |
|    -e REGISTRY_HTTP_TLS_KEY=/certs/registry.key \                    |
|    registry:2                                                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HARBOR (Enterprise Registry)                                         |
|  =============================                                          |
|                                                                         |
|  Full-featured open-source registry with:                            |
|  * Web UI                                                             |
|  * Vulnerability scanning                                            |
|  * Image signing                                                      |
|  * RBAC access control                                               |
|  * Replication                                                        |
|                                                                         |
|  # Install Harbor                                                      |
|  wget https://github.com/goharbor/harbor/releases/.../harbor.tgz    |
|  tar xvf harbor.tgz                                                    |
|  cd harbor                                                             |
|  ./install.sh                                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8.4: TAGGING STRATEGIES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TAGGING BEST PRACTICES                                               |
|  =======================                                                |
|                                                                         |
|  DON'T USE :latest IN PRODUCTION                                      |
|  ---------------------------------                                      |
|  * Not clear which version is running                                |
|  * Can't rollback easily                                             |
|  * Different machines may pull different images                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SEMANTIC VERSIONING                                                   |
|  ====================                                                   |
|                                                                         |
|  myapp:1.2.3                                                           |
|         | | |                                                          |
|         | | +-- Patch (bug fixes)                                    |
|         | +---- Minor (new features, backward compatible)           |
|         +------ Major (breaking changes)                             |
|                                                                         |
|  Multiple tags for same image:                                        |
|  myapp:1.2.3                                                           |
|  myapp:1.2                                                             |
|  myapp:1                                                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  GIT-BASED TAGGING                                                     |
|  ==================                                                    |
|                                                                         |
|  # Tag with git commit SHA                                            |
|  docker build -t myapp:$(git rev-parse --short HEAD) .               |
|  # Result: myapp:a1b2c3d                                              |
|                                                                         |
|  # Tag with git tag                                                   |
|  docker build -t myapp:$(git describe --tags) .                      |
|  # Result: myapp:v1.2.3                                               |
|                                                                         |
|  # Tag with branch name                                               |
|  docker build -t myapp:$(git branch --show-current) .                |
|  # Result: myapp:feature-login                                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CI/CD TAGGING                                                         |
|  =============                                                          |
|                                                                         |
|  # GitHub Actions example                                              |
|  - name: Build and push                                               |
|    uses: docker/build-push-action@v5                                  |
|    with:                                                               |
|      push: true                                                        |
|      tags: |                                                           |
|        myapp:${{ github.sha }}                                        |
|        myapp:${{ github.ref_name }}                                   |
|        myapp:latest                                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8.5: IMAGE MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LISTING AND INSPECTING                                               |
|  =======================                                                |
|                                                                         |
|  # List local images                                                   |
|  docker images                                                          |
|  docker image ls                                                        |
|                                                                         |
|  # List with digests                                                   |
|  docker images --digests                                               |
|                                                                         |
|  # Inspect image                                                       |
|  docker inspect myapp:v1.0                                            |
|                                                                         |
|  # View image history (layers)                                        |
|  docker history myapp:v1.0                                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CLEANUP                                                               |
|  =======                                                               |
|                                                                         |
|  # Remove specific image                                               |
|  docker rmi myapp:v1.0                                                |
|                                                                         |
|  # Remove all unused images                                           |
|  docker image prune                                                    |
|                                                                         |
|  # Remove ALL unused (dangling + unused)                              |
|  docker image prune -a                                                 |
|                                                                         |
|  # Remove images older than 24h                                       |
|  docker image prune -a --filter "until=24h"                          |
|                                                                         |
|  # Remove by pattern                                                   |
|  docker images | grep "myapp" | awk '{print $3}' | xargs docker rmi  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  REGISTRY CLEANUP                                                      |
|  ================                                                       |
|                                                                         |
|  # List tags in registry                                              |
|  curl https://myregistry/v2/myapp/tags/list                          |
|                                                                         |
|  # Delete tag (if enabled)                                            |
|  curl -X DELETE https://myregistry/v2/myapp/manifests/<digest>       |
|                                                                         |
|  # Run garbage collection                                             |
|  docker exec registry bin/registry garbage-collect \                 |
|    /etc/docker/registry/config.yml                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REGISTRY & DISTRIBUTION - KEY TAKEAWAYS                              |
|                                                                         |
|  REGISTRIES                                                            |
|  ----------                                                            |
|  * Docker Hub: Default, public/private                               |
|  * Cloud: ECR, GCR, ACR                                              |
|  * Self-hosted: registry:2, Harbor                                   |
|                                                                         |
|  NAMING                                                                |
|  ------                                                                |
|  registry/namespace/repo:tag                                          |
|                                                                         |
|  TAGGING                                                               |
|  -------                                                               |
|  * Avoid :latest in production                                       |
|  * Use semantic versioning                                           |
|  * Include git SHA for traceability                                  |
|                                                                         |
|  COMMANDS                                                              |
|  --------                                                              |
|  docker login/logout                                                   |
|  docker push/pull                                                      |
|  docker tag                                                             |
|  docker image prune                                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 8

