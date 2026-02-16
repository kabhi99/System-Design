================================================================================
         PAYMENT GATEWAY - HIGH LEVEL DESIGN
         Part 1: Requirements and Scale Estimation
================================================================================


================================================================================
SECTION 1.1: WHAT IS A PAYMENT GATEWAY?
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  PAYMENT GATEWAY                                                       │
    │                                                                         │
    │  A payment gateway is a service that authorizes and processes          │
    │  payments between customers, merchants, and financial institutions.    │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Customer                                                       │  │
    │  │  (Credit Card)                                                 │  │
    │  │       │                                                         │  │
    │  │       ▼                                                         │  │
    │  │  ┌─────────────┐                                               │  │
    │  │  │  Merchant   │  (E-commerce website)                        │  │
    │  │  │  Website    │                                               │  │
    │  │  └──────┬──────┘                                               │  │
    │  │         │                                                       │  │
    │  │         ▼                                                       │  │
    │  │  ┌─────────────────────────────────────────────────────────┐  │  │
    │  │  │            PAYMENT GATEWAY                              │  │  │
    │  │  │  (Stripe, PayPal, Razorpay, Adyen)                     │  │  │
    │  │  │                                                         │  │  │
    │  │  │  • Encrypt card data                                   │  │  │
    │  │  │  • Route to appropriate network                        │  │  │
    │  │  │  • Handle authorization                                │  │  │
    │  │  │  • Manage settlements                                  │  │  │
    │  │  └──────────────────────┬──────────────────────────────────┘  │  │
    │  │                         │                                      │  │
    │  │         ┌───────────────┼───────────────┐                      │  │
    │  │         ▼               ▼               ▼                      │  │
    │  │  ┌───────────┐   ┌───────────┐   ┌───────────┐                │  │
    │  │  │   Visa    │   │MasterCard │   │  Amex     │                │  │
    │  │  │  Network  │   │  Network  │   │  Network  │                │  │
    │  │  └─────┬─────┘   └─────┬─────┘   └─────┬─────┘                │  │
    │  │        │               │               │                       │  │
    │  │        ▼               ▼               ▼                       │  │
    │  │  ┌─────────────────────────────────────────────────────────┐  │  │
    │  │  │         ISSUING BANK (Customer's Bank)                 │  │  │
    │  │  │         Approves/Declines transaction                  │  │  │
    │  │  └─────────────────────────────────────────────────────────┘  │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


PAYMENT ECOSYSTEM PLAYERS
─────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  KEY PLAYERS IN PAYMENT PROCESSING                                     │
    │                                                                         │
    │  1. CARDHOLDER (Customer)                                              │
    │     Person making the purchase with credit/debit card                 │
    │                                                                         │
    │  2. MERCHANT                                                            │
    │     Business accepting the payment                                     │
    │                                                                         │
    │  3. PAYMENT GATEWAY                                                     │
    │     Encrypts and transmits payment data (Stripe, Razorpay)            │
    │     What we're designing!                                              │
    │                                                                         │
    │  4. PAYMENT PROCESSOR                                                   │
    │     Handles transaction routing and communication                     │
    │     (Often combined with gateway)                                      │
    │                                                                         │
    │  5. ACQUIRING BANK (Merchant's Bank)                                   │
    │     Bank that processes card payments on behalf of merchant           │
    │                                                                         │
    │  6. CARD NETWORK (Visa, MasterCard, Amex, RuPay)                       │
    │     Routes transactions between acquirer and issuer                   │
    │                                                                         │
    │  7. ISSUING BANK (Customer's Bank)                                     │
    │     Bank that issued the customer's card                              │
    │     Approves or declines the transaction                              │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 1.2: FUNCTIONAL REQUIREMENTS
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CORE FUNCTIONALITY                                                    │
    │                                                                         │
    │  1. PAYMENT PROCESSING                                                 │
    │     ═══════════════════                                                 │
    │     • Accept payments (cards, UPI, wallets, net banking)              │
    │     • Authorize transactions in real-time                             │
    │     • Capture payments (immediate or delayed)                         │
    │     • Process refunds (full and partial)                              │
    │     • Handle chargebacks                                               │
    │                                                                         │
    │  2. PAYMENT METHODS                                                     │
    │     ════════════════════                                                │
    │     • Credit/Debit cards (Visa, MC, Amex, RuPay)                      │
    │     • Digital wallets (Apple Pay, Google Pay, PayPal)                 │
    │     • UPI (India-specific)                                            │
    │     • Net banking                                                      │
    │     • Buy Now Pay Later (BNPL)                                        │
    │     • Bank transfers (ACH, SEPA, NEFT)                                │
    │                                                                         │
    │  3. MERCHANT MANAGEMENT                                                 │
    │     ═════════════════════                                               │
    │     • Merchant onboarding and KYC                                     │
    │     • API key management                                               │
    │     • Webhook configuration                                            │
    │     • Settlement configuration                                         │
    │     • Multi-currency support                                           │
    │                                                                         │
    │  4. TRANSACTION MANAGEMENT                                             │
    │     ═══════════════════════════                                         │
    │     • Transaction status tracking                                      │
    │     • Payment links and hosted checkout                               │
    │     • Recurring payments / Subscriptions                              │
    │     • Saved cards (tokenization)                                      │
    │     • Split payments (marketplaces)                                   │
    │                                                                         │
    │  5. REPORTING & RECONCILIATION                                         │
    │     ═════════════════════════════                                       │
    │     • Real-time transaction dashboard                                 │
    │     • Settlement reports                                               │
    │     • Reconciliation with banks                                       │
    │     • Dispute management                                               │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 1.3: NON-FUNCTIONAL REQUIREMENTS
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  CRITICAL NON-FUNCTIONAL REQUIREMENTS                                  │
    │                                                                         │
    │  1. RELIABILITY & CONSISTENCY                                          │
    │     ═══════════════════════════════                                     │
    │     • EXACTLY-ONCE processing (no duplicate charges!)                 │
    │     • 99.99% uptime (52 min downtime/year)                           │
    │     • Zero data loss                                                   │
    │     • Strong consistency for financial transactions                   │
    │                                                                         │
    │  2. SECURITY & COMPLIANCE                                              │
    │     ═════════════════════════                                           │
    │     • PCI-DSS Level 1 compliance                                      │
    │     • End-to-end encryption                                           │
    │     • Tokenization of sensitive data                                  │
    │     • Fraud detection                                                  │
    │     • SOC 2 Type II compliance                                        │
    │                                                                         │
    │  3. LATENCY                                                             │
    │     ══════════                                                          │
    │     • Authorization: < 2 seconds (p99)                                │
    │     • API response: < 500ms (p99)                                     │
    │     • User perception: instant                                        │
    │                                                                         │
    │  4. SCALABILITY                                                         │
    │     ═════════════                                                       │
    │     • Handle traffic spikes (10x during sales)                       │
    │     • Support millions of transactions/day                           │
    │     • Horizontal scaling                                               │
    │                                                                         │
    │  5. AVAILABILITY                                                        │
    │     ══════════════                                                      │
    │     • Multi-region deployment                                         │
    │     • Graceful degradation                                            │
    │     • Automatic failover                                               │
    │                                                                         │
    │  6. AUDITABILITY                                                        │
    │     ══════════════                                                      │
    │     • Complete audit trail                                            │
    │     • Immutable transaction logs                                      │
    │     • Regulatory reporting                                            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 1.4: SCALE ESTIMATION
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  SCALE ASSUMPTIONS (Stripe/Razorpay Scale)                            │
    │                                                                         │
    │  TRANSACTIONS:                                                          │
    │  • Daily transactions: 10 million                                     │
    │  • Peak TPS: 5,000 transactions/second                               │
    │  • Average TPS: 115 TPS                                               │
    │  • Flash sale peak: 50,000 TPS                                        │
    │                                                                         │
    │  MERCHANTS:                                                             │
    │  • Active merchants: 500,000                                          │
    │  • New merchants/day: 1,000                                           │
    │                                                                         │
    │  USERS:                                                                 │
    │  • Unique cardholders/day: 5 million                                  │
    │  • Saved cards: 100 million tokens                                    │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  STORAGE ESTIMATION                                                     │
    │                                                                         │
    │  Transaction record: ~2 KB                                             │
    │  • transaction_id, merchant_id, amount, currency                     │
    │  • card_token, status, timestamps                                     │
    │  • metadata, response codes, etc.                                     │
    │                                                                         │
    │  Daily storage: 10M × 2 KB = 20 GB/day                               │
    │  Annual storage: 20 GB × 365 = 7.3 TB/year (transactions only)       │
    │                                                                         │
    │  With logs, audit trails, analytics:                                  │
    │  Multiply by 10x = ~75 TB/year                                        │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  BANDWIDTH ESTIMATION                                                   │
    │                                                                         │
    │  Request size: ~1 KB (payment request)                                │
    │  Response size: ~2 KB (with receipt)                                  │
    │                                                                         │
    │  Peak bandwidth: 5,000 TPS × 3 KB = 15 MB/s                          │
    │  Daily bandwidth: 10M × 3 KB = 30 GB/day                             │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
SECTION 1.5: PAYMENT FLOW TYPES
================================================================================

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                         │
    │  1. AUTHORIZE + CAPTURE (Two-Step)                                    │
    │  ═══════════════════════════════════                                    │
    │                                                                         │
    │  Used by: Hotels, car rentals, e-commerce with delayed shipping       │
    │                                                                         │
    │  ┌─────────────────────────────────────────────────────────────────┐  │
    │  │                                                                 │  │
    │  │  Step 1: AUTHORIZE (Reserve funds)                             │  │
    │  │  ───────────────────────────────────                            │  │
    │  │  POST /payments                                                 │  │
    │  │  { amount: 100, capture: false }                               │  │
    │  │                                                                 │  │
    │  │  → Bank reserves $100 on card                                  │  │
    │  │  → No money moved yet                                          │  │
    │  │  → Auth valid for 7-30 days                                    │  │
    │  │                                                                 │  │
    │  │  Step 2: CAPTURE (Collect funds)                               │  │
    │  │  ───────────────────────────────                                │  │
    │  │  POST /payments/{id}/capture                                   │  │
    │  │  { amount: 100 }  // Can capture less than authorized         │  │
    │  │                                                                 │  │
    │  │  → Money moves from cardholder to merchant                    │  │
    │  │                                                                 │  │
    │  │  Alternative: VOID (Cancel authorization)                     │  │
    │  │  POST /payments/{id}/cancel                                    │  │
    │  │                                                                 │  │
    │  └─────────────────────────────────────────────────────────────────┘  │
    │                                                                         │
    │  2. DIRECT CAPTURE (One-Step)                                         │
    │  ═════════════════════════════                                          │
    │                                                                         │
    │  Used by: Digital goods, instant delivery                             │
    │                                                                         │
    │  POST /payments                                                        │
    │  { amount: 100, capture: true }  // Default                          │
    │                                                                         │
    │  → Authorize AND capture in single call                              │
    │  → Money moves immediately                                            │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  3. REFUND                                                              │
    │  ══════════                                                             │
    │                                                                         │
    │  POST /payments/{id}/refund                                           │
    │  { amount: 50 }  // Partial refund                                   │
    │                                                                         │
    │  • Full refund: Return entire amount                                 │
    │  • Partial refund: Return portion                                    │
    │  • Multiple partial refunds allowed                                  │
    │                                                                         │
    │  ────────────────────────────────────────────────────────────────────  │
    │                                                                         │
    │  4. RECURRING / SUBSCRIPTION                                           │
    │  ════════════════════════════                                           │
    │                                                                         │
    │  Initial: Save card with customer consent                             │
    │  Subsequent: Charge using saved token (no CVV needed)                │
    │                                                                         │
    │  POST /subscriptions                                                   │
    │  { customer_id, plan_id, payment_method_token }                      │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘


================================================================================
END OF PART 1
================================================================================

