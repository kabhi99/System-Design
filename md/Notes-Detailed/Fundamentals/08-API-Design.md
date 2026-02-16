# CHAPTER 8: API DESIGN
*Building Interfaces Between Systems*

APIs are the contracts between services. Well-designed APIs make systems
easier to use, maintain, and scale. Poor APIs create tech debt that
compounds over time.

## SECTION 8.1: API DESIGN PRINCIPLES

### FUNDAMENTAL PRINCIPLES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  API DESIGN PRINCIPLES                                                  |
|                                                                         |
|  1. CONSISTENCY                                                         |
|  -----------------                                                      |
|  Same patterns everywhere. If GET /users returns a list,                |
|  GET /orders should too.                                                |
|                                                                         |
|  GOOD:                                                                  |
|  GET /users         > { "data": [...], "meta": {...} }                  |
|  GET /orders        > { "data": [...], "meta": {...} }                  |
|                                                                         |
|  BAD:                                                                   |
|  GET /users         > { "users": [...] }                                |
|  GET /orders        > { "data": [...], "total": 100 }                   |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. PREDICTABILITY                                                      |
|  -------------------                                                    |
|  Developers should guess correctly what endpoints do.                   |
|                                                                         |
|  GOOD: GET /users/123/orders (get orders for user 123)                  |
|  BAD:  GET /fetchUserOrders?uid=123                                     |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. SIMPLICITY                                                          |
|  --------------                                                         |
|  Easy things should be easy. Complex things should be possible.         |
|                                                                         |
|  Simple case: GET /users/123                                            |
|  Complex case: GET /users?filter[age][gte]=21&include=orders            |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  4. BACKWARD COMPATIBILITY                                              |
|  ---------------------------                                            |
|  New versions shouldn't break existing clients.                         |
|                                                                         |
|  SAFE CHANGES:                                                          |
|  * Adding new endpoints                                                 |
|  * Adding new optional fields                                           |
|  * Adding new enum values (if client handles unknown)                   |
|                                                                         |
|  BREAKING CHANGES:                                                      |
|  * Removing endpoints                                                   |
|  * Removing fields                                                      |
|  * Changing field types                                                 |
|  * Making optional fields required                                      |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  5. DOCUMENTATION                                                       |
|  -----------------                                                      |
|  APIs without docs are useless.                                         |
|                                                                         |
|  * OpenAPI/Swagger spec                                                 |
|  * Example requests and responses                                       |
|  * Error codes and meanings                                             |
|  * Rate limits and quotas                                               |
|  * Authentication guide                                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8.2: REST API DESIGN

