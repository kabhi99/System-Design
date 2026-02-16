# MICROSERVICES ARCHITECTURE - HIGH LEVEL DESIGN

CHAPTER 1: FUNDAMENTALS AND PATTERNS
SECTION 1: WHAT ARE MICROSERVICES?
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  DEFINITION                                                            |*
*|                                                                         |*
*|  Microservices architecture is a design approach where a large         |*
*|  application is composed of small, independent services that:          |*
*|                                                                         |*
*|  * Run in their own process                                            |*
*|  * Communicate via lightweight protocols (HTTP, gRPC, messaging)       |*
*|  * Are independently deployable                                        |*
*|  * Are organized around business capabilities                          |*
*|  * Can be written in different programming languages                   |*
*|  * Can use different data storage technologies                         |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  MONOLITH vs MICROSERVICES                                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  MONOLITHIC ARCHITECTURE:                                       |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |              SINGLE DEPLOYABLE UNIT                    |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  +---------+  +---------+  +---------+  +---------+  |  |  |*
*|  |  |  |  User   |  |  Order  |  | Payment |  |Inventory|  |  |  |*
*|  |  |  | Module  |  | Module  |  | Module  |  | Module  |  |  |  |*
*|  |  |  +---------+  +---------+  +---------+  +---------+  |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |           SHARED DATABASE                               |  |  |*
*|  |  |  +-------------------------------------------------+  |  |  |*
*|  |  |  |                  PostgreSQL                      |  |  |  |*
*|  |  |  +-------------------------------------------------+  |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  |  Pros: Simple to develop, test, deploy initially              |  |*
*|  |  Cons: Tightly coupled, hard to scale, single point of failure|  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  MICROSERVICES ARCHITECTURE:                                   |  |*
*|  |                                                                 |  |*
*|  |  +-----------+  +-----------+  +-----------+  +-----------+  |  |*
*|  |  |   User    |  |   Order   |  |  Payment  |  | Inventory |  |  |*
*|  |  |  Service  |  |  Service  |  |  Service  |  |  Service  |  |  |*
*|  |  +-----+-----+  +-----+-----+  +-----+-----+  +-----+-----+  |  |*
*|  |        |              |              |              |         |  |*
*|  |        v              v              v              v         |  |*
*|  |  +---------+    +---------+    +---------+    +---------+   |  |*
*|  |  | User DB |    |Order DB |    |Payment  |    |Inventory|   |  |*
*|  |  |(Postgres)|   |(MongoDB)|    |   DB    |    |   DB    |   |  |*
*|  |  +---------+    +---------+    +---------+    +---------+   |  |*
*|  |                                                               |  |*
*|  |  Pros: Independent scaling, fault isolation, tech flexibility |  |*
*|  |  Cons: Complexity, distributed system challenges              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  WHEN TO USE MICROSERVICES                                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  USE MICROSERVICES WHEN:                                       |  |*
*|  |                                                                 |  |*
*|  |  Y Large, complex application with multiple teams              |  |*
*|  |  Y Need to scale different parts independently                 |  |*
*|  |  Y Require fault isolation (one failure shouldn't crash all)  |  |*
*|  |  Y Teams need autonomy to choose tech stack                    |  |*
*|  |  Y Frequent deployments needed for specific features           |  |*
*|  |  Y Organization structure supports distributed teams           |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  AVOID MICROSERVICES WHEN:                                     |  |*
*|  |                                                                 |  |*
*|  |  X Small team (< 10 developers)                               |  |*
*|  |  X Simple domain with few features                             |  |*
*|  |  X Startup phase (domain not well understood)                  |  |*
*|  |  X Tight deadlines with limited DevOps maturity                |  |*
*|  |  X Strong data consistency requirements                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2: SERVICE DECOMPOSITION
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  HOW TO BREAK DOWN A MONOLITH INTO SERVICES                           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  APPROACH 1: DECOMPOSE BY BUSINESS CAPABILITY                  |  |*
*|  |                                                                 |  |*
*|  |  E-Commerce Example:                                            |  |*
*|  |                                                                 |  |*
*|  |  Business Capabilities > Services                              |  |*
*|  |                                                                 |  |*
*|  |  * User Management      > User Service                         |  |*
*|  |  * Product Catalog      > Product Service                      |  |*
*|  |  * Shopping Cart        > Cart Service                         |  |*
*|  |  * Order Processing     > Order Service                        |  |*
*|  |  * Payment Processing   > Payment Service                      |  |*
*|  |  * Inventory Management > Inventory Service                    |  |*
*|  |  * Shipping/Delivery    > Shipping Service                     |  |*
*|  |  * Notifications        > Notification Service                 |  |*
*|  |  * Search               > Search Service                       |  |*
*|  |  * Recommendations      > Recommendation Service               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  APPROACH 2: DECOMPOSE BY SUBDOMAIN (Domain-Driven Design)     |  |*
*|  |                                                                 |  |*
*|  |  Identify Bounded Contexts:                                     |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  CORE DOMAIN (Competitive advantage)                   |  |  |*
*|  |  |  * Pricing Engine                                      |  |  |*
*|  |  |  * Recommendation Engine                               |  |  |*
*|  |  |  * Fraud Detection                                     |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  SUPPORTING DOMAIN (Necessary but not differentiating) |  |  |*
*|  |  |  * Order Management                                    |  |  |*
*|  |  |  * Inventory                                           |  |  |*
*|  |  |  * Customer Service                                    |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  GENERIC DOMAIN (Commodity, can buy off-shelf)        |  |  |*
*|  |  |  * Authentication (Auth0, Okta)                       |  |  |*
*|  |  |  * Payment Processing (Stripe, PayPal)                |  |  |*
*|  |  |  * Email/SMS (SendGrid, Twilio)                       |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  SERVICE SIZING (How Big/Small?)                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  GUIDELINES:                                                    |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  "Two Pizza Rule" (Amazon)                                     |  |*
*|  |  A service should be owned by a team that can be fed           |  |*
*|  |  by two pizzas (~6-10 people)                                  |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  "Single Responsibility"                                       |  |*
*|  |  A service should do one thing and do it well                 |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  "Can be rewritten in 2 weeks"                                 |  |*
*|  |  If a service is so complex it takes months to rewrite,       |  |*
*|  |  it's probably too big                                         |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  TOO SMALL (Nanoservices):                                     |  |*
*|  |  * Overhead outweighs benefits                                 |  |*
*|  |  * Too many network calls                                      |  |*
*|  |  * Hard to understand the system                               |  |*
*|  |                                                                 |  |*
*|  |  TOO BIG (Distributed Monolith):                               |  |*
*|  |  * Still tightly coupled                                       |  |*
*|  |  * Can't deploy independently                                  |  |*
*|  |  * Multiple teams stepping on each other                       |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3: KEY DESIGN PRINCIPLES
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  PRINCIPLE 1: DATABASE PER SERVICE                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Each service owns its data. No direct database sharing.       |  |*
*|  |                                                                 |  |*
*|  |  +-------------+       +-------------+       +-------------+  |  |*
*|  |  |   Order     |       |   Product   |       |    User     |  |  |*
*|  |  |   Service   |       |   Service   |       |   Service   |  |  |*
*|  |  +------+------+       +------+------+       +------+------+  |  |*
*|  |         |                     |                     |          |  |*
*|  |         v                     v                     v          |  |*
*|  |  +-------------+       +-------------+       +-------------+  |  |*
*|  |  |  Order DB   |       | Product DB  |       |   User DB   |  |  |*
*|  |  |  (MongoDB)  |       | (Postgres)  |       |  (Postgres) |  |  |*
*|  |  +-------------+       +-------------+       +-------------+  |  |*
*|  |                                                                 |  |*
*|  |  WHY?                                                          |  |*
*|  |  * Loose coupling: services can evolve independently          |  |*
*|  |  * Right tool for the job: each service picks best DB         |  |*
*|  |  * Independent scaling: scale DB per service needs            |  |*
*|  |  * Failure isolation: one DB down doesn't affect others       |  |*
*|  |                                                                 |  |*
*|  |  CHALLENGE:                                                    |  |*
*|  |  * No ACID transactions across services                       |  |*
*|  |  * Data consistency is eventual                               |  |*
*|  |  * Joins require API calls or data duplication                |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  PRINCIPLE 2: SMART ENDPOINTS, DUMB PIPES                              |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Business logic lives IN the services, not in the middleware.  |  |*
*|  |                                                                 |  |*
*|  |  DUMB PIPES:                                                    |  |*
*|  |  * Simple message transport (Kafka, RabbitMQ)                  |  |*
*|  |  * No business logic in messaging layer                        |  |*
*|  |  * HTTP/gRPC for synchronous calls                            |  |*
*|  |                                                                 |  |*
*|  |  SMART ENDPOINTS:                                               |  |*
*|  |  * Services contain all business logic                         |  |*
*|  |  * Services decide how to process messages                     |  |*
*|  |  * Services handle retries, transformations                    |  |*
*|  |                                                                 |  |*
*|  |  ANTI-PATTERN (ESB - Enterprise Service Bus):                  |  |*
*|  |  * Complex routing logic in middleware                         |  |*
*|  |  * Message transformation in bus                               |  |*
*|  |  * Orchestration in middleware                                 |  |*
*|  |  > Creates central bottleneck and coupling                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  PRINCIPLE 3: DESIGN FOR FAILURE                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  In distributed systems, failures are NORMAL, not exceptional. |  |*
*|  |                                                                 |  |*
*|  |  ASSUME:                                                        |  |*
*|  |  * Network calls WILL fail                                     |  |*
*|  |  * Services WILL be unavailable                                |  |*
*|  |  * Latency WILL spike                                          |  |*
*|  |  * Databases WILL have issues                                  |  |*
*|  |                                                                 |  |*
*|  |  PATTERNS TO HANDLE:                                            |  |*
*|  |  * Timeouts on all external calls                              |  |*
*|  |  * Retries with exponential backoff                            |  |*
*|  |  * Circuit breakers to prevent cascading failures              |  |*
*|  |  * Bulkheads to isolate failures                               |  |*
*|  |  * Graceful degradation                                        |  |*
*|  |  * Health checks and monitoring                                |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  PRINCIPLE 4: DECENTRALIZED GOVERNANCE                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Teams can choose their own:                                    |  |*
*|  |  * Programming language (Java, Go, Python, Node.js)            |  |*
*|  |  * Framework (Spring Boot, FastAPI, Express)                   |  |*
*|  |  * Database (PostgreSQL, MongoDB, Redis, Cassandra)            |  |*
*|  |  * Deployment model                                             |  |*
*|  |                                                                 |  |*
*|  |  STANDARDIZE ON:                                                |  |*
*|  |  * Communication protocols (HTTP/gRPC, message formats)        |  |*
*|  |  * API contracts and documentation                             |  |*
*|  |  * Logging format and observability                            |  |*
*|  |  * Security standards                                          |  |*
*|  |  * CI/CD pipeline patterns                                     |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4: SERVICE-TO-SERVICE COMMUNICATION
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SYNCHRONOUS vs ASYNCHRONOUS COMMUNICATION                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  SYNCHRONOUS (Request-Response)                                |  |*
*|  |                                                                 |  |*
*|  |  Service A --------> Service B                                 |  |*
*|  |      |                   |                                      |  |*
*|  |      | Request           | Process                             |  |*
*|  |      |                   |                                      |  |*
*|  |      |<----------------  |                                      |  |*
*|  |           Response                                              |  |*
*|  |                                                                 |  |*
*|  |  Protocols: HTTP/REST, gRPC, GraphQL                           |  |*
*|  |                                                                 |  |*
*|  |  Use When:                                                      |  |*
*|  |  * Need immediate response                                     |  |*
*|  |  * Simple request-response pattern                             |  |*
*|  |  * Query operations                                            |  |*
*|  |                                                                 |  |*
*|  |  Drawbacks:                                                     |  |*
*|  |  * Tight temporal coupling                                     |  |*
*|  |  * Caller blocked waiting for response                         |  |*
*|  |  * Cascading failures if downstream slow                       |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  ASYNCHRONOUS (Event-Driven / Messaging)                       |  |*
*|  |                                                                 |  |*
*|  |  Service A --------> Message Broker --------> Service B        |  |*
*|  |      |                     |                      |            |  |*
*|  |      | Publish             |                      | Consume    |  |*
*|  |      |                     |                      |            |  |*
*|  |      | (continues)         | (stored)             | (later)    |  |*
*|  |                                                                 |  |*
*|  |  Technologies: Kafka, RabbitMQ, AWS SQS/SNS                    |  |*
*|  |                                                                 |  |*
*|  |  Use When:                                                      |  |*
*|  |  * Fire-and-forget operations                                  |  |*
*|  |  * Long-running processes                                      |  |*
*|  |  * Decoupling producers from consumers                         |  |*
*|  |  * Event broadcasting to multiple consumers                    |  |*
*|  |                                                                 |  |*
*|  |  Benefits:                                                      |  |*
*|  |  * Loose coupling                                              |  |*
*|  |  * Better fault tolerance                                      |  |*
*|  |  * Load leveling (absorb traffic spikes)                       |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  COMMUNICATION PATTERNS COMPARISON                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  PATTERN          WHEN TO USE              EXAMPLE              |  |*
*|  |  ------------------------------------------------------------- |  |*
*|  |                                                                 |  |*
*|  |  REST/HTTP        CRUD operations,         GET /users/123      |  |*
*|  |                   Simple queries           POST /orders         |  |*
*|  |                                                                 |  |*
*|  |  gRPC             High performance,        Internal service    |  |*
*|  |                   Strong contracts,        communication,      |  |*
*|  |                   Streaming                Polyglot systems    |  |*
*|  |                                                                 |  |*
*|  |  GraphQL          Complex queries,         Client-facing API   |  |*
*|  |                   Mobile apps              with varying needs  |  |*
*|  |                   (bandwidth sensitive)                         |  |*
*|  |                                                                 |  |*
*|  |  Events           State changes,           Order placed,       |  |*
*|  |  (Pub/Sub)        Multiple consumers,      User registered     |  |*
*|  |                   Audit trail                                   |  |*
*|  |                                                                 |  |*
*|  |  Commands         Specific action,         ProcessPayment,     |  |*
*|  |  (Queue)          Single consumer,         SendEmail           |  |*
*|  |                   Guaranteed delivery                           |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 5: DATA CONSISTENCY PATTERNS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  THE CONSISTENCY CHALLENGE                                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  In monolith: Single database, ACID transactions                |  |*
*|  |                                                                 |  |*
*|  |  In microservices: Each service has own DB                     |  |*
*|  |  > No distributed transactions (2PC is impractical)            |  |*
*|  |  > Need eventual consistency patterns                           |  |*
*|  |                                                                 |  |*
*|  |  EXAMPLE PROBLEM:                                               |  |*
*|  |                                                                 |  |*
*|  |  Order Service wants to:                                        |  |*
*|  |  1. Create order in Order DB                                   |  |*
*|  |  2. Reserve inventory in Inventory DB                          |  |*
*|  |  3. Charge payment in Payment Service                          |  |*
*|  |                                                                 |  |*
*|  |  If step 3 fails, how to rollback step 1 and 2?               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  PATTERN 1: SAGA PATTERN                                               |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Sequence of local transactions where each step publishes      |  |*
*|  |  an event that triggers the next step. If a step fails,       |  |*
*|  |  compensating transactions undo previous steps.                |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  CHOREOGRAPHY SAGA (Event-driven, decentralized)               |  |*
*|  |                                                                 |  |*
*|  |  +-----------+    +-----------+    +-----------+              |  |*
*|  |  |  Order    |--->| Inventory |--->|  Payment  |              |  |*
*|  |  |  Service  |    |  Service  |    |  Service  |              |  |*
*|  |  +-----------+    +-----------+    +-----------+              |  |*
*|  |        |                |                |                     |  |*
*|  |        | OrderCreated   | InventoryReserved  | PaymentProcessed|  |*
*|  |        v                v                v                     |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                   EVENT BUS (Kafka)                     |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  |  On failure: Services listen for failure events and           |  |*
*|  |              trigger compensating actions                      |  |*
*|  |                                                                 |  |*
*|  |  Pros: Loose coupling, no single point of failure             |  |*
*|  |  Cons: Hard to track overall flow, complex to debug           |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  ORCHESTRATION SAGA (Central coordinator)                      |  |*
*|  |                                                                 |  |*
*|  |                  +---------------+                             |  |*
*|  |                  |     Saga      |                             |  |*
*|  |                  |  Orchestrator |                             |  |*
*|  |                  +-------+-------+                             |  |*
*|  |                          |                                     |  |*
*|  |          +---------------+---------------+                     |  |*
*|  |          |               |               |                     |  |*
*|  |          v               v               v                     |  |*
*|  |    +-----------+  +-----------+  +-----------+                |  |*
*|  |    |  Order    |  | Inventory |  |  Payment  |                |  |*
*|  |    |  Service  |  |  Service  |  |  Service  |                |  |*
*|  |    +-----------+  +-----------+  +-----------+                |  |*
*|  |                                                                 |  |*
*|  |  Orchestrator coordinates the flow:                            |  |*
*|  |  1. Call Order Service > Create Order                         |  |*
*|  |  2. Call Inventory Service > Reserve                          |  |*
*|  |  3. Call Payment Service > Charge                             |  |*
*|  |  On failure: Orchestrator calls compensating actions           |  |*
*|  |                                                                 |  |*
*|  |  Pros: Easy to understand flow, centralized logic             |  |*
*|  |  Cons: Single point of coordination, tighter coupling         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  PATTERN 2: OUTBOX PATTERN                                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  PROBLEM: How to reliably publish events when updating DB?    |  |*
*|  |                                                                 |  |*
*|  |  Naive approach fails:                                          |  |*
*|  |  1. Update database                                            |  |*
*|  |  2. Publish to Kafka < What if this fails? Data inconsistent! |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  SOLUTION: Transactional Outbox                                |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  SERVICE DATABASE                                         ||  |*
*|  |  |                                                           ||  |*
*|  |  |  +-----------------+    +-----------------+              ||  |*
*|  |  |  |   Orders Table  |    |  Outbox Table   |              ||  |*
*|  |  |  |                 |    |                 |              ||  |*
*|  |  |  | INSERT order    |    | INSERT event    |              ||  |*
*|  |  |  |                 |    |                 |              ||  |*
*|  |  |  +-----------------+    +-----------------+              ||  |*
*|  |  |                                                           ||  |*
*|  |  |  ^                                                        ||  |*
*|  |  |  | SINGLE TRANSACTION (ACID)                             ||  |*
*|  |  |  |                                                        ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |               |                                                 |  |*
*|  |               | Background process reads outbox                |  |*
*|  |               v                                                 |  |*
*|  |  +-------------------+                                         |  |*
*|  |  |  Message Relay    | (CDC or polling)                        |  |*
*|  |  |    Process        |                                         |  |*
*|  |  +---------+---------+                                         |  |*
*|  |            |                                                    |  |*
*|  |            | Publish events                                    |  |*
*|  |            v                                                    |  |*
*|  |  +-------------------+                                         |  |*
*|  |  |      Kafka        |                                         |  |*
*|  |  +-------------------+                                         |  |*
*|  |                                                                 |  |*
*|  |  Guarantees: Either both DB update AND event happen,           |  |*
*|  |              or neither happens                                |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  PATTERN 3: CQRS (Command Query Responsibility Segregation)           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Separate read and write models for different optimization.    |  |*
*|  |                                                                 |  |*
*|  |                     +-----------------+                        |  |*
*|  |                     |     Client      |                        |  |*
*|  |                     +--------+--------+                        |  |*
*|  |                              |                                  |  |*
*|  |              +---------------+---------------+                  |  |*
*|  |              |                               |                  |  |*
*|  |              v                               v                  |  |*
*|  |  +---------------------+       +---------------------+        |  |*
*|  |  |   COMMAND SIDE     |       |    QUERY SIDE       |        |  |*
*|  |  |   (Write Model)    |       |   (Read Model)      |        |  |*
*|  |  |                    |       |                     |        |  |*
*|  |  |  * Create Order    |       |  * Get Order List   |        |  |*
*|  |  |  * Update Order    |       |  * Get Order Details|        |  |*
*|  |  |  * Complex logic   |       |  * Optimized queries|        |  |*
*|  |  |                    |       |                     |        |  |*
*|  |  +---------+----------+       +----------+----------+        |  |*
*|  |            |                             |                    |  |*
*|  |            v                             v                    |  |*
*|  |  +---------------------+       +---------------------+        |  |*
*|  |  |   Write Database   |------>|   Read Database     |        |  |*
*|  |  |   (Normalized)     | Event |  (Denormalized)     |        |  |*
*|  |  |   PostgreSQL       |  Sync |  Elasticsearch      |        |  |*
*|  |  +---------------------+       +---------------------+        |  |*
*|  |                                                                 |  |*
*|  |  Benefits:                                                     |  |*
*|  |  * Reads and writes scaled independently                       |  |*
*|  |  * Read model optimized for query patterns                    |  |*
*|  |  * Write model optimized for business logic                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF CHAPTER 1
