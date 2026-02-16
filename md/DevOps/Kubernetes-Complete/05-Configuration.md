# KUBERNETES CONFIGURATION
*Chapter 5: ConfigMaps and Secrets*

Kubernetes separates configuration from application code using
ConfigMaps and Secrets. This enables the same image to run in
different environments.

## SECTION 5.1: WHY EXTERNAL CONFIGURATION?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE PROBLEM: HARDCODED CONFIGURATION                                   |
|  ====================================                                   |
|                                                                         |
|  Without ConfigMaps/Secrets:                                            |
|                                                                         |
|  # Dockerfile                                                           |
|  ENV DB_HOST=prod-mysql.company.com                                     |
|  ENV DB_PASSWORD=supersecret123                                         |
|                                                                         |
|  PROBLEMS:                                                              |
|                                                                         |
|  1. REBUILD FOR EVERY ENVIRONMENT                                       |
|     * Dev needs DB_HOST=dev-mysql                                       |
|     * Staging needs DB_HOST=staging-mysql                               |
|     * Prod needs DB_HOST=prod-mysql                                     |
|     * 3 different images for SAME code!                                 |
|                                                                         |
|  2. SECRETS IN SOURCE CODE                                              |
|     * Passwords committed to Git                                        |
|     * Anyone with code access sees secrets                              |
|     * Security audit nightmare                                          |
|                                                                         |
|  3. REBUILD TO CHANGE CONFIG                                            |
|     * Log level change? Rebuild image                                   |
|     * Timeout change? Rebuild image                                     |
|     * Slow and error-prone                                              |
|                                                                         |
|  4. NO SEPARATION OF CONCERNS                                           |
|     * Dev knows prod passwords                                          |
|     * Ops can't change config without rebuilding                        |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  THE SOLUTION: EXTERNALIZE CONFIGURATION                                |
|  ========================================                               |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |         SAME IMAGE           DIFFERENT CONFIG                    |   |
|  |         ==========           ================                    |   |
|  |                                                                  |   |
|  |    +--------------+         +------------------+                 |   |
|  |    |   myapp:v1   |-------->|  DEV ConfigMap   |                 |   |
|  |    |              |         |  DB_HOST=dev-db  |                 |   |
|  |    |  (no config  |         +------------------+                 |   |
|  |    |   inside!)   |                                              |   |
|  |    |              |         +------------------+                 |   |
|  |    |              |-------->| STAGING ConfigMap|                 |   |
|  |    |              |         |  DB_HOST=stg-db  |                 |   |
|  |    |              |         +------------------+                 |   |
|  |    |              |                                              |   |
|  |    |              |         +------------------+                 |   |
|  |    |              |-------->|  PROD ConfigMap  |                 |   |
|  |    +--------------+         |  DB_HOST=prod-db |                 |   |
|  |                             +------------------+                 |   |
|  |                                                                  |   |
|  |  ONE image > THREE environments!                                 |   |
|  |  Config injected at RUNTIME, not BUILDTIME                       |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
|                                                                         |
|  CONFIGMAP vs SECRET: WHEN TO USE WHICH?                                |
|  ========================================                               |
|                                                                         |
|  +--------------------+---------------------+-------------------------+ |
|  | Data Type          | Use                 | Example                 | |
|  +--------------------+---------------------+-------------------------+ |
|  | Database host      | ConfigMap           | DB_HOST=mysql           | |
|  | Database password  | Secret              | DB_PASSWORD=xxx         | |
|  | Log level          | ConfigMap           | LOG_LEVEL=debug         | |
|  | API key            | Secret              | API_KEY=abc123          | |
|  | Config file        | ConfigMap           | nginx.conf              | |
|  | TLS certificate    | Secret (tls type)   | tls.crt, tls.key        | |
|  | Feature flags      | ConfigMap           | FEATURE_X=true          | |
|  | OAuth token        | Secret              | OAUTH_TOKEN=xxx         | |
|  +--------------------+---------------------+-------------------------+ |
|                                                                         |
|  RULE OF THUMB:                                                         |
|  * Would you commit this to Git? > ConfigMap                            |
|  * Would it be a security issue if leaked? > Secret                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.2: CONFIGMAPS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS A CONFIGMAP?                                                   |
|                                                                         |
|  Key-value pairs for non-sensitive configuration data.                  |
|                                                                         |
|  USE CASES:                                                             |
|  * Environment variables (DB_HOST, LOG_LEVEL)                           |
|  * Configuration files (nginx.conf, app.properties)                     |
|  * Command-line arguments                                               |
|  * Feature flags                                                        |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CREATING CONFIGMAPS                                                    |
|  ====================                                                   |
|                                                                         |
|  # From literal values                                                  |
|  kubectl create configmap app-config \                                  |
|    --from-literal=DB_HOST=mysql \                                       |
|    --from-literal=DB_PORT=3306                                          |
|                                                                         |
|  # From file                                                            |
|  kubectl create configmap app-config \                                  |
|    --from-file=config.properties                                        |
|                                                                         |
|  # From directory                                                       |
|  kubectl create configmap app-config \                                  |
|    --from-file=config-dir/                                              |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  YAML DEFINITION                                                        |
|  ================                                                       |
|                                                                         |
|  apiVersion: v1                                                         |
|  kind: ConfigMap                                                        |
|  metadata:                                                              |
|    name: app-config                                                     |
|  data:                                                                  |
|    # Simple key-value                                                   |
|    DB_HOST: mysql                                                       |
|    DB_PORT: "3306"                                                      |
|    LOG_LEVEL: info                                                      |
|                                                                         |
|    # File-like key                                                      |
|    config.json: |                                                       |
|      {                                                                  |
|        "database": "myapp",                                             |
|        "debug": false                                                   |
|      }                                                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USING CONFIGMAPS                                                       |
|  =================                                                      |
|                                                                         |
|  1. AS ENVIRONMENT VARIABLES                                            |
|  ---------------------------                                            |
|                                                                         |
|  spec:                                                                  |
|    containers:                                                          |
|      - name: app                                                        |
|        image: myapp                                                     |
|        env:                                                             |
|          # Single key                                                   |
|          - name: DATABASE_HOST                                          |
|            valueFrom:                                                   |
|              configMapKeyRef:                                           |
|                name: app-config                                         |
|                key: DB_HOST                                             |
|        envFrom:                                                         |
|          # All keys as env vars                                         |
|          - configMapRef:                                                |
|              name: app-config                                           |
|                                                                         |
|  2. AS MOUNTED FILES                                                    |
|  --------------------                                                   |
|                                                                         |
|  spec:                                                                  |
|    containers:                                                          |
|      - name: app                                                        |
|        volumeMounts:                                                    |
|          - name: config-volume                                          |
|            mountPath: /etc/config                                       |
|    volumes:                                                             |
|      - name: config-volume                                              |
|        configMap:                                                       |
|          name: app-config                                               |
|                                                                         |
|  Result: /etc/config/DB_HOST, /etc/config/config.json                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.2: SECRETS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT ARE SECRETS?                                                      |
|                                                                         |
|  Like ConfigMaps but for sensitive data.                                |
|  Base64 encoded (not encrypted by default!).                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  CREATING SECRETS                                                       |
|  =================                                                      |
|                                                                         |
|  # Generic secret                                                       |
|  kubectl create secret generic db-secret \                              |
|    --from-literal=username=admin \                                      |
|    --from-literal=password=supersecret                                  |
|                                                                         |
|  # From file                                                            |
|  kubectl create secret generic tls-secret \                             |
|    --from-file=tls.crt=server.crt \                                     |
|    --from-file=tls.key=server.key                                       |
|                                                                         |
|  # Docker registry credentials                                          |
|  kubectl create secret docker-registry regcred \                        |
|    --docker-server=registry.example.com \                               |
|    --docker-username=user \                                             |
|    --docker-password=pass                                               |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  YAML DEFINITION                                                        |
|  ================                                                       |
|                                                                         |
|  apiVersion: v1                                                         |
|  kind: Secret                                                           |
|  metadata:                                                              |
|    name: db-secret                                                      |
|  type: Opaque                                                           |
|  data:                                                                  |
|    # Base64 encoded values                                              |
|    username: YWRtaW4=           # echo -n 'admin' | base64              |
|    password: c3VwZXJzZWNyZXQ=   # echo -n 'supersecret' | base64        |
|                                                                         |
|  # Or use stringData (auto-encoded)                                     |
|  apiVersion: v1                                                         |
|  kind: Secret                                                           |
|  metadata:                                                              |
|    name: db-secret                                                      |
|  stringData:                                                            |
|    username: admin                                                      |
|    password: supersecret                                                |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USING SECRETS                                                          |
|  =============                                                          |
|                                                                         |
|  spec:                                                                  |
|    containers:                                                          |
|      - name: app                                                        |
|        env:                                                             |
|          - name: DB_PASSWORD                                            |
|            valueFrom:                                                   |
|              secretKeyRef:                                              |
|                name: db-secret                                          |
|                key: password                                            |
|        volumeMounts:                                                    |
|          - name: secret-volume                                          |
|            mountPath: /etc/secrets                                      |
|            readOnly: true                                               |
|    volumes:                                                             |
|      - name: secret-volume                                              |
|        secret:                                                          |
|          secretName: db-secret                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.3: SECRET TYPES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BUILT-IN SECRET TYPES                                                  |
|                                                                         |
|  +----------------------------+-------------------------------------+   |
|  | Type                       | Use Case                            |   |
|  +----------------------------+-------------------------------------+   |
|  | Opaque                     | Generic (default)                   |   |
|  | kubernetes.io/tls          | TLS certificates                    |   |
|  | kubernetes.io/dockercfg    | Docker registry auth                |   |
|  | kubernetes.io/basic-auth   | Basic authentication                |   |
|  | kubernetes.io/ssh-auth     | SSH credentials                     |   |
|  +----------------------------+-------------------------------------+   |
|                                                                         |
|  TLS SECRET EXAMPLE                                                     |
|  ===================                                                    |
|                                                                         |
|  kubectl create secret tls my-tls \                                     |
|    --cert=path/to/tls.crt \                                             |
|    --key=path/to/tls.key                                                |
|                                                                         |
|  # Or YAML                                                              |
|  apiVersion: v1                                                         |
|  kind: Secret                                                           |
|  metadata:                                                              |
|    name: my-tls                                                         |
|  type: kubernetes.io/tls                                                |
|  data:                                                                  |
|    tls.crt: <base64-cert>                                               |
|    tls.key: <base64-key>                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 5.4: BEST PRACTICES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SECURITY                                                               |
|  ========                                                               |
|                                                                         |
|  1. Enable encryption at rest                                           |
|     (Kubernetes API server config)                                      |
|                                                                         |
|  2. Use RBAC to limit secret access                                     |
|                                                                         |
|  3. Don't commit secrets to git                                         |
|                                                                         |
|  4. Use external secret managers:                                       |
|     * HashiCorp Vault                                                   |
|     * AWS Secrets Manager                                               |
|     * Azure Key Vault                                                   |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  EXTERNAL SECRETS OPERATOR                                              |
|  ==========================                                             |
|                                                                         |
|  apiVersion: external-secrets.io/v1beta1                                |
|  kind: ExternalSecret                                                   |
|  metadata:                                                              |
|    name: db-secret                                                      |
|  spec:                                                                  |
|    refreshInterval: 1h                                                  |
|    secretStoreRef:                                                      |
|      name: aws-secrets-manager                                          |
|      kind: SecretStore                                                  |
|    target:                                                              |
|      name: db-secret                                                    |
|    data:                                                                |
|      - secretKey: password                                              |
|        remoteRef:                                                       |
|          key: prod/db/password                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONFIGURATION - KEY TAKEAWAYS                                          |
|                                                                         |
|  CONFIGMAPS                                                             |
|  ----------                                                             |
|  * Non-sensitive configuration                                          |
|  * Plain text storage                                                   |
|  * Mount as files or env vars                                           |
|                                                                         |
|  SECRETS                                                                |
|  -------                                                                |
|  * Sensitive data (passwords, keys)                                     |
|  * Base64 encoded (not encrypted!)                                      |
|  * Mount as files (recommended) or env vars                             |
|                                                                         |
|  ACCESS METHODS                                                         |
|  --------------                                                         |
|  * env.valueFrom.configMapKeyRef/secretKeyRef                           |
|  * envFrom.configMapRef/secretRef                                       |
|  * volumes.configMap/secret                                             |
|                                                                         |
|  COMMANDS                                                               |
|  --------                                                               |
|  kubectl create configmap/secret                                        |
|  kubectl get configmap/secret                                           |
|  kubectl describe configmap/secret                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 5