REST (Representational State Transfer) is the most common API style.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REST FUNDAMENTALS                                                      |
|                                                                         |
|  RESOURCES                                                              |
|  -----------                                                            |
|  Everything is a resource identified by URL.                            |
|                                                                         |
|  /users           Collection of users                                   |
|  /users/123       Single user with ID 123                               |
|  /users/123/orders Orders belonging to user 123                         |
|                                                                         |
|  HTTP METHODS (VERBS)                                                   |
|  ---------------------                                                  |
|                                                                         |
|  +----------+--------------------------------------------------------+  |
|  | Method   | Purpose                              | Idempotent      |  |
|  +----------+--------------------------------------------------------+  |
|  | GET      | Retrieve resource(s)                 | Yes             |  |
|  | POST     | Create new resource                  | No              |  |
|  | PUT      | Replace entire resource              | Yes             |  |
|  | PATCH    | Partial update                       | No*             |  |
|  | DELETE   | Remove resource                      | Yes             |  |
|  | HEAD     | Get headers only (no body)           | Yes             |  |
|  | OPTIONS  | Get allowed methods (CORS preflight) | Yes             |  |
|  +----------+--------------------------------------------------------+  |
|                                                                         |
|  *PATCH can be idempotent if using JSON Patch or similar                |
|                                                                         |
|  IDEMPOTENT: Calling multiple times = same result as calling once       |
|                                                                         |
+-------------------------------------------------------------------------+
```

### REST ENDPOINT DESIGN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REST URL PATTERNS                                                      |
|                                                                         |
|  COLLECTION OPERATIONS                                                  |
|  -----------------------                                                |
|  GET    /users           List all users (with pagination)               |
|  POST   /users           Create a new user                              |
|                                                                         |
|  ITEM OPERATIONS                                                        |
|  -----------------                                                      |
|  GET    /users/123       Get user 123                                   |
|  PUT    /users/123       Replace user 123                               |
|  PATCH  /users/123       Update fields of user 123                      |
|  DELETE /users/123       Delete user 123                                |
|                                                                         |
|  NESTED RESOURCES                                                       |
|  -----------------                                                      |
|  GET    /users/123/orders      Orders for user 123                      |
|  POST   /users/123/orders      Create order for user 123                |
|  GET    /users/123/orders/456  Specific order 456 of user 123           |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  URL DESIGN BEST PRACTICES                                              |
|                                                                         |
|  USE NOUNS, NOT VERBS                                                   |
|  Y POST /users                                                          |
|  X POST /createUser                                                     |
|  X GET  /getUsers                                                       |
|                                                                         |
|  PLURAL NOUNS FOR COLLECTIONS                                           |
|  Y /users, /orders, /products                                           |
|  X /user, /order, /product                                              |
|                                                                         |
|  KEBAB-CASE FOR MULTI-WORD                                              |
|  Y /user-profiles                                                       |
|  X /userProfiles, /user_profiles                                        |
|                                                                         |
|  AVOID DEEP NESTING (Max 2-3 levels)                                    |
|  X /users/123/orders/456/items/789/reviews                              |
|  Y /order-items/789/reviews                                             |
|                                                                         |
|  USE QUERY PARAMS FOR FILTERING                                         |
|  GET /users?role=admin&status=active&sort=-created_at                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### HTTP STATUS CODES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  HTTP STATUS CODES                                                      |
|                                                                         |
|  2XX SUCCESS                                                            |
|  -------------                                                          |
|  200 OK              Request succeeded                                  |
|  201 Created         Resource created (POST)                            |
|  202 Accepted        Request accepted, processing async                 |
|  204 No Content      Success, no body (DELETE)                          |
|                                                                         |
|  3XX REDIRECTION                                                        |
|  -----------------                                                      |
|  301 Moved Permanently   Resource moved, update bookmarks               |
|  302 Found               Temporary redirect                             |
|  304 Not Modified        Use cached version (conditional GET)           |
|                                                                         |
|  4XX CLIENT ERROR                                                       |
|  -----------------                                                      |
|  400 Bad Request         Invalid syntax/parameters                      |
|  401 Unauthorized        Authentication required                        |
|  403 Forbidden           Authenticated but not allowed                  |
|  404 Not Found           Resource doesn't exist                         |
|  405 Method Not Allowed  HTTP method not supported                      |
|  409 Conflict            State conflict (duplicate, version)            |
|  422 Unprocessable       Validation failed                              |
|  429 Too Many Requests   Rate limited                                   |
|                                                                         |
|  5XX SERVER ERROR                                                       |
|  -----------------                                                      |
|  500 Internal Server Error  Unhandled exception                         |
|  502 Bad Gateway           Upstream service failed                      |
|  503 Service Unavailable   Overloaded or maintenance                    |
|  504 Gateway Timeout       Upstream service timeout                     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  COMMON MISTAKES                                                        |
|                                                                         |
|  X Returning 200 with error in body                                     |
|    { "status": 200, "error": "User not found" }                         |
|                                                                         |
|  Y Return proper status code                                            |
|    HTTP 404                                                             |
|    { "error": "User not found" }                                        |
|                                                                         |
|  X Using 500 for validation errors                                      |
|  Y Use 400 or 422 for validation errors                                 |
|                                                                         |
+-------------------------------------------------------------------------+
```

