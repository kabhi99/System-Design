# KUBECTL COMMANDS QUICK REFERENCE
*Essential Commands with Examples*

kubectl is the CLI tool to interact with Kubernetes clusters.
This file provides syntax and examples for the most common operations.

## SECTION 1: BASIC SYNTAX

```
+--------------------------------------------------------------------------+
|                                                                          |
|  KUBECTL COMMAND STRUCTURE                                               |
|                                                                          |
|  kubectl [command] [TYPE] [NAME] [flags]                                 |
|          |         |      |      |                                       |
|          |         |      |      +-- Options: -n namespace, -o yaml      |
|          |         |      +-- Resource name (optional)                   |
|          |         +-- Resource type: pod, service, deployment, etc.     |
|          +-- Action: get, create, delete, apply, describe, logs          |
|                                                                          |
|  EXAMPLES:                                                               |
|  kubectl get pods                      # List all pods                   |
|  kubectl get pod nginx                 # Get specific pod                |
|  kubectl get pods -n kube-system       # Pods in specific namespace      |
|  kubectl get pods -o wide              # More details                    |
|  kubectl get pods -o yaml              # Full YAML output                |
|                                                                          |
+--------------------------------------------------------------------------+
```

### RESOURCE TYPE SHORTCUTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  COMMON RESOURCE ABBREVIATIONS                                          |
|                                                                         |
|  +----------------------+-------------+----------------------------+    |
|  | Full Name            | Short       | Example                     |   |
|  +----------------------+-------------+----------------------------+    |
|  | pods                 | po          | kubectl get po             |    |
|  | services             | svc         | kubectl get svc            |    |
|  | deployments          | deploy      | kubectl get deploy         |    |
|  | replicasets          | rs          | kubectl get rs             |    |
|  | namespaces           | ns          | kubectl get ns             |    |
|  | nodes                | no          | kubectl get no             |    |
|  | configmaps           | cm          | kubectl get cm             |    |
|  | secrets              | secret      | kubectl get secret         |    |
|  | persistentvolumes    | pv          | kubectl get pv             |    |
|  | persistentvolumeclaim| pvc         | kubectl get pvc            |    |
|  | serviceaccounts      | sa          | kubectl get sa             |    |
|  | ingresses            | ing         | kubectl get ing            |    |
|  | daemonsets           | ds          | kubectl get ds             |    |
|  | statefulsets         | sts         | kubectl get sts            |    |
|  | cronjobs             | cj          | kubectl get cj             |    |
|  | horizontalpodauto... | hpa         | kubectl get hpa            |    |
|  +----------------------+-------------+----------------------------+    |
|                                                                         |
|  # List all resource types                                              |
|  kubectl api-resources                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 2: CLUSTER & CONTEXT

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CLUSTER INFORMATION                                                    |
|                                                                         |
|  # View cluster info                                                    |
|  kubectl cluster-info                                                   |
|                                                                         |
|  # View nodes                                                           |
|  kubectl get nodes                                                      |
|  kubectl get nodes -o wide                                              |
|                                                                         |
|  # Node details                                                         |
|  kubectl describe node <node-name>                                      |
|                                                                         |
|  # View all resources in cluster                                        |
|  kubectl get all                                                        |
|  kubectl get all -A                     # All namespaces                |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  CONTEXT MANAGEMENT (Multiple Clusters)                                 |
|                                                                         |
|  # View current context                                                 |
|  kubectl config current-context                                         |
|                                                                         |
|  # List all contexts                                                    |
|  kubectl config get-contexts                                            |
|                                                                         |
|  # Switch context                                                       |
|  kubectl config use-context <context-name>                              |
|                                                                         |
|  # Set default namespace for current context                            |
|  kubectl config set-context --current --namespace=<namespace>           |
|                                                                         |
|  EXAMPLE:                                                               |
|  kubectl config use-context production-cluster                          |
|  kubectl config set-context --current --namespace=backend               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3: PODS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LISTING PODS                                                           |
|                                                                         |
|  kubectl get pods                       # Current namespace             |
|  kubectl get pods -A                    # All namespaces                |
|  kubectl get pods -n kube-system        # Specific namespace            |
|  kubectl get pods -o wide               # Show node, IP                 |
|  kubectl get pods -o yaml               # Full YAML                     |
|  kubectl get pods --show-labels         # Show labels                   |
|  kubectl get pods -l app=nginx          # Filter by label               |
|  kubectl get pods --watch               # Watch for changes             |
|  kubectl get pods --field-selector status.phase=Running                 |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  CREATING PODS                                                          |
|                                                                         |
|  # Imperative (quick testing)                                           |
|  kubectl run nginx --image=nginx                                        |
|  kubectl run nginx --image=nginx --port=80                              |
|  kubectl run nginx --image=nginx --dry-run=client -o yaml               |
|                                                                         |
|  # Declarative (from YAML file)                                         |
|  kubectl apply -f pod.yaml                                              |
|  kubectl create -f pod.yaml                                             |
|                                                                         |
|  EXAMPLE POD YAML:                                                      |
|  ------------------                                                     |
|  apiVersion: v1                                                         |
|  kind: Pod                                                              |
|  metadata:                                                              |
|    name: nginx-pod                                                      |
|    labels:                                                              |
|      app: nginx                                                         |
|  spec:                                                                  |
|    containers:                                                          |
|    - name: nginx                                                        |
|      image: nginx:1.21                                                  |
|      ports:                                                             |
|      - containerPort: 80                                                |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  POD DETAILS & DEBUGGING                                                |
|                                                                         |
|  # Describe pod (events, status, etc.)                                  |
|  kubectl describe pod <pod-name>                                        |
|                                                                         |
|  # View logs                                                            |
|  kubectl logs <pod-name>                                                |
|  kubectl logs <pod-name> -c <container>  # Multi-container pod          |
|  kubectl logs <pod-name> -f              # Follow logs                  |
|  kubectl logs <pod-name> --tail=100      # Last 100 lines               |
|  kubectl logs <pod-name> --previous      # Previous container logs      |
|                                                                         |
|  # Execute commands in pod                                              |
|  kubectl exec <pod-name> -- ls /                                        |
|  kubectl exec <pod-name> -- cat /etc/nginx/nginx.conf                   |
|  kubectl exec -it <pod-name> -- /bin/bash    # Interactive shell        |
|  kubectl exec -it <pod-name> -- /bin/sh      # If no bash               |
|  kubectl exec -it <pod-name> -c <container> -- /bin/bash                |
|                                                                         |
|  # Copy files to/from pod                                               |
|  kubectl cp <pod-name>:/path/to/file ./local-file                       |
|  kubectl cp ./local-file <pod-name>:/path/to/file                       |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  DELETING PODS                                                          |
|                                                                         |
|  kubectl delete pod <pod-name>                                          |
|  kubectl delete pod <pod-name> --force --grace-period=0                 |
|  kubectl delete pods -l app=nginx        # By label                     |
|  kubectl delete -f pod.yaml              # From file                    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 4: DEPLOYMENTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CREATING DEPLOYMENTS                                                   |
|                                                                         |
|  # Imperative                                                           |
|  kubectl create deployment nginx --image=nginx                          |
|  kubectl create deployment nginx --image=nginx --replicas=3             |
|  kubectl create deployment nginx --image=nginx --dry-run=client -o yaml |
|                                                                         |
|  # Declarative                                                          |
|  kubectl apply -f deployment.yaml                                       |
|                                                                         |
|  EXAMPLE DEPLOYMENT YAML:                                               |
|  -------------------------                                              |
|  apiVersion: apps/v1                                                    |
|  kind: Deployment                                                       |
|  metadata:                                                              |
|    name: nginx-deployment                                               |
|  spec:                                                                  |
|    replicas: 3                                                          |
|    selector:                                                            |
|      matchLabels:                                                       |
|        app: nginx                                                       |
|    template:                                                            |
|      metadata:                                                          |
|        labels:                                                          |
|          app: nginx                                                     |
|      spec:                                                              |
|        containers:                                                      |
|        - name: nginx                                                    |
|          image: nginx:1.21                                              |
|          ports:                                                         |
|          - containerPort: 80                                            |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  MANAGING DEPLOYMENTS                                                   |
|                                                                         |
|  # List deployments                                                     |
|  kubectl get deployments                                                |
|  kubectl get deploy -o wide                                             |
|                                                                         |
|  # Describe deployment                                                  |
|  kubectl describe deployment <name>                                     |
|                                                                         |
|  # Scale deployment                                                     |
|  kubectl scale deployment <name> --replicas=5                           |
|                                                                         |
|  # Update image (rolling update)                                        |
|  kubectl set image deployment/<name> <container>=<new-image>            |
|  kubectl set image deployment/nginx nginx=nginx:1.22                    |
|                                                                         |
|  # Rollout status                                                       |
|  kubectl rollout status deployment/<name>                               |
|                                                                         |
|  # Rollout history                                                      |
|  kubectl rollout history deployment/<name>                              |
|                                                                         |
|  # Rollback                                                             |
|  kubectl rollout undo deployment/<name>                                 |
|  kubectl rollout undo deployment/<name> --to-revision=2                 |
|                                                                         |
|  # Pause/Resume rollout                                                 |
|  kubectl rollout pause deployment/<name>                                |
|  kubectl rollout resume deployment/<name>                               |
|                                                                         |
|  # Restart all pods (rolling restart)                                   |
|  kubectl rollout restart deployment/<name>                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5: SERVICES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CREATING SERVICES                                                      |
|                                                                         |
|  # Expose deployment as service                                         |
|  kubectl expose deployment <name> --port=80 --target-port=8080          |
|  kubectl expose deployment <name> --type=NodePort --port=80             |
|  kubectl expose deployment <name> --type=LoadBalancer --port=80         |
|                                                                         |
|  # Create service from pod                                              |
|  kubectl expose pod <pod-name> --port=80 --name=my-service              |
|                                                                         |
|  # Declarative                                                          |
|  kubectl apply -f service.yaml                                          |
|                                                                         |
|  SERVICE TYPES:                                                         |
|  ---------------                                                        |
|  ClusterIP    > Internal only (default)                                 |
|  NodePort     > External via node port (30000-32767)                    |
|  LoadBalancer > External via cloud LB                                   |
|  ExternalName > DNS alias                                               |
|                                                                         |
|  EXAMPLE SERVICE YAML (ClusterIP):                                      |
|  -----------------------------------                                    |
|  apiVersion: v1                                                         |
|  kind: Service                                                          |
|  metadata:                                                              |
|    name: nginx-service                                                  |
|  spec:                                                                  |
|    selector:                                                            |
|      app: nginx                                                         |
|    ports:                                                               |
|    - port: 80            # Service port                                 |
|      targetPort: 8080    # Container port                               |
|    type: ClusterIP                                                      |
|                                                                         |
|  EXAMPLE SERVICE YAML (NodePort):                                       |
|  ----------------------------------                                     |
|  apiVersion: v1                                                         |
|  kind: Service                                                          |
|  metadata:                                                              |
|    name: nginx-nodeport                                                 |
|  spec:                                                                  |
|    type: NodePort                                                       |
|    selector:                                                            |
|      app: nginx                                                         |
|    ports:                                                               |
|    - port: 80                                                           |
|      targetPort: 8080                                                   |
|      nodePort: 30080     # Optional: auto-assigned if not specified     |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  MANAGING SERVICES                                                      |
|                                                                         |
|  kubectl get services                                                   |
|  kubectl get svc -o wide                                                |
|  kubectl describe service <name>                                        |
|  kubectl delete service <name>                                          |
|                                                                         |
|  # Get endpoints (pods backing service)                                 |
|  kubectl get endpoints <service-name>                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 6: CONFIGMAPS & SECRETS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONFIGMAPS                                                             |
|                                                                         |
|  # Create from literal                                                  |
|  kubectl create configmap my-config --from-literal=key1=value1          |
|  kubectl create configmap my-config \                                   |
|      --from-literal=DB_HOST=mysql \                                     |
|      --from-literal=DB_PORT=3306                                        |
|                                                                         |
|  # Create from file                                                     |
|  kubectl create configmap my-config --from-file=config.properties       |
|  kubectl create configmap my-config --from-file=./config-dir/           |
|                                                                         |
|  # Create from env file                                                 |
|  kubectl create configmap my-config --from-env-file=app.env             |
|                                                                         |
|  # View configmap                                                       |
|  kubectl get configmap                                                  |
|  kubectl get cm my-config -o yaml                                       |
|  kubectl describe configmap my-config                                   |
|                                                                         |
|  EXAMPLE CONFIGMAP YAML:                                                |
|  -------------------------                                              |
|  apiVersion: v1                                                         |
|  kind: ConfigMap                                                        |
|  metadata:                                                              |
|    name: app-config                                                     |
|  data:                                                                  |
|    DB_HOST: "mysql-service"                                             |
|    DB_PORT: "3306"                                                      |
|    config.json: |                                                       |
|      {                                                                  |
|        "logLevel": "info",                                              |
|        "maxConnections": 100                                            |
|      }                                                                  |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  SECRETS                                                                |
|                                                                         |
|  # Create generic secret                                                |
|  kubectl create secret generic my-secret \                              |
|      --from-literal=username=admin \                                    |
|      --from-literal=password=secret123                                  |
|                                                                         |
|  # Create from file                                                     |
|  kubectl create secret generic tls-secret \                             |
|      --from-file=tls.crt=server.crt \                                   |
|      --from-file=tls.key=server.key                                     |
|                                                                         |
|  # Create docker-registry secret                                        |
|  kubectl create secret docker-registry regcred \                        |
|      --docker-server=https://index.docker.io/v1/ \                      |
|      --docker-username=myuser \                                         |
|      --docker-password=mypass \                                         |
|      --docker-email=email@example.com                                   |
|                                                                         |
|  # View secrets                                                         |
|  kubectl get secrets                                                    |
|  kubectl get secret my-secret -o yaml                                   |
|  kubectl describe secret my-secret                                      |
|                                                                         |
|  # Decode secret value (base64)                                         |
|  kubectl get secret my-secret -o jsonpath='{.data.password}' | base64 -d|
|                                                                         |
|  EXAMPLE SECRET YAML:                                                   |
|  ----------------------                                                 |
|  apiVersion: v1                                                         |
|  kind: Secret                                                           |
|  metadata:                                                              |
|    name: db-credentials                                                 |
|  type: Opaque                                                           |
|  data:                                                                  |
|    username: YWRtaW4=        # base64 encoded "admin"                   |
|    password: c2VjcmV0MTIz    # base64 encoded "secret123"               |
|                                                                         |
|  # To encode: echo -n 'admin' | base64                                  |
|  # To decode: echo 'YWRtaW4=' | base64 -d                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 7: NAMESPACES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NAMESPACE COMMANDS                                                     |
|                                                                         |
|  # List namespaces                                                      |
|  kubectl get namespaces                                                 |
|  kubectl get ns                                                         |
|                                                                         |
|  # Create namespace                                                     |
|  kubectl create namespace my-namespace                                  |
|  kubectl create ns dev                                                  |
|                                                                         |
|  # Delete namespace (deletes all resources in it!)                      |
|  kubectl delete namespace my-namespace                                  |
|                                                                         |
|  # Run command in specific namespace                                    |
|  kubectl get pods -n kube-system                                        |
|  kubectl get all -n my-namespace                                        |
|                                                                         |
|  # Set default namespace                                                |
|  kubectl config set-context --current --namespace=my-namespace          |
|                                                                         |
|  # View current namespace                                               |
|  kubectl config view --minify | grep namespace                          |
|                                                                         |
|  DEFAULT NAMESPACES:                                                    |
|  --------------------                                                   |
|  default         > Default for resources without namespace              |
|  kube-system     > Kubernetes system components                         |
|  kube-public     > Publicly accessible data                             |
|  kube-node-lease > Node heartbeat leases                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8: LABELS & SELECTORS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WORKING WITH LABELS                                                    |
|                                                                         |
|  # Add label to resource                                                |
|  kubectl label pod <pod-name> env=prod                                  |
|  kubectl label node <node-name> disk=ssd                                |
|                                                                         |
|  # Update existing label                                                |
|  kubectl label pod <pod-name> env=staging --overwrite                   |
|                                                                         |
|  # Remove label                                                         |
|  kubectl label pod <pod-name> env-                                      |
|                                                                         |
|  # Show labels                                                          |
|  kubectl get pods --show-labels                                         |
|                                                                         |
|  # Filter by label                                                      |
|  kubectl get pods -l app=nginx                                          |
|  kubectl get pods -l app=nginx,env=prod                                 |
|  kubectl get pods -l 'env in (prod,staging)'                            |
|  kubectl get pods -l 'env notin (dev)'                                  |
|  kubectl get pods -l app!=frontend                                      |
|                                                                         |
|  LABEL SELECTORS:                                                       |
|  -----------------                                                      |
|  -l app=nginx             # Equality                                    |
|  -l app!=nginx            # Inequality                                  |
|  -l 'env in (a,b)'        # Set-based (in)                              |
|  -l 'env notin (a,b)'     # Set-based (not in)                          |
|  -l app                   # Exists                                      |
|  -l '!app'                # Does not exist                              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9: APPLY, CREATE, DELETE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  APPLY vs CREATE                                                        |
|                                                                         |
|  kubectl create -f file.yaml                                            |
|  * Creates resource                                                     |
|  * FAILS if resource already exists                                     |
|                                                                         |
|  kubectl apply -f file.yaml                                             |
|  * Creates if doesn't exist                                             |
|  * Updates if exists (declarative)                                      |
|  * RECOMMENDED for production                                           |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  APPLY COMMANDS                                                         |
|                                                                         |
|  # Apply single file                                                    |
|  kubectl apply -f deployment.yaml                                       |
|                                                                         |
|  # Apply all files in directory                                         |
|  kubectl apply -f ./manifests/                                          |
|                                                                         |
|  # Apply from URL                                                       |
|  kubectl apply -f https://raw.githubusercontent.com/.../deployment.yaml |
|                                                                         |
|  # Apply with record (for rollback history)                             |
|  kubectl apply -f deployment.yaml --record                              |
|                                                                         |
|  # Dry run (validate without applying)                                  |
|  kubectl apply -f deployment.yaml --dry-run=client                      |
|  kubectl apply -f deployment.yaml --dry-run=server                      |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  DELETE COMMANDS                                                        |
|                                                                         |
|  # Delete by name                                                       |
|  kubectl delete pod nginx                                               |
|  kubectl delete deployment nginx                                        |
|  kubectl delete service nginx                                           |
|                                                                         |
|  # Delete from file                                                     |
|  kubectl delete -f deployment.yaml                                      |
|  kubectl delete -f ./manifests/                                         |
|                                                                         |
|  # Delete by label                                                      |
|  kubectl delete pods -l app=nginx                                       |
|                                                                         |
|  # Delete all of a type                                                 |
|  kubectl delete pods --all                                              |
|  kubectl delete pods --all -n my-namespace                              |
|                                                                         |
|  # Force delete (stuck pods)                                            |
|  kubectl delete pod nginx --force --grace-period=0                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 10: EDITING & PATCHING

