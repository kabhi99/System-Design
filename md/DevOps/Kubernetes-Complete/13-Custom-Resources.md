# KUBERNETES CUSTOM RESOURCES
*Chapter 13: Extending Kubernetes*

Custom Resource Definitions (CRDs) let you extend Kubernetes with
your own resource types.

## SECTION 13.1: WHAT ARE CRDS?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  EXTENDING KUBERNETES                                                 |
|                                                                         |
|  Built-in resources: Pod, Service, Deployment, etc.                  |
|  Custom resources: Anything you define!                              |
|                                                                         |
|  EXAMPLES:                                                             |
|  * Certificate (cert-manager)                                        |
|  * VirtualService (Istio)                                            |
|  * PostgresCluster (database operators)                              |
|  * Application (ArgoCD)                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 13.2: CREATING A CRD

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CRD DEFINITION                                                        |
|  ==============                                                        |
|                                                                         |
|  apiVersion: apiextensions.k8s.io/v1                                  |
|  kind: CustomResourceDefinition                                        |
|  metadata:                                                              |
|    name: databases.mycompany.com                                      |
|  spec:                                                                  |
|    group: mycompany.com                                                |
|    versions:                                                            |
|      - name: v1                                                        |
|        served: true                                                    |
|        storage: true                                                   |
|        schema:                                                          |
|          openAPIV3Schema:                                              |
|            type: object                                                |
|            properties:                                                  |
|              spec:                                                      |
|                type: object                                            |
|                properties:                                              |
|                  engine:                                               |
|                    type: string                                        |
|                    enum: ["postgres", "mysql"]                        |
|                  size:                                                 |
|                    type: string                                        |
|                  replicas:                                             |
|                    type: integer                                       |
|    scope: Namespaced                                                    |
|    names:                                                               |
|      plural: databases                                                 |
|      singular: database                                                |
|      kind: Database                                                     |
|      shortNames:                                                        |
|        - db                                                            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  USING THE CUSTOM RESOURCE                                            |
|  ==========================                                            |
|                                                                         |
|  apiVersion: mycompany.com/v1                                         |
|  kind: Database                                                         |
|  metadata:                                                              |
|    name: my-postgres                                                   |
|  spec:                                                                  |
|    engine: postgres                                                    |
|    size: "100Gi"                                                       |
|    replicas: 3                                                         |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  COMMANDS                                                              |
|                                                                         |
|  kubectl apply -f crd.yaml                                            |
|  kubectl get crd                                                       |
|  kubectl get databases                                                 |
|  kubectl get db                  # Using shortName                    |
|  kubectl describe db my-postgres                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 13.3: CRD FEATURES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  VALIDATION                                                            |
|  ==========                                                            |
|                                                                         |
|  schema:                                                                |
|    openAPIV3Schema:                                                    |
|      properties:                                                        |
|        spec:                                                            |
|          properties:                                                    |
|            replicas:                                                   |
|              type: integer                                             |
|              minimum: 1                                                |
|              maximum: 10                                               |
|          required: ["engine", "size"]                                 |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  ADDITIONAL PRINTER COLUMNS                                           |
|  ===========================                                            |
|                                                                         |
|  versions:                                                              |
|    - name: v1                                                          |
|      additionalPrinterColumns:                                        |
|        - name: Engine                                                 |
|          type: string                                                  |
|          jsonPath: .spec.engine                                       |
|        - name: Size                                                   |
|          type: string                                                  |
|          jsonPath: .spec.size                                         |
|        - name: Age                                                    |
|          type: date                                                    |
|          jsonPath: .metadata.creationTimestamp                       |
|                                                                         |
|  # kubectl get databases                                               |
|  # NAME          ENGINE    SIZE    AGE                                |
|  # my-postgres   postgres  100Gi   5m                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CRDS - KEY TAKEAWAYS                                                 |
|                                                                         |
|  PURPOSE                                                               |
|  -------                                                               |
|  * Extend Kubernetes API                                             |
|  * Define custom resource types                                      |
|  * Used by operators                                                 |
|                                                                         |
|  COMPONENTS                                                            |
|  ----------                                                            |
|  * group: API group                                                  |
|  * names: Resource naming                                            |
|  * schema: Validation rules                                          |
|                                                                         |
|  NOTE                                                                  |
|  ----                                                                  |
|  CRDs define the schema.                                             |
|  Operators implement the logic.                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 13

