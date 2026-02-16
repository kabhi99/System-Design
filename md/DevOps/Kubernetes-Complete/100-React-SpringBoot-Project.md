# KUBERNETES REAL PROJECT: REACT + SPRING BOOT
*Deploy a Full-Stack Application (LOCAL with Minikube)*

This guide deploys a real-world application LOCALLY using Minikube:
- Frontend: React (served by Nginx)
- Backend: Spring Boot REST API
- Database: PostgreSQL

NO DOCKER HUB NEEDED! Images built directly in Minikube.

## ARCHITECTURE OVERVIEW

```
+-------------------------------------------------------------------------+
|                                                                         |
|                         FINAL ARCHITECTURE                              |
|                                                                         |
|                           INTERNET                                      |
|                              |                                          |
|                              | http://myapp.local                      |
|                              v                                          |
|  +-------------------------------------------------------------------+ |
|  |                    INGRESS CONTROLLER                              | |
|  |                                                                    | |
|  |     /  --------------------->  react-frontend (port 80)          | |
|  |     /api ------------------->  springboot-api (port 8080)        | |
|  |                                                                    | |
|  +-------------------------------------------------------------------+ |
|                     |                        |                          |
|                     v                        v                          |
|  +-------------------------+  +-------------------------------------+ |
|  |                         |  |                                      | |
|  |   FRONTEND SERVICE      |  |     BACKEND SERVICE                  | |
|  |   (ClusterIP)           |  |     (ClusterIP)                      | |
|  |   Port: 80              |  |     Port: 8080                       | |
|  |                         |  |                                      | |
|  |   +-----------------+   |  |   +-----------------+               | |
|  |   |   Deployment    |   |  |   |   Deployment    |               | |
|  |   |   replicas: 2   |   |  |   |   replicas: 2   |               | |
|  |   |                 |   |  |   |                 |               | |
|  |   |  +-----++-----+ |   |  |   |  +-----++-----+ |               | |
|  |   |  |React||React| |   |  |   |  | API || API | |               | |
|  |   |  |+Nginx|+Nginx| |   |  |   |  | Pod || Pod | |               | |
|  |   |  +-----++-----+ |   |  |   |  +-----++-----+ |               | |
|  |   +-----------------+   |  |   +--------+--------+               | |
|  |                         |  |            |                         | |
|  +-------------------------+  +------------+-------------------------+ |
|                                            |                            |
|                                            v                            |
|                               +-------------------------+              |
|                               |   POSTGRESQL SERVICE    |              |
|                               |   (ClusterIP)           |              |
|                               |   Port: 5432            |              |
|                               |                         |              |
|                               |   +-----------------+   |              |
|                               |   |  StatefulSet    |   |              |
|                               |   |    +-------+    |   |              |
|                               |   |    |  DB   |    |   |              |
|                               |   |    |  Pod  |    |   |              |
|                               |   |    +---+---+    |   |              |
|                               |   +--------+--------+   |              |
|                               |            |            |              |
|                               |       +----v----+       |              |
|                               |       |   PVC   |       |              |
|                               |       |   5Gi   |       |              |
|                               |       +---------+       |              |
|                               +-------------------------+              |
|                                                                         |
|  NAMESPACE: fullstack-app                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## STEP 0: START MINIKUBE

```bash
# Start minikube with enough resources
minikube start --cpus=4 --memory=4096

# Enable required addons
minikube addons enable ingress
minikube addons enable metrics-server
minikube addons enable storage-provisioner

