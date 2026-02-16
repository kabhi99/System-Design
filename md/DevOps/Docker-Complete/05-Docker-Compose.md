# CHAPTER 5: DOCKER COMPOSE
*Managing Multi-Container Applications*

Real applications rarely run as a single container. They need databases,
caches, message queues, and more. Docker Compose helps you define and run
multi-container applications with a simple YAML file.

## SECTION 5.1: WHAT IS DOCKER COMPOSE?

### THE MULTI-CONTAINER PROBLEM

A typical web application needs:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TYPICAL APPLICATION STACK                                             |
|                                                                         |
|  +-------------+   +-------------+   +-------------+   +-----------+  |
|  |   Web App   |-->|    API     |-->|  Database   |   |   Redis   |  |
|  |   (nginx)   |   |   (node)    |-->|  (postgres) |   |  (cache)  |  |
|  +-------------+   +-------------+   +-------------+   +-----------+  |
|                                                                         |
|  WITHOUT COMPOSE - Manual commands for each:                          |
|                                                                         |
|  docker network create myapp                                          |
|  docker volume create db-data                                         |
|  docker run -d --name postgres --network myapp \                      |
|    -v db-data:/var/lib/postgresql/data \                             |
|    -e POSTGRES_PASSWORD=secret postgres                               |
|  docker run -d --name redis --network myapp redis                     |
|  docker run -d --name api --network myapp \                          |
|    -e DATABASE_URL=postgres://... myapi                              |
|  docker run -d --name web --network myapp -p 80:80 nginx             |
|                                                                         |
|   Complex, error-prone, hard to remember                            |
|                                                                         |
|  WITH COMPOSE:                                                        |
|                                                                         |
|  docker-compose up -d                                                 |
|                                                                         |
|   One command, all services start correctly                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DOCKER COMPOSE FEATURES

- Define multi-container applications in YAML
- Create and start all services with one command
- Automatic network creation and service discovery
- Volume management
- Environment variable management
- Dependency ordering
- Easy scaling

## SECTION 5.2: DOCKER-COMPOSE.YML STRUCTURE

### BASIC STRUCTURE

```yaml
version: "3.8"               # Compose file version

services:                     # Container definitions
  web:                        # Service name
    image: nginx:alpine
    ports:
      - "80:80"

  api:
    build: ./api              # Build from Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - db

  db:
    image: postgres:14
    volumes:
      - db-data:/var/lib/postgresql/data

volumes:                      # Named volumes
  db-data:

networks:                     # Custom networks (optional)
  frontend:
  backend:
```

### SERVICE CONFIGURATION OPTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SERVICE OPTIONS                                                       |
|                                                                         |
|  IMAGE:                                                                |
|  ------                                                                |
|  image: nginx:alpine                                                  |
|  image: myregistry.com/myapp:v1.0                                    |
|                                                                         |
|  BUILD:                                                                |
|  ------                                                                |
|  # Simple                                                              |
|  build: ./directory                                                   |
|                                                                         |
|  # With options                                                       |
|  build:                                                               |
|    context: ./directory                                               |
|    dockerfile: Dockerfile.prod                                        |
|    args:                                                              |
|      NODE_ENV: production                                            |
|                                                                         |
|  PORTS:                                                                |
|  ------                                                                |
|  ports:                                                               |
|    - "8080:80"              # host:container                         |
|    - "3000"                 # random host port                        |
|    - "127.0.0.1:8080:80"    # localhost only                         |
|                                                                         |
|  ENVIRONMENT:                                                          |
|  ------------                                                          |
|  environment:                                                         |
|    - NODE_ENV=production                                             |
|    - DATABASE_URL=postgres://...                                     |
|  # Or                                                                 |
|  environment:                                                         |
|    NODE_ENV: production                                              |
|    DATABASE_URL: postgres://...                                      |
|  # Or from file                                                       |
|  env_file:                                                           |
|    - .env                                                            |
|                                                                         |
|  VOLUMES:                                                              |
|  --------                                                              |
|  volumes:                                                             |
|    - db-data:/var/lib/postgresql/data  # Named volume               |
|    - ./src:/app/src                     # Bind mount                 |
|    - /app/node_modules                  # Anonymous volume           |
|                                                                         |
|  NETWORKS:                                                             |
|  ---------                                                             |
|  networks:                                                            |
|    - frontend                                                         |
|    - backend                                                          |
|                                                                         |
|  DEPENDS_ON:                                                           |
|  -----------                                                           |
|  depends_on:                                                          |
|    - db                                                               |
|    - redis                                                            |
|  # With condition (Compose v2)                                       |
|  depends_on:                                                          |
|    db:                                                                |
|      condition: service_healthy                                      |
|                                                                         |
|  HEALTHCHECK:                                                          |
|  ------------                                                          |
|  healthcheck:                                                         |
|    test: ["CMD", "curl", "-f", "http://localhost/"]                  |
|    interval: 30s                                                      |
|    timeout: 10s                                                       |
|    retries: 3                                                         |
|    start_period: 40s                                                 |
|                                                                         |
|  RESTART POLICY:                                                       |
|  ---------------                                                       |
|  restart: "no"              # Never restart                          |
|  restart: always            # Always restart                         |
|  restart: on-failure        # Only on failure                        |
|  restart: unless-stopped    # Unless manually stopped                |
|                                                                         |
|  RESOURCES (Compose v3):                                               |
|  -----------------------                                               |
|  deploy:                                                              |
|    resources:                                                         |
|      limits:                                                          |
|        cpus: '0.50'                                                  |
|        memory: 512M                                                  |
|      reservations:                                                    |
|        cpus: '0.25'                                                  |
|        memory: 256M                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.3: NETWORKING IN COMPOSE

