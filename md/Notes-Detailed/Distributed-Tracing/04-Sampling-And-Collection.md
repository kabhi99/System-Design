# DISTRIBUTED TRACING SYSTEM DESIGN (JAEGER-LIKE)

CHAPTER 4: SAMPLING AND COLLECTION
## TABLE OF CONTENTS
*-----------------*
*1. Why Sampling?*
*2. Sampling Strategies*
*3. Sampling Implementation*
*4. Collector Deep Dive*
*5. Tail-Based Sampling*

SECTION 4.1: WHY SAMPLING?
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  THE SAMPLING PROBLEM                                                  |*
*|                                                                         |*
*|  At scale, 100% trace collection is:                                  |*
*|  * Expensive (storage costs)                                          |*
*|  * High overhead (network, CPU)                                       |*
*|  * Often unnecessary (most traces are "normal")                       |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  EXAMPLE: 100K requests/second                                        |*
*|                                                                         |*
*|  100% sampling:                                                        |*
*|  * 2M spans/second                                                    |*
*|  * 100 MB/s network bandwidth                                        |*
*|  * 8.6 TB/day storage                                                |*
*|  * $$$$ costs                                                         |*
*|                                                                         |*
*|  1% sampling:                                                          |*
*|  * 20K spans/second                                                   |*
*|  * 1 MB/s network bandwidth                                          |*
*|  * 86 GB/day storage                                                 |*
*|  * $ costs                                                            |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SAMPLING GOALS                                                        |*
*|                                                                         |*
*|  1. REPRESENTATIVE: Sample should reflect overall traffic            |*
*|  2. COMPLETE: If sampled, capture ALL spans in trace                |*
*|  3. IMPORTANT: Always capture errors/slow requests                   |*
*|  4. LOW OVERHEAD: Minimal impact on application                      |*
*|  5. CONSISTENT: Same trace sampled/dropped everywhere               |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SAMPLING DECISION POINT                                              |*
*|                                                                         |*
*|  HEAD-BASED SAMPLING:                                                  |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Request arrives > Decide NOW > All downstream follows        |  |*
*|  |                                                                 |  |*
*|  |  Decision at: Root span creation                               |  |*
*|  |  Propagated via: Trace flags in context                       |  |*
*|  |                                                                 |  |*
*|  |  Pros:                                                         |  |*
*|  |  * Simple implementation                                       |  |*
*|  |  * Low overhead                                                |  |*
*|  |  * Consistent (whole trace or nothing)                        |  |*
*|  |                                                                 |  |*
*|  |  Cons:                                                         |  |*
*|  |  * Can't know if trace will have errors                       |  |*
*|  |  * Can't know final duration                                  |  |*
*|  |  * May miss important traces                                  |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  TAIL-BASED SAMPLING:                                                  |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Collect all spans > Wait for trace complete > Then decide   |  |*
*|  |                                                                 |  |*
*|  |  Decision at: After all spans received                        |  |*
*|  |  Requires: Centralized collector                              |  |*
*|  |                                                                 |  |*
*|  |  Pros:                                                         |  |*
*|  |  * Can sample based on final outcome                          |  |*
*|  |  * 100% of errors captured                                    |  |*
*|  |  * 100% of slow traces captured                              |  |*
*|  |                                                                 |  |*
*|  |  Cons:                                                         |  |*
*|  |  * Higher complexity                                          |  |*
*|  |  * Must collect all spans first                              |  |*
*|  |  * More resource usage                                        |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4.2: SAMPLING STRATEGIES
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  1. PROBABILISTIC SAMPLING (Constant Rate)                            |*
*|  ------------------------------------------                            |*
*|                                                                         |*
*|  Sample X% of all traces randomly.                                    |*
*|                                                                         |*
*|  Implementation:                                                       |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  def should_sample(trace_id, rate=0.01):                      |  |*
*|  |      # Use trace_id for consistency across services           |  |*
*|  |      hash_value = hash(trace_id) % 10000                      |  |*
*|  |      threshold = rate * 10000  # 1% = 100                     |  |*
*|  |      return hash_value < threshold                            |  |*
*|  |                                                                 |  |*
*|  |  # Same trace_id > same decision in all services             |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  Configuration:                                                        |*
*|  {                                                                     |*
*|    "sampler": {                                                       |*
*|      "type": "probabilistic",                                        |*
*|      "param": 0.01   // 1%                                          |*
*|    }                                                                   |*
*|  }                                                                     |*
*|                                                                         |*
*|  Pros: Simple, predictable, uniform                                  |*
*|  Cons: May miss rare but important traces                            |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  2. RATE LIMITING SAMPLING                                            |*
*|  -----------------------------                                         |*
*|                                                                         |*
*|  Sample up to N traces per second.                                    |*
*|                                                                         |*
*|  Implementation:                                                       |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  class RateLimitingSampler:                                    |  |*
*|  |      def __init__(self, max_traces_per_second):               |  |*
*|  |          self.max_rate = max_traces_per_second                |  |*
*|  |          self.tokens = max_traces_per_second                  |  |*
*|  |          self.last_tick = time.time()                         |  |*
*|  |                                                                 |  |*
*|  |      def should_sample(self, trace_id):                       |  |*
*|  |          self._refill_tokens()                                 |  |*
*|  |          if self.tokens > 0:                                  |  |*
*|  |              self.tokens -= 1                                 |  |*
*|  |              return True                                       |  |*
*|  |          return False                                          |  |*
*|  |                                                                 |  |*
*|  |      def _refill_tokens(self):                                |  |*
*|  |          now = time.time()                                    |  |*
*|  |          elapsed = now - self.last_tick                       |  |*
*|  |          self.tokens = min(                                   |  |*
*|  |              self.max_rate,                                   |  |*
*|  |              self.tokens + (elapsed * self.max_rate)         |  |*
*|  |          )                                                     |  |*
*|  |          self.last_tick = now                                 |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  Configuration:                                                        |*
*|  {                                                                     |*
*|    "sampler": {                                                       |*
*|      "type": "ratelimiting",                                         |*
*|      "param": 100   // 100 traces/second                            |*
*|    }                                                                   |*
*|  }                                                                     |*
*|                                                                         |*
*|  Pros: Predictable volume, cost control                              |*
*|  Cons: Biased toward bursty traffic                                  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  3. ADAPTIVE SAMPLING                                                  |*
*|  -------------------------                                             |*
*|                                                                         |*
*|  Adjust sampling rate based on traffic volume.                        |*
*|                                                                         |*
*|  Goal: Sample more during low traffic, less during high traffic.     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Traffic: LOW (100 req/s)   > Sample 10%                      |  |*
*|  |  Traffic: MEDIUM (1K req/s) > Sample 1%                       |  |*
*|  |  Traffic: HIGH (10K req/s)  > Sample 0.1%                     |  |*
*|  |                                                                 |  |*
*|  |  Result: Roughly constant volume of sampled traces            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  Implementation:                                                       |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  class AdaptiveSampler:                                        |  |*
*|  |      def __init__(self, target_samples_per_second=100):       |  |*
*|  |          self.target = target_samples_per_second              |  |*
*|  |          self.window = deque(maxlen=100)  # Last 100 requests|  |*
*|  |                                                                 |  |*
*|  |      def should_sample(self, trace_id):                       |  |*
*|  |          current_rate = self._estimate_rate()                 |  |*
*|  |          sample_prob = min(1.0, self.target / current_rate)  |  |*
*|  |          return hash(trace_id) % 10000 < sample_prob * 10000 |  |*
*|  |                                                                 |  |*
*|  |      def _estimate_rate(self):                                |  |*
*|  |          self.window.append(time.time())                      |  |*
*|  |          if len(self.window) < 2:                             |  |*
*|  |              return 1                                          |  |*
*|  |          duration = self.window[-1] - self.window[0]         |  |*
*|  |          return len(self.window) / duration if duration > 0 else 1|*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  4. PER-OPERATION SAMPLING                                            |*
*|  ---------------------------                                           |*
*|                                                                         |*
*|  Different sampling rates for different operations.                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Configuration:                                                |  |*
*|  |  {                                                              |  |*
*|  |    "default_strategy": {                                      |  |*
*|  |      "type": "probabilistic",                                 |  |*
*|  |      "param": 0.01                                            |  |*
*|  |    },                                                          |  |*
*|  |    "per_operation_strategies": [                              |  |*
*|  |      {                                                         |  |*
*|  |        "operation": "health_check",                          |  |*
*|  |        "type": "probabilistic",                               |  |*
*|  |        "param": 0.0001   // 0.01% - very frequent, boring   |  |*
*|  |      },                                                        |  |*
*|  |      {                                                         |  |*
*|  |        "operation": "checkout",                               |  |*
*|  |        "type": "probabilistic",                               |  |*
*|  |        "param": 0.1      // 10% - critical, want more data  |  |*
*|  |      },                                                        |  |*
*|  |      {                                                         |  |*
*|  |        "operation": "payment",                                |  |*
*|  |        "type": "const",                                       |  |*
*|  |        "param": 1        // 100% - always sample payments   |  |*
*|  |      }                                                         |  |*
*|  |    ]                                                           |  |*
*|  |  }                                                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  5. PRIORITY SAMPLING (Force Sample)                                  |*
*|  -----------------------------------                                   |*
*|                                                                         |*
*|  Application can force-sample important traces.                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  // In application code                                       |  |*
*|  |  span.SetTag("sampling.priority", 1)  // Force sample        |  |*
*|  |  span.SetTag("sampling.priority", 0)  // Force drop          |  |*
*|  |                                                                 |  |*
*|  |  Use cases:                                                    |  |*
*|  |  * Debug mode for specific user                              |  |*
*|  |  * A/B test analysis                                          |  |*
*|  |  * VIP customer traces                                        |  |*
*|  |                                                                 |  |*
*|  |  Example:                                                      |  |*
*|  |  def process_request(user_id):                                |  |*
*|  |      span = tracer.start_span("process_request")             |  |*
*|  |                                                                 |  |*
*|  |      if user_id in DEBUG_USERS:                               |  |*
*|  |          span.set_tag("sampling.priority", 1)                |  |*
*|  |                                                                 |  |*
*|  |      if is_vip_customer(user_id):                            |  |*
*|  |          span.set_tag("sampling.priority", 1)                |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4.3: SAMPLING IMPLEMENTATION
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  WHERE SAMPLING HAPPENS                                                |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  1. CLIENT/SDK (Head sampling)                                 |  |*
*|  |     |                                                          |  |*
*|  |     |  Decision: Sample or not?                               |  |*
*|  |     |  Propagate: Flag in trace context                       |  |*
*|  |     |                                                          |  |*
*|  |     v                                                          |  |*
*|  |  2. AGENT                                                       |  |*
*|  |     |                                                          |  |*
*|  |     |  Respects sampling decision from SDK                    |  |*
*|  |     |  May apply additional filtering                         |  |*
*|  |     |                                                          |  |*
*|  |     v                                                          |  |*
*|  |  3. COLLECTOR (Post-sampling / Tail sampling)                  |  |*
*|  |                                                                 |  |*
*|  |     Final decision point                                       |  |*
*|  |     Can override client decisions                             |  |*
*|  |     Can apply tail-based sampling                             |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  SAMPLING FLAGS IN TRACE CONTEXT                                      |*
*|                                                                         |*
*|  W3C Trace Context:                                                    |*
*|  traceparent: 00-{trace-id}-{span-id}-{flags}                        |*
*|                                                                         |*
*|  Flags byte:                                                           |*
*|  +---+---+---+---+---+---+---+---+                                   |*
*|  | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |                                   |*
*|  +---+---+---+---+---+---+---+---+                                   |*
*|                                |                                       |*
*|                                +-- Sampled flag (1 = sampled)        |*
*|                                                                         |*
*|  Example:                                                              |*
*|  traceparent: 00-abc123-def456-01  (sampled)                         |*
*|  traceparent: 00-abc123-def456-00  (not sampled)                     |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  CENTRALIZED SAMPLING CONFIGURATION                                   |*
*|                                                                         |*
*|  Jaeger supports remote sampling configuration:                       |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+   |  |*
*|  |  |           Sampling Config Service                       |   |  |*
*|  |  |  (in Collector or separate service)                     |   |  |*
*|  |  |                                                         |   |  |*
*|  |  |  GET /sampling?service=order-service                   |   |  |*
*|  |  |                                                         |   |  |*
*|  |  |  Response:                                             |   |  |*
*|  |  |  {                                                      |   |  |*
*|  |  |    "strategyType": "PROBABILISTIC",                   |   |  |*
*|  |  |    "probabilisticSampling": {                         |   |  |*
*|  |  |      "samplingRate": 0.01                             |   |  |*
*|  |  |    }                                                   |   |  |*
*|  |  |  }                                                      |   |  |*
*|  |  +------------------------+--------------------------------+   |  |*
*|  |                           |                                     |  |*
*|  |         +-----------------+-----------------+                  |  |*
*|  |         |                 |                 |                  |  |*
*|  |         v                 v                 v                  |  |*
*|  |  +-----------+     +-----------+     +-----------+           |  |*
*|  |  | Service A |     | Service B |     | Service C |           |  |*
*|  |  |   SDK     |     |   SDK     |     |   SDK     |           |  |*
*|  |  |           |     |           |     |           |           |  |*
*|  |  | Polls for |     | Polls for |     | Polls for |           |  |*
*|  |  | config    |     | config    |     | config    |           |  |*
*|  |  +-----------+     +-----------+     +-----------+           |  |*
*|  |                                                                 |  |*
*|  |  Benefits:                                                     |  |*
*|  |  * Change sampling without redeploying                        |  |*
*|  |  * Different rates per service/operation                     |  |*
*|  |  * React to incidents (increase sampling)                    |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4.4: COLLECTOR DEEP DIVE
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  COLLECTOR INTERNALS                                                   |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |             +-------------------------------------+            |  |*
*|  |             |         COLLECTOR                    |            |  |*
*|  |             |                                      |            |  |*
*|  |  Spans ---->|  1. RECEIVER                        |            |  |*
*|  |  (gRPC)     |     Parse protocol (Thrift/Proto)   |            |  |*
*|  |             |     Validate span structure          |            |  |*
*|  |             |                                      |            |  |*
*|  |             |          |                           |            |  |*
*|  |             |          v                           |            |  |*
*|  |             |                                      |            |  |*
*|  |             |  2. PRE-PROCESSING PIPELINE         |            |  |*
*|  |             |     * Enrich (add metadata)         |            |  |*
*|  |             |     * Sanitize (redact PII)         |            |  |*
*|  |             |     * Normalize (fix timestamps)    |            |  |*
*|  |             |                                      |            |  |*
*|  |             |          |                           |            |  |*
*|  |             |          v                           |            |  |*
*|  |             |                                      |            |  |*
*|  |             |  3. SAMPLING                         |            |  |*
*|  |             |     * Post-sampling rules           |            |  |*
*|  |             |     * Tail-based sampling           |            |  |*
*|  |             |                                      |            |  |*
*|  |             |          |                           |            |  |*
*|  |             |          v                           |            |  |*
*|  |             |                                      |            |  |*
*|  |             |  4. WRITER                           |            |  |*
*|  |             |     * Batch spans                   |            |  |*
*|  |             |     * Write to storage/Kafka        |            |  |*
*|  |             |                                      |            |  |*
*|  |             +-------------------------------------+            |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  PROCESSING PIPELINE (OpenTelemetry Collector)                        |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  receivers:                                                    |  |*
*|  |    otlp:                                                       |  |*
*|  |      protocols:                                                |  |*
*|  |        grpc:                                                   |  |*
*|  |          endpoint: 0.0.0.0:4317                               |  |*
*|  |        http:                                                   |  |*
*|  |          endpoint: 0.0.0.0:4318                               |  |*
*|  |    jaeger:                                                     |  |*
*|  |      protocols:                                                |  |*
*|  |        grpc:                                                   |  |*
*|  |          endpoint: 0.0.0.0:14250                              |  |*
*|  |                                                                 |  |*
*|  |  processors:                                                   |  |*
*|  |    batch:                                                      |  |*
*|  |      timeout: 1s                                               |  |*
*|  |      send_batch_size: 1024                                    |  |*
*|  |                                                                 |  |*
*|  |    memory_limiter:                                            |  |*
*|  |      check_interval: 1s                                       |  |*
*|  |      limit_mib: 2000                                          |  |*
*|  |      spike_limit_mib: 400                                     |  |*
*|  |                                                                 |  |*
*|  |    attributes:                                                 |  |*
*|  |      actions:                                                  |  |*
*|  |        - key: environment                                     |  |*
*|  |          value: production                                    |  |*
*|  |          action: insert                                       |  |*
*|  |        - key: db.password                                     |  |*
*|  |          action: delete    # Redact sensitive data           |  |*
*|  |                                                                 |  |*
*|  |    probabilistic_sampler:                                     |  |*
*|  |      sampling_percentage: 10                                  |  |*
*|  |                                                                 |  |*
*|  |  exporters:                                                    |  |*
*|  |    otlp:                                                       |  |*
*|  |      endpoint: tempo:4317                                     |  |*
*|  |    kafka:                                                      |  |*
*|  |      brokers:                                                  |  |*
*|  |        - kafka:9092                                           |  |*
*|  |      topic: jaeger-spans                                      |  |*
*|  |                                                                 |  |*
*|  |  service:                                                      |  |*
*|  |    pipelines:                                                  |  |*
*|  |      traces:                                                   |  |*
*|  |        receivers: [otlp, jaeger]                             |  |*
*|  |        processors: [memory_limiter, batch, attributes]       |  |*
*|  |        exporters: [otlp, kafka]                              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  COLLECTOR SCALING                                                     |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  CAPACITY PLANNING                                             |  |*
*|  |                                                                 |  |*
*|  |  Single collector capacity:                                   |  |*
*|  |  * ~50,000-100,000 spans/second (depends on span size)       |  |*
*|  |  * 2-4 CPU cores                                              |  |*
*|  |  * 2-4 GB RAM                                                 |  |*
*|  |                                                                 |  |*
*|  |  Formula:                                                      |  |*
*|  |  num_collectors = (peak_spans_per_second / 50000) * 1.5      |  |*
*|  |                                                                 |  |*
*|  |  Example: 200,000 spans/second                                |  |*
*|  |  num_collectors = (200000 / 50000) * 1.5 = 6 collectors      |  |*
*|  |                                                                 |  |*
*|  |  ------------------------------------------------------------  |  |*
*|  |                                                                 |  |*
*|  |  DEPLOYMENT                                                    |  |*
*|  |                                                                 |  |*
*|  |                    Load Balancer (L4)                         |  |*
*|  |                          |                                     |  |*
*|  |     +--------------------+--------------------+               |  |*
*|  |     |                    |                    |               |  |*
*|  |     v                    v                    v               |  |*
*|  |  +--------+          +--------+          +--------+          |  |*
*|  |  |Collector|         |Collector|         |Collector|         |  |*
*|  |  |   1    |          |   2    |          |   3    |          |  |*
*|  |  +--------+          +--------+          +--------+          |  |*
*|  |     |                    |                    |               |  |*
*|  |     +--------------------+--------------------+               |  |*
*|  |                          |                                     |  |*
*|  |                          v                                     |  |*
*|  |                    Kafka / Storage                            |  |*
*|  |                                                                 |  |*
*|  |  Kubernetes HPA:                                              |  |*
*|  |  - Scale on CPU utilization (target: 70%)                    |  |*
*|  |  - Scale on memory utilization (target: 80%)                 |  |*
*|  |  - Min replicas: 3, Max replicas: 20                         |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

