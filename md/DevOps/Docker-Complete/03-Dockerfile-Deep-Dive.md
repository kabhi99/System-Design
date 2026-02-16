# CHAPTER 3: DOCKERFILE DEEP DIVE
*Mastering the Art of Building Docker Images*

The Dockerfile is a text file containing instructions for building Docker
images. Understanding how to write efficient Dockerfiles is crucial for
production deployments. This chapter covers every aspect in detail.

## SECTION 3.1: DOCKERFILE BASICS

### WHAT IS A DOCKERFILE?

A Dockerfile is a recipe for creating Docker images:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DOCKERFILE > docker build > IMAGE > docker run > CONTAINER           |
|                                                                         |
|  +----------------+      +----------------+      +----------------+   |
|  |   Dockerfile   |      |     Image      |      |   Container    |   |
|  |                |      |                |      |                |   |
|  |  FROM node:16  |----->|   my-app:v1   |----->|   Running app  |   |
|  |  COPY . .      |      |                |      |                |   |
|  |  RUN npm i     |      |    (layers)    |      |   (process)    |   |
|  |  CMD npm start |      |                |      |                |   |
|  +----------------+      +----------------+      +----------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DOCKERFILE STRUCTURE

```bash
# Comment
INSTRUCTION arguments

# Example Dockerfile
FROM node:16-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
```

**KEY RULES:**
- Each instruction creates a new layer
- Instructions are executed in order
- Case doesn't matter but UPPERCASE is convention
- Comments start with #

## SECTION 3.2: DOCKERFILE INSTRUCTIONS REFERENCE

### FROM — THE BASE IMAGE

Every Dockerfile must start with FROM (except ARG before it):

```
FROM image:tag

EXAMPLES:
FROM ubuntu:20.04           # Specific version
FROM python:3.9-slim        # Slim variant (smaller)
FROM node:16-alpine         # Alpine-based (smallest)
FROM scratch                # Empty base (for static binaries)

MULTI-STAGE (multiple FROM):
FROM node:16 AS builder
# ... build steps
FROM nginx:alpine
# ... copy from builder

+-------------------------------------------------------------------------+
|                                                                         |
|  CHOOSING BASE IMAGES                                                  |
|                                                                         |
|  IMAGE TYPE          SIZE        USE CASE                              |
|  ---------------------------------------------------------             |
|  ubuntu:20.04        ~72MB       Full OS, debugging                   |
|  python:3.9          ~900MB      Full Python with build tools         |
|  python:3.9-slim     ~120MB      Python without extras                |
|  python:3.9-alpine   ~50MB       Smallest, musl libc (compatibility?) |
|  node:16             ~900MB      Full Node.js                         |
|  node:16-slim        ~200MB      Node.js without extras               |
|  node:16-alpine      ~110MB      Smallest Node.js                     |
|  alpine              ~5MB        Minimal Linux                        |
|  scratch             0MB         Empty (for Go/Rust static binaries)  |
|                                                                         |
|  TIP: Start with -slim or -alpine variants for production             |
|                                                                         |
+-------------------------------------------------------------------------+
```

### RUN — EXECUTE COMMANDS

RUN executes commands and creates a new layer:

```
# Shell form (runs in /bin/sh -c)
RUN apt-get update && apt-get install -y nginx

# Exec form (runs directly)
RUN ["apt-get", "update"]

BEST PRACTICES:
+-------------------------------------------------------------------------+
|                                                                         |
|  COMBINE COMMANDS (fewer layers):                                      |
|                                                                         |
|  BAD (3 layers):                                                       |
|  RUN apt-get update                                                   |
|  RUN apt-get install -y nginx                                         |
|  RUN apt-get clean                                                    |
|                                                                         |
|  GOOD (1 layer):                                                       |
|  RUN apt-get update && \                                              |
|      apt-get install -y nginx && \                                    |
|      apt-get clean && \                                               |
|      rm -rf /var/lib/apt/lists/*                                      |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  CLEAN UP IN SAME LAYER:                                               |
|                                                                         |
|  BAD (downloaded packages remain in layer):                           |
|  RUN apt-get update && apt-get install -y nginx                       |
|  RUN rm -rf /var/lib/apt/lists/*   # Still in previous layer!        |
|                                                                         |
|  GOOD (no bloat):                                                      |
|  RUN apt-get update && \                                              |
|      apt-get install -y nginx && \                                    |
|      rm -rf /var/lib/apt/lists/*                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### COPY and ADD — TRANSFER FILES

COPY copies files from build context to image:

```dockerfile
COPY source destination
COPY file.txt /app/
COPY . /app/
COPY --chown=user:group file.txt /app/
```

ADD has extra features (usually avoid):

```
ADD source destination
ADD https://example.com/file.tar.gz /tmp/   # Downloads from URL
ADD archive.tar.gz /app/                     # Auto-extracts archives