# Verify
minikube status
kubectl get nodes
```

## PREREQUISITE: BUILD IMAGES IN MINIKUBE (NO DOCKER HUB!)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  📚 LOCAL DEVELOPMENT: Build images INSIDE Minikube                   |
|                                                                         |
|  IMPORTANT: Use Minikube's Docker daemon!                             |
|                                                                         |
|  Your Laptop                     Minikube VM                           |
|  +--------------------+         +--------------------------------+    |
|  |                    |         |                                |    |
|  |  source code       |         |  Docker daemon (inside VM)    |    |
|  |       |            |  eval   |       |                        |    |
|  |       |            | ------> |       |                        |    |
|  |  docker build      |         |  Images built HERE            |    |
|  |  (uses minikube's  |         |  Kubernetes can use them!     |    |
|  |   docker daemon)   |         |                                |    |
|  |                    |         |                                |    |
|  +--------------------+         +--------------------------------+    |
|                                                                         |
|  NO PUSH NEEDED! Images are already where Kubernetes can see them.   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  🔥 CRITICAL STEP: Connect to Minikube's Docker                        |
|  ============================================                           |
|                                                                         |
|  # Run this FIRST (in every new terminal!)                             |
|  eval $(minikube docker-env)                                           |
|                                                                         |
|  # Verify you're using minikube's Docker                               |
|  docker images                                                          |
|  # You should see k8s system images (pause, coredns, etc.)            |
|                                                                         |
|  # To go back to your local Docker later:                              |
|  eval $(minikube docker-env -u)                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DOCKERFILE FOR REACT FRONTEND

Create this file as: frontend/Dockerfile

```bash
# Stage 1: Build React app
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Set API URL (will be /api, Ingress routes to backend)
ENV REACT_APP_API_URL=/api

# Build the app
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy built files from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

Create this file as: frontend/nginx.conf

```bash
server {
    listen 80;
    server_name localhost;

    root /usr/share/nginx/html;
    index index.html;

    # Handle React Router (SPA)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Health check endpoint
    location /health {
        return 200 'healthy';
        add_header Content-Type text/plain;
    }
}
```

**BUILD IMAGE IN MINIKUBE:**