### REQUEST AND RESPONSE DESIGN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  REQUEST/RESPONSE PATTERNS                                              |
|                                                                         |
|  SUCCESSFUL RESPONSE (Single item)                                      |
|  -----------------------------------                                    |
|  GET /users/123                                                         |
|  HTTP 200 OK                                                            |
|                                                                         |
|  {                                                                      |
|    "data": {                                                            |
|      "id": "123",                                                       |
|      "type": "user",                                                    |
|      "attributes": {                                                    |
|        "name": "Alice",                                                 |
|        "email": "alice@example.com",                                    |
|        "created_at": "2024-01-15T10:30:00Z"                             |
|      }                                                                  |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
|  SUCCESSFUL RESPONSE (Collection with pagination)                       |
|  -------------------------------------------------                      |
|  GET /users?page=2&per_page=20                                          |
|  HTTP 200 OK                                                            |
|                                                                         |
|  {                                                                      |
|    "data": [                                                            |
|      { "id": "1", "name": "Alice" },                                    |
|      { "id": "2", "name": "Bob" }                                       |
|    ],                                                                   |
|    "meta": {                                                            |
|      "total": 100,                                                      |
|      "page": 2,                                                         |
|      "per_page": 20,                                                    |
|      "total_pages": 5                                                   |
|    },                                                                   |
|    "links": {                                                           |
|      "self": "/users?page=2&per_page=20",                               |
|      "first": "/users?page=1&per_page=20",                              |
|      "prev": "/users?page=1&per_page=20",                               |
|      "next": "/users?page=3&per_page=20",                               |
|      "last": "/users?page=5&per_page=20"                                |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
|  ERROR RESPONSE                                                         |
|  ----------------                                                       |
|  HTTP 422 Unprocessable Entity                                          |
|                                                                         |
|  {                                                                      |
|    "error": {                                                           |
|      "code": "VALIDATION_ERROR",                                        |
|      "message": "Validation failed",                                    |
|      "details": [                                                       |
|        {                                                                |
|          "field": "email",                                              |
|          "message": "Invalid email format"                              |
|        },                                                               |
|        {                                                                |
|          "field": "age",                                                |
|          "message": "Must be at least 18"                               |
|        }                                                                |
|      ]                                                                  |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8.3: PAGINATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PAGINATION STRATEGIES                                                  |
|                                                                         |
|  1. OFFSET-BASED (Page number)                                          |
|  -------------------------------                                        |
|  GET /users?page=3&per_page=20                                          |
|                                                                         |
|  SQL: SELECT * FROM users LIMIT 20 OFFSET 40                            |
|                                                                         |
|  PROS: Easy to implement, jump to any page                              |
|  CONS: Slow for large offsets, inconsistent during writes               |
|                                                                         |
|  PROBLEM WITH LARGE OFFSETS:                                            |
|  OFFSET 1,000,000 means DB must scan 1M rows to skip them               |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. CURSOR-BASED (Keyset pagination)                                    |
|  -------------------------------------                                  |
|  GET /users?cursor=eyJpZCI6MTIzfQ==&limit=20                            |
|                                                                         |
|  Cursor encodes position (e.g., last seen ID)                           |
|  SQL: SELECT * FROM users WHERE id > 123 LIMIT 20                       |
|                                                                         |
|  PROS: Consistent, efficient for any page                               |
|  CONS: Can't jump to arbitrary page                                     |
|                                                                         |
|  Response:                                                              |
|  {                                                                      |
|    "data": [...],                                                       |
|    "cursors": {                                                         |
|      "next": "eyJpZCI6MTQzfQ==",                                        |
|      "has_more": true                                                   |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
|  USED BY: Twitter, Facebook (Graph API), Stripe                         |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. TIME-BASED                                                          |
|  ---------------                                                        |
|  GET /events?since=2024-01-15T00:00:00Z&limit=100                       |
|                                                                         |
|  Good for feeds, logs, events                                           |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  RECOMMENDATION:                                                        |
|  * Offset-based: Small datasets, need page jumping                      |
|  * Cursor-based: Large datasets, infinite scroll                        |
|  * Time-based: Event streams, activity feeds                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8.4: API VERSIONING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  API VERSIONING STRATEGIES                                              |
|                                                                         |
|  1. URL PATH VERSIONING (Most common)                                   |
|  --------------------------------------                                 |
|  GET /api/v1/users                                                      |
|  GET /api/v2/users                                                      |
|                                                                         |
|  PROS: Clear, easy to understand, cacheable                             |
|  CONS: Not "pure" REST, URL changes                                     |
|                                                                         |
|  USED BY: Twitter, Stripe, Google                                       |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. QUERY PARAMETER                                                     |
|  ---------------------                                                  |
|  GET /api/users?version=2                                               |
|                                                                         |
|  PROS: Easy to add                                                      |
|  CONS: Easy to forget, caching issues                                   |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. HEADER VERSIONING                                                   |
|  ---------------------                                                  |
|  GET /api/users                                                         |
|  Accept: application/vnd.myapi.v2+json                                  |
|                                                                         |
|  Or custom header:                                                      |
|  X-API-Version: 2                                                       |
|                                                                         |
|  PROS: Clean URLs, "proper" REST                                        |
|  CONS: Hidden, harder to test                                           |
|                                                                         |
|  USED BY: GitHub                                                        |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  4. NO VERSIONING (Additive changes only)                               |
|  -------------------------------------------                            |
|  Never break, only add fields                                           |
|                                                                         |
|  PROS: Simplest for clients                                             |
|  CONS: Tech debt accumulates, hard to clean up                          |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  VERSIONING BEST PRACTICES                                              |
|                                                                         |
|  * Support at least 2 versions simultaneously                           |
|  * Deprecation warnings in headers                                      |
|  * Clear migration guides                                               |
|  * Sunset dates communicated in advance                                 |
|  * Default to latest stable version                                     |
|                                                                         |
|  DEPRECATION HEADER:                                                    |
|  Deprecation: true                                                      |
|  Sunset: Sat, 1 Jan 2025 00:00:00 GMT                                   |
|  Link: <https://docs.api.com/migration>; rel="deprecation"              |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8.5: GRAPHQL

```
+-------------------------------------------------------------------------+
|                                                                         |
|  GRAPHQL OVERVIEW                                                       |
|                                                                         |
|  Query language for APIs. Client specifies exactly what data needed.    |
|                                                                         |
|  GRAPHQL vs REST                                                        |
|  -----------------                                                      |
|                                                                         |
|  REST: Multiple endpoints, fixed responses                              |
|  GET /users/123                                                         |
|  GET /users/123/orders                                                  |
|  GET /users/123/posts                                                   |
|  (3 requests, may over-fetch)                                           |
|                                                                         |
|  GraphQL: Single endpoint, flexible queries                             |
|  POST /graphql                                                          |
|  {                                                                      |
|    user(id: "123") {                                                    |
|      name                                                               |
|      email                                                              |
|      orders(last: 5) { id, total }                                      |
|      posts(last: 10) { id, title }                                      |
|    }                                                                    |
|  }                                                                      |
|  (1 request, exact data needed)                                         |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  GRAPHQL OPERATIONS                                                     |
|                                                                         |
|  QUERY (Read data)                                                      |
|  -----------------                                                      |
|  query {                                                                |
|    user(id: "123") {                                                    |
|      name                                                               |
|      email                                                              |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
|  MUTATION (Write data)                                                  |
|  ----------------------                                                 |
|  mutation {                                                             |
|    createUser(input: { name: "Alice", email: "a@b.com" }) {             |
|      id                                                                 |
|      name                                                               |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
|  SUBSCRIPTION (Real-time)                                               |
|  -------------------------                                              |
|  subscription {                                                         |
|    orderStatusChanged(orderId: "456") {                                 |
|      status                                                             |
|      updatedAt                                                          |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  GRAPHQL PROS                                                           |
|  * Client gets exactly what it needs (no over/under-fetching)           |
|  * Single endpoint                                                      |
|  * Strongly typed schema                                                |
|  * Great for mobile (bandwidth sensitive)                               |
|  * Self-documenting (introspection)                                     |
|                                                                         |
|  GRAPHQL CONS                                                           |
|  * Complexity on server side                                            |
|  * Caching is harder (POST requests, dynamic responses)                 |
|  * N+1 query problem (need DataLoader)                                  |
|  * Rate limiting is complex                                             |
|  * Error handling differs from REST                                     |
|  * Learning curve                                                       |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  WHEN TO USE                                                            |
|                                                                         |
|  USE GRAPHQL:                                                           |
|  * Multiple clients with different data needs                           |
|  * Complex, interconnected data                                         |
|  * Mobile apps (bandwidth matters)                                      |
|  * Rapid frontend development                                           |
|                                                                         |
|  USE REST:                                                              |
|  * Simple CRUD operations                                               |
|  * Heavy caching requirements                                           |
|  * File uploads/downloads                                               |
|  * Public APIs                                                          |
|                                                                         |
|  USED BY: Facebook, GitHub, Shopify, Airbnb                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8.6: gRPC

```
+-------------------------------------------------------------------------+
|                                                                         |
|  gRPC OVERVIEW                                                          |
|                                                                         |
|  High-performance RPC framework from Google.                            |
|  Uses Protocol Buffers for serialization.                               |
|                                                                         |
|  gRPC vs REST                                                           |
|  -------------                                                          |
|  +--------------------+-----------------+----------------------------+  |
|  | Aspect             | REST            | gRPC                       |  |
|  +--------------------+-----------------+----------------------------+  |
|  | Protocol           | HTTP/1.1 (JSON) | HTTP/2 (Protobuf)          |  |
|  | Payload size       | Larger (text)   | Smaller (binary)           |  |
|  | Latency            | Higher          | Lower                      |  |
|  | Browser support    | Native          | Requires grpc-web          |  |
|  | Streaming          | Limited         | Full bidirectional         |  |
|  | Code generation    | Optional        | Built-in                   |  |
|  | Human readable     | Yes             | No (binary)                |  |
|  | Learning curve     | Low             | Medium                     |  |
|  +--------------------+-----------------+----------------------------+  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  PROTOCOL BUFFERS (Protobuf)                                            |
|                                                                         |
|  // user.proto                                                          |
|  syntax = "proto3";                                                     |
|                                                                         |
|  message User {                                                         |
|    string id = 1;                                                       |
|    string name = 2;                                                     |
|    string email = 3;                                                    |
|    int32 age = 4;                                                       |
|  }                                                                      |
|                                                                         |
|  service UserService {                                                  |
|    rpc GetUser(GetUserRequest) returns (User);                          |
|    rpc ListUsers(ListUsersRequest) returns (stream User);               |
|    rpc CreateUser(User) returns (User);                                 |
|  }                                                                      |
|                                                                         |
|  message GetUserRequest {                                               |
|    string id = 1;                                                       |
|  }                                                                      |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  gRPC STREAMING MODES                                                   |
|                                                                         |
|  1. UNARY: Simple request-response                                      |
|     rpc GetUser(Request) returns (Response);                            |
|                                                                         |
|  2. SERVER STREAMING: Client sends one, server sends many               |
|     rpc ListUsers(Request) returns (stream User);                       |
|                                                                         |
|  3. CLIENT STREAMING: Client sends many, server sends one               |
|     rpc UploadUsers(stream User) returns (Response);                    |
|                                                                         |
|  4. BIDIRECTIONAL: Both sides stream                                    |
|     rpc Chat(stream Message) returns (stream Message);                  |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  gRPC PROS                                                              |
|  * 10x faster than REST+JSON (binary, HTTP/2)                           |
|  * Strong typing with code generation                                   |
|  * Full streaming support                                               |
|  * Built-in load balancing                                              |
|  * Deadline propagation                                                 |
|                                                                         |
|  gRPC CONS                                                              |
|  * Not browser-native (needs proxy)                                     |
|  * Harder to debug (binary format)                                      |
|  * Less tooling than REST                                               |
|  * Breaking changes are harder to manage                                |
|                                                                         |
|  WHEN TO USE gRPC:                                                      |
|  * Internal microservice communication                                  |
|  * High-performance requirements                                        |
|  * Polyglot environments (good code gen)                                |
|  * Real-time streaming                                                  |
|                                                                         |
|  USED BY: Google, Netflix, Uber, Dropbox, Square                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8.7: RATE LIMITING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RATE LIMITING                                                          |
|                                                                         |
|  WHY RATE LIMIT:                                                        |
|  * Prevent abuse (DoS attacks)                                          |
|  * Ensure fair usage                                                    |
|  * Protect backend resources                                            |
|  * Monetize API (tier-based limits)                                     |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  RATE LIMITING ALGORITHMS                                               |
|                                                                         |
|  1. TOKEN BUCKET                                                        |
|  ------------------                                                     |
|  Bucket fills with tokens at fixed rate.                                |
|  Each request consumes a token.                                         |
|  No tokens = request rejected.                                          |
|                                                                         |
|  Example: 100 tokens/min, bucket size 20 (burst)                        |
|  * Steady: 100 req/min                                                  |
|  * Burst: Can handle 20 extra if bucket full                            |
|                                                                         |
|  PROS: Allows bursts, smooth average rate                               |
|  USED BY: AWS API Gateway, Stripe                                       |
|                                                                         |
|  2. LEAKY BUCKET                                                        |
|  -----------------                                                      |
|  Requests enter bucket, processed at fixed rate.                        |
|  If bucket full, requests rejected.                                     |
|                                                                         |
|  PROS: Smooths traffic, no bursts                                       |
|  CONS: Bursts are rejected even if average is fine                      |
|                                                                         |
|  3. FIXED WINDOW                                                        |
|  -----------------                                                      |
|  Count requests in fixed time windows (e.g., per minute).               |
|                                                                         |
|  Window: 10:00-10:01 > 100 requests allowed                             |
|  If 100 hit at 10:00:59, another 100 at 10:01:01                        |
|  > 200 requests in 2 seconds (burst at boundary!)                       |
|                                                                         |
|  PROS: Simple                                                           |
|  CONS: Boundary burst problem                                           |
|                                                                         |
|  4. SLIDING WINDOW                                                      |
|  -------------------                                                    |
|  Rolling window eliminates boundary issues.                             |
|                                                                         |
|  Count requests in last 60 seconds (not fixed minute)                   |
|                                                                         |
|  PROS: No boundary bursts                                               |
|  CONS: More memory (track timestamps)                                   |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  RATE LIMIT HEADERS                                                     |
|                                                                         |
|  X-RateLimit-Limit: 100           # Max requests allowed                |
|  X-RateLimit-Remaining: 45        # Requests left in window             |
|  X-RateLimit-Reset: 1640000000    # Unix timestamp when resets          |
|  Retry-After: 30                  # Seconds until retry (on 429)        |
|                                                                         |
|  RESPONSE WHEN RATE LIMITED:                                            |
|  HTTP 429 Too Many Requests                                             |
|  Retry-After: 30                                                        |
|                                                                         |
|  {                                                                      |
|    "error": {                                                           |
|      "code": "RATE_LIMIT_EXCEEDED",                                     |
|      "message": "Rate limit exceeded. Try again in 30 seconds."         |
|    }                                                                    |
|  }                                                                      |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  RATE LIMITING DIMENSIONS                                               |
|                                                                         |
|  * Per IP address: Basic DoS protection                                 |
|  * Per API key: Fair usage per customer                                 |
|  * Per user: Authenticated user limits                                  |
|  * Per endpoint: Expensive endpoints get lower limits                   |
|  * Global: Protect entire system                                        |
|                                                                         |
|  TIERED LIMITS:                                                         |
|  Free tier:    100 requests/day                                         |
|  Pro tier:     10,000 requests/day                                      |
|  Enterprise:   Unlimited                                                |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8.8: API AUTHENTICATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  API AUTHENTICATION METHODS                                             |
|                                                                         |
|  1. API KEYS                                                            |
|  -------------                                                          |
|  Simple token for identification.                                       |
|                                                                         |
|  GET /api/users                                                         |
|  X-API-Key: sk_live_abc123xyz                                           |
|                                                                         |
|  Or in query: /api/users?api_key=sk_live_abc123xyz                      |
|                                                                         |
|  PROS: Simple                                                           |
|  CONS: No expiration, shared across requests                            |
|                                                                         |
|  USED BY: Stripe, SendGrid, Google Maps                                 |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. BEARER TOKENS (OAuth 2.0)                                           |
|  -----------------------------                                          |
|  GET /api/users                                                         |
|  Authorization: Bearer eyJhbGciOiJIUzI1NiIs...                          |
|                                                                         |
|  Token obtained through OAuth flow                                      |
|                                                                         |
|  PROS: Standard, short-lived, scoped                                    |
|  CONS: Complex flows                                                    |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. JWT (JSON Web Tokens)                                               |
|  --------------------------                                             |
|  Self-contained token with user info.                                   |
|                                                                         |
|  Structure: header.payload.signature                                    |
|                                                                         |
|  Payload contains:                                                      |
|  {                                                                      |
|    "sub": "user123",                                                    |
|    "name": "Alice",                                                     |
|    "role": "admin",                                                     |
|    "exp": 1640000000                                                    |
|  }                                                                      |
|                                                                         |
|  PROS: Stateless, server doesn't need DB lookup                         |
|  CONS: Can't revoke easily (use short expiry + refresh tokens)          |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  4. BASIC AUTH                                                          |
|  --------------                                                         |
|  Base64 encoded username:password                                       |
|                                                                         |
|  Authorization: Basic YWxpY2U6cGFzc3dvcmQ=                              |
|                                                                         |
|  PROS: Very simple                                                      |
|  CONS: Credentials sent every request, must use HTTPS                   |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  5. HMAC SIGNATURES                                                     |
|  --------------------                                                   |
|  Sign request with secret key.                                          |
|                                                                         |
|  signature = HMAC-SHA256(secret, method + path + timestamp + body)      |
|                                                                         |
|  X-Signature: abc123                                                    |
|  X-Timestamp: 1640000000                                                |
|                                                                         |
|  PROS: Request integrity, replay protection                             |
|  CONS: Complex to implement                                             |
|                                                                         |
|  USED BY: AWS, Stripe webhooks                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 8.9: WEBHOOKS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT ARE WEBHOOKS?                                                     |
|                                                                         |
|  Webhooks are user-defined HTTP callbacks that are triggered by         |
|  events. Instead of polling for updates, the server pushes data         |
|  to your endpoint when something happens.                               |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  POLLING (Traditional):                                           |  |
|  |                                                                   |  |
|  |  Your App -- "Any new orders?" --> Payment Service                |  |
|  |  Your App -- "Any new orders?" --> Payment Service                |  |
|  |  Your App -- "Any new orders?" --> Payment Service                |  |
|  |  Your App -- "Any new orders?" --> "Yes, here's one!"             |  |
|  |                                                                   |  |
|  |  > Wasteful, most requests return nothing                         |  |
|  |                                                                   |  |
|  |  ------------------------------------------------------------     |  |
|  |                                                                   |  |
|  |  WEBHOOK (Event-driven):                                          |  |
|  |                                                                   |  |
|  |  Your App -- "Call me at /webhooks/payment when order paid" -->   |  |
|  |                                                                   |  |
|  |  (later, when event occurs)                                       |  |
|  |                                                                   |  |
|  |  Payment Service -- POST /webhooks/payment --> Your App           |  |
|  |  { "event": "payment.completed", "data": {...} }                  |  |
|  |                                                                   |  |
|  |  > Efficient, only notified when something happens                |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WEBHOOK ARCHITECTURE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TYPICAL WEBHOOK FLOW                                                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  1. REGISTRATION                                                  |  |
|  |     Your App --> Provider: "Register webhook"                     |  |
|  |     POST /webhooks                                                |  |
|  |     {                                                             |  |
|  |       "url": "https://myapp.com/webhooks/stripe",                 |  |
|  |       "events": ["payment.completed", "refund.created"]           |  |
|  |     }                                                             |  |
|  |                                                                   |  |
|  |  2. EVENT OCCURS                                                  |  |
|  |     Customer makes a payment                                      |  |
|  |                                                                   |  |
|  |  3. NOTIFICATION                                                  |  |
|  |     Provider --> Your App                                         |  |
|  |     POST https://myapp.com/webhooks/stripe                        |  |
|  |     {                                                             |  |
|  |       "id": "evt_123",                                            |  |
|  |       "type": "payment.completed",                                |  |
|  |       "data": {                                                   |  |
|  |         "amount": 9999,                                           |  |
|  |         "currency": "usd",                                        |  |
|  |         "customer_id": "cust_456"                                 |  |
|  |       },                                                          |  |
|  |       "created": 1705000000                                       |  |
|  |     }                                                             |  |
|  |                                                                   |  |
|  |  4. ACKNOWLEDGMENT                                                |  |
|  |     Your App --> 200 OK                                           |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WEBHOOK SECURITY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  PROBLEM: How do you know the webhook is really from the provider?      |
|                                                                         |
|  SOLUTIONS:                                                             |
|                                                                         |
|  1. SIGNATURE VERIFICATION (Recommended)                                |
|  =======================================                                |
|                                                                         |
|  Provider signs payload with shared secret                              |
|                                                                         |
|  Headers:                                                               |
|  X-Webhook-Signature: sha256=abc123def456...                            |
|  X-Webhook-Timestamp: 1705000000                                        |
|                                                                         |
|  Verification:                                                          |
|  expected = HMAC-SHA256(secret, timestamp + "." + body)                 |
|  if signature != expected: reject                                       |
|  if timestamp too old: reject (prevent replay)                          |
|                                                                         |
|  USED BY: Stripe, GitHub, Shopify                                       |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  2. WEBHOOK SECRET IN URL                                               |
|  =========================                                              |
|                                                                         |
|  Include secret in webhook URL (less secure)                            |
|  https://myapp.com/webhooks/stripe?secret=xyz789                        |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  3. IP ALLOWLISTING                                                     |
|  ===================                                                    |
|                                                                         |
|  Only accept requests from provider's IP ranges                         |
|  (Check provider's documentation for IP list)                           |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  4. mTLS (Mutual TLS)                                                   |
|  =====================                                                  |
|                                                                         |
|  Both parties authenticate with certificates                            |
|  Most secure, but complex                                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WEBHOOK BEST PRACTICES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FOR WEBHOOK CONSUMERS (Receiving webhooks):                            |
|                                                                         |
|  1. RESPOND QUICKLY                                                     |
|     Return 2xx within 5-30 seconds                                      |
|     Do heavy processing asynchronously                                  |
|                                                                         |
|     DO:                                                                 |
|     receive webhook > queue for processing > return 200                 |
|                                                                         |
|     DON'T:                                                              |
|     receive webhook > process for 60 seconds > return 200               |
|                                                                         |
|  2. HANDLE DUPLICATES (Idempotency)                                     |
|     Store event_id in database                                          |
|     If already processed, return 200 but skip processing                |
|                                                                         |
|  3. VERIFY SIGNATURES                                                   |
|     Always verify the webhook is authentic                              |
|                                                                         |
|  4. USE HTTPS                                                           |
|     Your webhook endpoint must use HTTPS                                |
|                                                                         |
|  5. HANDLE RETRIES GRACEFULLY                                           |
|     Provider will retry on failure                                      |
|     Design for at-least-once delivery                                   |
|                                                                         |
|  --------------------------------------------------------------------   |
|                                                                         |
|  FOR WEBHOOK PROVIDERS (Sending webhooks):                              |
|                                                                         |
|  1. RETRY WITH EXPONENTIAL BACKOFF                                      |
|     Retry: 1min, 5min, 30min, 2hr, 8hr...                               |
|     Max retries: 5-10 attempts                                          |
|                                                                         |
|  2. PROVIDE SIGNATURE                                                   |
|     Sign all payloads with HMAC-SHA256                                  |
|     Include timestamp to prevent replay                                 |
|                                                                         |
|  3. INCLUDE EVENT ID                                                    |
|     Unique ID for deduplication                                         |
|                                                                         |
|  4. SUPPORT FILTERING                                                   |
|     Let users subscribe to specific event types                         |
|                                                                         |
|  5. PROVIDE TESTING TOOLS                                               |
|     Test webhook endpoint                                               |
|     Replay failed webhooks                                              |
|     View webhook delivery logs                                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### WEBHOOKS vs OTHER PATTERNS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |                                                                  |   |
|  |  Pattern       Direction     Real-time   Complexity   Scale      |   |
|  |  ------------------------------------------------------------    |   |
|  |                                                                  |   |
|  |  Polling       Pull          No          Low          Low        |   |
|  |                                                                  |   |
|  |  Webhooks      Push          Yes         Medium       Medium     |   |
|  |                                                                  |   |
|  |  WebSockets    Bidirectional Yes         High         High       |   |
|  |                                                                  |   |
|  |  Message Queue Push          Yes         High         High       |   |
|  |                                                                  |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  WHEN TO USE WEBHOOKS:                                                  |
|  Y Infrequent events                                                    |
|  Y Server-to-server communication                                       |
|  Y Third-party integrations                                             |
|  Y Loosely coupled systems                                              |
|                                                                         |
|  WHEN TO USE ALTERNATIVES:                                              |
|  * High-frequency events > Message Queue                                |
|  * Browser/mobile real-time > WebSockets                                |
|  * Simple, low volume > Polling                                         |
|                                                                         |
|  POPULAR WEBHOOK PROVIDERS:                                             |
|  Stripe, GitHub, Shopify, Twilio, Slack, AWS SNS                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  API DESIGN - KEY TAKEAWAYS                                             |
|                                                                         |
|  REST                                                                   |
|  ----                                                                   |
|  * Resources as URLs, HTTP methods as verbs                             |
|  * Proper status codes (don't return 200 with error body)               |
|  * Consistent response format                                           |
|  * Support pagination for lists                                         |
|                                                                         |
|  GRAPHQL                                                                |
|  -------                                                                |
|  * Client specifies exact data needed                                   |
|  * Single endpoint, flexible queries                                    |
|  * Good for complex, interconnected data                                |
|  * Watch for N+1 queries                                                |
|                                                                         |
|  gRPC                                                                   |
|  ----                                                                   |
|  * Binary protocol (Protobuf), HTTP/2                                   |
|  * 10x faster than REST                                                 |
|  * Great for internal microservices                                     |
|  * Full streaming support                                               |
|                                                                         |
|  VERSIONING                                                             |
|  ----------                                                             |
|  * URL path (/v1/) is most common                                       |
|  * Support multiple versions                                            |
|  * Deprecate gracefully with headers                                    |
|                                                                         |
|  RATE LIMITING                                                          |
|  ------------                                                           |
|  * Token bucket for bursting                                            |
|  * Sliding window for precision                                         |
|  * Return proper headers                                                |
|                                                                         |
|  ====================================================================   |
|                                                                         |
|  INTERVIEW TIPS                                                         |
|  --------------                                                         |
|                                                                         |
|  1. API style choice:                                                   |
|     * REST: External APIs, simple CRUD                                  |
|     * GraphQL: Multiple clients, complex data                           |
|     * gRPC: Internal services, performance-critical                     |
|                                                                         |
|  2. Design an API endpoint:                                             |
|     * Use proper HTTP methods                                           |
|     * Return appropriate status codes                                   |
|     * Include pagination for lists                                      |
|     * Document error responses                                          |
|                                                                         |
|  3. Security:                                                           |
|     * Always use HTTPS                                                  |
|     * Validate all input                                                |
|     * Rate limit                                                        |
|     * Use short-lived tokens                                            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 8

