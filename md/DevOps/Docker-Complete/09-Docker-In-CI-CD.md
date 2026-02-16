# DOCKER IN CI/CD PIPELINES
*Chapter 9: Automated Build and Deployment*

Integrating Docker into CI/CD pipelines enables automated building,
testing, and deployment of containerized applications.

## SECTION 9.1: CI/CD OVERVIEW

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DOCKER CI/CD WORKFLOW                                                  |
|                                                                         |
|  +-----------------------------------------------------------------+    |
|  |                                                                 |    |
|  |   Code Push                                                    |     |
|  |       |                                                         |    |
|  |       v                                                         |    |
|  |   +---------+    +---------+    +---------+    +---------+     |     |
|  |   |  Build  |--->|  Test   |--->|  Push   |--->| Deploy  |     |     |
|  |   |  Image  |    |  Image  |    | to Reg  |    |  Prod   |     |     |
|  |   +---------+    +---------+    +---------+    +---------+     |     |
|  |                                                                 |    |
|  |   docker        docker run     docker push   kubectl apply    |      |
|  |   build         tests in       myapp:v1.0    deployment.yaml  |      |
|  |                 container                                      |     |
|  |                                                                 |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9.2: GITHUB ACTIONS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  BASIC BUILD AND PUSH                                                   |
|                                                                         |
|  # .github/workflows/docker.yml                                         |
|  name: Build and Push Docker Image                                      |
|                                                                         |
|  on:                                                                    |
|    push:                                                                |
|      branches: [main]                                                   |
|    pull_request:                                                        |
|      branches: [main]                                                   |
|                                                                         |
|  jobs:                                                                  |
|    build:                                                               |
|      runs-on: ubuntu-latest                                             |
|                                                                         |
|      steps:                                                             |
|        - uses: actions/checkout@v4                                      |
|                                                                         |
|        - name: Set up Docker Buildx                                     |
|          uses: docker/setup-buildx-action@v3                            |
|                                                                         |
|        - name: Login to Docker Hub                                      |
|          uses: docker/login-action@v3                                   |
|          with:                                                          |
|            username: ${{ secrets.DOCKER_USERNAME }}                     |
|            password: ${{ secrets.DOCKER_PASSWORD }}                     |
|                                                                         |
|        - name: Build and push                                           |
|          uses: docker/build-push-action@v5                              |
|          with:                                                          |
|            context: .                                                   |
|            push: ${{ github.event_name != 'pull_request' }}             |
|            tags: |                                                      |
|              myuser/myapp:latest                                        |
|              myuser/myapp:${{ github.sha }}                             |
|            cache-from: type=gha                                         |
|            cache-to: type=gha,mode=max                                  |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  WITH TESTING                                                           |
|                                                                         |
|  jobs:                                                                  |
|    test:                                                                |
|      runs-on: ubuntu-latest                                             |
|      steps:                                                             |
|        - uses: actions/checkout@v4                                      |
|                                                                         |
|        - name: Build test image                                         |
|          run: docker build --target test -t myapp:test .                |
|                                                                         |
|        - name: Run tests                                                |
|          run: docker run myapp:test npm test                            |
|                                                                         |
|    build:                                                               |
|      needs: test                                                        |
|      runs-on: ubuntu-latest                                             |
|      steps:                                                             |
|        # ... build and push steps                                       |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9.3: GITLAB CI

