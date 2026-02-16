# E-COMMERCE SYSTEM DESIGN
*Chapter 3: Checkout Flow and SAGA Pattern*

The checkout process involves multiple services that must coordinate
correctly. This chapter covers the SAGA pattern for distributed transactions
and handling failures gracefully.

## SECTION 3.1: THE CHECKOUT PROBLEM

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHY IS CHECKOUT HARD?                                                |
|                                                                         |
|  A single checkout involves:                                          |
|                                                                         |
|  1. INVENTORY SERVICE: Reserve items                                  |
|  2. PAYMENT SERVICE: Charge customer                                  |
|  3. ORDER SERVICE: Create order record                                |
|  4. SHIPPING SERVICE: Schedule delivery                               |
|  5. NOTIFICATION: Send confirmation                                   |
|                                                                         |
|  Each is a separate microservice with its own database.              |
|  We can't use a single database transaction!                         |
|                                                                         |
|  THE DISTRIBUTED TRANSACTION PROBLEM                                  |
|  -------------------------------------                                  |
|                                                                         |
|  Scenario: User buys last item in stock                              |
|                                                                         |
|  1. Reserve inventory  [x]                                             |
|  2. Charge payment     [x]                                             |
|  3. Create order       [ ] (fails!)                                    |
|                                                                         |
|  NOW WHAT?                                                             |
|  - Payment is charged but order doesn't exist!                       |
|  - Inventory is reserved but no order!                               |
|  - Customer is unhappy!                                               |
|                                                                         |
|  WE NEED TO UNDO THE PREVIOUS STEPS (COMPENSATION)                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.2: THE SAGA PATTERN

