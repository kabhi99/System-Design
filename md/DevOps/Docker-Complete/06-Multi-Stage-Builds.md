# DOCKER MULTI-STAGE BUILDS
*Chapter 6: Building Optimized Images*

Multi-stage builds let you create small, production-ready images by
separating build-time dependencies from runtime requirements.

## SECTION 6.1: THE SIZE PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY IMAGE SIZE MATTERS                                                 |
|                                                                         |
|  Large images cause:                                                    |
|  * Slow deployments (longer pull times)                                 |
|  * More storage costs                                                   |
|  * Larger attack surface (more packages = more vulnerabilities)         |
|  * Slower container startup                                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  TYPICAL GO APPLICATION                                                 |
|                                                                         |
|  BEFORE (Single-stage):                                                 |
|  +------------------------------------------------------------------+   |
|  | FROM golang:1.21                                                 |   |
|  |                                                                  |   |
|  | WORKDIR /app                                                     |   |
|  | COPY . .                                                         |   |
|  | RUN go build -o myapp                                            |   |
|  |                                                                  |   |
|  | CMD ["./myapp"]                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  Image size: ~1.1 GB!                                                   |
|                                                                         |
|  Contains:                                                              |
|  * Full Go compiler (not needed at runtime)                             |
|  * All build tools                                                      |
|  * Source code                                                          |
|  * Downloaded dependencies                                              |
|  * Your tiny 10MB binary                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6.2: MULTI-STAGE BUILD SOLUTION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MULTI-STAGE DOCKERFILE                                                 |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  | # Stage 1: Build                                                 |   |
|  | FROM golang:1.21 AS builder                                      |   |
|  |                                                                  |   |
|  | WORKDIR /app                                                     |   |
|  | COPY go.mod go.sum ./                                            |   |
|  | RUN go mod download                                              |   |
|  | COPY . .                                                         |   |
|  | RUN CGO_ENABLED=0 go build -o myapp                              |   |
|  |                                                                  |   |
|  | # Stage 2: Production                                            |   |
|  | FROM alpine:3.18                                                 |   |
|  |                                                                  |   |
|  | COPY --from=builder /app/myapp /myapp                            |   |
|  | CMD ["/myapp"]                                                   |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  Image size: ~15 MB!                                                    |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HOW IT WORKS                                                           |
|                                                                         |
|  +---------------------+      +---------------------+                   |
|  | Stage 1: builder    |      | Stage 2: final      |                   |
|  |                     |      |                     |                   |
|  | golang:1.21 (1.1GB) |      | alpine:3.18 (5MB)   |                   |
|  | + source code       |      | + your binary (10MB)|                   |
|  | + dependencies      | ---> |                     |                   |
|  | + build tools       | COPY | = 15MB total        |                   |
|  | = compile binary    | only |                     |                   |
|  |                     |binary|                     |                   |
|  +---------------------+      +---------------------+                   |
|        (discarded)                  (final image)                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6.3: LANGUAGE-SPECIFIC EXAMPLES

### NODE.JS MULTI-STAGE BUILD