```bash
# STEP 1: Connect to Minikube's Docker (IMPORTANT!)
eval $(minikube docker-env)

# STEP 2: Build the image
cd frontend
docker build -t react-frontend:v1.0 .

# STEP 3: Verify image exists
docker images | grep react-frontend
# Should show: react-frontend   v1.0   ...

# (Optional) Test the image
docker run -p 3000:80 react-frontend:v1.0
# Visit http://localhost:3000 (Ctrl+C to stop)
```

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ⚠️  REMEMBER: In Kubernetes YAML, you MUST add:                       |
|                                                                         |
|  image: react-frontend:v1.0                                            |
|  imagePullPolicy: Never     < CRITICAL! Don't try to pull             |
|                                                                         |
|  Without "imagePullPolicy: Never", Kubernetes will try to pull        |
|  from Docker Hub and FAIL (image doesn't exist there).               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### DOCKERFILE FOR SPRING BOOT BACKEND

Create this file as: backend/Dockerfile

```bash
# Stage 1: Build with Maven
FROM maven:3.9-eclipse-temurin-17 AS builder

WORKDIR /app

# Copy pom.xml first (for dependency caching)
COPY pom.xml .

# Download dependencies (cached if pom.xml unchanged)
RUN mvn dependency:go-offline -B

# Copy source code
COPY src ./src

# Build the JAR
RUN mvn package -DskipTests -B

# Stage 2: Run with slim JRE
FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

# Copy JAR from builder
COPY --from=builder /app/target/*.jar app.jar

# Create non-root user
RUN addgroup -S spring && adduser -S spring -G spring
USER spring:spring

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget -q --spider http://localhost:8080/actuator/health || exit 1

# Run the app
ENTRYPOINT ["java", "-jar", "app.jar"]
```

### SPRING BOOT APPLICATION.PROPERTIES (for Kubernetes):

```bash
# src/main/resources/application.properties

# Server
server.port=8080

# Database (will be overridden by env vars in Kubernetes)
spring.datasource.url=jdbc:postgresql://${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME:myapp}
spring.datasource.username=${DB_USER:postgres}
spring.datasource.password=${DB_PASSWORD:postgres}

# JPA
spring.jpa.hibernate.ddl-auto=update
spring.jpa.show-sql=false

# Actuator (for health checks)
management.endpoints.web.exposure.include=health,info
management.endpoint.health.show-details=always
```

**BUILD IMAGE IN MINIKUBE:**

```bash
# STEP 1: Connect to Minikube's Docker (if not already done)
eval $(minikube docker-env)

# STEP 2: Build the image
cd backend
docker build -t springboot-api:v1.0 .

# STEP 3: Verify image exists
docker images | grep springboot-api
# Should show: springboot-api   v1.0   ...
```

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ⚠️  REMEMBER: In Kubernetes YAML, you MUST add:                       |
|                                                                         |
|  image: springboot-api:v1.0                                            |
|  imagePullPolicy: Never     < CRITICAL! Don't try to pull             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## STEP 1: CREATE NAMESPACE

```bash
# File: 01-namespace.yaml
-------------------------

apiVersion: v1
kind: Namespace
metadata:
  name: fullstack-app
  labels:
    app: fullstack
    environment: development
```

**COMMANDS:**
---------

```bash
kubectl apply -f 01-namespace.yaml
kubectl config set-context --current --namespace=fullstack-app
```

## STEP 2: CONFIGMAP AND SECRETS

```bash
# File: 02-config.yaml
-----------------------

apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: fullstack-app
data:
  # Database config (non-sensitive)
  DB_HOST: "postgres-service"
  DB_PORT: "5432"
  DB_NAME: "appdb"

  # Spring Boot config
  SPRING_PROFILES_ACTIVE: "prod"
  SERVER_PORT: "8080"

---

apiVersion: v1
kind: Secret
metadata:
  name: db-secret
  namespace: fullstack-app
type: Opaque
stringData:
  DB_USER: "appuser"
  DB_PASSWORD: "AppSecurePass123!"
  POSTGRES_USER: "appuser"
  POSTGRES_PASSWORD: "AppSecurePass123!"
  POSTGRES_DB: "appdb"
```

**COMMANDS:**
---------

```bash
kubectl apply -f 02-config.yaml

# Verify
kubectl get configmap
kubectl get secrets
```

## STEP 3: POSTGRESQL DATABASE

```bash
# File: 03-postgres.yaml
-------------------------

# PersistentVolumeClaim
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: fullstack-app
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: standard

---

# StatefulSet for PostgreSQL
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: fullstack-app
spec:
  serviceName: postgres-service
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:15-alpine
          ports:
            - containerPort: 5432
          envFrom:
            - secretRef:
                name: db-secret
          volumeMounts:
            - name: postgres-storage
              mountPath: /var/lib/postgresql/data
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          readinessProbe:
            exec:
              command:
                - pg_isready
                - -U
                - appuser
                - -d
                - appdb
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            exec:
              command:
                - pg_isready
                - -U
                - appuser
                - -d
                - appdb
            initialDelaySeconds: 30
            periodSeconds: 10
      volumes:
        - name: postgres-storage
          persistentVolumeClaim:
            claimName: postgres-pvc

---

# Service for PostgreSQL
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: fullstack-app
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
  clusterIP: None    # Headless service for StatefulSet
```

**COMMANDS:**
---------

```bash
kubectl apply -f 03-postgres.yaml

# Wait for PostgreSQL to be ready
kubectl get pods -w

# Verify database is running
kubectl logs postgres-0

# Test connection (optional)
kubectl exec -it postgres-0 -- psql -U appuser -d appdb -c "\dt"
```

```
+-------------------------------------------------------------------------+
|  ✅ EXPECTED: postgres-0 should be Running and Ready (1/1)             |
+-------------------------------------------------------------------------+
```

## STEP 4: SPRING BOOT BACKEND DEPLOYMENT

```bash
# File: 04-backend.yaml
------------------------

apiVersion: apps/v1
kind: Deployment
metadata:
  name: springboot-api
  namespace: fullstack-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: springboot-api
  template:
    metadata:
      labels:
        app: springboot-api
    spec:
      containers:
        - name: api
          image: springboot-api:v1.0           # Local image name
          imagePullPolicy: Never               # < CRITICAL for local!
          ports:
            - containerPort: 8080
          envFrom:
            - configMapRef:
                name: app-config
            - secretRef:
                name: db-secret
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1000m"
              memory: "1024Mi"
          readinessProbe:
            httpGet:
              path: /actuator/health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /actuator/health
              port: 8080
            initialDelaySeconds: 60
            periodSeconds: 10

---

apiVersion: v1
kind: Service
metadata:
  name: springboot-service
  namespace: fullstack-app
spec:
  selector:
    app: springboot-api
  ports:
    - port: 8080
      targetPort: 8080
  type: ClusterIP
```

```
+-------------------------------------------------------------------------+
|  🔍 UNDERSTAND THE CONFIG                                               |
|                                                                         |
|  envFrom:                                                               |
|    - configMapRef:                                                      |
|        name: app-config     < DB_HOST, DB_PORT become env vars         |
|    - secretRef:                                                         |
|        name: db-secret      < DB_USER, DB_PASSWORD become env vars     |
|                                                                         |
|  Spring Boot application.properties uses:                              |
|    spring.datasource.url=jdbc:postgresql://${DB_HOST}:${DB_PORT}/...  |
|                                                                         |
|  These env vars override the defaults!                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

**COMMANDS:**
---------

```bash
kubectl apply -f 04-backend.yaml

# Wait for pods to be ready
kubectl get pods -w

# Check logs for any errors
kubectl logs -l app=springboot-api --tail=50

# Test API internally
kubectl run test --rm -it --image=busybox -- wget -qO- http://springboot-service:8080/actuator/health
```

```
+-------------------------------------------------------------------------+
|  ✅ EXPECTED: 2 springboot-api pods Running and Ready (1/1)            |
|                                                                         |
|  ⚠️  IF PODS CRASH (CrashLoopBackOff):                                 |
|  1. Check logs: kubectl logs <pod-name>                                |
|  2. Common issues:                                                     |
|     - Database not ready (wait for postgres-0 first)                  |
|     - Wrong DB_HOST (should be postgres-service)                      |
|     - Wrong credentials                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## STEP 5: REACT FRONTEND DEPLOYMENT

```bash
# File: 05-frontend.yaml
-------------------------

apiVersion: apps/v1
kind: Deployment
metadata:
  name: react-frontend
  namespace: fullstack-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: react-frontend
  template:
    metadata:
      labels:
        app: react-frontend
    spec:
      containers:
        - name: frontend
          image: react-frontend:v1.0           # Local image name
          imagePullPolicy: Never               # < CRITICAL for local!
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "200m"
              memory: "256Mi"
          readinessProbe:
            httpGet:
              path: /health
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 80
            initialDelaySeconds: 10
            periodSeconds: 10

---

apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: fullstack-app
spec:
  selector:
    app: react-frontend
  ports:
    - port: 80
      targetPort: 80
  type: ClusterIP
```

**COMMANDS:**
---------

```bash
kubectl apply -f 05-frontend.yaml

# Wait for pods
kubectl get pods -w

# Verify all pods are running
kubectl get pods
```

```
+-------------------------------------------------------------------------+
|  ✅ AT THIS POINT YOU SHOULD HAVE:                                     |
|                                                                         |
|  $ kubectl get pods                                                    |
|  NAME                              READY   STATUS    AGE               |
|  postgres-0                        1/1     Running   5m                |
|  springboot-api-xxx-yyy            1/1     Running   3m                |
|  springboot-api-xxx-zzz            1/1     Running   3m                |
|  react-frontend-xxx-aaa            1/1     Running   1m                |
|  react-frontend-xxx-bbb            1/1     Running   1m                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## STEP 6: INGRESS (HTTP ROUTING)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  📚 HOW INGRESS ROUTES TRAFFIC                                         |
|                                                                         |
|  User Request: http://myapp.local/api/users                           |
|                                                                         |
|       |                                                                 |
|       v                                                                 |
|  +------------------------------------------------------------------+  |
|  |                    INGRESS CONTROLLER                             |  |
|  |                                                                   |  |
|  |  Path starts with /api?                                          |  |
|  |       |                                                           |  |
|  |       +-- YES --> Route to springboot-service:8080              |  |
|  |       |           (request: /api/users > backend gets /api/users)|  |
|  |       |                                                           |  |
|  |       +-- NO ---> Route to frontend-service:80                   |  |
|  |                   (request: / > React app)                       |  |
|  |                                                                   |  |
|  +------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

```bash
# File: 06-ingress.yaml
------------------------

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: fullstack-app
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
spec:
  ingressClassName: nginx
  rules:
    - host: myapp.local    # < Change to your domain in production
      http:
        paths:
          # API routes to backend
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: springboot-service
                port:
                  number: 8080

          # Everything else routes to frontend
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80
```

**COMMANDS:**
---------

```bash
kubectl apply -f 06-ingress.yaml

# Get Ingress details
kubectl get ingress
kubectl describe ingress app-ingress
```

**FOR MINIKUBE - ADD HOST ENTRY:**

```bash
# Get minikube IP
minikube ip
# Example output: 192.168.49.2

# Add to /etc/hosts (Linux/Mac) or C:\Windows\System32\drivers\etc\hosts (Windows)
# Add this line:
192.168.49.2    myapp.local

# Or use minikube tunnel (alternative)
minikube tunnel
```

**TEST THE APPLICATION:**

```bash
# Test frontend
curl http://myapp.local/
# Should return React HTML

# Test API
curl http://myapp.local/api/actuator/health
# Should return: {"status":"UP"}

# Or open in browser:
# http://myapp.local
```

## STEP 7: HORIZONTAL POD AUTOSCALER (Optional)

```bash
# File: 07-hpa.yaml
--------------------

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: fullstack-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: springboot-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

**COMMANDS:**
---------

```bash
kubectl apply -f 07-hpa.yaml

# Watch HPA status
kubectl get hpa -w
```

## COMPLETE FILE STRUCTURE

```
fullstack-k8s/
+-- 01-namespace.yaml
+-- 02-config.yaml
+-- 03-postgres.yaml
+-- 04-backend.yaml
+-- 05-frontend.yaml
+-- 06-ingress.yaml
+-- 07-hpa.yaml (optional)
```

## DEPLOYMENT ORDER (IMPORTANT!)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DEPLOY IN THIS ORDER:                                                 |
|                                                                         |
|  1. Namespace        (creates isolated environment)                    |
|        |                                                                |
|        v                                                                |
|  2. ConfigMap/Secret (backend needs these to start)                   |
|        |                                                                |
|        v                                                                |
|  3. PostgreSQL       (backend needs database to connect)              |
|        |                                                                |
|        |  WAIT until postgres-0 is Running!                           |
|        v                                                                |
|  4. Spring Boot API  (needs database ready)                           |
|        |                                                                |
|        |  WAIT until api pods are Running!                            |
|        v                                                                |
|  5. React Frontend   (can start anytime, but API should be ready)    |
|        |                                                                |
|        v                                                                |
|  6. Ingress          (routes traffic to frontend/backend)             |
|                                                                         |
+-------------------------------------------------------------------------+
```

**DEPLOY ALL AT ONCE:**

```bash
# Apply all files
kubectl apply -f 01-namespace.yaml
kubectl config set-context --current --namespace=fullstack-app
kubectl apply -f 02-config.yaml
kubectl apply -f 03-postgres.yaml

# Wait for postgres
kubectl wait --for=condition=ready pod/postgres-0 --timeout=120s

kubectl apply -f 04-backend.yaml

# Wait for backend
kubectl wait --for=condition=ready pod -l app=springboot-api --timeout=120s

kubectl apply -f 05-frontend.yaml
kubectl apply -f 06-ingress.yaml
```

## USEFUL COMMANDS

```bash
# View all resources
kubectl get all

# View logs
kubectl logs -l app=springboot-api --tail=100 -f
kubectl logs -l app=react-frontend --tail=100 -f

# Describe for troubleshooting
kubectl describe pod <pod-name>

# Execute into pod
kubectl exec -it <pod-name> -- /bin/sh

# Port forward for direct access (bypass Ingress)
kubectl port-forward svc/springboot-service 8080:8080
kubectl port-forward svc/frontend-service 3000:80

# Scale manually
kubectl scale deployment springboot-api --replicas=3

# View resource usage
kubectl top pods
```

## TROUBLESHOOTING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROBLEM: Backend pods in CrashLoopBackOff                             |
|  ------------------------------------------                            |
|  1. Check logs: kubectl logs <pod-name>                                |
|  2. Common causes:                                                     |
|     - Database not ready yet (wait for postgres-0)                    |
|     - Wrong DB_HOST (should be postgres-service)                      |
|     - Wrong credentials in secret                                      |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROBLEM: ImagePullBackOff                                             |
|  -------------------------                                             |
|  1. Image doesn't exist in registry                                   |
|  2. For minikube local images, add:                                   |
|     imagePullPolicy: Never                                             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROBLEM: Ingress not working                                          |
|  -----------------------------                                         |
|  1. Check ingress controller: kubectl get pods -n ingress-nginx       |
|  2. Enable in minikube: minikube addons enable ingress                |
|  3. Add host to /etc/hosts                                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  PROBLEM: API returns 502/503                                          |
|  ----------------------------                                          |
|  1. Backend pods not ready yet                                        |
|  2. Check readiness probe is passing                                  |
|  3. kubectl describe pod <backend-pod>                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CLEANUP

```bash
# Delete everything in namespace
kubectl delete namespace fullstack-app

# This deletes ALL resources we created!
```

## PRODUCTION CONSIDERATIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FOR PRODUCTION, ADD:                                                  |
|                                                                         |
|  1. TLS/HTTPS (cert-manager + Let's Encrypt)                          |
|  2. Network Policies (restrict pod-to-pod traffic)                    |
|  3. Resource Quotas per namespace                                     |
|  4. Pod Disruption Budgets                                            |
|  5. Managed PostgreSQL (RDS, Cloud SQL) instead of StatefulSet       |
|  6. External Secrets Manager (not Kubernetes secrets)                 |
|  7. CI/CD pipeline for deployments                                    |
|  8. Monitoring (Prometheus + Grafana)                                 |
|  9. Logging (EFK stack or CloudWatch)                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## QUICK START: COMPLETE LOCAL SETUP (Copy-Paste Ready)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  Run these commands in order to deploy everything locally:             |
|                                                                         |
+-------------------------------------------------------------------------+

# =======================================================================
# PART 1: SETUP MINIKUBE
# =======================================================================
```

```
minikube start --cpus=4 --memory=4096
minikube addons enable ingress
minikube addons enable metrics-server
minikube addons enable storage-provisioner

# =======================================================================
# PART 2: BUILD DOCKER IMAGES (inside Minikube)
# =======================================================================

# Connect to Minikube's Docker
eval $(minikube docker-env)

# Build frontend
cd /path/to/your/react-project
docker build -t react-frontend:v1.0 .

# Build backend
cd /path/to/your/springboot-project
docker build -t springboot-api:v1.0 .

# Verify images
docker images | grep -E "react-frontend|springboot-api"

# =======================================================================
# PART 3: CREATE KUBERNETES YAML FILES
# =======================================================================

mkdir -p ~/fullstack-k8s
cd ~/fullstack-k8s

# Create all YAML files (copy from sections above)
# Or use this all-in-one command:

cat > all-in-one.yaml << 'EOF'
# -------------------------------------------------------------------------
# NAMESPACE
# -------------------------------------------------------------------------
apiVersion: v1
kind: Namespace
metadata:
  name: fullstack-app
---
# -------------------------------------------------------------------------
# CONFIGMAP
# -------------------------------------------------------------------------
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: fullstack-app
data:
  DB_HOST: "postgres-service"
  DB_PORT: "5432"
  DB_NAME: "appdb"
---
# -------------------------------------------------------------------------
# SECRETS
# -------------------------------------------------------------------------
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
  namespace: fullstack-app
type: Opaque
stringData:
  DB_USER: "appuser"
  DB_PASSWORD: "AppSecurePass123!"
  POSTGRES_USER: "appuser"
  POSTGRES_PASSWORD: "AppSecurePass123!"
  POSTGRES_DB: "appdb"
---
# -------------------------------------------------------------------------
# POSTGRESQL PVC
# -------------------------------------------------------------------------
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: fullstack-app
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: standard
---
# -------------------------------------------------------------------------
# POSTGRESQL STATEFULSET
# -------------------------------------------------------------------------
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: fullstack-app
spec:
  serviceName: postgres-service
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:15-alpine
          ports:
            - containerPort: 5432
          envFrom:
            - secretRef:
                name: db-secret
          volumeMounts:
            - name: postgres-storage
              mountPath: /var/lib/postgresql/data
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
      volumes:
        - name: postgres-storage
          persistentVolumeClaim:
            claimName: postgres-pvc
---
# -------------------------------------------------------------------------
# POSTGRESQL SERVICE (Headless)
# -------------------------------------------------------------------------
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: fullstack-app
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
  clusterIP: None
---
# -------------------------------------------------------------------------
# SPRING BOOT DEPLOYMENT
# -------------------------------------------------------------------------
apiVersion: apps/v1
kind: Deployment
metadata:
  name: springboot-api
  namespace: fullstack-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: springboot-api
  template:
    metadata:
      labels:
        app: springboot-api
    spec:
      containers:
        - name: api
          image: springboot-api:v1.0
          imagePullPolicy: Never
          ports:
            - containerPort: 8080
          envFrom:
            - configMapRef:
                name: app-config
            - secretRef:
                name: db-secret
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1000m"
              memory: "1024Mi"
          readinessProbe:
            httpGet:
              path: /actuator/health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /actuator/health
              port: 8080
            initialDelaySeconds: 60
            periodSeconds: 10
---
# -------------------------------------------------------------------------
# SPRING BOOT SERVICE
# -------------------------------------------------------------------------
apiVersion: v1
kind: Service
metadata:
  name: springboot-service
  namespace: fullstack-app
spec:
  selector:
    app: springboot-api
  ports:
    - port: 8080
      targetPort: 8080
  type: ClusterIP
---
# -------------------------------------------------------------------------
# REACT DEPLOYMENT
# -------------------------------------------------------------------------
apiVersion: apps/v1
kind: Deployment
metadata:
  name: react-frontend
  namespace: fullstack-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: react-frontend
  template:
    metadata:
      labels:
        app: react-frontend
    spec:
      containers:
        - name: frontend
          image: react-frontend:v1.0
          imagePullPolicy: Never
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "200m"
              memory: "256Mi"
---
# -------------------------------------------------------------------------
# REACT SERVICE
# -------------------------------------------------------------------------
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: fullstack-app
spec:
  selector:
    app: react-frontend
  ports:
    - port: 80
      targetPort: 80
  type: ClusterIP
---
# -------------------------------------------------------------------------
# INGRESS
# -------------------------------------------------------------------------
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: fullstack-app
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
    - host: myapp.local
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: springboot-service
                port:
                  number: 8080
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80
EOF

# =======================================================================
# PART 4: DEPLOY TO KUBERNETES
# =======================================================================

kubectl apply -f all-in-one.yaml

# Set namespace
kubectl config set-context --current --namespace=fullstack-app

# Watch pods come up
kubectl get pods -w
# Wait until all pods show "Running" and "1/1" Ready
# Press Ctrl+C when ready

# =======================================================================
# PART 5: CONFIGURE LOCAL ACCESS
# =======================================================================

# Get Minikube IP
MINIKUBE_IP=$(minikube ip)
echo "Minikube IP: $MINIKUBE_IP"

# Add to /etc/hosts (requires sudo)
echo "$MINIKUBE_IP    myapp.local" | sudo tee -a /etc/hosts

# =======================================================================
# PART 6: TEST YOUR APPLICATION!
# =======================================================================

# Open in browser
open http://myapp.local           # Mac
# Or: xdg-open http://myapp.local # Linux

# Test API
curl http://myapp.local/api/actuator/health

# View all resources
kubectl get all

# View logs
kubectl logs -l app=springboot-api --tail=50
kubectl logs -l app=react-frontend --tail=50
```

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ✅ SUCCESS CHECKLIST                                                  |
|                                                                         |
|  □ minikube status shows "Running"                                     |
|  □ docker images shows react-frontend:v1.0 and springboot-api:v1.0    |
|  □ kubectl get pods shows 5 pods Running (1 postgres, 2 api, 2 react) |
|  □ http://myapp.local shows React app                                  |
|  □ http://myapp.local/api/actuator/health returns {"status":"UP"}     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CLEANUP (Delete Everything)

```bash
# Delete all resources
kubectl delete namespace fullstack-app

# Stop minikube
minikube stop

# Delete minikube cluster entirely (optional)
minikube delete
```

## END OF REACT + SPRING BOOT PROJECT

