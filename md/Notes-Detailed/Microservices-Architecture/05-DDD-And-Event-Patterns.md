# MICROSERVICES ARCHITECTURE - DDD & EVENT-DRIVEN PATTERNS

CHAPTER 5: DOMAIN-DRIVEN DESIGN, CHOREOGRAPHY, AND EVENT PATTERNS
SECTION 1: DOMAIN-DRIVEN DESIGN (DDD) FUNDAMENTALS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHAT IS DDD?                                                          |*
*|                                                                         |*
*|  Domain-Driven Design is an approach to software development that:     |*
*|                                                                         |*
*|  * Focuses on the core BUSINESS DOMAIN                                 |*
*|  * Uses a UBIQUITOUS LANGUAGE shared by developers and domain experts |*
*|  * Models complex business logic through well-defined patterns         |*
*|  * Organizes code around BOUNDED CONTEXTS                              |*
*|                                                                         |*
*|  Key insight: The structure of your code should mirror the structure  |*
*|  of your business domain.                                              |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 2: STRATEGIC DDD PATTERNS
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  BOUNDED CONTEXT                                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  A BOUNDED CONTEXT is a boundary within which a particular     |  |*
*|  |  model is defined and applicable. The same term can mean       |  |*
*|  |  different things in different contexts.                       |  |*
*|  |                                                                 |  |*
*|  |  Example: "Customer" in E-Commerce                             |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  SALES CONTEXT            SUPPORT CONTEXT               |  |  |*
*|  |  |  -------------            ---------------               |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  Customer =               Customer =                    |  |  |*
*|  |  |  * Name                   * Name                        |  |  |*
*|  |  |  * Email                  * Account ID                  |  |  |*
*|  |  |  * Shipping Address       * Ticket History              |  |  |*
*|  |  |  * Payment Methods        * Satisfaction Score          |  |  |*
*|  |  |  * Order History          * Priority Level              |  |  |*
*|  |  |  * Cart                   * Support Plan                |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  Different attributes, different behavior!              |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  |  Each Bounded Context > One Microservice                       |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  UBIQUITOUS LANGUAGE                                                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  A shared language between developers and domain experts       |  |*
*|  |  that is used consistently in:                                 |  |*
*|  |  * Conversations                                               |  |*
*|  |  * Documentation                                               |  |*
*|  |  * CODE (class names, method names, variables)                |  |*
*|  |                                                                 |  |*
*|  |  BAD: Generic technical terms                                  |  |*
*|  |  ----------------------------                                  |  |*
*|  |  class DataProcessor {                                        |  |*
*|  |      void process(Record record) { ... }                      |  |*
*|  |  }                                                             |  |*
*|  |                                                                 |  |*
*|  |  GOOD: Domain language                                         |  |*
*|  |  ---------------------                                         |  |*
*|  |  class OrderFulfillmentService {                              |  |*
*|  |      void shipOrder(Order order) { ... }                      |  |*
*|  |      void cancelOrder(Order order, CancellationReason r) {}  |  |*
*|  |  }                                                             |  |*
*|  |                                                                 |  |*
*|  |  Terms like "Order", "Shipment", "Cancellation" come from     |  |*
*|  |  business domain, not technical jargon.                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  DOMAIN CLASSIFICATION                                                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  CORE DOMAIN                                            |  |  |*
*|  |  |  -----------                                            |  |  |*
*|  |  |  What makes your business UNIQUE and COMPETITIVE        |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  * Build in-house                                      |  |  |*
*|  |  |  * Invest heavily                                      |  |  |*
*|  |  |  * Best engineers                                      |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  Examples:                                              |  |  |*
*|  |  |  * Amazon: Recommendation engine, fulfillment          |  |  |*
*|  |  |  * Uber: Pricing algorithm, matching                   |  |  |*
*|  |  |  * Netflix: Content recommendation                     |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  SUPPORTING DOMAIN                                      |  |  |*
*|  |  |  -----------------                                      |  |  |*
*|  |  |  Necessary for business but not differentiating         |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  * Build or buy                                        |  |  |*
*|  |  |  * Less investment than core                           |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  Examples:                                              |  |  |*
*|  |  |  * Order management                                    |  |  |*
*|  |  |  * Customer support                                    |  |  |*
*|  |  |  * Inventory tracking                                  |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  GENERIC DOMAIN                                         |  |  |*
*|  |  |  --------------                                         |  |  |*
*|  |  |  Commodity functionality, same for everyone             |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  * Buy off-the-shelf or SaaS                           |  |  |*
*|  |  |  * Don't reinvent the wheel                            |  |  |*
*|  |  |                                                         |  |  |*
*|  |  |  Examples:                                              |  |  |*
*|  |  |  * Authentication (Auth0, Okta)                        |  |  |*
*|  |  |  * Payments (Stripe, PayPal)                           |  |  |*
*|  |  |  * Email (SendGrid, Mailgun)                           |  |  |*
*|  |  |  * Analytics (Mixpanel, Amplitude)                     |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  CONTEXT MAPPING                                                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  How do bounded contexts relate to each other?                 |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  PARTNERSHIP                                              ||  |*
*|  |  |  Two teams collaborate closely, mutual dependency         ||  |*
*|  |  |                                                           ||  |*
*|  |  |  [Context A] <-----------> [Context B]                   ||  |*
*|  |  |              mutual success                               ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  CUSTOMER-SUPPLIER                                        ||  |*
*|  |  |  Upstream (supplier) provides to downstream (customer)    ||  |*
*|  |  |                                                           ||  |*
*|  |  |  [Supplier] -------------> [Customer]                    ||  |*
*|  |  |             upstream        downstream                    ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Customer can request features from supplier              ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  CONFORMIST                                               ||  |*
*|  |  |  Downstream conforms to upstream's model (no influence)   ||  |*
*|  |  |                                                           ||  |*
*|  |  |  [Upstream] -------------> [Conformist]                  ||  |*
*|  |  |             take it or leave it                           ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Example: Using external API as-is                        ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  ANTI-CORRUPTION LAYER (ACL)                             ||  |*
*|  |  |  Translation layer to protect your model from external   ||  |*
*|  |  |                                                           ||  |*
*|  |  |  [External] --> [ACL] --> [Your Context]                 ||  |*
*|  |  |              translate                                    ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Example: Wrap legacy system or external API             ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  SHARED KERNEL                                            ||  |*
*|  |  |  Small shared model between contexts (use sparingly!)    ||  |*
*|  |  |                                                           ||  |*
*|  |  |  [Context A]--+     +--[Context B]                       ||  |*
*|  |  |               +-+---+                                     ||  |*
*|  |  |            [Shared Kernel]                                ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Example: Shared Money type, shared ID types             ||  |*
*|  |  |   Creates coupling - minimize usage                    ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |  OPEN HOST SERVICE + PUBLISHED LANGUAGE                  ||  |*
*|  |  |  Well-documented API for multiple consumers              ||  |*
*|  |  |                                                           ||  |*
*|  |  |            +--[Consumer A]                               ||  |*
*|  |  |            |                                              ||  |*
*|  |  |  [Service]-+--[Consumer B]                               ||  |*
*|  |  |    API     |                                              ||  |*
*|  |  |            +--[Consumer C]                               ||  |*
*|  |  |                                                           ||  |*
*|  |  |  Example: REST API with OpenAPI spec, gRPC with proto   ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 3: TACTICAL DDD PATTERNS (Building Blocks)
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  ENTITY                                                                |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  An object with a unique IDENTITY that persists over time.     |  |*
*|  |  Two entities are equal if they have the same ID,              |  |*
*|  |  regardless of other attributes.                               |  |*
*|  |                                                                 |  |*
*|  |  Example:                                                       |  |*
*|  |                                                                 |  |*
*|  |  class Order:                                                  |  |*
*|  |      id: OrderId            # Identity                         |  |*
*|  |      customer_id: CustomerId                                   |  |*
*|  |      items: List[OrderItem]                                    |  |*
*|  |      status: OrderStatus                                       |  |*
*|  |      created_at: DateTime                                      |  |*
*|  |                                                                 |  |*
*|  |  order_a = Order(id="123", status="pending")                  |  |*
*|  |  order_b = Order(id="123", status="shipped")                  |  |*
*|  |                                                                 |  |*
*|  |  order_a == order_b  # TRUE (same identity)                   |  |*
*|  |                                                                 |  |*
*|  |  Characteristics:                                               |  |*
*|  |  * Has unique identifier                                       |  |*
*|  |  * Mutable (state changes over time)                          |  |*
*|  |  * Tracked through lifecycle                                   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  VALUE OBJECT                                                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  An object defined by its ATTRIBUTES, not identity.            |  |*
*|  |  Two value objects are equal if all attributes are equal.      |  |*
*|  |                                                                 |  |*
*|  |  Example:                                                       |  |*
*|  |                                                                 |  |*
*|  |  class Money:                 # Value Object                   |  |*
*|  |      amount: Decimal                                           |  |*
*|  |      currency: Currency                                        |  |*
*|  |                                                                 |  |*
*|  |  class Address:               # Value Object                   |  |*
*|  |      street: str                                               |  |*
*|  |      city: str                                                 |  |*
*|  |      country: str                                              |  |*
*|  |      postal_code: str                                          |  |*
*|  |                                                                 |  |*
*|  |  money_a = Money(100, "USD")                                  |  |*
*|  |  money_b = Money(100, "USD")                                  |  |*
*|  |                                                                 |  |*
*|  |  money_a == money_b  # TRUE (same values)                     |  |*
*|  |                                                                 |  |*
*|  |  Characteristics:                                               |  |*
*|  |  * NO unique identifier                                        |  |*
*|  |  * IMMUTABLE (create new instead of modify)                   |  |*
*|  |  * Replaceable (swap one $100 for another $100)               |  |*
*|  |  * Can contain validation logic                               |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  AGGREGATE                                                             |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  A cluster of entities and value objects treated as a single   |  |*
*|  |  unit for data changes. Has an AGGREGATE ROOT that controls   |  |*
*|  |  access to the aggregate.                                      |  |*
*|  |                                                                 |  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |  |                                                           ||  |*
*|  |  |           ORDER AGGREGATE                                 ||  |*
*|  |  |                                                           ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  |           +-----------------+                      | ||  |*
*|  |  |  |           |     ORDER       | < Aggregate Root    | ||  |*
*|  |  |  |           |    (Entity)     |                      | ||  |*
*|  |  |  |           +--------+--------+                      | ||  |*
*|  |  |  |                    |                                | ||  |*
*|  |  |  |         +---------+---------+                      | ||  |*
*|  |  |  |         |                   |                      | ||  |*
*|  |  |  |         v                   v                      | ||  |*
*|  |  |  |  +-------------+    +-------------+               | ||  |*
*|  |  |  |  | OrderItem   |    | OrderItem   |  (Entities)   | ||  |*
*|  |  |  |  |  quantity   |    |  quantity   |               | ||  |*
*|  |  |  |  |  price      |    |  price      |               | ||  |*
*|  |  |  |  +-------------+    +-------------+               | ||  |*
*|  |  |  |         |                   |                      | ||  |*
*|  |  |  |         v                   v                      | ||  |*
*|  |  |  |  +-------------+    +-------------+               | ||  |*
*|  |  |  |  |   Money     |    |   Money     |  (Value Obj)  | ||  |*
*|  |  |  |  +-------------+    +-------------+               | ||  |*
*|  |  |  |                                                     | ||  |*
*|  |  |  +-----------------------------------------------------+ ||  |*
*|  |  |                                                           ||  |*
*|  |  +-----------------------------------------------------------+|  |*
*|  |                                                                 |  |*
*|  |  RULES:                                                        |  |*
*|  |  * External access ONLY through aggregate root                 |  |*
*|  |  * Aggregate root enforces invariants                          |  |*
*|  |  * One transaction = One aggregate                             |  |*
*|  |  * Reference other aggregates by ID only                       |  |*
*|  |  * Keep aggregates SMALL                                       |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  DOMAIN EVENT                                                          |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Something significant that happened in the domain.            |  |*
*|  |  Named in PAST TENSE.                                          |  |*
*|  |                                                                 |  |*
*|  |  Examples:                                                      |  |*
*|  |  * OrderPlaced                                                 |  |*
*|  |  * PaymentReceived                                             |  |*
*|  |  * OrderShipped                                                |  |*
*|  |  * InventoryReserved                                           |  |*
*|  |  * CustomerRegistered                                          |  |*
*|  |                                                                 |  |*
*|  |  Structure:                                                     |  |*
*|  |                                                                 |  |*
*|  |  class OrderPlaced:           # Domain Event                   |  |*
*|  |      event_id: UUID                                            |  |*
*|  |      occurred_at: DateTime                                     |  |*
*|  |      order_id: OrderId                                         |  |*
*|  |      customer_id: CustomerId                                   |  |*
*|  |      total_amount: Money                                       |  |*
*|  |      items: List[OrderItemSnapshot]                           |  |*
*|  |                                                                 |  |*
*|  |  Characteristics:                                               |  |*
*|  |  * Immutable (happened in the past)                           |  |*
*|  |  * Contains relevant data at time of event                    |  |*
*|  |  * Can trigger reactions in other contexts                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  REPOSITORY                                                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Abstraction for storing and retrieving aggregates.            |  |*
*|  |  Hides persistence details from domain.                        |  |*
*|  |                                                                 |  |*
*|  |  Interface:                                                     |  |*
*|  |                                                                 |  |*
*|  |  interface OrderRepository:                                    |  |*
*|  |      def find_by_id(order_id: OrderId) -> Order                |  |*
*|  |      def save(order: Order) -> None                            |  |*
*|  |      def find_by_customer(customer_id: CustomerId) -> List    |  |*
*|  |                                                                 |  |*
*|  |  ONE repository per AGGREGATE ROOT                             |  |*
*|  |  (Not per entity or table)                                     |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+-------------------------------------------------------------------------+*
*|                                                                         |*
*|  DOMAIN SERVICE                                                        |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Business logic that doesn't naturally fit in an entity.       |  |*
*|  |  Operations involving multiple aggregates.                     |  |*
*|  |                                                                 |  |*
*|  |  Example:                                                       |  |*
*|  |                                                                 |  |*
*|  |  class TransferMoneyService:                                   |  |*
*|  |      def transfer(from: Account, to: Account, amount: Money):  |  |*
*|  |          # Involves two aggregates                             |  |*
*|  |          from.withdraw(amount)                                 |  |*
*|  |          to.deposit(amount)                                    |  |*
*|  |                                                                 |  |*
*|  |  class PricingService:                                         |  |*
*|  |      def calculate_price(product, customer, promotions):       |  |*
*|  |          # Complex rules involving multiple contexts          |  |*
*|  |          ...                                                   |  |*
*|  |                                                                 |  |*
*|  |  Characteristics:                                               |  |*
*|  |  * Stateless                                                   |  |*
*|  |  * Named after domain operation                                |  |*
*|  |  * Coordinates between aggregates                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4: CHOREOGRAPHY vs ORCHESTRATION
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  TWO APPROACHES TO COORDINATE MICROSERVICES                            |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CHOREOGRAPHY: Services react to events independently          |  |*
*|  |  (Decentralized, event-driven)                                 |  |*
*|  |                                                                 |  |*
*|  |  ORCHESTRATION: Central coordinator directs the flow           |  |*
*|  |  (Centralized, command-driven)                                 |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  CHOREOGRAPHY (Event-Driven)                                                |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Services communicate through events. Each service:                   | |*
*|  |  * Publishes events when something happens                           | |*
*|  |  * Subscribes to events it cares about                              | |*
*|  |  * Reacts independently                                              | |*
*|  |                                                                        | |*
*|  |  +---------------------------------------------------------------+   | |*
*|  |  |                                                               |   | |*
*|  |  |                    ORDER FLOW (Choreography)                 |   | |*
*|  |  |                                                               |   | |*
*|  |  |  User places order                                           |   | |*
*|  |  |       |                                                       |   | |*
*|  |  |       v                                                       |   | |*
*|  |  |  +-----------+                                               |   | |*
*|  |  |  |   Order   |--publish--> "OrderPlaced"                     |   | |*
*|  |  |  |  Service  |                    |                          |   | |*
*|  |  |  +-----------+                    |                          |   | |*
*|  |  |                                   |                          |   | |*
*|  |  |       +---------------------------+-------------------+      |   | |*
*|  |  |       |                           |                   |      |   | |*
*|  |  |       v                           v                   v      |   | |*
*|  |  |  +-----------+           +-----------+         +-----------+|   | |*
*|  |  |  | Inventory |           |  Payment  |         |Notification|   | |*
*|  |  |  |  Service  |           |  Service  |         |  Service  ||   | |*
*|  |  |  +-----+-----+           +-----+-----+         +-----------+|   | |*
*|  |  |        |                       |                            |   | |*
*|  |  |        | publish               | publish                    |   | |*
*|  |  |        v                       v                            |   | |*
*|  |  |  "InventoryReserved"     "PaymentProcessed"                 |   | |*
*|  |  |        |                       |                            |   | |*
*|  |  |        +-----------+-----------+                            |   | |*
*|  |  |                    |                                        |   | |*
*|  |  |                    v                                        |   | |*
*|  |  |              +-----------+                                  |   | |*
*|  |  |              | Shipping  |--publish--> "OrderShipped"       |   | |*
*|  |  |              |  Service  |                                  |   | |*
*|  |  |              +-----------+                                  |   | |*
*|  |  |                                                               |   | |*
*|  |  |  Each service knows what events to listen to and react       |   | |*
*|  |  |  No central coordinator                                       |   | |*
*|  |  |                                                               |   | |*
*|  |  +---------------------------------------------------------------+   | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*|  PROS:                                                                       |*
*|  Y Loose coupling (services don't know about each other)                   |*
*|  Y No single point of failure                                              |*
*|  Y Easy to add new services (just subscribe to events)                     |*
*|  Y Services are independently deployable                                   |*
*|  Y Natural fit for event sourcing                                          |*
*|                                                                              |*
*|  CONS:                                                                       |*
*|  X Hard to see the overall flow                                            |*
*|  X Difficult to debug and trace                                            |*
*|  X Complex failure handling (compensating events)                          |*
*|  X Risk of cyclic dependencies                                             |*
*|  X Harder to test end-to-end                                               |*
*|  X No central place to see workflow status                                 |*
*|                                                                              |*
*|  USE WHEN:                                                                   |*
*|  * Simple, linear flows                                                     |*
*|  * High autonomy needed                                                     |*
*|  * Event sourcing architecture                                              |*
*|  * Broadcasting events to many consumers                                    |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  ORCHESTRATION (Command-Driven)                                              |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  A central orchestrator coordinates the workflow by sending           | |*
*|  |  commands to services and handling responses.                         | |*
*|  |                                                                        | |*
*|  |  +---------------------------------------------------------------+   | |*
*|  |  |                                                               |   | |*
*|  |  |                    ORDER FLOW (Orchestration)                |   | |*
*|  |  |                                                               |   | |*
*|  |  |  User places order                                           |   | |*
*|  |  |       |                                                       |   | |*
*|  |  |       v                                                       |   | |*
*|  |  |  +---------------------------------------------------------+ |   | |*
*|  |  |  |                                                         | |   | |*
*|  |  |  |              ORDER SAGA ORCHESTRATOR                   | |   | |*
*|  |  |  |                                                         | |   | |*
*|  |  |  |  Step 1: Create Order                                  | |   | |*
*|  |  |  |       |                                                 | |   | |*
*|  |  |  |       | command: CreateOrder                           | |   | |*
*|  |  |  |       v                                                 | |   | |*
*|  |  |  |  +-----------+                                         | |   | |*
*|  |  |  |  |   Order   | > reply: OrderCreated                   | |   | |*
*|  |  |  |  |  Service  |                                         | |   | |*
*|  |  |  |  +-----------+                                         | |   | |*
*|  |  |  |       |                                                 | |   | |*
*|  |  |  |  Step 2: Reserve Inventory                             | |   | |*
*|  |  |  |       |                                                 | |   | |*
*|  |  |  |       | command: ReserveInventory                      | |   | |*
*|  |  |  |       v                                                 | |   | |*
*|  |  |  |  +-----------+                                         | |   | |*
*|  |  |  |  | Inventory | > reply: InventoryReserved              | |   | |*
*|  |  |  |  |  Service  |                                         | |   | |*
*|  |  |  |  +-----------+                                         | |   | |*
*|  |  |  |       |                                                 | |   | |*
*|  |  |  |  Step 3: Process Payment                               | |   | |*
*|  |  |  |       |                                                 | |   | |*
*|  |  |  |       | command: ProcessPayment                        | |   | |*
*|  |  |  |       v                                                 | |   | |*
*|  |  |  |  +-----------+                                         | |   | |*
*|  |  |  |  |  Payment  | > reply: PaymentProcessed               | |   | |*
*|  |  |  |  |  Service  |                                         | |   | |*
*|  |  |  |  +-----------+                                         | |   | |*
*|  |  |  |       |                                                 | |   | |*
*|  |  |  |  If any step fails: Orchestrator triggers compensation | |   | |*
*|  |  |  |                                                         | |   | |*
*|  |  |  +---------------------------------------------------------+ |   | |*
*|  |  |                                                               |   | |*
*|  |  |  Orchestrator knows the entire workflow                       |   | |*
*|  |  |  Services just execute commands                               |   | |*
*|  |  |                                                               |   | |*
*|  |  +---------------------------------------------------------------+   | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*|  PROS:                                                                       |*
*|  Y Easy to understand the flow (one place)                                 |*
*|  Y Centralized error handling and compensation                             |*
*|  Y Easy to track workflow status                                           |*
*|  Y Better for complex, branching workflows                                 |*
*|  Y Easier to test                                                          |*
*|                                                                              |*
*|  CONS:                                                                       |*
*|  X Orchestrator is a single point of failure                               |*
*|  X Tighter coupling to orchestrator                                        |*
*|  X Orchestrator can become complex (god service)                           |*
*|  X Services less autonomous                                                |*
*|  X Changes to flow require orchestrator changes                            |*
*|                                                                              |*
*|  USE WHEN:                                                                   |*
*|  * Complex workflows with many steps                                        |*
*|  * Need visibility into workflow state                                      |*
*|  * Conditional/branching logic                                              |*
*|  * Strong error handling requirements                                       |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  CHOREOGRAPHY vs ORCHESTRATION COMPARISON                                    |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  Aspect              Choreography           Orchestration              | |*
*|  |  --------------------------------------------------------------------  | |*
*|  |                                                                        | |*
*|  |  Communication       Events (async)         Commands (sync/async)      | |*
*|  |                                                                        | |*
*|  |  Coupling            Loose                  Tighter (to orchestrator)  | |*
*|  |                                                                        | |*
*|  |  Single Point of     No                     Yes (orchestrator)         | |*
*|  |  Failure                                                               | |*
*|  |                                                                        | |*
*|  |  Flow Visibility     Distributed            Centralized                | |*
*|  |                      (hard to see)          (easy to see)              | |*
*|  |                                                                        | |*
*|  |  Error Handling      Compensating events    Orchestrator handles       | |*
*|  |                      (complex)              (simpler)                   | |*
*|  |                                                                        | |*
*|  |  Adding Services     Easy (subscribe)       Requires orchestrator      | |*
*|  |                                             change                      | |*
*|  |                                                                        | |*
*|  |  Testing             Harder (distributed)   Easier (mock services)     | |*
*|  |                                                                        | |*
*|  |  State Management    Each service tracks    Orchestrator tracks        | |*
*|  |                                                                        | |*
*|  |  Best For            Simple linear flows,   Complex workflows,         | |*
*|  |                      high autonomy          strong error handling      | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*|  RECOMMENDATION:                                                             |*
*|  * Start with Choreography for simple flows                                 |*
*|  * Move to Orchestration when complexity grows                              |*
*|  * Hybrid: Choreography between bounded contexts,                           |*
*|            Orchestration within complex workflows                            |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*

SECTION 5: SAGA PATTERNS IN DETAIL
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  SAGA: Distributed Transaction Without 2PC                             |*
*|                                                                         |*
*|  A sequence of local transactions where each transaction               |*
*|  publishes events/commands to trigger the next step.                   |*
*|  If a step fails, compensating transactions undo previous work.        |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  CHOREOGRAPHY SAGA                                                           |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  HAPPY PATH:                                                          | |*
*|  |                                                                        | |*
*|  |  Order Service                                                        | |*
*|  |       |                                                               | |*
*|  |       | 1. Create order (PENDING)                                    | |*
*|  |       |    Publish: OrderCreated                                     | |*
*|  |       v                                                               | |*
*|  |  Inventory Service (listens to OrderCreated)                         | |*
*|  |       |                                                               | |*
*|  |       | 2. Reserve inventory                                         | |*
*|  |       |    Publish: InventoryReserved                                | |*
*|  |       v                                                               | |*
*|  |  Payment Service (listens to InventoryReserved)                      | |*
*|  |       |                                                               | |*
*|  |       | 3. Process payment                                           | |*
*|  |       |    Publish: PaymentSucceeded                                 | |*
*|  |       v                                                               | |*
*|  |  Order Service (listens to PaymentSucceeded)                         | |*
*|  |       |                                                               | |*
*|  |       | 4. Mark order CONFIRMED                                      | |*
*|  |       |    Publish: OrderConfirmed                                   | |*
*|  |                                                                        | |*
*|  |  ----------------------------------------------------------------    | |*
*|  |                                                                        | |*
*|  |  FAILURE PATH (Payment fails):                                        | |*
*|  |                                                                        | |*
*|  |  Payment Service                                                      | |*
*|  |       |                                                               | |*
*|  |       | 3. Payment fails!                                            | |*
*|  |       |    Publish: PaymentFailed                                    | |*
*|  |       v                                                               | |*
*|  |  Inventory Service (listens to PaymentFailed)                        | |*
*|  |       |                                                               | |*
*|  |       | COMPENSATE: Release reserved inventory                       | |*
*|  |       |    Publish: InventoryReleased                                | |*
*|  |       v                                                               | |*
*|  |  Order Service (listens to PaymentFailed OR InventoryReleased)       | |*
*|  |       |                                                               | |*
*|  |       | COMPENSATE: Mark order CANCELLED                             | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*
*+------------------------------------------------------------------------------+*
*|                                                                              |*
*|  ORCHESTRATION SAGA                                                          |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |  +-----------------------------------------------------------------+  | |*
*|  |  |                                                                 |  | |*
*|  |  |                 ORDER SAGA ORCHESTRATOR                        |  | |*
*|  |  |                                                                 |  | |*
*|  |  |  State Machine:                                                |  | |*
*|  |  |                                                                 |  | |*
*|  |  |  +--------------+                                             |  | |*
*|  |  |  |   STARTED    |                                             |  | |*
*|  |  |  +------+-------+                                             |  | |*
*|  |  |         | CreateOrder > success                               |  | |*
*|  |  |         v                                                      |  | |*
*|  |  |  +--------------+                                             |  | |*
*|  |  |  |ORDER_CREATED |                                             |  | |*
*|  |  |  +------+-------+                                             |  | |*
*|  |  |         | ReserveInventory > success                          |  | |*
*|  |  |         v                                                      |  | |*
*|  |  |  +--------------+                                             |  | |*
*|  |  |  |INV_RESERVED  |                                             |  | |*
*|  |  |  +------+-------+                                             |  | |*
*|  |  |         | ProcessPayment > success                            |  | |*
*|  |  |         v                                                      |  | |*
*|  |  |  +--------------+                                             |  | |*
*|  |  |  |PAYMENT_DONE  |                                             |  | |*
*|  |  |  +------+-------+                                             |  | |*
*|  |  |         | ConfirmOrder                                        |  | |*
*|  |  |         v                                                      |  | |*
*|  |  |  +--------------+                                             |  | |*
*|  |  |  |  COMPLETED   |                                             |  | |*
*|  |  |  +--------------+                                             |  | |*
*|  |  |                                                                 |  | |*
*|  |  |  On Failure (e.g., PaymentFailed):                            |  | |*
*|  |  |                                                                 |  | |*
*|  |  |  +--------------+                                             |  | |*
*|  |  |  |PAYMENT_FAILED|                                             |  | |*
*|  |  |  +------+-------+                                             |  | |*
*|  |  |         | Compensate: ReleaseInventory                        |  | |*
*|  |  |         v                                                      |  | |*
*|  |  |  +--------------+                                             |  | |*
*|  |  |  |INV_RELEASED  |                                             |  | |*
*|  |  |  +------+-------+                                             |  | |*
*|  |  |         | Compensate: CancelOrder                             |  | |*
*|  |  |         v                                                      |  | |*
*|  |  |  +--------------+                                             |  | |*
*|  |  |  |   FAILED     |                                             |  | |*
*|  |  |  +--------------+                                             |  | |*
*|  |  |                                                                 |  | |*
*|  |  +-----------------------------------------------------------------+  | |*
*|  |                                                                        | |*
*|  |  Orchestrator persists its state at each step                         | |*
*|  |  Can resume after crash                                               | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*|  TOOLS:                                                                      |*
*|  * Temporal (orchestration framework)                                       |*
*|  * Apache Airflow (workflow orchestration)                                  |*
*|  * AWS Step Functions (managed orchestration)                               |*
*|  * Camunda (BPMN-based orchestration)                                       |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*

SECTION 6: EVENT SOURCING
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  EVENT SOURCING                                                        |*
*|                                                                         |*
*|  Instead of storing current state, store ALL EVENTS that led to        |*
*|  the current state. Rebuild state by replaying events.                 |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TRADITIONAL (State-based):                                    |  |*
*|  |                                                                 |  |*
*|  |  Account Table:                                                |  |*
*|  |  | id  | balance |                                             |  |*
*|  |  | 123 | $500    |  < Only current state                      |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  EVENT SOURCING:                                               |  |*
*|  |                                                                 |  |*
*|  |  Event Store:                                                  |  |*
*|  |  | event_id | account_id | type        | data          |      |  |*
*|  |  | 1        | 123        | Created     | initial: $0   |      |  |*
*|  |  | 2        | 123        | Deposited   | amount: $1000 |      |  |*
*|  |  | 3        | 123        | Withdrawn   | amount: $300  |      |  |*
*|  |  | 4        | 123        | Withdrawn   | amount: $200  |      |  |*
*|  |                                                                 |  |*
*|  |  Replay: $0 + $1000 - $300 - $200 = $500                      |  |*
*|  |                                                                 |  |*
*|  |  Full history preserved!                                       |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  PROS:                                                                 |*
*|  Y Complete audit trail                                               |*
*|  Y Can rebuild state at any point in time                             |*
*|  Y Debug issues by replaying events                                   |*
*|  Y Natural fit for event-driven architecture                          |*
*|  Y Enables CQRS pattern                                               |*
*|                                                                         |*
*|  CONS:                                                                 |*
*|  X Complexity (event versioning, schema evolution)                    |*
*|  X Eventual consistency                                               |*
*|  X Replaying can be slow for long event streams                       |*
*|  X Learning curve                                                     |*
*|                                                                         |*
*|  USE WHEN:                                                             |*
*|  * Audit trail is critical (finance, healthcare)                      |*
*|  * Need to answer "how did we get here?"                              |*
*|  * Complex domain with many state changes                             |*
*|  * Event-driven architecture already in place                         |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 7: CQRS (Command Query Responsibility Segregation)
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  CQRS: Separate Read and Write Models                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  TRADITIONAL (Same model for read/write):                      |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                     Service                             |  |  |*
*|  |  |                        |                                |  |  |*
*|  |  |               +--------+--------+                       |  |  |*
*|  |  |               |                 |                       |  |  |*
*|  |  |            Create            Read                       |  |  |*
*|  |  |            Update            Query                      |  |  |*
*|  |  |            Delete                                       |  |  |*
*|  |  |               |                 |                       |  |  |*
*|  |  |               +--------+--------+                       |  |  |*
*|  |  |                        |                                |  |  |*
*|  |  |                        v                                |  |  |*
*|  |  |              +-----------------+                        |  |  |*
*|  |  |              |    Database     | < Same model          |  |  |*
*|  |  |              +-----------------+                        |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  CQRS (Separate models):                                       |  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |  |                                                         |  |  |*
*|  |  |           COMMAND SIDE          QUERY SIDE             |  |  |*
*|  |  |           (Write Model)         (Read Model)           |  |  |*
*|  |  |                |                     |                  |  |  |*
*|  |  |         +------+------+       +------+------+          |  |  |*
*|  |  |         |   Command   |       |   Query     |          |  |  |*
*|  |  |         |   Handler   |       |   Handler   |          |  |  |*
*|  |  |         +------+------+       +------+------+          |  |  |*
*|  |  |                |                     |                  |  |  |*
*|  |  |                v                     v                  |  |  |*
*|  |  |         +--------------+      +--------------+         |  |  |*
*|  |  |         | Write DB     |      |  Read DB     |         |  |  |*
*|  |  |         | (Normalized) |      |(Denormalized)|         |  |  |*
*|  |  |         | PostgreSQL   |----->|Elasticsearch |         |  |  |*
*|  |  |         +--------------+ sync +--------------+         |  |  |*
*|  |  |                                                         |  |  |*
*|  |  +---------------------------------------------------------+  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  PROS:                                                                 |*
*|  Y Scale reads and writes independently                               |*
*|  Y Optimize read model for queries (denormalized)                     |*
*|  Y Optimize write model for business logic (normalized)               |*
*|  Y Different tech for different needs                                 |*
*|                                                                         |*
*|  CONS:                                                                 |*
*|  X Complexity (two models to maintain)                                |*
*|  X Eventual consistency between models                                |*
*|  X Sync mechanism needed                                              |*
*|                                                                         |*
*|  USE WHEN:                                                             |*
*|  * Read and write patterns are very different                         |*
*|  * Need to scale reads independently (high read traffic)              |*
*|  * Complex queries that don't fit write model                         |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 8: DDD SUMMARY DIAGRAM
## +------------------------------------------------------------------------------+
*|                                                                              |*
*|                        DDD BUILDING BLOCKS                                  |*
*|                                                                              |*
*|  +------------------------------------------------------------------------+ |*
*|  |                                                                        | |*
*|  |   STRATEGIC PATTERNS              TACTICAL PATTERNS                   | |*
*|  |   (Big Picture)                   (Code Level)                        | |*
*|  |                                                                        | |*
*|  |   +---------------------+        +---------------------+             | |*
*|  |   |  Bounded Context    |        |     Aggregate       |             | |*
*|  |   |  -----------------  |        |     ---------       |             | |*
*|  |   |  * Define boundaries|        |  +-----------------+|             | |*
*|  |   |  * One per service  |        |  | Aggregate Root  ||             | |*
*|  |   +---------------------+        |  |   (Entity)      ||             | |*
*|  |                                   |  +--------+--------+|             | |*
*|  |   +---------------------+        |           |         |             | |*
*|  |   | Ubiquitous Language |        |  +--------+--------+|             | |*
*|  |   | --------------------|        |  |    Entities     ||             | |*
*|  |   |  * Shared terms     |        |  |  Value Objects  ||             | |*
*|  |   |  * Used in code     |        |  +-----------------+|             | |*
*|  |   +---------------------+        +---------------------+             | |*
*|  |                                                                        | |*
*|  |   +---------------------+        +---------------------+             | |*
*|  |   |   Context Mapping   |        |   Domain Event      |             | |*
*|  |   |   ---------------   |        |   ------------      |             | |*
*|  |   |  * Partnership      |        |  * Past tense       |             | |*
*|  |   |  * Customer-Supplier|        |  * Immutable        |             | |*
*|  |   |  * Conformist       |        |  * Triggers actions |             | |*
*|  |   |  * ACL              |        |                     |             | |*
*|  |   |  * Shared Kernel    |        |  OrderPlaced        |             | |*
*|  |   |  * Open Host        |        |  PaymentReceived    |             | |*
*|  |   +---------------------+        +---------------------+             | |*
*|  |                                                                        | |*
*|  |   +---------------------+        +---------------------+             | |*
*|  |   | Domain Classification|       |    Repository       |             | |*
*|  |   | ------------------- |        |    ----------       |             | |*
*|  |   |  * Core (build)     |        |  * Persistence      |             | |*
*|  |   |  * Supporting (build|        |    abstraction      |             | |*
*|  |   |    or buy)          |        |  * One per          |             | |*
*|  |   |  * Generic (buy)    |        |    aggregate root   |             | |*
*|  |   +---------------------+        +---------------------+             | |*
*|  |                                                                        | |*
*|  |                                   +---------------------+             | |*
*|  |                                   |   Domain Service    |             | |*
*|  |                                   |   --------------    |             | |*
*|  |                                   |  * Stateless        |             | |*
*|  |                                   |  * Cross-aggregate  |             | |*
*|  |                                   |    operations       |             | |*
*|  |                                   +---------------------+             | |*
*|  |                                                                        | |*
*|  +------------------------------------------------------------------------+ |*
*|                                                                              |*
*+------------------------------------------------------------------------------+*

END OF DDD & EVENT PATTERNS
