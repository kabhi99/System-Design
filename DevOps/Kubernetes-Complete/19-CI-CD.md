================================================================================
                    KUBERNETES CI/CD
                    Chapter 19: Continuous Deployment to Kubernetes
================================================================================

This chapter covers deploying applications to Kubernetes using
CI/CD pipelines and GitOps practices.


================================================================================
SECTION 19.1: DEPLOYMENT STRATEGIES
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  ROLLING UPDATE (Default)                                             │
    │  ═════════════════════════                                              │
    │                                                                         │
    │  Gradually replace old pods with new ones.                            │
    │                                                                         │
    │  spec:                                                                  │
    │    strategy:                                                            │
    │      type: RollingUpdate                                               │
    │      rollingUpdate:                                                     │
    │        maxSurge: 25%         # Extra pods during update              │
    │        maxUnavailable: 25%   # Max pods that can be unavailable      │
    │                                                                         │
    │  ─────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  BLUE-GREEN DEPLOYMENT                                                │
    │  ══════════════════════                                                │
    │                                                                         │
    │  Run two identical environments, switch traffic instantly.           │
    │                                                                         │
    │  # Blue (current)              # Green (new)                         │
    │  apiVersion: apps/v1            apiVersion: apps/v1                   │
    │  kind: Deployment               kind: Deployment                       │
    │  metadata:                      metadata:                              │
    │    name: myapp-blue             name: myapp-green                     │
    │  spec:                          spec:                                  │
    │    replicas: 3                    replicas: 3                         │
    │    template:                      template:                            │
    │      metadata:                      metadata:                          │
    │        labels:                        labels:                          │
    │          app: myapp                     app: myapp                     │
    │          version: blue                  version: green               │
    │                                                                         │
    │  # Service points to blue or green                                    │
    │  spec:                                                                  │
    │    selector:                                                            │
    │      app: myapp                                                        │
    │      version: blue    # Switch to 'green' to cutover                 │
    │                                                                         │
    │  ─────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  CANARY DEPLOYMENT                                                    │
    │  ══════════════════                                                    │
    │                                                                         │
    │  Route small percentage to new version.                              │
    │                                                                         │
    │  # Stable: 9 replicas                                                 │
    │  # Canary: 1 replica (10% traffic)                                   │
    │                                                                         │
    │  Or use Ingress/Service Mesh for weighted routing.                   │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 19.2: CI/CD PIPELINES
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  GITHUB ACTIONS TO KUBERNETES                                         │
    │  ═════════════════════════════                                          │
    │                                                                         │
    │  name: Deploy to Kubernetes                                           │
    │                                                                         │
    │  on:                                                                    │
    │    push:                                                               │
    │      branches: [main]                                                  │
    │                                                                         │
    │  jobs:                                                                  │
    │    build-and-deploy:                                                   │
    │      runs-on: ubuntu-latest                                           │
    │      steps:                                                             │
    │        - uses: actions/checkout@v4                                    │
    │                                                                         │
    │        - name: Login to Docker Hub                                    │
    │          uses: docker/login-action@v3                                 │
    │          with:                                                         │
    │            username: ${{ secrets.DOCKER_USERNAME }}                   │
    │            password: ${{ secrets.DOCKER_PASSWORD }}                   │
    │                                                                         │
    │        - name: Build and push                                         │
    │          uses: docker/build-push-action@v5                            │
    │          with:                                                         │
    │            push: true                                                  │
    │            tags: myuser/myapp:${{ github.sha }}                       │
    │                                                                         │
    │        - name: Set up kubectl                                         │
    │          uses: azure/setup-kubectl@v3                                 │
    │                                                                         │
    │        - name: Configure kubectl                                      │
    │          run: |                                                        │
    │            echo "${{ secrets.KUBECONFIG }}" > kubeconfig              │
    │            export KUBECONFIG=kubeconfig                               │
    │                                                                         │
    │        - name: Deploy                                                 │
    │          run: |                                                        │
    │            kubectl set image deployment/myapp \                       │
    │              myapp=myuser/myapp:${{ github.sha }}                    │
    │            kubectl rollout status deployment/myapp                   │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 19.3: GITOPS WITH ARGOCD
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  GITOPS PRINCIPLES                                                     │
    │  ══════════════════                                                    │
    │                                                                         │
    │  • Git is the source of truth                                        │
    │  • All changes through Git commits                                   │
    │  • Automatic sync from Git to cluster                                │
    │  • Self-healing (drift detection)                                    │
    │                                                                         │
    │  ─────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  ARGOCD SETUP                                                          │
    │  ════════════                                                          │
    │                                                                         │
    │  # Install ArgoCD                                                      │
    │  kubectl create namespace argocd                                      │
    │  kubectl apply -n argocd -f \                                         │
    │    https://raw.githubusercontent.com/argoproj/argo-cd/stable/\       │
    │    manifests/install.yaml                                              │
    │                                                                         │
    │  # Access UI                                                           │
    │  kubectl port-forward svc/argocd-server -n argocd 8080:443           │
    │                                                                         │
    │  # Get admin password                                                 │
    │  kubectl -n argocd get secret argocd-initial-admin-secret \          │
    │    -o jsonpath="{.data.password}" | base64 -d                        │
    │                                                                         │
    │  ─────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  ARGOCD APPLICATION                                                    │
    │  ══════════════════                                                    │
    │                                                                         │
    │  apiVersion: argoproj.io/v1alpha1                                     │
    │  kind: Application                                                      │
    │  metadata:                                                              │
    │    name: myapp                                                         │
    │    namespace: argocd                                                   │
    │  spec:                                                                  │
    │    project: default                                                    │
    │    source:                                                              │
    │      repoURL: https://github.com/myorg/myapp-manifests               │
    │      targetRevision: main                                              │
    │      path: k8s                                                         │
    │    destination:                                                         │
    │      server: https://kubernetes.default.svc                           │
    │      namespace: default                                                │
    │    syncPolicy:                                                          │
    │      automated:                                                         │
    │        prune: true         # Delete removed resources               │
    │        selfHeal: true      # Revert manual changes                  │
    │                                                                         │
    │  WORKFLOW:                                                             │
    │  1. Developer pushes code → CI builds image                         │
    │  2. CI updates manifest repo with new image tag                     │
    │  3. ArgoCD detects change → syncs to cluster                        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 19.4: FLUX CD
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  FLUX (Alternative to ArgoCD)                                         │
    │  ═════════════════════════════                                          │
    │                                                                         │
    │  # Install Flux                                                        │
    │  flux bootstrap github \                                               │
    │    --owner=myorg \                                                      │
    │    --repository=fleet-infra \                                          │
    │    --path=clusters/my-cluster \                                        │
    │    --personal                                                           │
    │                                                                         │
    │  # Define GitRepository                                               │
    │  apiVersion: source.toolkit.fluxcd.io/v1                              │
    │  kind: GitRepository                                                    │
    │  metadata:                                                              │
    │    name: myapp                                                         │
    │  spec:                                                                  │
    │    url: https://github.com/myorg/myapp                                │
    │    interval: 1m                                                        │
    │                                                                         │
    │  # Define Kustomization                                               │
    │  apiVersion: kustomize.toolkit.fluxcd.io/v1                           │
    │  kind: Kustomization                                                    │
    │  metadata:                                                              │
    │    name: myapp                                                         │
    │  spec:                                                                  │
    │    sourceRef:                                                           │
    │      kind: GitRepository                                               │
    │      name: myapp                                                       │
    │    path: ./k8s                                                          │
    │    interval: 10m                                                        │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
CHAPTER SUMMARY
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CI/CD - KEY TAKEAWAYS                                                │
    │                                                                         │
    │  DEPLOYMENT STRATEGIES                                                 │
    │  ─────────────────────                                                  │
    │  • Rolling: Gradual replacement (default)                            │
    │  • Blue-Green: Instant switch                                        │
    │  • Canary: Gradual traffic shift                                     │
    │                                                                         │
    │  APPROACHES                                                            │
    │  ──────────                                                            │
    │  • Push-based: CI pushes to cluster                                  │
    │  • Pull-based (GitOps): Cluster pulls from Git                      │
    │                                                                         │
    │  GITOPS TOOLS                                                          │
    │  ────────────                                                          │
    │  • ArgoCD: Popular, great UI                                         │
    │  • Flux: CNCF project, lightweight                                   │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
                              END OF CHAPTER 19
================================================================================

