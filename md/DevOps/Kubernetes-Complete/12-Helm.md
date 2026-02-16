# KUBERNETES HELM
*Chapter 12: Package Management*

Helm is the package manager for Kubernetes, simplifying deployment
of complex applications.

## SECTION 12.1: WHY HELM? (The Problem It Solves)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM: DEPLOYING A REAL APPLICATION IS COMPLEX                 |
|  =====================================================                  |
|                                                                         |
|  To deploy a simple web app, you need MULTIPLE YAML files:            |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |   deployment.yaml       (the app containers)                   |   |
|  |   service.yaml          (networking)                           |   |
|  |   ingress.yaml          (external access)                      |   |
|  |   configmap.yaml        (configuration)                        |   |
|  |   secret.yaml           (passwords)                            |   |
|  |   pvc.yaml              (storage)                              |   |
|  |   serviceaccount.yaml   (permissions)                          |   |
|  |   hpa.yaml              (autoscaling)                          |   |
|  |                                                                 |   |
|  |   That's 8+ files for ONE application!                        |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  PROBLEMS WITHOUT HELM:                                                |
|                                                                         |
|  1. TOO MANY FILES TO MANAGE                                          |
|     kubectl apply -f deployment.yaml                                  |
|     kubectl apply -f service.yaml                                     |
|     kubectl apply -f configmap.yaml                                   |
|     ... repeat for each file, in correct order!                      |
|                                                                         |
|  2. HARDCODED VALUES                                                   |
|     # deployment.yaml for DEV                                         |
|     replicas: 1                                                       |
|     image: myapp:dev                                                  |
|                                                                         |
|     # deployment.yaml for PROD (different file!)                     |
|     replicas: 10                                                      |
|     image: myapp:v1.2.3                                               |
|                                                                         |
|     -> Need separate YAML files for each environment!                 |
|                                                                         |
|  3. NO VERSIONING / ROLLBACK                                          |
|     "We deployed broken code, how do we go back?"                    |
|     -> Manually re-apply old YAMLs (if you saved them!)              |
|                                                                         |
|  4. INSTALLING THIRD-PARTY APPS IS HARD                               |
|     Want to install MySQL? Redis? Prometheus?                        |
|     -> Find all the YAMLs, understand them, customize them...        |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  THE SOLUTION: HELM                                                    |
|  ===================                                                    |
|                                                                         |
|  Think of Helm like apt/yum for Linux or npm for JavaScript:          |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |   Linux:      apt install mysql                                |   |
|  |   JavaScript: npm install express                              |   |
|  |   Kubernetes: helm install mysql bitnami/mysql                 |   |
|  |                                                                 |   |
|  |   ONE command installs everything needed!                      |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
|  WHAT HELM DOES:                                                       |
|                                                                         |
|  1. PACKAGES MULTIPLE YAMLS INTO ONE "CHART"                          |
|     +------------------------------------------------------------+    |
|     |  MySQL Chart contains:                                      |    |
|     |  * Deployment (MySQL server)                               |    |
|     |  * Service (networking)                                    |    |
|     |  * Secret (root password)                                  |    |
|     |  * PVC (data storage)                                      |    |
|     |  * ConfigMap (mysql.cnf)                                   |    |
|     |                                                             |    |
|     |  ALL in one package, deployed with ONE command!            |    |
|     +------------------------------------------------------------+    |
|                                                                         |
|  2. TEMPLATING (Same chart, different values)                         |
|     +------------------------------------------------------------+    |
|     |                                                             |    |
|     |  # DEV install                                             |    |
|     |  helm install mysql bitnami/mysql \                        |    |
|     |    --set replicas=1 \                                      |    |
|     |    --set persistence.size=1Gi                              |    |
|     |                                                             |    |
|     |  # PROD install                                            |    |
|     |  helm install mysql bitnami/mysql \                        |    |
|     |    --set replicas=3 \                                      |    |
|     |    --set persistence.size=100Gi                            |    |
|     |                                                             |    |
|     |  SAME chart, DIFFERENT configuration!                      |    |
|     |                                                             |    |
|     +------------------------------------------------------------+    |
|                                                                         |
|  3. VERSIONING & ROLLBACK                                             |
|     helm upgrade mysql bitnami/mysql --set replicas=5                |
|     # Oops, something broke!                                          |
|     helm rollback mysql 1   <- Go back to previous version            |
|                                                                         |
|  4. EASY THIRD-PARTY INSTALLS                                         |
|     helm install prometheus prometheus-community/prometheus           |
|     helm install grafana grafana/grafana                             |
|     helm install redis bitnami/redis                                 |
|     # Complex apps installed in seconds!                             |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  HELM ANALOGY: Restaurant Menu                                        |
|  ==============================                                         |
|                                                                         |
|  WITHOUT HELM (ordering ingredients):                                 |
|  -------------------------------------                                 |
|  "I want a burger. Please bring me:                                   |
|   - 200g beef patty, cooked medium                                   |
|   - 1 sesame bun, toasted                                            |
|   - 2 slices tomato                                                  |
|   - 1 leaf lettuce                                                   |
|   - 30g cheddar cheese, melted                                       |
|   - 15ml ketchup                                                     |
|   - 10ml mustard                                                     |
|   ... assemble in this specific order..."                            |
|                                                                         |
|  WITH HELM (ordering from menu):                                      |
|  ---------------------------------                                     |
|  "I want a burger, extra cheese, no mustard"                         |
|                                                                         |
|  The CHART is the recipe (all ingredients + instructions)            |
|  The VALUES are your customizations (extra cheese, no mustard)       |
|  The RELEASE is the actual burger you get                            |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  WITHOUT HELM vs WITH HELM                                            |
|  ==========================                                             |
|                                                                         |
|  DEPLOYING MYSQL WITHOUT HELM:                                        |
|  ------------------------------                                        |
|                                                                         |
|  # 1. Find/create all YAML files                                      |
|  # 2. Apply in correct order                                          |
|  kubectl apply -f mysql-secret.yaml                                   |
|  kubectl apply -f mysql-configmap.yaml                                |
|  kubectl apply -f mysql-pvc.yaml                                      |
|  kubectl apply -f mysql-statefulset.yaml                              |
|  kubectl apply -f mysql-service.yaml                                  |
|                                                                         |
|  # 3. To change config, edit multiple files                          |
|  # 4. To delete, remember all resources                               |
|  kubectl delete -f mysql-secret.yaml                                  |
|  kubectl delete -f mysql-configmap.yaml                               |
|  ...                                                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  DEPLOYING MYSQL WITH HELM:                                           |
|  ---------------------------                                           |
|                                                                         |
|  # Install with one command                                           |
|  helm install my-mysql bitnami/mysql \                               |
|    --set auth.rootPassword=secret123 \                               |
|    --set primary.persistence.size=20Gi                               |
|                                                                         |
|  # Upgrade                                                             |
|  helm upgrade my-mysql bitnami/mysql --set replicas=3                |
|                                                                         |
|  # Delete everything                                                   |
|  helm uninstall my-mysql                                              |
|                                                                         |
|  MUCH SIMPLER!                                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12.2: HELM TERMINOLOGY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY TERMS EXPLAINED                                                   |
|  ====================                                                   |
|                                                                         |
|  +-------------+----------------------------------------------------+  |
|  | Term        | What It Is                                         |  |
|  +-------------+----------------------------------------------------+  |
|  | CHART       | A package containing all K8s YAML templates       |  |
|  |             | Like: apt package, npm package                     |  |
|  |             | Example: bitnami/mysql, prometheus/prometheus     |  |
|  +-------------+----------------------------------------------------+  |
|  | RELEASE     | A deployed instance of a chart                    |  |
|  |             | You can install same chart multiple times         |  |
|  |             | Example: "my-mysql" is a release of mysql chart   |  |
|  +-------------+----------------------------------------------------+  |
|  | VALUES      | Configuration for customizing the chart           |  |
|  |             | Example: replicas=3, image.tag=v2.0               |  |
|  +-------------+----------------------------------------------------+  |
|  | REPOSITORY  | Where charts are stored (like apt repo)           |  |
|  |             | Example: bitnami, prometheus-community            |  |
|  +-------------+----------------------------------------------------+  |
|  | TEMPLATE    | YAML file with placeholders ({{ .Values.x }})    |  |
|  |             | Helm fills in values when installing              |  |
|  +-------------+----------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  CHART vs RELEASE (Important!)                                        |
|  =============================                                          |
|                                                                         |
|  CHART = Recipe (reusable)                                            |
|  RELEASE = Actual dish made from recipe (instance)                    |
|                                                                         |
|  +-----------------------------------------------------------------+   |
|  |                                                                 |   |
|  |   bitnami/mysql (CHART)                                        |   |
|  |          |                                                      |   |
|  |          +----> helm install orders-db bitnami/mysql           |   |
|  |          |      RELEASE: orders-db                             |   |
|  |          |                                                      |   |
|  |          +----> helm install users-db bitnami/mysql            |   |
|  |          |      RELEASE: users-db                              |   |
|  |          |                                                      |   |
|  |          +----> helm install analytics-db bitnami/mysql        |   |
|  |                 RELEASE: analytics-db                          |   |
|  |                                                                 |   |
|  |   ONE chart -> THREE releases (3 different MySQL instances)    |   |
|  |                                                                 |   |
|  +-----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS HELM?                                                         |
|                                                                         |
|  * Package manager for Kubernetes (like apt, yum, npm)               |
|  * Charts: Packages of K8s resources                                 |
|  * Releases: Instances of charts                                     |
|  * Templating: Customize deployments                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  HELM CHART STRUCTURE                                                  |
|                                                                         |
|  mychart/                                                              |
|  +-- Chart.yaml        # Chart metadata                              |
|  +-- values.yaml       # Default configuration                       |
|  +-- templates/        # Kubernetes manifests (templated)            |
|  |   +-- deployment.yaml                                             |
|  |   +-- service.yaml                                                |
|  |   +-- ingress.yaml                                                |
|  |   +-- _helpers.tpl  # Template helpers                           |
|  |   +-- NOTES.txt     # Post-install notes                         |
|  +-- charts/           # Dependencies                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12.2: BASIC COMMANDS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  INSTALL AND MANAGE                                                    |
|  ==================                                                    |
|                                                                         |
|  # Add repository                                                      |
|  helm repo add bitnami https://charts.bitnami.com/bitnami            |
|  helm repo update                                                      |
|                                                                         |
|  # Search charts                                                       |
|  helm search repo nginx                                                |
|                                                                         |
|  # Install chart                                                       |
|  helm install my-nginx bitnami/nginx                                  |
|                                                                         |
|  # Install with custom values                                         |
|  helm install my-nginx bitnami/nginx -f custom-values.yaml           |
|  helm install my-nginx bitnami/nginx --set replicaCount=3            |
|                                                                         |
|  # List releases                                                       |
|  helm list                                                              |
|                                                                         |
|  # Upgrade release                                                     |
|  helm upgrade my-nginx bitnami/nginx --set replicaCount=5            |
|                                                                         |
|  # Rollback                                                            |
|  helm rollback my-nginx 1                                             |
|                                                                         |
|  # Uninstall                                                           |
|  helm uninstall my-nginx                                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12.3: VALUES AND TEMPLATING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  values.yaml                                                           |
|  ===========                                                            |
|                                                                         |
|  replicaCount: 3                                                       |
|  image:                                                                 |
|    repository: nginx                                                   |
|    tag: "1.25"                                                         |
|  service:                                                               |
|    type: ClusterIP                                                     |
|    port: 80                                                            |
|  resources:                                                             |
|    limits:                                                              |
|      cpu: 100m                                                         |
|      memory: 128Mi                                                     |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  templates/deployment.yaml                                             |
|  ==========================                                            |
|                                                                         |
|  apiVersion: apps/v1                                                   |
|  kind: Deployment                                                       |
|  metadata:                                                              |
|    name: {{ .Release.Name }}-nginx                                    |
|  spec:                                                                  |
|    replicas: {{ .Values.replicaCount }}                               |
|    template:                                                            |
|      spec:                                                              |
|        containers:                                                      |
|          - name: nginx                                                 |
|            image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"|
|            resources:                                                   |
|              {{- toYaml .Values.resources | nindent 14 }}             |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  TEMPLATE FUNCTIONS                                                    |
|                                                                         |
|  {{ .Values.key }}         Access values                              |
|  {{ .Release.Name }}       Release name                               |
|  {{ .Chart.Name }}         Chart name                                 |
|  {{ default "val" .Values.x }}  Default value                        |
|  {{ if .Values.enabled }}   Conditionals                             |
|  {{ range .Values.list }}   Loops                                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12.4: CREATE YOUR OWN CHART

```
+-------------------------------------------------------------------------+
|                                                                         |
|  # Create new chart                                                    |
|  helm create mychart                                                   |
|                                                                         |
|  # Test template rendering                                            |
|  helm template mychart ./mychart                                      |
|                                                                         |
|  # Lint chart                                                          |
|  helm lint ./mychart                                                   |
|                                                                         |
|  # Dry run install                                                     |
|  helm install --dry-run --debug myrelease ./mychart                  |
|                                                                         |
|  # Package chart                                                       |
|  helm package ./mychart                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HELM - KEY TAKEAWAYS                                                 |
|                                                                         |
|  CONCEPTS                                                              |
|  --------                                                              |
|  * Chart: Package of K8s resources                                   |
|  * Release: Deployed instance                                        |
|  * Values: Configuration                                             |
|                                                                         |
|  COMMANDS                                                              |
|  --------                                                              |
|  helm install/upgrade/rollback/uninstall                             |
|  helm list                                                             |
|  helm repo add/update                                                  |
|                                                                         |
|  TEMPLATING                                                            |
|  ----------                                                            |
|  {{ .Values.x }}, {{ .Release.Name }}                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 12