```
+-------------------------------------------------------------------------------------------+
|                                                                                           |
|  EDIT (Opens in editor)                                                                   |
|                                                                                           |
|  kubectl edit deployment nginx                                                            |
|  kubectl edit svc nginx                                                                   |
|  kubectl edit configmap my-config                                                         |
|                                                                                           |
|  # Set editor                                                                             |
|  KUBE_EDITOR="nano" kubectl edit deployment nginx                                         |
|                                                                                           |
+-------------------------------------------------------------------------------------------+
|                                                                                           |
|  PATCH (Inline update)                                                                    |
|                                                                                           |
|  # Update replicas                                                                        |
|  kubectl patch deployment nginx -p '{"spec":{"replicas":5}}'                              |
|                                                                                           |
|  # Update image                                                                           |
|  kubectl patch deployment nginx -p \                                                      |
|    '{"spec":{"template":{"spec":{"containers":[{"name":"nginx","image":"nginx:1.22"}]}}}}'|
|                                                                                           |
|  # Add annotation                                                                         |
|  kubectl patch deployment nginx -p \                                                      |
|    '{"metadata":{"annotations":{"version":"v2"}}}'                                        |
|                                                                                           |
+-------------------------------------------------------------------------------------------+
|                                                                                           |
|  SET (Shortcut commands)                                                                  |
|                                                                                           |
|  # Update image                                                                           |
|  kubectl set image deployment/nginx nginx=nginx:1.22                                      |
|                                                                                           |
|  # Update environment variable                                                            |
|  kubectl set env deployment/nginx LOG_LEVEL=debug                                         |
|                                                                                           |
|  # Update resources                                                                       |
|  kubectl set resources deployment/nginx \                                                 |
|      --limits=cpu=200m,memory=512Mi \                                                     |
|      --requests=cpu=100m,memory=256Mi                                                     |
|                                                                                           |
+-------------------------------------------------------------------------------------------+
```

