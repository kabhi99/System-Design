# MICROSERVICES ARCHITECTURE - ADVANCED TOPICS

CHAPTER 6: SERVICE MESH, SECURITY, TESTING, ANTI-PATTERNS & MORE
SECTION 1: SERVICE MESH
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHAT IS A SERVICE MESH?                                               |*
*|                                                                         |*
*|  A dedicated infrastructure layer for handling service-to-service      |*
*|  communication. It abstracts the network away from the application.    |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  WITHOUT SERVICE MESH:                                          |  |*
*|  |                                                                 |  |*
*|  |  Each service handles:                                          |  |*
*|  |  * Retries                                                      |  |*
*|  |  * Timeouts                                                     |  |*
*|  |  * Circuit breaking                                             |  |*
*|  |  * TLS/mTLS                                                     |  |*
*|  |  * Load balancing                                               |  |*
*|  |  * Metrics collection                                           |  |*
*|  |                                                                 |  |*
*|  |  > Duplicated logic in every service!                          |  |*
*|  |  > Different implementations per language                       |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  WITH SERVICE MESH:                                            |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  +-------------+           +-------------+               ||  |*
*|  |  |  |  Service A  |           |  Service B  |               ||  |*
*|  |  |  +------+------+           +------+------+               ||  |*
*|  |  |         |                         |                       ||  |*
*|  |  |         v                         v                       ||  |*
*|  |  |  +-------------+           +-------------+               ||  |*
*|  |  |  |   Sidecar   |<--------->|   Sidecar   |               ||  |*
*|  |  |  |   Proxy     |           |   Proxy     |               ||  |*
*|  |  |  |  (Envoy)    |           |  (Envoy)    |               ||  |*
*|  |  |  +-------------+           +-------------+               ||  |*
*|  |  |         |                         |                       ||  |*
*|  |  |         +----------+--------------+                       ||  |*
*|  |  |                    |                                      ||  |*
*|  |  |                    v                                      ||  |*
*|  |  |            +-----------------+                            ||  |*
*|  |  |            |  Control Plane  |                            ||  |*
*|  |  |            |  (Istio/Linkerd)|                            ||  |*
*|  |  |            +-----------------+                            ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  Sidecar proxy handles all network concerns!                   |  |*
*|  |  Service code stays clean and simple.                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  SERVICE MESH FEATURES                                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TRAFFIC MANAGEMENT:                                           |  |*
*|  |  * Load balancing (round robin, least conn, consistent hash)  |  |*
*|  |  * Traffic splitting (canary, A/B testing)                    |  |*
*|  |  * Retries with backoff                                       |  |*
*|  |  * Timeouts                                                    |  |*
*|  |  * Circuit breaking                                           |  |*
*|  |  * Rate limiting                                              |  |*
*|  |  * Fault injection (testing)                                  |  |*
*|  |                                                                 |  |*
*|  |  SECURITY:                                                     |  |*
*|  |  * Mutual TLS (mTLS) between services                         |  |*
*|  |  * Certificate management (auto-rotation)                     |  |*
*|  |  * Authorization policies (who can call whom)                 |  |*
*|  |  * End-user authentication                                    |  |*
*|  |                                                                 |  |*
*|  |  OBSERVABILITY:                                                |  |*
*|  |  * Distributed tracing (automatic span propagation)           |  |*
*|  |  * Metrics (request rate, latency, errors)                    |  |*
*|  |  * Access logging                                             |  |*
*|  |  * Service topology visualization                             |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  SERVICE MESH COMPARISON                                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Feature          Istio           Linkerd        Consul Connect|  |*
*|  |  ------------------------------------------------------------ |  |*
*|  |                                                                 |  |*
*|  |  Complexity       High            Low            Medium        |  |*
*|  |  Performance      Good            Excellent      Good          |  |*
*|  |  Resource Usage   Heavy           Light          Medium        |  |*
*|  |  Features         Most            Essential      Good          |  |*
*|  |  Learning Curve   Steep           Gentle         Medium        |  |*
*|  |  Proxy            Envoy           linkerd2-proxy Envoy        |  |*
*|  |  Best For         Enterprise,     Simple needs,  HashiCorp    |  |*
*|  |                   Complex needs   K8s-native     ecosystem    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  WHEN TO USE SERVICE MESH:                                             |*
*|  Y Many services (50+)                                                |*
*|  Y Need zero-trust security (mTLS everywhere)                         |*
*|  Y Complex traffic management                                         |*
*|  Y Polyglot environment (multiple languages)                          |*
*|                                                                         |*
*|  WHEN TO SKIP:                                                         |*
*|  X Few services (< 10)                                                |*
*|  X Resource constrained                                               |*
*|  X Simple networking needs                                            |*
*|  X Team not ready for complexity                                      |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2: API VERSIONING STRATEGIES
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHY VERSION APIs?                                                     |*
*|                                                                         |*
*|  * Breaking changes need gradual migration                             |*
*|  * Multiple clients on different versions                              |*
*|  * Backward compatibility                                              |*
*|  * Independent service evolution                                       |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  STRATEGY 1: URI PATH VERSIONING                                            |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  /api/v1/users                                                        | |*
*|  |  /api/v2/users                                                        | |*
*|  |  /api/v3/users                                                        | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*|  PROS:                                                                       |*
*|  Y Very explicit and visible                                               |*
*|  Y Easy to route at load balancer                                          |*
*|  Y Easy to cache (different URLs)                                          |*
*|  Y Simple to understand                                                    |*
*|                                                                              |*
*|  CONS:                                                                       |*
*|  X URL pollution                                                           |*
*|  X Not RESTful (resource URL changes)                                      |*
*|  X Duplicate routes                                                        |*
*|                                                                              |*
*|  MOST COMMONLY USED                                                         |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  STRATEGY 2: QUERY PARAMETER VERSIONING                                      |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  /api/users?version=1                                                 | |*
*|  |  /api/users?version=2                                                 | |*
*|  |  /api/users?api-version=2024-01-01                                   | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*|  PROS:                                                                       |*
*|  Y URL stays clean                                                         |*
*|  Y Optional parameter (default version)                                    |*
*|  Y Easy to implement                                                       |*
*|                                                                              |*
*|  CONS:                                                                       |*
*|  X Easy to forget parameter                                                |*
*|  X Caching complexity                                                      |*
*|  X Routing harder at LB level                                              |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  STRATEGY 3: HEADER VERSIONING                                               |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  GET /api/users                                                       | |*
*|  |  Accept: application/vnd.myapi.v2+json                               | |*
*|  |                                                                        | |*
*|  |  or                                                                   | |*
*|  |                                                                        | |*
*|  |  GET /api/users                                                       | |*
*|  |  X-API-Version: 2                                                    | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*|  PROS:                                                                       |*
*|  Y Clean URLs                                                              |*
*|  Y More RESTful                                                            |*
*|  Y Content negotiation support                                             |*
*|                                                                              |*
*|  CONS:                                                                       |*
*|  X Hidden from URL                                                         |*
*|  X Harder to test/debug                                                    |*
*|  X Requires header inspection                                              |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  STRATEGY 4: NO VERSIONING (Evolutionary Design)                             |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Design APIs to be backward compatible:                               | |*
*|  |                                                                        | |*
*|  |  * Only ADD fields, never remove                                     | |*
*|  |  * New fields are optional                                           | |*
*|  |  * Old clients ignore unknown fields                                 | |*
*|  |  * Use feature flags for behavior changes                            | |*
*|  |                                                                        | |*
*|  |  Example:                                                             | |*
*|  |  v1: { "name": "John" }                                              | |*
*|  |  v2: { "name": "John", "nickname": "Johnny" }                       | |*
*|  |  (Old clients still work, just don't see nickname)                   | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*|  PROS:                                                                       |*
*|  Y No version management                                                   |*
*|  Y One codebase                                                            |*
*|  Y Gradual evolution                                                       |*
*|                                                                              |*
*|  CONS:                                                                       |*
*|  X Can't make breaking changes                                             |*
*|  X API bloat over time                                                     |*
*|  X Requires discipline                                                     |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  API VERSIONING COMPARISON                                                   |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Strategy       Visibility   RESTful   Caching    Complexity          | |*
*|  |  --------------------------------------------------------------------  | |*
*|  |                                                                        | |*
*|  |  URI Path       High         No        Easy       Low                 | |*
*|  |  Query Param    Medium       No        Medium     Low                 | |*
*|  |  Header         Low          Yes       Hard       Medium              | |*
*|  |  No Version     N/A          Yes       Easy       Low initially,      | |*
*|  |                                                   high long-term      | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*|  RECOMMENDATION:                                                             |*
*|  * External APIs: URI Path versioning (explicit, easy for consumers)       |*
*|  * Internal APIs: No versioning + evolutionary design                       |*
*|  * GraphQL: No versioning (add fields, deprecate old ones)                 |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*

SECTION 3: SECURITY PATTERNS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  MICROSERVICES SECURITY CONCERNS                                       |*
*|                                                                         |*
*|  * More network surface = more attack vectors                          |*
*|  * Service-to-service authentication                                   |*
*|  * User identity propagation                                           |*
*|  * Secret management                                                   |*
*|  * API security                                                        |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  PATTERN 1: API GATEWAY AUTHENTICATION                                       |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Gateway validates JWT, services trust internal network               | |*
*|  |                                                                        | |*
*|  |  Client --JWT--> API Gateway --verified user ctx--> Services         | |*
*|  |                     |                                                  | |*
*|  |                     | Validate JWT                                    | |*
*|  |                     | Extract user info                               | |*
*|  |                     | Pass as headers:                                | |*
*|  |                     |   X-User-ID: 123                               | |*
*|  |                     |   X-User-Role: admin                           | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*|  PROS: Simple, services don't need auth logic                               |*
*|  CONS: Internal network must be trusted                                     |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  PATTERN 2: JWT TOKEN PROPAGATION                                            |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Pass JWT to all downstream services for validation                   | |*
*|  |                                                                        | |*
*|  |  Client --JWT--> Gateway --JWT--> Service A --JWT--> Service B       | |*
*|  |                     |                |                  |              | |*
*|  |                     | Validate       | Validate         | Validate    | |*
*|  |                     |                |                  |              | |*
*|  |                                                                        | |*
*|  |  Each service validates JWT independently                            | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*|  PROS: Services can validate independently, defense in depth                |*
*|  CONS: Extra validation overhead, token must be available everywhere       |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  PATTERN 3: MUTUAL TLS (mTLS)                                                |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Both client and server authenticate with certificates                | |*
*|  |                                                                        | |*
*|  |  +---------------------------------------------------------------+   | |*
*|  |  |                                                               |   | |*
*|  |  |  Service A                          Service B                |   | |*
*|  |  |  +--------------+                  +--------------+          |   | |*
*|  |  |  | Certificate A|------------------| Certificate B|          |   | |*
*|  |  |  +--------------+                  +--------------+          |   | |*
*|  |  |        |                                  |                   |   | |*
*|  |  |        +---------- mTLS Handshake --------+                   |   | |*
*|  |  |                                                               |   | |*
*|  |  |  1. Service A presents its certificate                       |   | |*
*|  |  |  2. Service B verifies A's certificate                       |   | |*
*|  |  |  3. Service B presents its certificate                       |   | |*
*|  |  |  4. Service A verifies B's certificate                       |   | |*
*|  |  |  5. Encrypted connection established                         |   | |*
*|  |  |                                                               |   | |*
*|  |  +---------------------------------------------------------------+   | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*|  PROS: Strong authentication, encrypted traffic, zero-trust               |*
*|  CONS: Certificate management complexity, performance overhead             |*
*|                                                                              |*
*|  Usually handled by Service Mesh (Istio, Linkerd)                          |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  PATTERN 4: SERVICE-TO-SERVICE AUTHENTICATION                                |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  OPTIONS:                                                             | |*
*|  |                                                                        | |*
*|  |  A. SERVICE ACCOUNTS                                                  | |*
*|  |     Each service has identity (like Kubernetes ServiceAccount)       | |*
*|  |     Used with RBAC to control access                                 | |*
*|  |                                                                        | |*
*|  |  B. API KEYS                                                          | |*
*|  |     Services use pre-shared keys                                     | |*
*|  |     Simple but key rotation is challenging                           | |*
*|  |                                                                        | |*
*|  |  C. OAUTH2 CLIENT CREDENTIALS                                        | |*
*|  |     Services get tokens from auth server                             | |*
*|  |     Service A > Auth Server > Token > Service B                     | |*
*|  |                                                                        | |*
*|  |  D. SPIFFE/SPIRE                                                      | |*
*|  |     Workload identity standard                                       | |*
*|  |     Automatic identity issuance and rotation                        | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*

SECTION 4: TESTING STRATEGIES
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  TESTING PYRAMID FOR MICROSERVICES                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |                        ^                                        |  |*
*|  |                       / \                                       |  |*
*|  |                      /   \                                      |  |*
*|  |                     / E2E \    (Few, slow, expensive)           |  |*
*|  |                    /-------\                                    |  |*
*|  |                   /         \                                   |  |*
*|  |                  / Contract  \                                  |  |*
*|  |                 /-------------\                                 |  |*
*|  |                /               \                                |  |*
*|  |               /   Integration   \                               |  |*
*|  |              /-------------------\                              |  |*
*|  |             /                     \                             |  |*
*|  |            /     Unit Tests        \  (Many, fast, cheap)      |  |*
*|  |           /-------------------------\                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  UNIT TESTS                                                                  |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Test individual components in isolation                              | |*
*|  |  * Business logic                                                     | |*
*|  |  * Domain objects                                                     | |*
*|  |  * Utility functions                                                  | |*
*|  |                                                                        | |*
*|  |  Mock external dependencies                                           | |*
*|  |                                                                        | |*
*|  |  Target: 70-80% coverage                                             | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  INTEGRATION TESTS                                                           |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Test service with real dependencies:                                 | |*
*|  |  * Real database (Testcontainers)                                    | |*
*|  |  * Real message queue                                                | |*
*|  |  * Real cache                                                        | |*
*|  |                                                                        | |*
*|  |  Mock external services (WireMock, MockServer)                       | |*
*|  |                                                                        | |*
*|  |  Example:                                                             | |*
*|  |  Service > Real PostgreSQL (container) > Test assertions            | |*
*|  |  Service > WireMock (mocked Payment API) > Test assertions          | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  CONTRACT TESTS (Consumer-Driven)                                            |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Verify API contracts between services without full integration       | |*
*|  |                                                                        | |*
*|  |  +---------------------------------------------------------------+   | |*
*|  |  |                                                               |   | |*
*|  |  |  CONSUMER SIDE (Order Service needs User Service)            |   | |*
*|  |  |                                                               |   | |*
*|  |  |  "When I call GET /users/123,                                |   | |*
*|  |  |   I expect { 'id': 123, 'name': string, 'email': string }"  |   | |*
*|  |  |                                                               |   | |*
*|  |  |  This expectation > CONTRACT (Pact file)                     |   | |*
*|  |  |                                                               |   | |*
*|  |  |  --------------------------------------------------------    |   | |*
*|  |  |                                                               |   | |*
*|  |  |  PROVIDER SIDE (User Service)                                |   | |*
*|  |  |                                                               |   | |*
*|  |  |  Run Contract against actual service                         |   | |*
*|  |  |  Verify it returns what consumer expects                     |   | |*
*|  |  |                                                               |   | |*
*|  |  +---------------------------------------------------------------+   | |*
*|  |                                                                        | |*
*|  |  TOOLS: Pact, Spring Cloud Contract                                  | |*
*|  |                                                                        | |*
*|  |  Benefits:                                                            | |*
*|  |  * Catch breaking changes before deployment                          | |*
*|  |  * Faster than full E2E tests                                        | |*
*|  |  * Consumer defines expectations                                     | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  END-TO-END (E2E) TESTS                                                      |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Test complete user flows through all services                        | |*
*|  |                                                                        | |*
*|  |  Example: Place an order                                             | |*
*|  |  1. User login > Auth Service                                        | |*
*|  |  2. Browse products > Product Service                                | |*
*|  |  3. Add to cart > Cart Service                                       | |*
*|  |  4. Checkout > Order Service > Inventory > Payment                   | |*
*|  |  5. Verify order created                                             | |*
*|  |                                                                        | |*
*|  |  CHALLENGES:                                                          | |*
*|  |  * Slow to run                                                       | |*
*|  |  * Flaky (network, timing issues)                                    | |*
*|  |  * Hard to set up test data                                          | |*
*|  |  * Hard to debug failures                                            | |*
*|  |                                                                        | |*
*|  |  RECOMMENDATION: Few critical path tests only                        | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  CHAOS TESTING                                                               |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Intentionally inject failures to test resilience                    | |*
*|  |                                                                        | |*
*|  |  TYPES OF CHAOS:                                                      | |*
*|  |  * Kill random pods                                                  | |*
*|  |  * Add network latency                                               | |*
*|  |  * Inject 500 errors                                                 | |*
*|  |  * Exhaust resources (CPU, memory)                                   | |*
*|  |  * Partition network                                                 | |*
*|  |                                                                        | |*
*|  |  TOOLS:                                                               | |*
*|  |  * Chaos Monkey (Netflix)                                            | |*
*|  |  * Litmus Chaos (Kubernetes)                                         | |*
*|  |  * Gremlin (SaaS)                                                    | |*
*|  |  * Chaos Mesh                                                         | |*
*|  |                                                                        | |*
*|  |  RUN IN: Staging first, then production (carefully!)                 | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*

SECTION 5: ANTI-PATTERNS TO AVOID
## +------------------------------------------------------------------------------+
*|                                                                              |*
*|  ANTI-PATTERN 1: DISTRIBUTED MONOLITH                                        |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Services are "microservices" but:                                    | |*
*|  |  * Must be deployed together                                         | |*
*|  |  * Share database                                                     | |*
*|  |  * Tightly coupled APIs                                              | |*
*|  |  * Can't be developed independently                                  | |*
*|  |                                                                        | |*
*|  |  > Worst of both worlds!                                             | |*
*|  |                                                                        | |*
*|  |  FIX: True bounded contexts, database per service, async events      | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  ANTI-PATTERN 2: SHARED DATABASE                                             |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Multiple services accessing same database tables                     | |*
*|  |                                                                        | |*
*|  |  Service A --+                                                        | |*
*|  |              |                                                         | |*
*|  |  Service B --+--> Same Database                                       | |*
*|  |              |                                                         | |*
*|  |  Service C --+                                                        | |*
*|  |                                                                        | |*
*|  |  PROBLEMS:                                                            | |*
*|  |  * Schema changes break multiple services                            | |*
*|  |  * Can't scale independently                                         | |*
*|  |  * Tight coupling                                                     | |*
*|  |  * Single point of failure                                           | |*
*|  |                                                                        | |*
*|  |  FIX: Database per service, API calls or events for data sharing     | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  ANTI-PATTERN 3: CHATTY SERVICES (Too Many Calls)                           |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  One request requires many inter-service calls                        | |*
*|  |                                                                        | |*
*|  |  Client > A > B > C > D > E > F                                      | |*
*|  |                                                                        | |*
*|  |  PROBLEMS:                                                            | |*
*|  |  * Latency adds up                                                   | |*
*|  |  * Failure probability increases                                     | |*
*|  |  * Hard to debug                                                     | |*
*|  |                                                                        | |*
*|  |  FIX:                                                                 | |*
*|  |  * API composition (BFF aggregates calls)                           | |*
*|  |  * Denormalize data (data duplication is OK)                        | |*
*|  |  * Reconsider service boundaries                                    | |*
*|  |  * Use async events instead of sync calls                           | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  ANTI-PATTERN 4: NO API VERSIONING                                           |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Making breaking changes without version management                   | |*
*|  |                                                                        | |*
*|  |  RESULT:                                                              | |*
*|  |  * Break all consumers at once                                       | |*
*|  |  * Coordinated deployments required                                  | |*
*|  |  * Can't rollback easily                                             | |*
*|  |                                                                        | |*
*|  |  FIX: Version APIs, backward compatibility, deprecation period       | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  ANTI-PATTERN 5: NANOSERVICES (Too Small)                                    |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Breaking down into too many tiny services                           | |*
*|  |                                                                        | |*
*|  |  PROBLEMS:                                                            | |*
*|  |  * Operational overhead per service                                  | |*
*|  |  * Network latency                                                    | |*
*|  |  * Distributed transaction complexity                                | |*
*|  |  * Hard to understand the system                                     | |*
*|  |                                                                        | |*
*|  |  SIGNS:                                                               | |*
*|  |  * Service has only CRUD operations                                  | |*
*|  |  * Service can't do anything useful alone                           | |*
*|  |  * Service is just a database wrapper                               | |*
*|  |                                                                        | |*
*|  |  FIX: Merge related services, align with business capability        | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  ANTI-PATTERN 6: SYNCHRONOUS CHAIN                                           |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  A --sync--> B --sync--> C --sync--> D                               | |*
*|  |                                                                        | |*
*|  |  If D is slow/down, A blocks for entire chain!                       | |*
*|  |                                                                        | |*
*|  |  PROBLEMS:                                                            | |*
*|  |  * Cascading failures                                                | |*
*|  |  * Latency compounds                                                 | |*
*|  |  * Availability: 99%^4 = 96% for chain of 4                         | |*
*|  |                                                                        | |*
*|  |  FIX:                                                                 | |*
*|  |  * Use async messaging where possible                               | |*
*|  |  * Circuit breakers                                                  | |*
*|  |  * Caching                                                           | |*
*|  |  * Timeouts and fallbacks                                           | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*

SECTION 6: CONWAY'S LAW & TEAM ORGANIZATION
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  CONWAY'S LAW                                                          |*
*|                                                                         |*
*|  "Organizations design systems that mirror their communication         |*
*|   structure."                                                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  If you have 4 teams, you'll likely get 4 services             |  |*
*|  |                                                                 |  |*
*|  |  Team structure shapes architecture!                           |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  BAD: Teams organized by technical layer                 ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Frontend Team    Backend Team    Database Team          ||  |*
*|  |  |       v               v               v                  ||  |*
*|  |  |  [Frontend]      [Backend]        [Database]             ||  |*
*|  |  |                                                           ||  |*
*|  |  |  > Changes require 3 teams to coordinate!                ||  |*
*|  |  |                                                           ||  |*
*|  |  |  ------------------------------------------------------  ||  |*
*|  |  |                                                           ||  |*
*|  |  |  GOOD: Teams organized by business capability            ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Order Team         Payment Team      Shipping Team      ||  |*
*|  |  |       v                  v                 v              ||  |*
*|  |  |  [Order Service]   [Payment Service]  [Shipping Service] ||  |*
*|  |  |  (full stack)      (full stack)       (full stack)       ||  |*
*|  |  |                                                           ||  |*
*|  |  |  > Each team owns end-to-end!                            ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  INVERSE CONWAY MANEUVER                                               |*
*|                                                                         |*
*|  Design your org structure to get the architecture you want!           |*
*|                                                                         |*
*|  Want microservices? > Create small, cross-functional teams            |*
*|  Want fewer services? > Consolidate teams                              |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  TEAM TOPOLOGIES                                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  STREAM-ALIGNED TEAM                                           |  |*
*|  |  * Owns a business capability end-to-end                       |  |*
*|  |  * Delivers value directly to customers                        |  |*
*|  |  * Example: Checkout Team, Search Team                         |  |*
*|  |                                                                 |  |*
*|  |  PLATFORM TEAM                                                  |  |*
*|  |  * Provides internal services to stream-aligned teams          |  |*
*|  |  * Reduces cognitive load                                      |  |*
*|  |  * Example: CI/CD platform, Kubernetes platform                |  |*
*|  |                                                                 |  |*
*|  |  ENABLING TEAM                                                  |  |*
*|  |  * Helps other teams adopt new practices                       |  |*
*|  |  * Temporary support                                           |  |*
*|  |  * Example: DevOps enablement, Security coaching               |  |*
*|  |                                                                 |  |*
*|  |  COMPLICATED SUBSYSTEM TEAM                                     |  |*
*|  |  * Owns complex technical component                            |  |*
*|  |  * Requires specialist knowledge                               |  |*
*|  |  * Example: ML model training, Video encoding                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 7: gRPC vs REST COMPARISON
## +------------------------------------------------------------------------------+
*|                                                                              |*
*|  REST vs gRPC DETAILED COMPARISON                                            |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Aspect              REST                    gRPC                      | |*
*|  |  --------------------------------------------------------------------  | |*
*|  |                                                                        | |*
*|  |  Protocol            HTTP/1.1 (usually)      HTTP/2                    | |*
*|  |                                                                        | |*
*|  |  Payload             JSON (text)             Protobuf (binary)         | |*
*|  |                                                                        | |*
*|  |  Contract            OpenAPI/Swagger         .proto files              | |*
*|  |                      (optional)              (required)                | |*
*|  |                                                                        | |*
*|  |  Streaming           Limited (SSE, WS)       Native bidirectional     | |*
*|  |                                                                        | |*
*|  |  Browser Support     Native                  Needs grpc-web proxy      | |*
*|  |                                                                        | |*
*|  |  Debugging           Easy (readable JSON)    Harder (binary)           | |*
*|  |                                                                        | |*
*|  |  Performance         Good                    Better (3-10x faster)     | |*
*|  |                                                                        | |*
*|  |  Tooling             Mature, widespread      Growing                   | |*
*|  |                                                                        | |*
*|  |  Code Generation     Optional                Required                  | |*
*|  |                                                                        | |*
*|  |  Learning Curve      Low                     Medium                    | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*|  WHEN TO USE REST:                                                           |*
*|  * Public APIs (browser clients)                                            |*
*|  * Simple CRUD operations                                                   |*
*|  * Need easy debugging                                                      |*
*|  * Wide client compatibility                                                |*
*|                                                                              |*
*|  WHEN TO USE gRPC:                                                           |*
*|  * Internal service-to-service                                              |*
*|  * High performance requirements                                            |*
*|  * Streaming needed                                                         |*
*|  * Polyglot environment (strong typing helps)                              |*
*|  * Real-time communication                                                  |*
*|                                                                              |*
*|  COMMON PATTERN:                                                             |*
*|  * REST for external APIs                                                   |*
*|  * gRPC for internal communication                                          |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*

SECTION 8: MIGRATION FROM MONOLITH
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  MIGRATION STRATEGIES                                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. STRANGLER FIG PATTERN                                      |  |*
*|  |     * Gradually replace parts                                  |  |*
*|  |     * Use facade to route                                     |  |*
*|  |     * Extract one capability at a time                        |  |*
*|  |     * Best for: Large, complex monoliths                      |  |*
*|  |                                                                 |  |*
*|  |  2. BRANCH BY ABSTRACTION                                      |  |*
*|  |     * Create abstraction layer                                |  |*
*|  |     * Implement new service behind abstraction                |  |*
*|  |     * Switch implementations                                   |  |*
*|  |     * Best for: Internal modules                              |  |*
*|  |                                                                 |  |*
*|  |  3. PARALLEL RUN                                               |  |*
*|  |     * Run both old and new                                    |  |*
*|  |     * Compare results                                         |  |*
*|  |     * Switch when confident                                   |  |*
*|  |     * Best for: Critical functionality                        |  |*
*|  |                                                                 |  |*
*|  |  4. BIG BANG REWRITE                                           |  |*
*|  |     * Rewrite everything                                      |  |*
*|  |     * Usually fails!                                          |  |*
*|  |     * Avoid unless monolith is tiny                          |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  EXTRACTION PRIORITIZATION:                                            |*
*|  1. Identify bounded contexts in monolith                             |*
*|  2. Extract what changes most frequently                              |*
*|  3. Extract what needs different scaling                              |*
*|  4. Extract what causes most coupling issues                          |*
*|  5. Keep stable, rarely changing parts last                           |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 9: INTERVIEW QUICK REFERENCE
## +------------------------------------------------------------------------------+
*|                                                                              |*
*|  COMMONLY ASKED QUESTIONS                                                    |*
*|                                                                              |*
*|  Q: How do you handle distributed transactions?                             |*
*|  A: Saga pattern (choreography/orchestration), eventual consistency,        |*
*|     avoid 2PC in microservices                                              |*
*|                                                                              |*
*|  Q: How do you ensure data consistency?                                     |*
*|  A: Event sourcing, outbox pattern, idempotency, compensating transactions |*
*|                                                                              |*
*|  Q: How do you handle service failures?                                     |*
*|  A: Circuit breaker, retries with backoff, timeouts, fallbacks, bulkhead  |*
*|                                                                              |*
*|  Q: How do services discover each other?                                    |*
*|  A: Service discovery (Consul, K8s DNS), service mesh, API gateway         |*
*|                                                                              |*
*|  Q: How do you debug issues across services?                               |*
*|  A: Distributed tracing (Jaeger), correlation IDs, centralized logging    |*
*|                                                                              |*
*|  Q: How do you secure service-to-service communication?                    |*
*|  A: mTLS, JWT propagation, service mesh, API gateway auth                  |*
*|                                                                              |*
*|  Q: When would you NOT use microservices?                                  |*
*|  A: Small team, simple domain, early startup, tight deadlines             |*
*|                                                                              |*
*|  Q: How do you handle API versioning?                                      |*
*|  A: URL path versioning, backward compatible changes, deprecation period  |*
*|                                                                              |*
*|  Q: What's the distributed monolith anti-pattern?                          |*
*|  A: Services that must be deployed together, share DB, tightly coupled    |*
*|                                                                              |*
*|  Q: How do you test microservices?                                         |*
*|  A: Unit > Integration > Contract > E2E > Chaos testing                   |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*

END OF ADVANCED TOPICS