+-------------------------------------------------------------------------+
|                                                                         |
|  COPY vs ADD                                                           |
|                                                                         |
|  COPY:                                                                 |
|  * Simple file/directory copy                                         |
|  * Predictable behavior                                               |
|  * RECOMMENDED for most cases                                         |
|                                                                         |
|  ADD:                                                                  |
|  * Can download from URLs (but better to use curl/wget)               |
|  * Auto-extracts tar archives (can be surprising)                    |
|  * Use ONLY when you need auto-extraction                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WORKDIR — SET WORKING DIRECTORY

WORKDIR sets the working directory for subsequent instructions:

```dockerfile
WORKDIR /app

# All subsequent commands run in /app
RUN pwd           # Outputs /app
COPY . .          # Copies to /app
CMD ["./start"]   # Runs /app/start

# Can use multiple times
WORKDIR /app
WORKDIR src       # Now in /app/src

# Creates directory if it doesn't exist
WORKDIR /new/directory   # Created automatically
```

### ENV — SET ENVIRONMENT VARIABLES

ENV sets environment variables:

```dockerfile
ENV KEY=value
ENV KEY1=value1 KEY2=value2
ENV NODE_ENV=production

# Variables persist in running container
# Variables available in subsequent instructions

FROM node:16
ENV NODE_ENV=production
RUN echo $NODE_ENV           # production
```

### ARG — BUILD-TIME VARIABLES

ARG defines variables only available during build:

```
ARG VERSION=latest
ARG BUILD_DATE

FROM ubuntu:20.04
ARG VERSION
RUN echo "Building version $VERSION"

# Usage:
# docker build --build-arg VERSION=1.0 .

+-------------------------------------------------------------------------+
|                                                                         |
|  ARG vs ENV                                                            |
|                                                                         |
|  ARG:                                                                  |
|  * Only available during build                                        |
|  * NOT in running container                                           |
|  * Set with --build-arg                                               |
|  * Can be before FROM                                                 |
|                                                                         |
|  ENV:                                                                  |
|  * Available during build AND in container                           |
|  * Persists in image                                                  |
|  * Can override with docker run -e                                   |
|                                                                         |
|  PATTERN - Use both:                                                   |
|  ARG NODE_VERSION=16                                                  |
|  FROM node:${NODE_VERSION}                                            |
|  ENV NODE_ENV=production                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

### EXPOSE — DOCUMENT PORTS

EXPOSE documents which ports the container listens on:

```dockerfile
EXPOSE 80
EXPOSE 80/tcp
EXPOSE 443
EXPOSE 80 443

IMPORTANT:
* EXPOSE does NOT publish the port!
* It's documentation only
* Still need -p to actually publish

# To publish:
docker run -p 8080:80 myimage
```

### CMD and ENTRYPOINT — CONTAINER STARTUP

CMD specifies the default command:

```bash
# Exec form (preferred)
CMD ["python", "app.py"]

# Shell form (runs in shell)
CMD python app.py
```

ENTRYPOINT specifies the executable:

```
ENTRYPOINT ["python"]
CMD ["app.py"]       # Default argument

+-------------------------------------------------------------------------+
|                                                                         |
|  CMD vs ENTRYPOINT                                                     |
|                                                                         |
|  CMD ALONE:                                                            |
|  ------------                                                          |
|  CMD ["python", "app.py"]                                             |
|                                                                         |
|  docker run myimage              > python app.py                      |
|  docker run myimage bash         > bash (CMD replaced)                |
|                                                                         |
|  ENTRYPOINT ALONE:                                                     |
|  ------------------                                                    |
|  ENTRYPOINT ["python"]                                                |
|                                                                         |
|  docker run myimage              > python                             |
|  docker run myimage app.py       > python app.py                     |
|                                                                         |
|  ENTRYPOINT + CMD (recommended):                                       |
|  -------------------------------                                       |
|  ENTRYPOINT ["python"]                                                |
|  CMD ["app.py"]                                                       |
|                                                                         |
|  docker run myimage              > python app.py                      |
|  docker run myimage other.py     > python other.py                   |
|  docker run --entrypoint bash myimage  > bash (override EP)          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### USER — SET USER

USER sets the user for RUN, CMD, ENTRYPOINT:

```bash
USER username
USER uid
USER uid:gid

# Create and switch to non-root user
RUN useradd -m appuser
USER appuser

# SECURITY: Always run as non-root in production!
```

### VOLUME — DECLARE MOUNT POINTS

VOLUME declares that a path should be a volume:

```dockerfile
VOLUME /data
VOLUME ["/var/log", "/var/db"]

# At runtime, creates anonymous volume if not mounted
# Data persists even if container removed
```

### HEALTHCHECK — CONTAINER HEALTH

HEALTHCHECK defines how to check if container is healthy:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost/ || exit 1

# Options:
# --interval=DURATION (default 30s)
# --timeout=DURATION (default 30s)
# --start-period=DURATION (default 0s)
# --retries=N (default 3)
```

## SECTION 3.3: BUILD CONTEXT AND .dockerignore

### UNDERSTANDING BUILD CONTEXT

When you run docker build, the entire directory is sent to the daemon:

```
docker build -t myapp .
                     ^
                     This is the build context