## SECTION 11: DEBUGGING & TROUBLESHOOTING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DESCRIBE (Detailed info + events)                                      |
|                                                                         |
|  kubectl describe pod <pod-name>                                        |
|  kubectl describe deployment <name>                                     |
|  kubectl describe service <name>                                        |
|  kubectl describe node <node-name>                                      |
|                                                                         |
|  # Shows: Status, Events, Conditions, Resource usage                    |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  LOGS                                                                   |
|                                                                         |
|  kubectl logs <pod-name>                                                |
|  kubectl logs <pod-name> -f                    # Follow                 |
|  kubectl logs <pod-name> --tail=50             # Last 50 lines          |
|  kubectl logs <pod-name> --since=1h            # Last hour              |
|  kubectl logs <pod-name> --timestamps          # With timestamps        |
|  kubectl logs <pod-name> -c <container>        # Specific container     |
|  kubectl logs <pod-name> --previous            # Previous instance      |
|  kubectl logs -l app=nginx                     # All pods with label    |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  EXEC (Run commands in container)                                       |
|                                                                         |
|  kubectl exec <pod-name> -- <command>                                   |
|  kubectl exec <pod-name> -- ls /                                        |
|  kubectl exec <pod-name> -- cat /etc/hosts                              |
|  kubectl exec <pod-name> -- env                                         |
|  kubectl exec -it <pod-name> -- /bin/bash      # Interactive shell      |
|  kubectl exec -it <pod-name> -- /bin/sh        # If no bash             |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  PORT-FORWARD (Local access to pods/services)                           |
|                                                                         |
|  # Forward pod port                                                     |
|  kubectl port-forward pod/<pod-name> 8080:80                            |
|                                                                         |
|  # Forward service port                                                 |
|  kubectl port-forward svc/<service-name> 8080:80                        |
|                                                                         |
|  # Forward deployment                                                   |
|  kubectl port-forward deployment/<name> 8080:80                         |
|                                                                         |
|  # Listen on all interfaces                                             |
|  kubectl port-forward --address 0.0.0.0 pod/nginx 8080:80               |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  EVENTS                                                                 |
|                                                                         |
|  kubectl get events                                                     |
|  kubectl get events --sort-by='.lastTimestamp'                          |
|  kubectl get events -n kube-system                                      |
|  kubectl get events --field-selector type=Warning                       |
|                                                                         |
+-------------------------------------------------------------------------+
|                                                                         |
|  TOP (Resource usage - requires metrics-server)                         |
|                                                                         |
|  kubectl top nodes                                                      |
|  kubectl top pods                                                       |
|  kubectl top pods -n kube-system                                        |
|  kubectl top pod <pod-name> --containers                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 12: OUTPUT FORMATTING