```
+-------------------------------------------------------------------------+
|                                                                         |
|  # Stage 1: Build                                                       |
|  FROM node:20-alpine AS builder                                         |
|                                                                         |
|  WORKDIR /app                                                           |
|  COPY package*.json ./                                                  |
|  RUN npm ci                                                             |
|  COPY . .                                                               |
|  RUN npm run build                                                      |
|                                                                         |
|  # Stage 2: Production dependencies only                                |
|  FROM node:20-alpine AS deps                                            |
|                                                                         |
|  WORKDIR /app                                                           |
|  COPY package*.json ./                                                  |
|  RUN npm ci --only=production                                           |
|                                                                         |
|  # Stage 3: Final                                                       |
|  FROM node:20-alpine                                                    |
|                                                                         |
|  WORKDIR /app                                                           |
|  COPY --from=deps /app/node_modules ./node_modules                      |
|  COPY --from=builder /app/dist ./dist                                   |
|  COPY package*.json ./                                                  |
|                                                                         |
|  USER node                                                              |
|  CMD ["node", "dist/index.js"]                                          |
|                                                                         |
|  Result: No devDependencies, no source code, just production files      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### JAVA MULTI-STAGE BUILD

```
+-------------------------------------------------------------------------+
|                                                                         |
|  # Stage 1: Build with Maven                                            |
|  FROM maven:3.9-eclipse-temurin-17 AS builder                           |
|                                                                         |
|  WORKDIR /app                                                           |
|  COPY pom.xml .                                                         |
|  RUN mvn dependency:go-offline                                          |
|  COPY src ./src                                                         |
|  RUN mvn package -DskipTests                                            |
|                                                                         |
|  # Stage 2: Runtime only                                                |
|  FROM eclipse-temurin:17-jre-alpine                                     |
|                                                                         |
|  WORKDIR /app                                                           |
|  COPY --from=builder /app/target/*.jar app.jar                          |
|                                                                         |
|  USER 1000                                                              |
|  EXPOSE 8080                                                            |
|  CMD ["java", "-jar", "app.jar"]                                        |
|                                                                         |
|  Build image: ~800MB (Maven + JDK)                                      |
|  Final image: ~150MB (JRE only)                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### PYTHON MULTI-STAGE BUILD

```
+-------------------------------------------------------------------------+
|                                                                         |
|  # Stage 1: Build wheels                                                |
|  FROM python:3.11-slim AS builder                                       |
|                                                                         |
|  WORKDIR /app                                                           |
|  RUN apt-get update && apt-get install -y --no-install-recommends \     |
|      build-essential gcc                                                |
|                                                                         |
|  COPY requirements.txt .                                                |
|  RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt   |
|                                                                         |
|  # Stage 2: Production                                                  |
|  FROM python:3.11-slim                                                  |
|                                                                         |
|  WORKDIR /app                                                           |
|  COPY --from=builder /wheels /wheels                                    |
|  RUN pip install --no-cache-dir /wheels/*                               |
|                                                                         |
|  COPY . .                                                               |
|  USER 1000                                                              |
|  CMD ["python", "app.py"]                                               |
|                                                                         |
|  No build tools in final image (gcc, build-essential removed)           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6.4: ADVANCED TECHNIQUES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCRATCH IMAGE (Minimal possible)                                       |
|  =================================                                      |
|                                                                         |
|  For statically compiled binaries (Go, Rust).                           |
|  Zero base image-just your binary!                                      |
|                                                                         |
|  FROM golang:1.21 AS builder                                            |
|  WORKDIR /app                                                           |
|  COPY . .                                                               |
|  RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo \          |
|      -ldflags="-w -s" -o myapp                                          |
|                                                                         |
|  FROM scratch                                                           |
|  COPY --from=builder /app/myapp /myapp                                  |
|  COPY --from=builder /etc/ssl/certs/ca-certificates.crt \               |
|      /etc/ssl/certs/                                                    |
|  CMD ["/myapp"]                                                         |
|                                                                         |
|  Image size: ~5-10MB (just your binary + certs)                         |
|                                                                         |
|  Note: scratch has NO shell, no debugging tools                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DISTROLESS IMAGES (Google)                                             |
|  ===========================                                            |
|                                                                         |
|  Minimal images with just runtime, no shell or package manager.         |
|                                                                         |
|  FROM golang:1.21 AS builder                                            |
|  # ... build ...                                                        |
|                                                                         |
|  FROM gcr.io/distroless/static-debian12                                 |
|  COPY --from=builder /app/myapp /myapp                                  |
|  CMD ["/myapp"]                                                         |
|                                                                         |
|  Available distroless images:                                           |
|  * gcr.io/distroless/static (for static binaries)                       |
|  * gcr.io/distroless/base (glibc)                                       |
|  * gcr.io/distroless/java17                                             |
|  * gcr.io/distroless/python3                                            |
|  * gcr.io/distroless/nodejs18                                           |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  BUILD TARGET SELECTION                                                 |
|  =======================                                                |
|                                                                         |
|  Build specific stages for different purposes.                          |
|                                                                         |
|  FROM node:20-alpine AS base                                            |
|  WORKDIR /app                                                           |
|  COPY package*.json ./                                                  |
|                                                                         |
|  FROM base AS dev                                                       |
|  RUN npm install                                                        |
|  CMD ["npm", "run", "dev"]                                              |
|                                                                         |
|  FROM base AS test                                                      |
|  RUN npm ci                                                             |
|  COPY . .                                                               |
|  CMD ["npm", "test"]                                                    |
|                                                                         |
|  FROM base AS prod                                                      |
|  RUN npm ci --only=production                                           |
|  COPY . .                                                               |
|  CMD ["npm", "start"]                                                   |
|                                                                         |
|  # Build specific target:                                               |
|  docker build --target dev -t myapp:dev .                               |
|  docker build --target test -t myapp:test .                             |
|  docker build --target prod -t myapp:prod .                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6.5: OPTIMIZATION TIPS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IMAGE SIZE REDUCTION TECHNIQUES                                        |
|                                                                         |
|  1. USE SMALLER BASE IMAGES                                             |
|     ------------------------                                            |
|     node:20         > 1.1GB                                             |
|     node:20-slim    > 200MB                                             |
|     node:20-alpine  > 130MB                                             |
|                                                                         |
|  2. MINIMIZE LAYERS                                                     |
|     -----------------                                                   |
|     # Bad: 3 layers                                                     |
|     RUN apt-get update                                                  |
|     RUN apt-get install -y curl                                         |
|     RUN rm -rf /var/lib/apt/lists/*                                     |
|                                                                         |
|     # Good: 1 layer                                                     |
|     RUN apt-get update && \                                             |
|         apt-get install -y curl && \                                    |
|         rm -rf /var/lib/apt/lists/*                                     |
|                                                                         |
|  3. CLEAN UP IN SAME LAYER                                              |
|     ----------------------                                              |
|     # Cache cleaning must be in same RUN                                |
|     RUN pip install -r requirements.txt && \                            |
|         rm -rf ~/.cache/pip                                             |
|                                                                         |
|  4. USE .dockerignore                                                   |
|     ------------------                                                  |
|     # .dockerignore                                                     |
|     node_modules                                                        |
|     .git                                                                |
|     *.md                                                                |
|     Dockerfile                                                          |
|     .env                                                                |
|                                                                         |
|  5. ORDER LAYERS BY CHANGE FREQUENCY                                    |
|     ---------------------------------                                   |
|     # Rarely changes (cached)                                           |
|     COPY package.json .                                                 |
|     RUN npm install                                                     |
|                                                                         |
|     # Frequently changes (rebuild from here)                            |
|     COPY src ./src                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MULTI-STAGE BUILDS - KEY TAKEAWAYS                                     |
|                                                                         |
|  CONCEPT                                                                |
|  -------                                                                |
|  * Multiple FROM statements in one Dockerfile                           |
|  * Each FROM starts a new stage                                         |
|  * COPY --from=stagename copies between stages                          |
|  * Only final stage is in the output image                              |
|                                                                         |
|  BENEFITS                                                               |
|  --------                                                               |
|  * Smaller images (10-100x reduction possible)                          |
|  * Faster deployments                                                   |
|  * Fewer vulnerabilities                                                |
|  * Build tools not in production                                        |
|                                                                         |
|  BASE IMAGE CHOICES                                                     |
|  -------------------                                                    |
|  * alpine: Small, musl libc (some compatibility issues)                 |
|  * slim: Debian-based, smaller than full                                |
|  * distroless: No shell, minimal attack surface                         |
|  * scratch: Empty, for static binaries only                             |
|                                                                         |
|  COMMANDS                                                               |
|  --------                                                               |
|  docker build --target <stage> -t image:tag .                           |
|  COPY --from=<stage> /src /dest                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 6

