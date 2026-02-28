# CHAPTER 25: ML SYSTEM DESIGN
*Designing Machine Learning Systems for Production — Interview Ready*

ML system design interviews test whether you can build the **infrastructure around the model**,
not the model itself. You won't be asked to derive gradients — you'll be asked how to serve
predictions at 100K QPS with <50ms latency.

## SECTION 25.1: ML SYSTEM DESIGN FUNDAMENTALS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ML SYSTEM ≠ ML MODEL                                                   |
|  ======================                                                 |
|                                                                         |
|  In production, the model is ~5% of the code.                           |
|  The rest is: data pipelines, feature engineering, serving infra,       |
|  monitoring, retraining, A/B testing, and operationalization.           |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Data        Feature       Model        Model        Prediction  |   |
|  |  Collection  Engineering   Training     Serving      Monitoring  |   |
|  |  (30%)       (25%)         (10%)        (20%)        (15%)       |   |
|  |                                                                   |  |
|  |  [Data] --> [Features] --> [Train] --> [Serve] --> [Monitor]      |  |
|  |    ^                                                    |         |  |
|  |    +----------------------------------------------------+         |  |
|  |              Feedback loop (retrain on new data)                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ONLINE vs OFFLINE — THE CORE DISTINCTION                               |
|  =========================================                              |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |              | Offline (Batch)        | Online (Real-time)        |  |
|  |--------------|------------------------|--------------------------|   |
|  | When         | Periodically (hourly/  | At request time           |  |
|  |              | daily)                 |                           |  |
|  | Latency      | Minutes to hours       | <50ms (p99)              |   |
|  | Compute      | Large cluster (Spark,  | Low-latency servers      |   |
|  |              | GPU training)          | (GPU inference)          |   |
|  | Data         | Full historical data   | Real-time features +     |   |
|  |              |                        | pre-computed features    |   |
|  | Example      | Train model, compute   | Score this user NOW,     |   |
|  |              | recommendations for    | rank these 50 items      |   |
|  |              | all users              |                          |   |
|  |--------------|------------------------|--------------------------|   |
|  | Storage      | Data lake (S3/GCS)     | Feature store (Redis)    |   |
|  | Framework    | Spark, Airflow, Kubeflow| TF Serving, Triton,     |   |
|  |              |                        | custom gRPC server       |   |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  MOST SYSTEMS USE BOTH:                                                 |
|  * Offline: train model + pre-compute heavy features                    |
|  * Online: real-time scoring with fresh features                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ML SYSTEM DESIGN INTERVIEW FRAMEWORK                                   |
|  =====================================                                  |
|                                                                         |
|  Use this structure for ANY ML design question:                         |
|                                                                         |
|  1. CLARIFY REQUIREMENTS                                                |
|     - What are we predicting/ranking/recommending?                      |
|     - What is the business metric? (CTR, revenue, engagement)           |
|     - Latency requirement? (real-time vs batch)                         |
|     - Scale? (QPS, number of items, users)                              |
|                                                                         |
|  2. DATA                                                                |
|     - What data is available? (logs, user actions, content metadata)    |
|     - How much? How fresh does it need to be?                           |
|     - Labels: explicit (ratings) vs implicit (clicks, time spent)       |
|     - Data pipeline: batch (Spark) vs streaming (Kafka + Flink)         |
|                                                                         |
|  3. FEATURES                                                            |
|     - User features (demographics, history, preferences)                |
|     - Item features (metadata, popularity, freshness)                   |
|     - Context features (time, device, location)                         |
|     - Cross features (user-item interactions)                           |
|     - Pre-computed (offline) vs real-time (online)                      |
|                                                                         |
|  4. MODEL                                                               |
|     - Start simple (logistic regression / gradient boosted trees)       |
|     - Then discuss deep learning if relevant                            |
|     - Multi-stage: candidate generation + ranking                       |
|     - Loss function tied to business metric                             |
|                                                                         |
|  5. SERVING                                                             |
|     - How to serve predictions at scale?                                |
|     - Pre-compute vs real-time inference                                |
|     - Caching, batching, model optimization                             |
|                                                                         |
|  6. MONITORING & ITERATION                                              |
|     - Online metrics (A/B test) vs offline metrics (AUC, NDCG)          |
|     - Model drift detection                                             |
|     - Feedback loop: log predictions, retrain                           |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 25.2: DATA PIPELINE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ML DATA PIPELINE                                                       |
|  =================                                                      |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  User Actions   App Logs    Content DB   External APIs            |  |
|  |       |            |            |              |                  |  |
|  |       v            v            v              v                  |  |
|  |  +---------------------------------------------------+           |   |
|  |  |          Kafka (Event Streaming)                   |           |  |
|  |  +---------------------------------------------------+           |   |
|  |       |                              |                            |  |
|  |       v                              v                            |  |
|  |  +-----------------+         +------------------+                 |  |
|  |  | Batch Pipeline  |         | Stream Pipeline  |                 |  |
|  |  | (Spark/Airflow) |         | (Flink/Kafka     |                 |  |
|  |  |                 |         |  Streams)        |                 |  |
|  |  +-----------------+         +------------------+                 |  |
|  |       |                              |                            |  |
|  |       v                              v                            |  |
|  |  +-----------------+         +------------------+                 |  |
|  |  | Data Warehouse  |         | Feature Store    |                 |  |
|  |  | (S3/BigQuery)   |         | (Redis/DynamoDB) |                 |  |
|  |  +-----------------+         +------------------+                 |  |
|  |       |                              |                            |  |
|  |       v                              v                            |  |
|  |  Model Training              Online Serving                       |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  BATCH PIPELINE (Spark + Airflow):                                      |
|  * Daily/hourly jobs                                                    |
|  * Process full history                                                 |
|  * Generate training data                                               |
|  * Compute aggregate features (user's avg order value last 30 days)     |
|  * Tools: Apache Spark, Airflow, dbt, Databricks                        |
|                                                                         |
|  STREAM PIPELINE (Flink / Kafka Streams):                               |
|  * Real-time event processing                                           |
|  * Compute features as events arrive                                    |
|  * Update feature store immediately                                     |
|  * Examples: "user clicked 3 items in last 5 min" (session feature)     |
|  * Tools: Apache Flink, Kafka Streams, Spark Streaming                  |
|                                                                         |
|  DATA QUALITY CHECKS:                                                   |
|  * Schema validation (missing fields, wrong types)                      |
|  * Distribution drift (feature values shifted from training)            |
|  * Freshness monitoring (is data pipeline delayed?)                     |
|  * Volume checks (did we get expected number of events?)                |
|  * Tools: Great Expectations, Deequ, Monte Carlo                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 25.3: FEATURE STORE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FEATURE STORE                                                          |
|  ==============                                                         |
|                                                                         |
|  Central repository of ML features, shared across teams & models.       |
|  Solves: feature duplication, training-serving skew, freshness.         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  WHY FEATURE STORE:                                               |  |
|  |                                                                   |  |
|  |  WITHOUT:                                                         |  |
|  |  Team A computes "user_avg_spend" in Python for training          |  |
|  |  Team B re-computes it in Java for serving                        |  |
|  |  Slight difference -> TRAINING-SERVING SKEW -> bad predictions   |   |
|  |                                                                   |  |
|  |  WITH FEATURE STORE:                                              |  |
|  |  Feature computed ONCE, stored centrally.                         |  |
|  |  Training reads from offline store (S3/Hive).                    |   |
|  |  Serving reads from online store (Redis/DynamoDB).                |  |
|  |  Same value. No skew.                                             |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  ARCHITECTURE:                                                          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Feature Pipelines (Spark/Flink)                                  |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  +---------------------+                                         |   |
|  |  |   Feature Store     |                                         |   |
|  |  |                     |                                         |   |
|  |  |  Offline Store      |  <-- Training reads (batch, S3/Hive)   |    |
|  |  |  (S3/BigQuery)      |                                         |   |
|  |  |                     |                                         |   |
|  |  |  Online Store       |  <-- Serving reads (real-time, Redis)  |    |
|  |  |  (Redis/DynamoDB)   |                                         |   |
|  |  |                     |                                         |   |
|  |  |  Feature Registry   |  <-- Metadata (name, owner, schema)    |    |
|  |  +---------------------+                                         |   |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  FEATURE TYPES:                                                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Type           | Example                    | Freshness           |  |
|  |----------------|----------------------------|---------------------|  |
|  | Static         | user age, country           | Days / never changes| |
|  | Batch          | user's 30-day avg spend     | Hourly / daily      | |
|  | Near real-time | items viewed in last 5 min  | Seconds             | |
|  | Real-time      | current cart total           | Milliseconds        ||
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  TOOLS: Feast (open-source), Tecton, Hopsworks, Vertex AI Feature       |
|  Store (GCP), SageMaker Feature Store (AWS)                             |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 25.4: MODEL TRAINING PIPELINE

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MODEL TRAINING PIPELINE                                                |
|  ========================                                               |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Training Data     Feature       Model         Model     Model   |   |
|  |  (S3/BigQuery) --> Store    -->  Training  --> Evaluation Registry|  |
|  |                    (offline)     (GPU cluster)  (metrics)  (store)|  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  TRAINING DATA PREPARATION:                                             |
|                                                                         |
|  * Join labels with features at point-in-time                           |
|    CRITICAL: Use features as they were WHEN the event happened.         |
|    Not current features! This is called POINT-IN-TIME JOIN.             |
|                                                                         |
|    BAD: User clicked ad on Jan 1. Use user features from Feb 1.         |
|    GOOD: User clicked ad on Jan 1. Use user features from Jan 1.        |
|                                                                         |
|  * Train/validation/test split (time-based, NOT random for time data)   |
|  * Handle class imbalance (fraud: 0.1% positive, 99.9% negative)        |
|    Techniques: oversampling, undersampling, class weights, SMOTE        |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  TRAINING INFRASTRUCTURE:                                               |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Scale            | Approach                                       |  |
|  |------------------|------------------------------------------------|  |
|  | Small (<10 GB)   | Single GPU machine (SageMaker, Vertex AI)      |  |
|  | Medium (10-1 TB) | Multi-GPU (data parallelism, Horovod)          |  |
|  | Large (>1 TB)    | Distributed training (parameter servers,        | |
|  |                  | PyTorch DDP, DeepSpeed, FSDP)                  |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  MODEL REGISTRY:                                                        |
|                                                                         |
|  Version control for models (like Git for code).                        |
|                                                                         |
|  Stores: model artifact, metrics, training config, data snapshot ID     |
|                                                                         |
|  model_v1: AUC=0.82, trained on data_2025_01, prod since Feb 1          |
|  model_v2: AUC=0.85, trained on data_2025_02, canary testing            |
|  model_v3: AUC=0.79, trained on data_2025_02, REJECTED (regression)     |
|                                                                         |
|  Tools: MLflow, Weights & Biases, SageMaker Model Registry,             |
|  Vertex AI Model Registry, custom (S3 + metadata DB)                    |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  RETRAINING STRATEGIES:                                                 |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Strategy         | When                     | Example              | |
|  |------------------|--------------------------|----------------------| |
|  | Scheduled        | Fixed interval (daily/   | Recommendation model | |
|  |                  | weekly)                  | retrained daily      | |
|  | Triggered        | When performance drops   | Fraud model: retrain | |
|  |                  | below threshold          | when precision < 90% | |
|  | Continuous       | Incremental learning on  | Ad click prediction  | |
|  |                  | streaming data           | (always learning)    | |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 25.5: MODEL SERVING

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MODEL SERVING PATTERNS                                                 |
|  =======================                                                |
|                                                                         |
|  PATTERN 1: PRE-COMPUTED (Batch Prediction)                             |
|                                                                         |
|  Compute predictions for all users/items offline. Store in DB/cache.    |
|  At request time: just look up the pre-computed result.                 |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  [Nightly Job]                                                    |  |
|  |  For each user: compute top-100 recommendations                   |  |
|  |  Store: Redis hash per user                                       |  |
|  |    recs:{user_id} = ["item_1", "item_2", ..., "item_100"]        |   |
|  |                                                                   |  |
|  |  [Request Time]                                                   |  |
|  |  GET recs:{user_id} --> return instantly (<1ms)                   |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  PROS: Lowest latency, simplest serving, no GPU at request time         |
|  CONS: Stale (computed hours ago), can't use real-time features,        |
|        storage cost (must compute for ALL users)                        |
|                                                                         |
|  BEST FOR: Email recommendations, homepage "for you" (if staleness      |
|  is acceptable), candidate generation stage                             |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  PATTERN 2: REAL-TIME INFERENCE                                         |
|                                                                         |
|  Model runs at request time. Fresh predictions with latest features.    |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Client --> API Gateway --> Model Server (TF Serving / Triton)    |  |
|  |                                |                                  |  |
|  |                         Feature Store (Redis)                     |  |
|  |                                |                                  |  |
|  |                         [Fetch features]                          |  |
|  |                         [Run inference]                           |  |
|  |                         [Return prediction]                       |  |
|  |                                                                   |  |
|  |  Latency budget: ~50ms total                                     |   |
|  |    Feature fetch: ~5ms (Redis)                                   |   |
|  |    Model inference: ~20-40ms (GPU/CPU)                           |   |
|  |    Network: ~5ms                                                  |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  PROS: Fresh, uses real-time features, personalized per-request         |
|  CONS: Higher latency, GPU cost, more complex infra                     |
|                                                                         |
|  BEST FOR: Search ranking, ad prediction, fraud detection,              |
|  real-time pricing                                                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  PATTERN 3: HYBRID (most common in production)                          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  Stage 1: CANDIDATE GENERATION (offline or lightweight online)    |  |
|  |  --------------------------------------------------------        |   |
|  |  From 10M items -> select 1000 candidates                        |   |
|  |  Approach: pre-computed (ANN index), simple heuristics,           |  |
|  |  or lightweight embedding similarity                              |  |
|  |  Latency: <10ms (just an index lookup)                           |   |
|  |                                                                   |  |
|  |  Stage 2: RANKING (online, heavier model)                        |   |
|  |  --------------------------------------------------------        |   |
|  |  From 1000 candidates -> rank by relevance score                  |  |
|  |  Uses: user features + item features + context + real-time signals|  |
|  |  Model: deep neural network or gradient boosted tree              |  |
|  |  Latency: ~30ms for scoring 1000 items                           |   |
|  |                                                                   |  |
|  |  Stage 3: RE-RANKING (business rules)                            |   |
|  |  --------------------------------------------------------        |   |
|  |  Apply filters: already seen, out of stock, diversity, freshness |   |
|  |  Boost: sponsored content, new items, editorial picks             |  |
|  |  Latency: ~5ms (simple rules)                                    |   |
|  |                                                                   |  |
|  |  10M items --> [1000 candidates] --> [ranked 50] --> [show 20]   |   |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  THIS IS THE ANSWER FOR MOST ML DESIGN INTERVIEWS.                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  MODEL SERVING INFRASTRUCTURE:                                          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Tool              | Type       | Best For                         |  |
|  |-------------------|------------|----------------------------------|  |
|  | TF Serving        | gRPC/REST  | TensorFlow models, Google-scale |   |
|  | Triton (NVIDIA)   | gRPC/REST  | Multi-framework, GPU batching   |   |
|  | TorchServe        | gRPC/REST  | PyTorch models                  |   |
|  | ONNX Runtime      | Library    | Cross-framework, edge/mobile    |   |
|  | vLLM              | gRPC/REST  | LLM serving (batched inference) |   |
|  | SageMaker Endpt   | AWS managed| Don't want to manage infra      |   |
|  | Vertex AI Endpt   | GCP managed| Same, GCP ecosystem             |   |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  OPTIMIZATION TECHNIQUES:                                               |
|  * Model quantization (FP32 -> INT8): 2-4x faster, slight accuracy      |
|    loss                                                                 |
|  * Model distillation: train smaller model to mimic large one           |
|  * Batching: batch multiple inference requests (Triton dynamic batch)   |
|  * Caching: cache predictions for same input features                   |
|  * Model pruning: remove low-impact weights (sparse inference)          |
|  * ONNX export: optimize computation graph for target hardware          |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 25.6: EMBEDDING AND APPROXIMATE NEAREST NEIGHBOR (ANN)

```
+-------------------------------------------------------------------------+
|                                                                         |
|  EMBEDDINGS + ANN SEARCH                                                |
|  ========================                                               |
|                                                                         |
|  Embedding: represent users/items as dense vectors (128-512 dims).      |
|  Similar items are CLOSE in vector space.                               |
|                                                                         |
|  TRAINING EMBEDDINGS:                                                   |
|  * Two-tower model: user tower + item tower -> dot product = score      |
|  * Trained on: user-item interactions (clicks, purchases, watches)      |
|  * User embedding captures preferences                                  |
|  * Item embedding captures content/properties                           |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  User Tower          Item Tower                                   |  |
|  |  [user features] --> [user embedding]    [item features]          |  |
|  |                          |               --> [item embedding]     |  |
|  |                          |                        |               |  |
|  |                          +--- dot product --------+               |  |
|  |                                  |                                |  |
|  |                           similarity score                        |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  ANN SEARCH (Approximate Nearest Neighbor):                             |
|                                                                         |
|  Problem: find 100 most similar items from 100M items.                  |
|  Brute force: compare with ALL 100M -> too slow.                        |
|  ANN: find APPROXIMATE top-100 in <10ms. 95%+ recall.                   |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Algorithm    | How                       | Used By                |  |
|  |--------------|---------------------------|------------------------|  |
|  | HNSW         | Hierarchical graph search | Pinecone, Weaviate,    |  |
|  |              | Best recall/speed tradeoff| pgvector, Redis        |  |
|  | IVF          | Cluster then search within| FAISS (Meta)           |  |
|  |              | nearby clusters           |                        |  |
|  | ScaNN        | Learned quantization      | Google (Vertex AI)     |  |
|  | LSH          | Hash similar items to same| Older, simple          |  |
|  |              | bucket                    |                        |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  VECTOR DATABASES:                                                      |
|  +-------------------------------------------------------------------+  |
|  | Tool        | Type          | Notes                                | |
|  |-------------|---------------|--------------------------------------| |
|  | FAISS       | Library (Meta)| In-memory, very fast, no DB features | |
|  | Pinecone    | Managed SaaS  | Easiest, serverless, expensive       | |
|  | Weaviate    | Open source   | Full DB features + hybrid search     | |
|  | Milvus      | Open source   | Distributed, high scale              | |
|  | pgvector    | Postgres ext  | Good enough for <10M vectors         | |
|  | Redis (VSS) | Redis module  | If already using Redis               | |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  WHEN TO USE:                                                           |
|  * Recommendation: find similar items / users with similar taste        |
|  * Search: semantic search ("comfy shoes" matches "sneakers")           |
|  * Ads: match ad to user interest                                       |
|  * Content: "more like this" feature                                    |
|  * RAG: retrieve relevant documents for LLM context                     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 25.7: MONITORING, A/B TESTING, AND FEEDBACK LOOPS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ML MONITORING                                                          |
|  ==============                                                         |
|                                                                         |
|  ML models DEGRADE over time. The world changes, but the model          |
|  was trained on old data. This is called MODEL DRIFT.                   |
|                                                                         |
|  TYPES OF DRIFT:                                                        |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Type             | What Changed           | Example                | |
|  |------------------|------------------------|------------------------| |
|  | Data drift       | Input feature           | Users' shopping habits ||
|  |                  | distribution changed    | changed post-COVID     ||
|  | Concept drift    | Relationship between    | "Good" credit score    ||
|  |                  | features and label      | threshold shifted      ||
|  |                  | changed                 | during recession       ||
|  | Label drift      | Distribution of labels  | Fraud rate spiked from ||
|  |                  | changed                 | 0.1% to 2%            | |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  WHAT TO MONITOR:                                                       |
|                                                                         |
|  1. MODEL PERFORMANCE METRICS                                           |
|     * Offline: AUC, precision, recall, NDCG, MAP                        |
|     * Online: CTR, conversion rate, revenue per session                 |
|     * Compare: current vs baseline (last week, last model)              |
|                                                                         |
|  2. PREDICTION DISTRIBUTION                                             |
|     * Score distribution shift (model outputting more 0.5s than 0.9s)   |
|     * Prediction volume anomalies (sudden drop = pipeline broken)       |
|                                                                         |
|  3. FEATURE DISTRIBUTION                                                |
|     * PSI (Population Stability Index) for each feature                 |
|     * Null rate, out-of-range values, new categories                    |
|                                                                         |
|  4. INFRASTRUCTURE METRICS                                              |
|     * Inference latency (p50, p95, p99)                                 |
|     * Throughput (QPS), GPU utilization, memory usage                   |
|     * Feature store freshness (is data stale?)                          |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  A/B TESTING FOR ML                                                     |
|  ==================                                                     |
|                                                                         |
|  NEVER deploy a new model to all users at once.                         |
|                                                                         |
|  ROLLOUT STRATEGY:                                                      |
|                                                                         |
|  1. OFFLINE EVALUATION                                                  |
|     Run new model on historical data.                                   |
|     Compare metrics: AUC, NDCG (new model must be better).              |
|     If worse -> stop. Don't waste time on A/B test.                     |
|                                                                         |
|  2. SHADOW MODE (logging only)                                          |
|     Run new model in parallel, log predictions, don't serve them.       |
|     Compare predictions with production model.                          |
|     Check: latency, errors, distribution of scores.                     |
|                                                                         |
|  3. A/B TEST (online experiment)                                        |
|     5% of traffic -> new model                                          |
|     95% of traffic -> current model (control)                           |
|     Measure business metrics (CTR, revenue, engagement).                |
|     Run for 1-2 weeks for statistical significance.                     |
|                                                                         |
|  4. RAMP UP                                                             |
|     5% -> 10% -> 25% -> 50% -> 100%                                     |
|     Monitor at each stage. Rollback if regression.                      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  FEEDBACK LOOP:                                                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  [Users interact] --> [Log: impression, click, purchase]          |  |
|  |         |                                                         |  |
|  |         v                                                         |  |
|  |  [Kafka event stream]                                             |  |
|  |         |                                                         |  |
|  |         +--> [Feature pipeline] --> Update feature store          |  |
|  |         |                                                         |  |
|  |         +--> [Training data] --> Retrain model (daily/weekly)     |  |
|  |         |                                                         |  |
|  |         +--> [Monitoring] --> Alert if metrics degrade            |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  CAUTION: Feedback loops can cause problems:                            |
|  * Popularity bias: popular items get more clicks -> model promotes     |
|    them more -> they get even more clicks (rich get richer)             |
|  * Filter bubble: model shows user only what they liked before ->       |
|    user never discovers new interests                                   |
|  * Fix: exploration (epsilon-greedy), diversity injection               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 25.8: COMMON ML SYSTEM DESIGN INTERVIEWS

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TOP ML SYSTEM DESIGN INTERVIEW QUESTIONS                               |
|  =========================================                              |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Question               | Key Components                           |  |
|  |------------------------|------------------------------------------|  |
|  | Recommendation System  | Two-tower, ANN, candidate gen + ranker,  |  |
|  | (Netflix, YouTube)     | feature store, cold start, diversity      | |
|  |------------------------|------------------------------------------|  |
|  | Search Ranking         | Query understanding, retrieval (BM25 +   |  |
|  | (Google, Amazon)       | semantic), L2 ranker, click model        |  |
|  |------------------------|------------------------------------------|  |
|  | Ad Click Prediction    | CTR model (deep+wide), real-time         |  |
|  | (Meta, Google)         | features, bid optimization, budget pacing | |
|  |------------------------|------------------------------------------|  |
|  | News Feed Ranking      | Multi-objective (engagement + quality),   | |
|  | (Facebook, Twitter)    | re-ranking for diversity, freshness      |  |
|  |------------------------|------------------------------------------|  |
|  | Fraud Detection        | Imbalanced data, real-time inference,     | |
|  | (Stripe, PayPal)       | graph features, explanation, low latency |  |
|  |------------------------|------------------------------------------|  |
|  | Content Moderation     | Multi-modal (text + image + video),       | |
|  | (YouTube, TikTok)      | human-in-the-loop, edge cases, appeal    |  |
|  |------------------------|------------------------------------------|  |
|  | Autocomplete /         | Trie + ML ranking, personalization,       | |
|  | Typeahead              | trending queries, latency < 100ms        |  |
|  |------------------------|------------------------------------------|  |
|  | Similar Items          | Item embeddings, ANN search, content     |  |
|  | ("More Like This")     | vs collaborative filtering               |  |
|  |------------------------|------------------------------------------|  |
|  | ETA Prediction         | Graph features + real-time traffic,       | |
|  | (Uber, Google Maps)    | historical patterns, road segments       |  |
|  |------------------------|------------------------------------------|  |
|  | Notification           | Timing model (when to send), relevance   |  |
|  | Optimization           | model (what to send), fatigue model      |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

```
+-------------------------------------------------------------------------+
|                                                                         |
|  EXAMPLE: RECOMMENDATION SYSTEM (YouTube / Netflix)                     |
|  ===================================================                    |
|                                                                         |
|  REQUIREMENTS:                                                          |
|  * 1B users, 100M items, <100ms latency, personalized                   |
|  * Metric: watch time (YouTube) / completion rate (Netflix)             |
|                                                                         |
|  ARCHITECTURE:                                                          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                                                                   |  |
|  |  User Request                                                     |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  CANDIDATE GENERATION (recall stage)                              |  |
|  |  100M items -> 1000 candidates                                    |  |
|  |  * ANN: user embedding -> nearest item embeddings (HNSW/FAISS)   |   |
|  |  * Collaborative filtering: users-who-watched-X-also-watched     |   |
|  |  * Content-based: similar genre, director, actors                 |  |
|  |  * Trending: popular in user's region                             |  |
|  |  Latency: ~10ms                                                   |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  RANKING (precision stage)                                        |  |
|  |  1000 candidates -> scored and ranked                             |  |
|  |  * Deep model: user features + item features + context            |  |
|  |  * Features: watch history, time of day, device, freshness        |  |
|  |  * Output: P(click), P(watch >50%), expected watch time           |  |
|  |  Latency: ~30ms (batch score 1000 items on GPU)                  |   |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  RE-RANKING (business logic)                                      |  |
|  |  * Remove already watched                                         |  |
|  |  * Diversity: don't show 10 action movies in a row                |  |
|  |  * Freshness boost for new releases                               |  |
|  |  * Sponsored content insertion                                    |  |
|  |  * Parental controls, region restrictions                         |  |
|  |  Latency: ~5ms                                                    |  |
|  |       |                                                           |  |
|  |       v                                                           |  |
|  |  Return top 20-50 items to client                                 |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  COLD START PROBLEM:                                                    |
|  * New user: show popular / trending / ask preferences on signup        |
|  * New item: use content features (genre, actors, description)          |
|    Gradually blend in collaborative signals as interactions grow.       |
|                                                                         |
|  HANDLING SCALE:                                                        |
|  * Embeddings pre-computed offline (nightly)                            |
|  * ANN index rebuilt nightly, served from memory                        |
|  * Ranking model: batch inference on GPU (Triton dynamic batching)      |
|  * Feature store: Redis Cluster for online features                     |
|  * Result caching: cache recommendations per user for 10 min            |
|                                                                         |
+-------------------------------------------------------------------------+
```

## SECTION 25.9: ML SYSTEM DESIGN CHEAT SHEET

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ML SYSTEM DESIGN — INTERVIEW CHEAT SHEET                               |
|  ==========================================                             |
|                                                                         |
|  ALWAYS MENTION:                                                        |
|                                                                         |
|  1. "Candidate generation + ranking" (two-stage, not one model)         |
|  2. "Feature store for training-serving consistency"                    |
|  3. "Offline metrics (AUC) + online metrics (A/B test CTR)"             |
|  4. "Shadow mode before A/B, gradual rollout 5% -> 100%"                |
|  5. "Monitor for data drift and model degradation"                      |
|  6. "Start simple (logistic regression), iterate to deep learning"      |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Component          | FAANG Stack                                  |  |
|  |--------------------|----------------------------------------------|  |
|  | Data pipeline      | Kafka -> Spark/Flink -> S3/BigQuery          |  |
|  | Feature store      | Feast / Tecton / custom (Redis + S3)         |  |
|  | Training           | PyTorch + distributed (DDP/FSDP)             |  |
|  | Experiment tracking| MLflow / Weights & Biases / internal         |  |
|  | Model registry     | MLflow / SageMaker / custom                  |  |
|  | Serving            | TF Serving / Triton / custom gRPC            |  |
|  | Vector search      | FAISS / Pinecone / HNSW index                |  |
|  | A/B testing        | Internal platform / Optimizely / custom      |  |
|  | Monitoring         | Prometheus + Grafana + custom drift alerts   |  |
|  | Orchestration      | Airflow / Kubeflow / Metaflow                |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  COMMON PITFALLS (what NOT to do in interview):                         |
|                                                                         |
|  X Jump straight to model architecture (interviewers care about         |
|    system, not math)                                                    |
|  X Ignore data quality / feature engineering                            |
|  X Forget training-serving skew (feature computed differently)          |
|  X Skip cold start problem                                              |
|  X Propose only offline evaluation (must discuss A/B testing)           |
|  X Ignore feedback loops and their biases                               |
|  X Use one model for everything (multi-stage is always better)          |
|                                                                         |
|  -------------------------------------------------------------------    |
|                                                                         |
|  INTERVIEW TIP:                                                         |
|  "I'd approach this with a two-stage architecture: candidate            |
|   generation using ANN search on pre-computed embeddings, followed      |
|   by a real-time ranking model that scores candidates using features    |
|   from our feature store. The model is trained on user interaction      |
|   logs with point-in-time feature joins to avoid data leakage. We       |
|   deploy via shadow mode, then A/B test with 5% traffic, monitoring     |
|   both offline metrics like AUC and online metrics like CTR and         |
|   watch time. Feature pipelines run on Spark (batch) and Flink          |
|   (real-time), feeding into a Feast feature store with Redis for        |
|   online serving and S3 for training."                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

## END OF CHAPTER 25