```
+--------------------------------------------------------------------------------------+
|                                                                                      |
|  OUTPUT OPTIONS (-o flag)                                                            |
|                                                                                      |
|  kubectl get pods -o wide                  # Additional columns                      |
|  kubectl get pods -o yaml                  # Full YAML                               |
|  kubectl get pods -o json                  # Full JSON                               |
|  kubectl get pods -o name                  # Just names                              |
|                                                                                      |
|  # Custom columns                                                                    |
|  kubectl get pods -o custom-columns=\                                                |
|    NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName                      |
|                                                                                      |
|  # JSONPath                                                                          |
|  kubectl get pods -o jsonpath='{.items[*].metadata.name}'                            |
|  kubectl get pod nginx -o jsonpath='{.spec.containers[0].image}'                     |
|  kubectl get nodes -o jsonpath='{.items[*].status.addresses[0].address}'             |
|                                                                                      |
|  # Go template                                                                       |
|  kubectl get pods -o go-template=\                                                   |
|    '{{range .items}}{{.metadata.name}}{{"\n"}}{{end}}'                               |
|                                                                                      |
+--------------------------------------------------------------------------------------+
|                                                                                      |
|  USEFUL EXAMPLES                                                                     |
|                                                                                      |
|  # Get all pod names                                                                 |
|  kubectl get pods -o jsonpath='{.items[*].metadata.name}'                            |
|                                                                                      |
|  # Get all images in cluster                                                         |
|  kubectl get pods -o jsonpath='{.items[*].spec.containers[*].image}'                 |
|                                                                                      |
|  # Get pod IPs                                                                       |
|  kubectl get pods -o jsonpath='{.items[*].status.podIP}'                             |
|                                                                                      |
|  # Get node IPs                                                                      |
|  kubectl get nodes -o jsonpath=\                                                     |
|    '{range .items[*]}{.metadata.name}{"\t"}{.status.addresses[0].address}{"\n"}{end}'|
|                                                                                      |
+--------------------------------------------------------------------------------------+
```