SECTION 4.5: TAIL-BASED SAMPLING
## +-------------------------------------------------------------------------+
*|                                                                         |*
*|  TAIL-BASED SAMPLING ARCHITECTURE                                     |*
*|                                                                         |*
*|  Make sampling decision AFTER seeing all spans in a trace.           |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  +---------------------------------------------------------+   |  |*
*|  |  |                 TAIL SAMPLER                            |   |  |*
*|  |  |                                                         |   |  |*
*|  |  |  1. COLLECT ALL SPANS                                  |   |  |*
*|  |  |     Buffer spans in memory by trace_id                 |   |  |*
*|  |  |                                                         |   |  |*
*|  |  |     trace_buffer = {                                   |   |  |*
*|  |  |       "trace_123": [span1, span2, span3],             |   |  |*
*|  |  |       "trace_456": [span1, span2],                    |   |  |*
*|  |  |       ...                                              |   |  |*
*|  |  |     }                                                   |   |  |*
*|  |  |                                                         |   |  |*
*|  |  |  2. WAIT FOR TRACE COMPLETION                          |   |  |*
*|  |  |     How to know trace is complete?                     |   |  |*
*|  |  |     * Timeout (no new spans for 30s)                  |   |  |*
*|  |  |     * Root span ended                                  |   |  |*
*|  |  |     * Expected span count reached                     |   |  |*
*|  |  |                                                         |   |  |*
*|  |  |  3. EVALUATE SAMPLING POLICIES                         |   |  |*
*|  |  |     * Has error? > SAMPLE                             |   |  |*
*|  |  |     * Duration > 5s? > SAMPLE                         |   |  |*
*|  |  |     * Status code 5xx? > SAMPLE                       |   |  |*
*|  |  |     * Random 1%? > SAMPLE                             |   |  |*
*|  |  |                                                         |   |  |*
*|  |  |  4. EMIT OR DROP                                        |   |  |*
*|  |  |     If sampled: emit all spans to storage             |   |  |*
*|  |  |     If not: discard                                    |   |  |*
*|  |  |                                                         |   |  |*
*|  |  +---------------------------------------------------------+   |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  IMPLEMENTATION CHALLENGES                                            |*
*|                                                                         |*
*|  CHALLENGE 1: Distributed Traces                                      |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Spans for same trace arrive at different collectors!         |  |*
*|  |                                                                 |  |*
*|  |  Collector 1: [span A, span C]  -+                            |  |*
*|  |  Collector 2: [span B]          -+-> Same trace_id           |  |*
*|  |  Collector 3: [span D]          -+                            |  |*
*|  |                                                                 |  |*
*|  |  SOLUTION: Consistent hashing                                 |  |*
*|  |  Route all spans with same trace_id to same collector        |  |*
*|  |                                                                 |  |*
*|  |  Load Balancer: hash(trace_id) % num_collectors              |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  CHALLENGE 2: Memory Pressure                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  Buffering traces requires significant memory:                |  |*
*|  |  * 50,000 traces/second                                       |  |*
*|  |  * 30 second buffer window                                    |  |*
*|  |  * 20 spans/trace × 500 bytes                                |  |*
*|  |  = 15 GB memory just for buffering!                          |  |*
*|  |                                                                 |  |*
*|  |  SOLUTIONS:                                                    |  |*
*|  |  * Shorter buffer window (10s)                               |  |*
*|  |  * Pre-filter obvious drops                                  |  |*
*|  |  * Spill to disk if needed                                   |  |*
*|  |  * Limit max traces in buffer                                |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  CHALLENGE 3: Trace Completion Detection                              |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  When is a trace "complete"?                                  |  |*
*|  |                                                                 |  |*
*|  |  STRATEGY 1: Timeout-based                                    |  |*
*|  |  No new spans for X seconds > consider complete              |  |*
*|  |  Pro: Simple                                                   |  |*
*|  |  Con: Slow, delays sampling decision                         |  |*
*|  |                                                                 |  |*
*|  |  STRATEGY 2: Root span ended                                  |  |*
*|  |  Root span has duration set > trace complete                 |  |*
*|  |  Pro: Fast decision                                           |  |*
*|  |  Con: May miss late-arriving child spans                     |  |*
*|  |                                                                 |  |*
*|  |  STRATEGY 3: Expected span count                              |  |*
*|  |  Application hints: "this trace will have N spans"           |  |*
*|  |  Pro: Accurate                                                |  |*
*|  |  Con: Requires application changes                           |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*|  ==================================================================== |*
*|                                                                         |*
*|  OTEL COLLECTOR TAIL SAMPLING CONFIG                                  |*
*|                                                                         |*
*|  +-----------------------------------------------------------------+  |*
*|  |                                                                 |  |*
*|  |  processors:                                                   |  |*
*|  |    tail_sampling:                                             |  |*
*|  |      decision_wait: 30s      # Wait time for trace           |  |*
*|  |      num_traces: 100000      # Max traces in memory          |  |*
*|  |      expected_new_traces_per_sec: 10000                      |  |*
*|  |                                                                 |  |*
*|  |      policies:                                                 |  |*
*|  |        # Always sample errors                                 |  |*
*|  |        - name: errors                                         |  |*
*|  |          type: status_code                                    |  |*
*|  |          status_code:                                         |  |*
*|  |            status_codes: [ERROR]                             |  |*
*|  |                                                                 |  |*
*|  |        # Sample slow traces (> 5 seconds)                    |  |*
*|  |        - name: slow-traces                                    |  |*
*|  |          type: latency                                        |  |*
*|  |          latency:                                             |  |*
*|  |            threshold_ms: 5000                                 |  |*
*|  |                                                                 |  |*
*|  |        # Sample traces with specific attribute                |  |*
*|  |        - name: debug-traces                                   |  |*
*|  |          type: string_attribute                               |  |*
*|  |          string_attribute:                                    |  |*
*|  |            key: debug                                         |  |*
*|  |            values: ["true"]                                  |  |*
*|  |                                                                 |  |*
*|  |        # Random sample 1% of remaining                       |  |*
*|  |        - name: random-sample                                  |  |*
*|  |          type: probabilistic                                  |  |*
*|  |          probabilistic:                                       |  |*
*|  |            sampling_percentage: 1                            |  |*
*|  |                                                                 |  |*
*|  |      # Composite policy (AND conditions)                     |  |*
*|  |        - name: high-value-errors                              |  |*
*|  |          type: and                                            |  |*
*|  |          and:                                                  |  |*
*|  |            and_sub_policy:                                    |  |*
*|  |              - name: error-check                              |  |*
*|  |                type: status_code                              |  |*
*|  |                status_code:                                   |  |*
*|  |                  status_codes: [ERROR]                       |  |*
*|  |              - name: service-check                            |  |*
*|  |                type: string_attribute                         |  |*
*|  |                string_attribute:                              |  |*
*|  |                  key: service.name                            |  |*
*|  |                  values: ["payment-service"]                 |  |*
*|  |                                                                 |  |*
*|  +-----------------------------------------------------------------+  |*
*|                                                                         |*
*+-------------------------------------------------------------------------+*

END OF CHAPTER 4
