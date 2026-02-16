# DOCKER SECURITY BEST PRACTICES
*Chapter 7: Securing Your Containers*

Container security is crucial for production deployments. This chapter
covers security best practices from image building to runtime.

## SECTION 7.1: IMAGE SECURITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USE TRUSTED BASE IMAGES                                              |
|  ========================                                               |
|                                                                         |
|  # Good: Official images                                               |
|  FROM node:20-alpine                                                    |
|  FROM python:3.11-slim                                                  |
|  FROM nginx:1.25                                                        |
|                                                                         |
|  # Better: Verified publisher images                                  |
|  FROM docker.io/library/node:20-alpine                                |
|                                                                         |
|  # Best: Pin exact digest                                              |
|  FROM node:20-alpine@sha256:a1b2c3d4e5f6...                           |
|                                                                         |
|  WHY PIN DIGESTS?                                                      |
|  * Tags can be overwritten                                            |
|  * Digest guarantees exact image                                     |
|  * Reproducible builds                                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SCAN IMAGES FOR VULNERABILITIES                                      |
|  ================================                                       |
|                                                                         |
|  # Docker Scout (built-in)                                            |
|  docker scout cves myimage:latest                                     |
|                                                                         |
|  # Trivy (open source)                                                |
|  trivy image myimage:latest                                           |
|                                                                         |
|  # Snyk                                                                |
|  snyk container test myimage:latest                                   |
|                                                                         |
|  # In CI/CD pipeline                                                   |
|  - name: Scan image                                                    |
|    run: |                                                              |
|      trivy image --exit-code 1 --severity HIGH,CRITICAL myimage      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  MINIMIZE IMAGE CONTENTS                                              |
|  ========================                                               |
|                                                                         |
|  Less software = fewer vulnerabilities                               |
|                                                                         |
|  Y Use multi-stage builds                                            |
|  Y Use alpine or distroless base images                             |
|  Y Remove package manager caches                                     |
|  Y Don't install unnecessary packages                               |
|                                                                         |
|  RUN apt-get update && \                                              |
|      apt-get install -y --no-install-recommends curl && \            |
|      rm -rf /var/lib/apt/lists/*                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.2: RUN AS NON-ROOT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY NON-ROOT MATTERS                                                 |
|                                                                         |
|  By default, containers run as root (UID 0).                         |
|  If container is compromised, attacker has root access.              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CREATING A NON-ROOT USER                                             |
|  =========================                                              |
|                                                                         |
|  FROM node:20-alpine                                                    |
|                                                                         |
|  # Create non-root user                                               |
|  RUN addgroup -g 1001 appgroup && \                                   |
|      adduser -u 1001 -G appgroup -D appuser                           |
|                                                                         |
|  WORKDIR /app                                                          |
|  COPY --chown=appuser:appgroup . .                                    |
|                                                                         |
|  # Switch to non-root user                                            |
|  USER appuser                                                           |
|                                                                         |
|  CMD ["node", "server.js"]                                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  FOR OFFICIAL IMAGES WITH EXISTING USERS                              |
|  ========================================                               |
|                                                                         |
|  # Node.js has 'node' user                                            |
|  FROM node:20-alpine                                                    |
|  USER node                                                              |
|  WORKDIR /home/node/app                                                |
|  COPY --chown=node:node . .                                            |
|  CMD ["node", "server.js"]                                             |
|                                                                         |
|  # nginx has 'nginx' user                                             |
|  FROM nginx:alpine                                                      |
|  USER nginx                                                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  RUNTIME ENFORCEMENT                                                   |
|  ====================                                                   |
|                                                                         |
|  # Run as specific user                                               |
|  docker run --user 1001:1001 myimage                                  |
|                                                                         |
|  # Prevent privilege escalation                                       |
|  docker run --security-opt=no-new-privileges myimage                 |
|                                                                         |
|  # In Kubernetes                                                       |
|  securityContext:                                                       |
|    runAsNonRoot: true                                                  |
|    runAsUser: 1001                                                     |
|    allowPrivilegeEscalation: false                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.3: SECRETS MANAGEMENT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NEVER PUT SECRETS IN IMAGES                                          |
|  ============================                                           |
|                                                                         |
|  # WRONG ❌                                                            |
|  ENV DATABASE_PASSWORD=mysecretpassword                               |
|  COPY .env /app/.env                                                   |
|                                                                         |
|  Secrets in images:                                                    |
|  * Visible in image layers (docker history)                          |
|  * Visible in running container (docker inspect)                     |
|  * Stored in registries                                               |
|  * Can't be rotated without rebuilding                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CORRECT APPROACHES                                                    |
|  ===================                                                    |
|                                                                         |
|  1. ENVIRONMENT VARIABLES AT RUNTIME                                   |
|     ---------------------------------                                   |
|     docker run -e DATABASE_PASSWORD=secret myimage                    |
|                                                                         |
|  2. DOCKER SECRETS (Swarm mode)                                        |
|     ---------------------------                                         |
|     echo "mysecret" | docker secret create db_password -              |
|                                                                         |
|     # In compose                                                       |
|     secrets:                                                            |
|       db_password:                                                      |
|         external: true                                                  |
|                                                                         |
|     # In container, available at /run/secrets/db_password             |
|                                                                         |
|  3. MOUNT SECRET FILES                                                 |
|     ----------------------                                              |
|     docker run -v /secure/secrets:/run/secrets:ro myimage            |
|                                                                         |
|  4. SECRET MANAGERS                                                    |
|     ----------------                                                    |
|     * HashiCorp Vault                                                 |
|     * AWS Secrets Manager                                             |
|     * Azure Key Vault                                                 |
|     * GCP Secret Manager                                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BUILD-TIME SECRETS (Docker BuildKit)                                 |
|  =====================================                                  |
|                                                                         |
|  For secrets needed during build (npm tokens, pip credentials):      |
|                                                                         |
|  # syntax=docker/dockerfile:1                                          |
|  FROM node:20-alpine                                                    |
|                                                                         |
|  RUN --mount=type=secret,id=npm_token \                               |
|      NPM_TOKEN=$(cat /run/secrets/npm_token) && \                     |
|      npm install                                                        |
|                                                                         |
|  # Build with:                                                         |
|  docker build --secret id=npm_token,src=.npmrc .                      |
|                                                                         |
|  Secret is available during build but NOT in final image.            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.4: RUNTIME SECURITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  READ-ONLY ROOT FILESYSTEM                                            |
|  ==========================                                            |
|                                                                         |
|  Prevent writes to container filesystem.                              |
|  Attackers can't modify binaries or drop malware.                    |
|                                                                         |
|  docker run --read-only myimage                                       |
|                                                                         |
|  # If app needs to write (logs, temp files):                         |
|  docker run --read-only \                                              |
|    --tmpfs /tmp \                                                       |
|    --tmpfs /var/log \                                                   |
|    myimage                                                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DROP CAPABILITIES                                                     |
|  ==================                                                    |
|                                                                         |
|  Linux capabilities = granular root privileges.                       |
|  Drop all unnecessary capabilities.                                   |
|                                                                         |
|  # Drop all, add only what's needed                                   |
|  docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE myimage        |
|                                                                         |
|  Common capabilities:                                                  |
|  * NET_BIND_SERVICE: Bind to ports < 1024                            |
|  * CHOWN: Change file ownership                                       |
|  * SETUID/SETGID: Change UID/GID                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  RESOURCE LIMITS                                                       |
|  ================                                                       |
|                                                                         |
|  Prevent denial-of-service from runaway containers.                  |
|                                                                         |
|  docker run \                                                           |
|    --memory=512m \                                                      |
|    --memory-swap=512m \                                                 |
|    --cpus=1 \                                                           |
|    --pids-limit=100 \                                                   |
|    myimage                                                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  NETWORK SECURITY                                                      |
|  =================                                                      |
|                                                                         |
|  # Disable network entirely                                           |
|  docker run --network=none myimage                                    |
|                                                                         |
|  # Use internal networks (no external access)                        |
|  docker network create --internal internal-net                        |
|  docker run --network=internal-net myimage                            |
|                                                                         |
|  # Don't expose unnecessary ports                                     |
|  # Only expose what's needed                                          |
|  docker run -p 127.0.0.1:8080:8080 myimage  # localhost only         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7.5: DOCKERFILE SECURITY CHECKLIST

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SECURE DOCKERFILE TEMPLATE                                           |
|                                                                         |
|  # syntax=docker/dockerfile:1                                          |
|                                                                         |
|  # 1. Use specific version, not :latest                              |
|  FROM node:20.10-alpine                                                |
|                                                                         |
|  # 2. Create non-root user                                            |
|  RUN addgroup -g 1001 app && adduser -u 1001 -G app -D app           |
|                                                                         |
|  # 3. Set working directory                                           |
|  WORKDIR /app                                                          |
|                                                                         |
|  # 4. Copy only what's needed                                         |
|  COPY --chown=app:app package*.json ./                                |
|                                                                         |
|  # 5. Install dependencies                                            |
|  RUN npm ci --only=production && \                                    |
|      npm cache clean --force                                          |
|                                                                         |
|  # 6. Copy application code                                           |
|  COPY --chown=app:app . .                                              |
|                                                                         |
|  # 7. Switch to non-root user                                         |
|  USER app                                                               |
|                                                                         |
|  # 8. Expose only necessary port                                      |
|  EXPOSE 3000                                                            |
|                                                                         |
|  # 9. Define healthcheck                                               |
|  HEALTHCHECK --interval=30s --timeout=3s \                            |
|    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 \  |
|    || exit 1                                                            |
|                                                                         |
|  # 10. Use exec form for CMD                                          |
|  CMD ["node", "server.js"]                                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SECURITY CHECKLIST                                                    |
|  ==================                                                    |
|                                                                         |
|  □ Use specific base image version (not :latest)                     |
|  □ Scan image for vulnerabilities                                    |
|  □ Run as non-root user                                              |
|  □ No secrets in Dockerfile or image                                 |
|  □ Use COPY, not ADD (unless extracting tar)                        |
|  □ Multi-stage build for smaller image                              |
|  □ .dockerignore file present                                        |
|  □ HEALTHCHECK defined                                               |
|  □ Only necessary ports exposed                                      |
|  □ Read-only filesystem where possible                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DOCKER SECURITY - KEY TAKEAWAYS                                      |
|                                                                         |
|  IMAGE SECURITY                                                        |
|  --------------                                                        |
|  * Use official/trusted base images                                  |
|  * Pin versions (tags or digests)                                    |
|  * Scan for vulnerabilities                                          |
|  * Minimize image contents                                           |
|                                                                         |
|  USER SECURITY                                                         |
|  -------------                                                         |
|  * Never run as root                                                 |
|  * Create dedicated app user                                         |
|  * Use USER instruction                                              |
|                                                                         |
|  SECRETS                                                               |
|  -------                                                               |
|  * Never embed in images                                             |
|  * Use env vars, mounts, or secret managers                         |
|  * BuildKit secrets for build-time                                  |
|                                                                         |
|  RUNTIME                                                               |
|  -------                                                               |
|  * Read-only filesystem                                              |
|  * Drop capabilities                                                 |
|  * Set resource limits                                               |
|  * Limit network exposure                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 7