```
+-------------------------------------------------------------------------+
|                                                                         |
|  WHAT IS A SAGA?                                                       |
|                                                                         |
|  A SAGA is a sequence of local transactions where each step has      |
|  a compensating action to undo it if a later step fails.             |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  FORWARD TRANSACTIONS          COMPENSATING TRANSACTIONS      |   |
|  |  --------------------          -------------------------      |   |
|  |  T1: Reserve inventory    <-->   C1: Release inventory          |   |
|  |  T2: Charge payment       <-->   C2: Refund payment             |   |
|  |  T3: Create order         <-->   C3: Cancel order               |   |
|  |  T4: Schedule shipping    <-->   C4: Cancel shipping            |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
|  IF ANY STEP FAILS:                                                    |
|  Execute compensating transactions in REVERSE order                   |
|                                                                         |
|  EXAMPLE: T3 (Create order) fails                                     |
|  ---------------------------------                                      |
|  1. T1: Reserve inventory   [x]                                        |
|  2. T2: Charge payment      [x]                                        |
|  3. T3: Create order        [ ] (FAIL!)                               |
|  4. C2: Refund payment      [x] (compensate T2)                       |
|  5. C1: Release inventory   [x] (compensate T1)                       |
|                                                                         |
|  Result: System returns to consistent state                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SAGA IMPLEMENTATION APPROACHES

```
+-------------------------------------------------------------------------+
|                                                                         |
|  1. CHOREOGRAPHY (Event-driven)                                       |
|  ===============================                                        |
|                                                                         |
|  Each service listens to events and decides what to do next.         |
|  No central coordinator.                                              |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  Order          Inventory        Payment          Notification |   |
|  |  Service        Service          Service          Service      |   |
|  |     |               |                |                |        |   |
|  |     | OrderCreated  |                |                |        |   |
|  |     |-------------->|                |                |        |   |
|  |     |               |                |                |        |   |
|  |     |               | InventoryReserved               |        |   |
|  |     |               |--------------->|                |        |   |
|  |     |               |                |                |        |   |
|  |     |               |                | PaymentCompleted        |   |
|  |     |               |                |--------------->|        |   |
|  |     |               |                |                |        |   |
|  |     |<--------------------------------------------------       |   |
|  |     |               OrderConfirmed                    |        |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
|  FAILURE HANDLING:                                                     |
|  If PaymentFailed event is published:                                 |
|  - Inventory Service listens -> releases reservation                  |
|  - Order Service listens -> marks order as failed                     |
|                                                                         |
|  PROS:                                                                 |
|  [x] Loose coupling                                                    |
|  [x] No single point of failure                                        |
|  [x] Simple for small workflows                                        |
|                                                                         |
|  CONS:                                                                 |
|  [ ] Hard to understand the full flow                                  |
|  [ ] Cyclic dependencies possible                                      |
|  [ ] Testing is complex                                                |
|                                                                         |
|  ==================================================================== |
|                                                                         |
|  2. ORCHESTRATION (Central coordinator)                               |
|  =======================================                                |
|                                                                         |
|  A central SAGA Orchestrator manages the flow.                        |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |                    SAGA ORCHESTRATOR                          |   |
|  |                          |                                     |   |
|  |         +----------------+----------------+                   |   |
|  |         |                |                |                   |   |
|  |         v                v                v                   |   |
|  |    +---------+     +---------+     +---------+               |   |
|  |    |Inventory|     | Payment |     |  Order  |               |   |
|  |    | Service |     | Service |     | Service |               |   |
|  |    +---------+     +---------+     +---------+               |   |
|  |                                                                |   |
|  |  Orchestrator:                                                 |   |
|  |  1. Call Inventory.reserve()                                  |   |
|  |  2. If success -> Call Payment.charge()                       |   |
|  |  3. If success -> Call Order.create()                         |   |
|  |  4. If any fails -> Call compensations in reverse             |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
|  PROS:                                                                 |
|  [x] Easy to understand the flow                                       |
|  [x] Easier to test                                                    |
|  [x] Better for complex workflows                                      |
|                                                                         |
|  CONS:                                                                 |
|  [ ] Orchestrator can be bottleneck                                    |
|  [ ] More coupling to orchestrator                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.3: CHECKOUT SAGA IMPLEMENTATION

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHECKOUT SAGA ORCHESTRATOR                                           |
|                                                                         |
|  public class CheckoutSagaOrchestrator {                              |
|                                                                         |
|      public OrderResult executeCheckout(CheckoutRequest request) {    |
|          String sagaId = UUID.randomUUID().toString();                |
|          SagaState state = new SagaState(sagaId);                     |
|                                                                         |
|          try {                                                         |
|              // Step 1: Reserve Inventory                             |
|              ReservationResult reservation =                          |
|                  inventoryService.reserve(                            |
|                      request.getItems(),                              |
|                      sagaId,                                          |
|                      Duration.ofMinutes(15)                           |
|                  );                                                    |
|              state.setInventoryReserved(true);                        |
|              state.setReservationId(reservation.getId());            |
|                                                                         |
|              // Step 2: Process Payment                               |
|              PaymentResult payment = paymentService.charge(          |
|                  request.getPaymentMethod(),                          |
|                  request.getTotalAmount(),                            |
|                  sagaId  // idempotency key                          |
|              );                                                        |
|              state.setPaymentCompleted(true);                         |
|              state.setPaymentId(payment.getId());                    |
|                                                                         |
|              // Step 3: Create Order                                  |
|              Order order = orderService.create(                       |
|                  request,                                              |
|                  reservation,                                          |
|                  payment                                               |
|              );                                                        |
|              state.setOrderCreated(true);                             |
|              state.setOrderId(order.getId());                        |
|                                                                         |
|              // Step 4: Confirm inventory (move from reserved to sold)|
|              inventoryService.confirmReservation(reservation.getId());|
|                                                                         |
|              // Step 5: Publish success event                         |
|              publishEvent(new OrderConfirmedEvent(order));           |
|                                                                         |
|              return OrderResult.success(order);                       |
|                                                                         |
|          } catch (Exception e) {                                      |
|              // COMPENSATION: Undo completed steps                   |
|              compensate(state);                                        |
|              return OrderResult.failed(e.getMessage());              |
|          }                                                             |
|      }                                                                 |
|                                                                         |
|      private void compensate(SagaState state) {                       |
|          // Undo in REVERSE order                                     |
|                                                                         |
|          if (state.isPaymentCompleted()) {                           |
|              paymentService.refund(state.getPaymentId());            |
|          }                                                             |
|                                                                         |
|          if (state.isInventoryReserved()) {                          |
|              inventoryService.releaseReservation(                    |
|                  state.getReservationId()                            |
|              );                                                        |
|          }                                                             |
|                                                                         |
|          publishEvent(new OrderFailedEvent(state.getSagaId()));      |
|      }                                                                 |
|  }                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### SAGA STATE PERSISTENCE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SAGA STATE TABLE                                                      |
|                                                                         |
|  CREATE TABLE saga_states (                                           |
|      saga_id             UUID PRIMARY KEY,                            |
|      type                VARCHAR(50) NOT NULL,  -- CHECKOUT, RETURN  |
|      status              VARCHAR(20) NOT NULL,  -- RUNNING, COMPLETED|
|      current_step        VARCHAR(50),                                 |
|      payload             JSONB,                                        |
|      completed_steps     JSONB,  -- ["INVENTORY_RESERVED", ...]     |
|      failed_step         VARCHAR(50),                                 |
|      error_message       TEXT,                                         |
|      created_at          TIMESTAMP DEFAULT NOW(),                     |
|      updated_at          TIMESTAMP DEFAULT NOW()                      |
|  );                                                                    |
|                                                                         |
|  WHY PERSIST SAGA STATE?                                              |
|  -------------------------                                              |
|  * Recovery: If orchestrator crashes, can resume from persisted state|
|  * Audit: Complete history of what happened                          |
|  * Debugging: Can see exactly where a saga failed                    |
|  * Manual intervention: Support team can see stuck sagas            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.4: IDEMPOTENCY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  IDEMPOTENCY IN SAGA STEPS                                            |
|                                                                         |
|  Every saga step MUST be idempotent:                                  |
|  "Calling it multiple times has the same effect as calling once"     |
|                                                                         |
|  WHY?                                                                  |
|  * Network failures can cause retries                                |
|  * Message queues may deliver same message twice                     |
|  * Recovery process may re-execute steps                             |
|                                                                         |
|  IMPLEMENTATION:                                                       |
|                                                                         |
|  +----------------------------------------------------------------+   |
|  |                                                                |   |
|  |  public PaymentResult charge(                                 |   |
|  |      PaymentMethod method,                                     |   |
|  |      BigDecimal amount,                                        |   |
|  |      String idempotencyKey  // e.g., sagaId                  |   |
|  |  ) {                                                           |   |
|  |      // Check if already processed                            |   |
|  |      Payment existing = paymentRepo.findByIdempotencyKey(     |   |
|  |          idempotencyKey                                        |   |
|  |      );                                                        |   |
|  |                                                                |   |
|  |      if (existing != null) {                                  |   |
|  |          return existing.toResult();  // Return cached result |   |
|  |      }                                                         |   |
|  |                                                                |   |
|  |      // Lock to prevent concurrent processing                 |   |
|  |      boolean locked = redisLock.tryLock(                      |   |
|  |          "payment:" + idempotencyKey,                         |   |
|  |          Duration.ofMinutes(5)                                 |   |
|  |      );                                                        |   |
|  |                                                                |   |
|  |      if (!locked) {                                           |   |
|  |          throw new ConcurrentProcessingException();           |   |
|  |      }                                                         |   |
|  |                                                                |   |
|  |      try {                                                     |   |
|  |          // Double-check after acquiring lock                 |   |
|  |          existing = paymentRepo.findByIdempotencyKey(...);   |   |
|  |          if (existing != null) return existing.toResult();   |   |
|  |                                                                |   |
|  |          // Process payment                                   |   |
|  |          Payment payment = processPayment(method, amount);   |   |
|  |          payment.setIdempotencyKey(idempotencyKey);          |   |
|  |          paymentRepo.save(payment);                           |   |
|  |                                                                |   |
|  |          return payment.toResult();                           |   |
|  |                                                                |   |
|  |      } finally {                                               |   |
|  |          redisLock.unlock("payment:" + idempotencyKey);      |   |
|  |      }                                                         |   |
|  |  }                                                             |   |
|  |                                                                |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.5: FAILURE SCENARIOS AND RECOVERY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FAILURE SCENARIOS                                                     |
|                                                                         |
|  SCENARIO 1: Payment Gateway Timeout                                  |
|  -----------------------------------                                    |
|  Payment request sent, no response received.                          |
|  Did payment succeed or fail?                                         |
|                                                                         |
|  Solution:                                                             |
|  1. Mark saga as PENDING_PAYMENT                                      |
|  2. Background job queries payment gateway for status                |
|  3. If SUCCESS -> continue saga                                       |
|  4. If FAILED -> compensate                                           |
|  5. If STILL_UNKNOWN after timeout -> mark for manual review         |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  SCENARIO 2: Orchestrator Crashes Mid-Saga                           |
|  -------------------------------------------                            |
|  Server dies after payment but before order creation.                 |
|                                                                         |
|  Solution:                                                             |
|  1. Saga state is persisted to database                              |
|  2. On startup, recovery job finds RUNNING sagas                     |
|  3. Resume from last completed step                                  |
|                                                                         |
|  Recovery Job:                                                         |
|  +----------------------------------------------------------------+   |
|  |  @Scheduled(fixedRate = 60000)  // Every minute               |   |
|  |  public void recoverStuckSagas() {                            |   |
|  |      List<SagaState> stuck = sagaRepo.findStuck(             |   |
|  |          Duration.ofMinutes(5)  // Stuck for > 5 minutes     |   |
|  |      );                                                        |   |
|  |                                                                |   |
|  |      for (SagaState saga : stuck) {                          |   |
|  |          try {                                                 |   |
|  |              resumeOrCompensate(saga);                        |   |
|  |          } catch (Exception e) {                              |   |
|  |              alertOps(saga, e);                               |   |
|  |          }                                                     |   |
|  |      }                                                         |   |
|  |  }                                                             |   |
|  +----------------------------------------------------------------+   |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  SCENARIO 3: Compensation Fails                                       |
|  ------------------------------                                         |
|  Refund fails due to payment gateway error.                           |
|                                                                         |
|  Solution:                                                             |
|  1. Retry compensation with exponential backoff                      |
|  2. If still fails, alert operations team                            |
|  3. Log full context for manual resolution                           |
|  4. Mark saga as COMPENSATION_FAILED                                 |
|                                                                         |
|  --------------------------------------------------------------------  |
|                                                                         |
|  SCENARIO 4: Out of Stock During Checkout                            |
|  --------------------------------------------                           |
|  User has items in cart, starts checkout, but inventory ran out.    |
|                                                                         |
|  Solution:                                                             |
|  1. Inventory reservation fails immediately                          |
|  2. Return clear error: "Item X is out of stock"                    |
|  3. Suggest alternatives or notify when back in stock               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 3.6: KAFKA EVENT CONTRACTS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHECKOUT SAGA EVENTS                                                  |
|                                                                         |
|  CHECKOUT_INITIATED                                                    |
|  ---------------------                                                  |
|  {                                                                     |
|    "eventType": "CHECKOUT_INITIATED",                                 |
|    "sagaId": "saga-123-456",                                          |
|    "userId": "user-789",                                              |
|    "items": [                                                          |
|      { "productId": "prod-1", "quantity": 2, "price": 999.00 }       |
|    ],                                                                  |
|    "totalAmount": 1998.00,                                            |
|    "timestamp": "2024-01-15T10:00:00Z"                                |
|  }                                                                     |
|                                                                         |
|  INVENTORY_RESERVED                                                    |
|  ---------------------                                                  |
|  {                                                                     |
|    "eventType": "INVENTORY_RESERVED",                                 |
|    "sagaId": "saga-123-456",                                          |
|    "reservationId": "res-111",                                        |
|    "items": [...],                                                     |
|    "expiresAt": "2024-01-15T10:15:00Z",                              |
|    "timestamp": "2024-01-15T10:00:01Z"                                |
|  }                                                                     |
|                                                                         |
|  PAYMENT_COMPLETED                                                     |
|  --------------------                                                   |
|  {                                                                     |
|    "eventType": "PAYMENT_COMPLETED",                                  |
|    "sagaId": "saga-123-456",                                          |
|    "paymentId": "pay-222",                                            |
|    "amount": 1998.00,                                                 |
|    "method": "CREDIT_CARD",                                           |
|    "timestamp": "2024-01-15T10:00:30Z"                                |
|  }                                                                     |
|                                                                         |
|  ORDER_CONFIRMED                                                       |
|  ------------------                                                     |
|  {                                                                     |
|    "eventType": "ORDER_CONFIRMED",                                    |
|    "sagaId": "saga-123-456",                                          |
|    "orderId": "order-333",                                            |
|    "orderNumber": "ORD20240115001",                                  |
|    "timestamp": "2024-01-15T10:00:35Z"                                |
|  }                                                                     |
|                                                                         |
|  CHECKOUT_FAILED                                                       |
|  ------------------                                                     |
|  {                                                                     |
|    "eventType": "CHECKOUT_FAILED",                                    |
|    "sagaId": "saga-123-456",                                          |
|    "failedStep": "PAYMENT",                                           |
|    "reason": "Insufficient funds",                                    |
|    "compensationsExecuted": ["INVENTORY_RELEASED"],                  |
|    "timestamp": "2024-01-15T10:00:40Z"                                |
|  }                                                                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## CHAPTER SUMMARY

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CHECKOUT & SAGA - KEY TAKEAWAYS                                      |
|                                                                         |
|  THE PROBLEM                                                           |
|  -----------                                                           |
|  * Checkout spans multiple services                                   |
|  * Can't use single database transaction                             |
|  * Need to handle partial failures                                    |
|                                                                         |
|  SAGA PATTERN                                                          |
|  ------------                                                          |
|  * Sequence of local transactions                                     |
|  * Each step has compensating action                                  |
|  * Choreography: Event-driven, loose coupling                        |
|  * Orchestration: Central coordinator, easier to understand          |
|                                                                         |
|  IDEMPOTENCY                                                           |
|  -----------                                                           |
|  * Every step must be idempotent                                     |
|  * Use idempotency keys                                               |
|  * Cache results for duplicate requests                              |
|                                                                         |
|  RECOVERY                                                              |
|  --------                                                              |
|  * Persist saga state to database                                    |
|  * Recovery job handles stuck sagas                                  |
|  * Alert on compensation failures                                    |
|                                                                         |
|  INTERVIEW TIP                                                         |
|  -------------                                                         |
|  Draw the saga flow with compensation arrows.                        |
|  Explain what happens when each step fails.                          |
|  Mention idempotency as critical requirement.                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 3