## SECTION 13: DRY-RUN & GENERATE YAML

```
+-------------------------------------------------------------------------+
|                                                                         |
|  GENERATE YAML WITHOUT CREATING                                         |
|                                                                         |
|  # Pod                                                                  |
|  kubectl run nginx --image=nginx --dry-run=client -o yaml               |
|                                                                         |
|  # Deployment                                                           |
|  kubectl create deployment nginx --image=nginx \                        |
|      --dry-run=client -o yaml                                           |
|                                                                         |
|  # Service                                                              |
|  kubectl expose deployment nginx --port=80 \                            |
|      --dry-run=client -o yaml                                           |
|                                                                         |
|  # ConfigMap                                                            |
|  kubectl create configmap my-config \                                   |
|      --from-literal=key=value \                                         |
|      --dry-run=client -o yaml                                           |
|                                                                         |
|  # Secret                                                               |
|  kubectl create secret generic my-secret \                              |
|      --from-literal=pass=secret \                                       |
|      --dry-run=client -o yaml                                           |
|                                                                         |
|  # Job                                                                  |
|  kubectl create job my-job --image=busybox \                            |
|      --dry-run=client -o yaml -- /bin/sh -c "echo hello"                |
|                                                                         |
|  # CronJob                                                              |
|  kubectl create cronjob my-cron --image=busybox \                       |
|      --schedule="*/5 * * * *" \                                         |
|      --dry-run=client -o yaml -- /bin/sh -c "date"                      |
|                                                                         |
|  REDIRECT TO FILE:                                                      |
|  -----------------                                                      |
|  kubectl create deployment nginx --image=nginx \                        |
|      --dry-run=client -o yaml > deployment.yaml                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 14: QUICK REFERENCE CHEAT SHEET

```
+--------------------------------------------------------------------------+
|                                                                          |
|  MOST USED COMMANDS                                                      |
|                                                                          |
|  # VIEWING                                                               |
|  kubectl get pods                          # List pods                   |
|  kubectl get pods -A                       # All namespaces              |
|  kubectl get all                           # All resources               |
|  kubectl describe pod <name>               # Details + events            |
|  kubectl logs <pod>                        # View logs                   |
|  kubectl logs <pod> -f                     # Follow logs                 |
|                                                                          |
|  # CREATING                                                              |
|  kubectl apply -f file.yaml                # Create/update               |
|  kubectl run nginx --image=nginx           # Quick pod                   |
|  kubectl create deployment app --image=img # Quick deployment            |
|  kubectl expose deployment app --port=80   # Quick service               |
|                                                                          |
|  # MODIFYING                                                             |
|  kubectl scale deploy <name> --replicas=3  # Scale                       |
|  kubectl set image deploy/<name> c=img:v2  # Update image                |
|  kubectl edit deployment <name>            # Edit in editor              |
|  kubectl rollout restart deploy/<name>     # Rolling restart             |
|                                                                          |
|  # DEBUGGING                                                             |
|  kubectl exec -it <pod> -- /bin/bash       # Shell into pod              |
|  kubectl port-forward pod/<name> 8080:80   # Local access                |
|  kubectl get events --sort-by='.lastTimestamp'                           |
|  kubectl top pods                          # Resource usage              |
|                                                                          |
|  # DELETING                                                              |
|  kubectl delete pod <name>                 # Delete pod                  |
|  kubectl delete -f file.yaml               # Delete from file            |
|  kubectl delete pods -l app=nginx          # Delete by label             |
|                                                                          |
|  # YAML GENERATION                                                       |
|  kubectl run nginx --image=nginx --dry-run=client -o yaml                |
|                                                                          |
+--------------------------------------------------------------------------+
```

## END OF KUBECTL COMMANDS