+-------------------------------------------------------------------------+
|                                                                         |
|  BUILD PROCESS                                                         |
|                                                                         |
|  Your Directory                      Docker Daemon                     |
|  +------------------+               +----------------------+          |
|  | myproject/       |               |                      |          |
|  | +-- src/         |               |  Receives all files  |          |
|  | +-- node_modules/|-------------->|  in build context    |          |
|  | +-- .git/        |    network    |                      |          |
|  | +-- Dockerfile   |               |  Then builds image   |          |
|  | +-- package.json |               |                      |          |
|  +------------------+               +----------------------+          |
|                                                                         |
|  PROBLEM: Sending huge directories (node_modules, .git) is SLOW!     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### .dockerignore FILE

.dockerignore excludes files from build context (like .gitignore):

```bash
# .dockerignore file

# Dependencies (install fresh in container)
node_modules
vendor

# Git
.git
.gitignore

# IDE
.idea
.vscode

# Build artifacts
dist
build
*.log

# Tests
test
__tests__
*.test.js

# Docker
Dockerfile*
docker-compose*

BENEFITS:
* Faster builds (less to transfer)
* Smaller build context
* Avoid accidentally including sensitive files
```

## SECTION 3.4: DOCKERFILE BEST PRACTICES

### 1. ORDER INSTRUCTIONS BY CHANGE FREQUENCY

Put instructions that change rarely first (better caching):

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BAD ORDER (cache invalidated often):                                  |
|                                                                         |
|  FROM node:16                                                          |
|  COPY . .                    <-- Changes every time code changes      |
|  RUN npm install             <-- Must reinstall every time!           |
|  CMD ["npm", "start"]                                                 |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  GOOD ORDER (maximize cache):                                          |
|                                                                         |
|  FROM node:16                                                          |
|  WORKDIR /app                                                          |
|  COPY package*.json ./       <-- Only changes when deps change        |
|  RUN npm install             <-- Cached unless package.json changes   |
|  COPY . .                    <-- Code changes don't affect npm install|
|  CMD ["npm", "start"]                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 2. USE SPECIFIC TAGS

```dockerfile
BAD:
FROM node:latest    # Could change anytime!

GOOD:
FROM node:16.17.0   # Exact version, reproducible
```

### 3. MINIMIZE LAYERS

```dockerfile
BAD (5 layers):
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y wget
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*

GOOD (1 layer):
RUN apt-get update && \
    apt-get install -y curl wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

### 4. RUN AS NON-ROOT USER

```dockerfile
FROM node:16-alpine
WORKDIR /app

# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY --chown=appuser:appgroup . .
RUN npm install

USER appuser
CMD ["npm", "start"]
```

### 5. USE MULTI-STAGE BUILDS

```bash
# Build stage
FROM node:16 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Production stage
FROM node:16-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY package*.json ./
RUN npm install --production
USER node
CMD ["node", "dist/main.js"]
```

## SECTION 3.5: COMPLETE DOCKERFILE EXAMPLES

### NODE.JS APPLICATION

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Build application
COPY . .
RUN npm run build

# Production image
FROM node:18-alpine
WORKDIR /app
ENV NODE_ENV=production

# Create non-root user
RUN addgroup -S nodejs && adduser -S nodejs -G nodejs

# Copy built files
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/node_modules ./node_modules

USER nodejs
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget --quiet --tries=1 --spider http://localhost:3000/health || exit 1

CMD ["node", "dist/main.js"]
```

### PYTHON APPLICATION

```dockerfile
FROM python:3.10-slim AS builder
WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Production image
FROM python:3.10-slim
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy wheels and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

# Create non-root user
RUN useradd -m appuser
USER appuser

# Copy application
COPY --chown=appuser:appuser . .

EXPOSE 8000
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]
```

### GO APPLICATION

```bash
# Build stage
FROM golang:1.19-alpine AS builder
WORKDIR /app

# Download dependencies
COPY go.mod go.sum ./
RUN go mod download

# Build binary
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main .

# Final stage - scratch for minimal image
FROM scratch
COPY --from=builder /app/main /main
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

EXPOSE 8080
ENTRYPOINT ["/main"]
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DOCKERFILE - KEY TAKEAWAYS                                            |
|                                                                         |
|  ESSENTIAL INSTRUCTIONS                                                |
|  ----------------------                                                |
|  FROM        Base image                                               |
|  RUN         Execute commands                                         |
|  COPY        Copy files                                               |
|  WORKDIR     Set working directory                                    |
|  ENV         Set environment variables                                |
|  EXPOSE      Document ports                                           |
|  CMD         Default command                                          |
|  ENTRYPOINT  Container executable                                     |
|  USER        Run as user                                              |
|                                                                         |
|  BEST PRACTICES                                                        |
|  --------------                                                        |
|  * Use specific base image tags                                       |
|  * Order by change frequency (cache!)                                 |
|  * Minimize layers                                                    |
|  * Use multi-stage builds                                             |
|  * Run as non-root                                                    |
|  * Use .dockerignore                                                  |
|  * Clean up in same layer                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 3