### AUTOMATIC NETWORKING

Compose automatically creates a network for your application:

```
+-------------------------------------------------------------------------+
|                                                                         |
|  AUTOMATIC NETWORK CREATION                                            |
|                                                                         |
|  # docker-compose.yml                                                  |
|  version: "3.8"                                                        |
|  services:                                                             |
|    web:                                                               |
|      image: nginx                                                     |
|    api:                                                               |
|      image: myapi                                                     |
|    db:                                                                |
|      image: postgres                                                  |
|                                                                         |
|  Running: docker-compose up                                           |
|                                                                         |
|  Creates network: myproject_default                                   |
|                                                                         |
|  +-----------------------------------------------------------------+  |
|  |               myproject_default network                         |  |
|  |                                                                 |  |
|  |  +---------+    +---------+    +---------+                    |  |
|  |  |   web   |    |   api   |    |   db    |                    |  |
|  |  |         |--->|         |--->|         |                    |  |
|  |  |         |    |         |    |         |                    |  |
|  |  +---------+    +---------+    +---------+                    |  |
|  |                                                                 |  |
|  |  DNS RESOLUTION:                                               |  |
|  |  * api can reach db at hostname "db"                          |  |
|  |  * web can reach api at hostname "api"                        |  |
|  |  * No need to know IP addresses!                              |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### CUSTOM NETWORKS

Define custom networks for isolation:

```yaml
version: "3.8"

services:
  web:
    image: nginx
    networks:
      - frontend

  api:
    image: myapi
    networks:
      - frontend
      - backend

  db:
    image: postgres
    networks:
      - backend

networks:
  frontend:
  backend:
    internal: true    # No external access!
```

## SECTION 5.4: COMPOSE COMMANDS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DOCKER COMPOSE COMMANDS                                               |
|                                                                         |
|  STARTING/STOPPING:                                                    |
|  ------------------                                                    |
|  docker-compose up                 # Start all services               |
|  docker-compose up -d              # Start in background              |
|  docker-compose up --build         # Rebuild images first             |
|  docker-compose up api db          # Start specific services          |
|  docker-compose down               # Stop and remove containers       |
|  docker-compose down -v            # Also remove volumes              |
|  docker-compose stop               # Stop without removing            |
|  docker-compose start              # Start stopped services           |
|  docker-compose restart            # Restart services                 |
|                                                                         |
|  VIEWING STATUS:                                                       |
|  ---------------                                                       |
|  docker-compose ps                 # List services                    |
|  docker-compose logs               # View all logs                    |
|  docker-compose logs -f            # Follow logs                      |
|  docker-compose logs api           # Logs for specific service        |
|  docker-compose top                # View running processes           |
|                                                                         |
|  EXECUTING COMMANDS:                                                   |
|  -------------------                                                   |
|  docker-compose exec api bash      # Shell in running container      |
|  docker-compose run api npm test   # Run one-off command             |
|  docker-compose run --rm api bash  # Run and remove                  |
|                                                                         |
|  BUILDING:                                                             |
|  ---------                                                             |
|  docker-compose build              # Build all images                 |
|  docker-compose build api          # Build specific service           |
|  docker-compose build --no-cache   # Without cache                    |
|                                                                         |
|  SCALING (older syntax):                                               |
|  -----------------------                                               |
|  docker-compose up -d --scale api=3                                  |
|                                                                         |
|  CONFIGURATION:                                                        |
|  --------------                                                        |
|  docker-compose config             # Validate and view config        |
|  docker-compose config --services  # List services                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.5: COMPLETE EXAMPLE - FULL STACK APPLICATION

### PROJECT STRUCTURE

```
myapp/
+-- docker-compose.yml
+-- docker-compose.override.yml    # Development overrides
+-- docker-compose.prod.yml        # Production overrides
+-- .env
+-- frontend/
|   +-- Dockerfile
|   +-- src/
+-- api/
|   +-- Dockerfile
|   +-- src/
+-- nginx/
    +-- nginx.conf