```
+-------------------------------------------------------------------------+
|                                                                         |
|  # .gitlab-ci.yml                                                       |
|                                                                         |
|  stages:                                                                |
|    - build                                                              |
|    - test                                                               |
|    - push                                                               |
|    - deploy                                                             |
|                                                                         |
|  variables:                                                             |
|    DOCKER_IMAGE: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA                      |
|                                                                         |
|  build:                                                                 |
|    stage: build                                                         |
|    image: docker:24                                                     |
|    services:                                                            |
|      - docker:dind                                                      |
|    script:                                                              |
|      - docker build -t $DOCKER_IMAGE .                                  |
|      - docker save $DOCKER_IMAGE > image.tar                            |
|    artifacts:                                                           |
|      paths:                                                             |
|        - image.tar                                                      |
|                                                                         |
|  test:                                                                  |
|    stage: test                                                          |
|    image: docker:24                                                     |
|    services:                                                            |
|      - docker:dind                                                      |
|    script:                                                              |
|      - docker load < image.tar                                          |
|      - docker run $DOCKER_IMAGE npm test                                |
|                                                                         |
|  push:                                                                  |
|    stage: push                                                          |
|    image: docker:24                                                     |
|    services:                                                            |
|      - docker:dind                                                      |
|    script:                                                              |
|      - docker load < image.tar                                          |
|      - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD \     |
|          $CI_REGISTRY                                                   |
|      - docker push $DOCKER_IMAGE                                        |
|    only:                                                                |
|      - main                                                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9.4: JENKINS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  // Jenkinsfile                                                         |
|                                                                         |
|  pipeline {                                                             |
|      agent any                                                          |
|                                                                         |
|      environment {                                                      |
|          DOCKER_IMAGE = "myuser/myapp"                                  |
|          DOCKER_TAG = "${env.BUILD_NUMBER}"                             |
|      }                                                                  |
|                                                                         |
|      stages {                                                           |
|          stage('Build') {                                               |
|              steps {                                                    |
|                  script {                                               |
|                      docker.build("${DOCKER_IMAGE}:${DOCKER_TAG}")      |
|                  }                                                      |
|              }                                                          |
|          }                                                              |
|                                                                         |
|          stage('Test') {                                                |
|              steps {                                                    |
|                  script {                                               |
|                      docker.image("${DOCKER_IMAGE}:${DOCKER_TAG}")      |
|                          .inside {                                      |
|                              sh 'npm test'                              |
|                          }                                              |
|                  }                                                      |
|              }                                                          |
|          }                                                              |
|                                                                         |
|          stage('Push') {                                                |
|              when {                                                     |
|                  branch 'main'                                          |
|              }                                                          |
|              steps {                                                    |
|                  script {                                               |
|                      docker.withRegistry('', 'docker-hub-creds') {      |
|                          docker.image("${DOCKER_IMAGE}:${DOCKER_TAG}")  |
|                              .push()                                    |
|                          docker.image("${DOCKER_IMAGE}:${DOCKER_TAG}")  |
|                              .push('latest')                            |
|                      }                                                  |
|                  }                                                      |
|              }                                                          |
|          }                                                              |
|      }                                                                  |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 9.5: BUILD OPTIMIZATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  LAYER CACHING                                                          |
|  ==============                                                         |
|                                                                         |
|  # GitHub Actions with cache                                            |
|  - uses: docker/build-push-action@v5                                    |
|    with:                                                                |
|      cache-from: type=gha                                               |
|      cache-to: type=gha,mode=max                                        |
|                                                                         |
|  # Or use registry cache                                                |
|  - uses: docker/build-push-action@v5                                    |
|    with:                                                                |
|      cache-from: type=registry,ref=myuser/myapp:cache                   |
|      cache-to: type=registry,ref=myuser/myapp:cache,mode=max            |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  MULTI-PLATFORM BUILDS                                                  |
|  ======================                                                 |
|                                                                         |
|  # Build for multiple architectures                                     |
|  - uses: docker/build-push-action@v5                                    |
|    with:                                                                |
|      platforms: linux/amd64,linux/arm64                                 |
|      push: true                                                         |
|      tags: myuser/myapp:latest                                          |
|                                                                         |
|  ---------------------------------------------------------------------  |
|                                                                         |
|  SECURITY SCANNING IN PIPELINE                                          |
|  ==============================                                         |
|                                                                         |
|  - name: Run Trivy vulnerability scanner                                |
|    uses: aquasecurity/trivy-action@master                               |
|    with:                                                                |
|      image-ref: myuser/myapp:${{ github.sha }}                          |
|      format: 'sarif'                                                    |
|      exit-code: '1'                                                     |
|      severity: 'CRITICAL,HIGH'                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  DOCKER CI/CD - KEY TAKEAWAYS                                           |
|                                                                         |
|  PIPELINE STAGES                                                        |
|  ---------------                                                        |
|  1. Build: docker build                                                 |
|  2. Test: Run tests in container                                        |
|  3. Scan: Vulnerability scanning                                        |
|  4. Push: docker push to registry                                       |
|  5. Deploy: Update production                                           |
|                                                                         |
|  BEST PRACTICES                                                         |
|  --------------                                                         |
|  * Use layer caching for faster builds                                  |
|  * Tag with git SHA for traceability                                    |
|  * Scan images before pushing                                           |
|  * Use multi-stage builds                                               |
|  * Store credentials in secrets                                         |
|                                                                         |
|  PLATFORMS                                                              |
|  ---------                                                              |
|  * GitHub Actions: docker/build-push-action                             |
|  * GitLab CI: docker:dind service                                       |
|  * Jenkins: Docker Pipeline plugin                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 9