```

### DOCKER-COMPOSE.YML (BASE)

```yaml
version: "3.8"

services:
  # NGINX Reverse Proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - frontend
      - api
    networks:
      - frontend-net

  # Frontend (React)
  frontend:
    build: ./frontend
    environment:
      - REACT_APP_API_URL=/api
    networks:
      - frontend-net

  # API (Node.js)
  api:
    build: ./api
    environment:
      - NODE_ENV=${NODE_ENV:-development}
      - DATABASE_URL=postgres://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - frontend-net
      - backend-net

  # PostgreSQL Database
  db:
    image: postgres:14-alpine
    environment:
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=${DB_NAME}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend-net

  # Redis Cache
  redis:
    image: redis:alpine
    volumes:
      - redis-data:/data
    networks:
      - backend-net

volumes:
  postgres-data:
  redis-data:

networks:
  frontend-net:
  backend-net:
    internal: true    # No external access to backend
```

.ENV FILE
---------

```bash
# .env
NODE_ENV=development
DB_USER=myapp
DB_PASSWORD=secretpassword
DB_NAME=myapp_db
```

### DOCKER-COMPOSE.OVERRIDE.YML (DEVELOPMENT)

```bash
# Automatically loaded with docker-compose up
version: "3.8"

services:
  frontend:
    build:
      context: ./frontend
      target: development
    volumes:
      - ./frontend/src:/app/src    # Hot reload
    environment:
      - CHOKIDAR_USEPOLLING=true

  api:
    build:
      context: ./api
      target: development
    volumes:
      - ./api/src:/app/src         # Hot reload
    command: npm run dev
```

### DOCKER-COMPOSE.PROD.YML (PRODUCTION)

```yaml
version: "3.8"

services:
  nginx:
    restart: always

  frontend:
    restart: always
    deploy:
      resources:
        limits:
          memory: 512M

  api:
    restart: always
    environment:
      - NODE_ENV=production
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

  db:
    restart: always
    deploy:
      resources:
        limits:
          memory: 2G

  redis:
    restart: always
```

### RUNNING IN DIFFERENT ENVIRONMENTS

```bash
# Development (uses docker-compose.override.yml automatically)
docker-compose up -d

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or with COMPOSE_FILE env variable
export COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml
docker-compose up -d
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DOCKER COMPOSE - KEY TAKEAWAYS                                        |
|                                                                         |
|  PURPOSE                                                               |
|  -------                                                               |
|  * Define multi-container applications                                |
|  * One command to start everything                                    |
|  * Automatic networking and service discovery                         |
|                                                                         |
|  KEY CONCEPTS                                                          |
|  ------------                                                          |
|  * services: Container definitions                                    |
|  * volumes: Data persistence                                          |
|  * networks: Service communication                                    |
|  * depends_on: Startup order                                          |
|                                                                         |
|  ESSENTIAL COMMANDS                                                    |
|  -----------------                                                     |
|  docker-compose up -d         # Start services                        |
|  docker-compose down          # Stop and remove                       |
|  docker-compose logs -f       # Follow logs                           |
|  docker-compose exec          # Run commands                          |
|  docker-compose ps            # List services                         |
|                                                                         |
|  BEST PRACTICES                                                        |
|  --------------                                                        |
|  * Use .env for secrets                                               |
|  * Separate dev/prod configs                                          |
|  * Use healthchecks                                                   |
|  * Define restart policies                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 5

