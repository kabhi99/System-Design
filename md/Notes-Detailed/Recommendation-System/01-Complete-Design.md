# Recommendation System - Complete System Design

## Table of Contents

1. Introduction & Motivation
2. Requirements
3. Scale Estimation
4. High-Level Architecture
5. Collaborative Filtering
6. Content-Based Filtering
7. Hybrid Approaches
8. Deep Learning Approaches
9. Recommendation Pipeline
10. Feature Store Design
11. Cold Start Problem
12. A/B Testing Framework
13. Feedback Loops & Bias Handling
14. Storage Design
15. Real-Time vs Batch Pipeline
16. Trade-offs Summary
17. Interview Q&A

---

## 1. Introduction & Motivation

### What Is a Recommendation System?

A recommendation system predicts the preference or rating a user would give to an
item, and uses these predictions to suggest items the user is likely to engage with.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  THE CORE VALUE PROPOSITION                                             |
|                                                                         |
|  Without Recommendations:                                               |
|  - Netflix has 15,000+ titles. User browses... gives up after 90s.      |
|  - Amazon has 350M+ products. User searches for exactly what they       |
|    already know they want.                                              |
|  - YouTube has 800M+ videos. User only watches what friends share.      |
|                                                                         |
|  With Recommendations:                                                  |
|  - Netflix: 80% of content watched comes from recommendations           |
|  - Amazon: 35% of revenue comes from recommendations                    |
|  - YouTube: 70% of watch time from recommended videos                   |
|                                                                         |
|  KEY INSIGHT: Recommendations turn a "search" problem into a            |
|  "discovery" problem. Users find things they didn't know they wanted.   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Types of Recommendations

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RECOMMENDATION TYPES                                                   |
|                                                                         |
|  1. Personalized Recommendations                                        |
|     "Because you watched Breaking Bad..." --> Better Call Saul          |
|     Input: User history + user profile + context                        |
|                                                                         |
|  2. Similar Items ("More Like This")                                    |
|     "Customers who bought X also bought..." --> Y, Z                    |
|     Input: Current item being viewed                                    |
|                                                                         |
|  3. Trending / Popular                                                  |
|     "Trending in your region..." --> Top 10 this week                   |
|     Input: Aggregate popularity signals + location/time                 |
|                                                                         |
|  4. "Complete the Look" / Bundle                                        |
|     "Frequently bought together..." --> complementary items             |
|     Input: Cart contents or current item                                |
|                                                                         |
|  5. Contextual Recommendations                                          |
|     "Good morning! Here's your daily mix..." --> time-aware             |
|     Input: Time of day, device, location, mood                          |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 2. Requirements

### Functional Requirements

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FUNCTIONAL REQUIREMENTS                                                |
|                                                                         |
|  FR1: Personalized Home Feed                                            |
|       - Generate a ranked list of recommended items for each user       |
|       - Update based on recent activity                                 |
|                                                                         |
|  FR2: Similar Items                                                     |
|       - Given an item, return a list of similar/related items           |
|       - Based on content similarity AND behavioral similarity           |
|                                                                         |
|  FR3: Trending / Popular                                                |
|       - Show globally or regionally trending items                      |
|       - Time-decayed popularity (recent activity weighted more)         |
|                                                                         |
|  FR4: Real-Time Personalization                                         |
|       - Incorporate user's current session behavior                     |
|       - If user just watched a comedy, boost comedy recommendations     |
|                                                                         |
|  FR5: Multi-Surface Support                                             |
|       - Home page, search results, item detail page, email, push        |
|       - Each surface may have different ranking criteria                |
|                                                                         |
|  FR6: Explainability                                                    |
|       - "Because you watched X" or "Popular in your area"               |
|       - Builds user trust and engagement                                |
|                                                                         |
|  FR7: Diversity & Freshness                                             |
|       - Avoid showing too many similar items                            |
|       - Mix in new/unexplored content                                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Non-Functional Requirements

```
+-------------------------------------------------------------------------+
|                                                                         |
|  NON-FUNCTIONAL REQUIREMENTS                                            |
|                                                                         |
|  NFR1: Low Latency                                                      |
|        - Recommendation serving: < 200ms (p99)                          |
|        - Must not block page rendering                                  |
|                                                                         |
|  NFR2: High Availability                                                |
|        - 99.99% uptime                                                  |
|        - Graceful degradation (show popular items if model fails)       |
|                                                                         |
|  NFR3: Scalability                                                      |
|        - 500M users, 100M items, 10B interactions per day               |
|        - Handle traffic spikes (e.g., Black Friday, new releases)       |
|                                                                         |
|  NFR4: Real-Time Updates                                                |
|        - New user actions reflected in minutes (near real-time)         |
|        - New items available for recommendation within hours            |
|                                                                         |
|  NFR5: A/B Testing Support                                              |
|        - Run multiple recommendation models simultaneously              |
|        - Measure impact on engagement metrics                           |
|                                                                         |
|  NFR6: Privacy & Compliance                                             |
|        - GDPR/CCPA compliance                                           |
|        - User can opt out of personalization                            |
|        - Data retention policies                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 3. Scale Estimation

```
+-------------------------------------------------------------------------+
|                                                                         |
|  SCALE NUMBERS                                                          |
|                                                                         |
|  Users:             500M total, 50M DAU                                 |
|  Items:             100M (movies, products, videos)                     |
|  Interactions/day:  10B (views, clicks, ratings, purchases)             |
|                                                                         |
|  SERVING LOAD:                                                          |
|    50M DAU x 20 recommendation requests/user/day = 1B requests/day      |
|    = ~12K requests/second (average)                                     |
|    = ~50K requests/second (peak)                                        |
|                                                                         |
|  STORAGE:                                                               |
|    User profiles:   500M x 1KB = 500 GB                                 |
|    Item catalog:    100M x 2KB = 200 GB                                 |
|    Interactions:    10B/day x 100B = 1 TB/day (raw logs)                |
|    User embeddings: 500M x 256 floats x 4B = 512 GB                     |
|    Item embeddings: 100M x 256 floats x 4B = 102 GB                     |
|                                                                         |
|  MODEL TRAINING:                                                        |
|    Training data:   30 days x 1 TB/day = 30 TB                          |
|    Training time:   hours (batch), minutes (incremental)                |
|    GPU cluster:     100-1000 GPUs for large models                      |
|                                                                         |
|  CANDIDATE GENERATION:                                                  |
|    From 100M items -> ~1000 candidates -> ~50 ranked -> ~20 shown       |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 4. High-Level Architecture

```
+--------------------------------------------------------------------------+
|                     RECOMMENDATION SYSTEM ARCHITECTURE                   |
+--------------------------------------------------------------------------+
|                                                                          |
|  +------------------+                                                    |
|  |   User Device    |                                                    |
|  | (App / Browser)  |                                                    |
|  +--------+---------+                                                    |
|           |                                                              |
|           v                                                              |
|  +------------------+     +-------------------+                          |
|  |   API Gateway    |---->|  A/B Test Router   |                         |
|  +------------------+     +--------+----------+                          |
|                                    |                                     |
|                    +---------------+---------------+                     |
|                    |                               |                     |
|                    v                               v                     |
|  +-----------------------------------+  +------------------------+       |
|  |  ONLINE SERVING LAYER             |  | EXPERIMENT TRACKING    |       |
|  |                                   |  | (metrics, logging)     |       |
|  |  +-----------------------------+  |  +------------------------+       |
|  |  | 1. Candidate Generation     |  |                                   |
|  |  |    (retrieve ~1000 items)   |  |                                   |
|  |  +-------------+---------------+  |                                   |
|  |                |                  |                                   |
|  |  +-------------v---------------+  |                                   |
|  |  | 2. Scoring / Ranking        |  |                                   |
|  |  |    (rank 1000 -> top 50)    |  |                                   |
|  |  +-------------+---------------+  |                                   |
|  |                |                  |                                   |
|  |  +-------------v---------------+  |                                   |
|  |  | 3. Re-ranking / Filtering   |  |                                   |
|  |  |    (diversity, freshness,   |  |                                   |
|  |  |     business rules)         |  |                                   |
|  |  +-------------+---------------+  |                                   |
|  |                |                  |                                   |
|  +-----------------------------------+                                   |
|                   |                                                      |
|                   v                                                      |
|           +-------+--------+                                             |
|           | Recommended     |                                            |
|           | Items (~20)     |                                            |
|           +----------------+                                             |
|                                                                          |
+--------------------------------------------------------------------------+
|                                                                          |
|  +-----------------------------------+  +-----------------------------+  |
|  |  OFFLINE / NEARLINE LAYER         |  |  DATA STORES                |  |
|  |                                   |  |                             |  |
|  |  +-----------------------------+  |  |  +-----------------------+  |  |
|  |  | Batch Training Pipeline     |  |  |  | User Profile Store    |  |  |
|  |  | (daily/weekly model train)  |  |  |  | (Redis / DynamoDB)    |  |  |
|  |  +-----------------------------+  |  |  +-----------------------+  |  |
|  |                                   |  |                             |  |
|  |  +-----------------------------+  |  |  +-----------------------+  |  |
|  |  | Near-Realtime Pipeline      |  |  |  | Item Catalog          |  |  |
|  |  | (Kafka -> Flink -> update   |  |  |  | (Elasticsearch)       |  |  |
|  |  |  features, embeddings)      |  |  |  +-----------------------+  |  |
|  |  +-----------------------------+  |  |                             |  |
|  |                                   |  |  +-----------------------+  |  |
|  |  +-----------------------------+  |  |  | Feature Store         |  |  |
|  |  | Feature Engineering         |  |  |  | (Feast / Tecton)      |  |  |
|  |  | (user features, item        |  |  |  +-----------------------+  |  |
|  |  |  features, cross-features)  |  |  |                             |  |
|  |  +-----------------------------+  |  |  +-----------------------+  |  |
|  |                                   |  |  | Embedding Index       |  |  |
|  |  +-----------------------------+  |  |  | (FAISS / Pinecone)    |  |  |
|  |  | Model Registry              |  |  |  +-----------------------+  |  |
|  |  | (MLflow / Sagemaker)        |  |  |                             |  |
|  |  +-----------------------------+  |  |  +-----------------------+  |  |
|  |                                   |  |  | Interaction Logs      |  |  |
|  +-----------------------------------+  |  | (Kafka -> S3/HDFS)    |  |  |
|                                         |  +-----------------------+  |  |
|                                         +-----------------------------+  |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 5. Collaborative Filtering

### 5.1 Overview

```
+--------------------------------------------------------------------------+
|                                                                          |
|  COLLABORATIVE FILTERING                                                 |
|                                                                          |
|  Core Idea: "Users who behaved similarly in the past will behave         |
|  similarly in the future."                                               |
|                                                                          |
|  Uses ONLY interaction data (no content features).                       |
|                                                                          |
|  Types:                                                                  |
|  1. User-Based CF: Find similar users -> recommend what they liked       |
|  2. Item-Based CF: Find similar items -> recommend similar to what       |
|                    user already liked                                    |
|  3. Matrix Factorization: Decompose user-item matrix into latent         |
|                           factors                                        |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 5.2 User-Item Interaction Matrix

```
+-------------------------------------------------------------------------+
|                                                                         |
|  USER-ITEM MATRIX (Ratings 1-5, ? = unknown)                            |
|                                                                         |
|              | Movie A | Movie B | Movie C | Movie D | Movie E |        |
|  +-----------+---------+---------+---------+---------+---------+        |
|  | User 1    |    5    |    3    |    ?    |    1    |    ?    |        |
|  | User 2    |    4    |    ?    |    ?    |    1    |    ?    |        |
|  | User 3    |    ?    |    ?    |    5    |    ?    |    4    |        |
|  | User 4    |    ?    |    3    |    4    |    ?    |    5    |        |
|  | User 5    |    1    |    ?    |    5    |    4    |    ?    |        |
|  +-----------+---------+---------+---------+---------+---------+        |
|                                                                         |
|  Goal: Fill in the "?" values (predict ratings for unseen items)        |
|                                                                         |
|  Challenge: Matrix is EXTREMELY SPARSE                                  |
|  - Netflix: 500M users x 15K movies = 7.5 trillion cells                |
|  - Only ~0.01% are filled (users rate very few movies)                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 5.3 User-Based Collaborative Filtering

```
+--------------------------------------------------------------------------+
|                                                                          |
|  USER-BASED CF ALGORITHM                                                 |
|                                                                          |
|  Step 1: Compute similarity between users                                |
|          (cosine similarity, Pearson correlation)                        |
|                                                                          |
|  Step 2: Find K most similar users to the target user                    |
|          (K-Nearest Neighbors)                                           |
|                                                                          |
|  Step 3: Predict rating as weighted average of neighbors' ratings        |
|                                                                          |
|  Similarity(User1, User2) = cos(v1, v2)                                  |
|                            = (v1 . v2) / (|v1| * |v2|)                   |
|                                                                          |
|  Prediction for User u on Item i:                                        |
|    r(u,i) = avg(u) + SUM[sim(u,v) * (r(v,i) - avg(v))]                   |
|                       / SUM[|sim(u,v)|]                                  |
|    (over neighbors v who rated item i)                                   |
|                                                                          |
|  PROS:                                                                   |
|  - Simple and intuitive                                                  |
|  - No need for item features                                             |
|                                                                          |
|  CONS:                                                                   |
|  - Does not scale: O(n^2) user similarity computation                    |
|  - Sparse data -> unreliable similarities                                |
|  - Cold start for new users                                              |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 5.4 Item-Based Collaborative Filtering

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ITEM-BASED CF ALGORITHM                                                |
|                                                                         |
|  Core Idea: Item similarities are MORE STABLE than user similarities.   |
|  A movie's similarity to another movie changes slowly.                  |
|  A user's taste can change quickly.                                     |
|                                                                         |
|  Step 1: Compute similarity between items                               |
|          Based on users who rated both items                            |
|                                                                         |
|  Step 2: For target user, look at items they already liked              |
|                                                                         |
|  Step 3: Recommend items most similar to their liked items              |
|                                                                         |
|  Prediction for User u on Item i:                                       |
|    r(u,i) = SUM[sim(i,j) * r(u,j)] / SUM[|sim(i,j)|]                    |
|    (over items j that user u has rated)                                 |
|                                                                         |
|  ADVANTAGES OVER USER-BASED:                                            |
|  - Item similarities can be precomputed (offline)                       |
|  - More stable over time                                                |
|  - Better scaling (fewer items than users typically)                    |
|  - Amazon's original recommendation engine used this approach           |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 5.5 Matrix Factorization

```
+-------------------------------------------------------------------------+
|                                                                         |
|  MATRIX FACTORIZATION (ALS / SVD)                                       |
|                                                                         |
|  Decompose user-item matrix R into two lower-rank matrices:             |
|                                                                         |
|  R  (m x n)  ~=  U  (m x k)  *  V^T  (k x n)                            |
|                                                                         |
|  m = number of users                                                    |
|  n = number of items                                                    |
|  k = number of latent factors (e.g., 50-300)                            |
|                                                                         |
|  Each user  -> k-dimensional vector (user embedding)                    |
|  Each item  -> k-dimensional vector (item embedding)                    |
|                                                                         |
|  Predicted rating: r(u,i) = dot(U[u], V[i]) + bias_u + bias_i + mu      |
|                                                                         |
|  TRAINING: Minimize                                                     |
|    SUM[(r_actual - r_predicted)^2] + lambda * (|U|^2 + |V|^2)           |
|    (over known ratings, with L2 regularization)                         |
|                                                                         |
|  Methods:                                                               |
|  - SGD (Stochastic Gradient Descent): iterate over known ratings        |
|  - ALS (Alternating Least Squares): fix U, solve V; fix V, solve U      |
|    ALS is parallelizable -> great for distributed training (Spark)      |
|                                                                         |
|  LATENT FACTORS might capture:                                          |
|  - Genre preference (action vs comedy)                                  |
|  - Mood (dark vs lighthearted)                                          |
|  - Production quality (indie vs blockbuster)                            |
|  - But they are NOT explicitly labeled                                  |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 6. Content-Based Filtering

```
+-------------------------------------------------------------------------+
|                                                                         |
|  CONTENT-BASED FILTERING                                                |
|                                                                         |
|  Core Idea: Recommend items similar to what the user has liked,         |
|  based on ITEM FEATURES (not other users' behavior).                    |
|                                                                         |
|  ITEM FEATURE EXTRACTION:                                               |
|                                                                         |
|  Movies:  genre, director, actors, plot keywords, release year          |
|  Products: category, brand, price range, description, attributes        |
|  Articles: TF-IDF of text, topics, author, publication                  |
|  Music:   genre, tempo, key, artist, audio features (Mel spectrograms)  |
|                                                                         |
|  USER PROFILE:                                                          |
|  Aggregate features of items the user has liked.                        |
|  user_profile = weighted_average(liked_item_features)                   |
|                                                                         |
|  SIMILARITY:                                                            |
|  score(user, item) = cosine_similarity(user_profile, item_features)     |
|                                                                         |
+-------------------------------------------------------------------------+
```

### TF-IDF for Text-Based Items

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TF-IDF (Term Frequency - Inverse Document Frequency)                   |
|                                                                         |
|  TF(t, d)  = count(t in d) / total_terms(d)                             |
|  IDF(t)    = log(N / df(t))                                             |
|  TF-IDF    = TF * IDF                                                   |
|                                                                         |
|  Example for a movie description:                                       |
|                                                                         |
|  "A thrilling heist in a futuristic city"                               |
|                                                                         |
|  +----------+------+------+---------+                                   |
|  | Term     | TF   | IDF  | TF-IDF  |                                   |
|  +----------+------+------+---------+                                   |
|  | thrilling| 0.14 | 3.2  | 0.45    |                                   |
|  | heist    | 0.14 | 4.1  | 0.57    |                                   |
|  | futurist.| 0.14 | 3.8  | 0.53    |                                   |
|  | city     | 0.14 | 1.2  | 0.17    |  (common word, low IDF)           |
|  +----------+------+------+---------+                                   |
|                                                                         |
|  PROS:                                                                  |
|  - No cold start for new items (features are immediately available)     |
|  - Transparent and explainable                                          |
|  - No need for other users' data                                        |
|                                                                         |
|  CONS:                                                                  |
|  - Over-specialization (filter bubble)                                  |
|  - Cannot discover surprising recommendations                           |
|  - Requires good feature engineering                                    |
|  - Cold start for new users (no liked items yet)                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 7. Hybrid Approaches

```
+--------------------------------------------------------------------------+
|                                                                          |
|  HYBRID RECOMMENDATION STRATEGIES                                        |
|                                                                          |
|  1. WEIGHTED HYBRID                                                      |
|     score = alpha * CF_score + (1 - alpha) * CB_score                    |
|     alpha tuned via A/B testing                                          |
|     Simple but effective                                                 |
|                                                                          |
|  2. SWITCHING HYBRID                                                     |
|     - Use content-based for new users (cold start)                       |
|     - Switch to collaborative filtering once enough data exists          |
|     - Threshold: e.g., 20+ interactions                                  |
|                                                                          |
|  3. CASCADE HYBRID                                                       |
|     - Stage 1: CF generates rough candidate list                         |
|     - Stage 2: CB re-ranks within the candidate list                     |
|     - Or vice versa                                                      |
|                                                                          |
|  4. FEATURE AUGMENTATION                                                 |
|     - CF produces a "latent factor" for each item                        |
|     - Feed this as an additional feature to a CB model                   |
|     - Best of both worlds                                                |
|                                                                          |
|  5. META-LEARNER (STACKING)                                              |
|     - Multiple base recommenders produce scores                          |
|     - A meta-model (e.g., gradient-boosted trees) combines them          |
|     - Most flexible and typically best performing                        |
|                                                                          |
|     +--------+   +--------+   +--------+                                 |
|     | CF     |   | CB     |   | Popular|                                 |
|     | Model  |   | Model  |   | Model  |                                 |
|     +---+----+   +---+----+   +---+----+                                 |
|         |            |            |                                      |
|         v            v            v                                      |
|     +--------------------------------------+                             |
|     |       Meta-Learner (GBT/NN)          |                             |
|     |  Input: all base model scores +       |                            |
|     |         user/item features            |                            |
|     +------------------+-------------------+                             |
|                        |                                                 |
|                        v                                                 |
|                  Final Ranking                                           |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 8. Deep Learning Approaches

### 8.1 Embedding-Based Models

```
+-------------------------------------------------------------------------+
|                                                                         |
|  EMBEDDING-BASED RECOMMENDATIONS                                        |
|                                                                         |
|  Core Idea: Map users and items into the SAME vector space.             |
|  Similar users/items are close together in this space.                  |
|                                                                         |
|  USER EMBEDDING (256-dim vector):                                       |
|  [0.23, -0.11, 0.87, 0.02, ..., 0.45]                                   |
|                                                                         |
|  ITEM EMBEDDING (256-dim vector):                                       |
|  [0.21, -0.09, 0.91, 0.05, ..., 0.43]                                   |
|                                                                         |
|  Score = dot_product(user_embedding, item_embedding)                    |
|  Or: Score = cosine_similarity(user_embedding, item_embedding)          |
|                                                                         |
|  Training: Learn embeddings by predicting interactions                  |
|  - Positive pairs: (user, item_they_liked)                              |
|  - Negative pairs: (user, random_item)                                  |
|  - Loss: maximize score for positives, minimize for negatives           |
|                                                                         |
|  At serving time:                                                       |
|  - Compute user embedding                                               |
|  - Use ANN (Approximate Nearest Neighbor) to find closest items         |
|  - ANN indexes: FAISS, ScaNN, HNSW, Annoy                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 8.2 Two-Tower Model

```
+--------------------------------------------------------------------------+
|                                                                          |
|  TWO-TOWER MODEL (Dual Encoder)                                          |
|                                                                          |
|    User Features            Item Features                                |
|    +----------+             +----------+                                 |
|    | user_id  |             | item_id  |                                 |
|    | age      |             | category |                                 |
|    | gender   |             | title    |                                 |
|    | history  |             | price    |                                 |
|    | context  |             | image    |                                 |
|    +----+-----+             +----+-----+                                 |
|         |                        |                                       |
|         v                        v                                       |
|    +----------+             +----------+                                 |
|    |  User    |             |  Item    |                                 |
|    |  Tower   |             |  Tower   |                                 |
|    | (DNN)    |             | (DNN)    |                                 |
|    +----+-----+             +----+-----+                                 |
|         |                        |                                       |
|         v                        v                                       |
|    +----------+             +----------+                                 |
|    | User     |             | Item     |                                 |
|    | Embedding|             | Embedding|                                 |
|    | (256-d)  |             | (256-d)  |                                 |
|    +----+-----+             +----+-----+                                 |
|         |                        |                                       |
|         +----------+-------------+                                       |
|                    |                                                     |
|                    v                                                     |
|             dot_product(u, i)                                            |
|                    |                                                     |
|                    v                                                     |
|              Relevance Score                                             |
|                                                                          |
|  KEY ADVANTAGE:                                                          |
|  - Item embeddings can be PRE-COMPUTED and indexed                       |
|  - At serving time, only compute user embedding (once)                   |
|  - Then use ANN search over pre-indexed item embeddings                  |
|  - Scales to billions of items                                           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### 8.3 Transformer-Based Models

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TRANSFORMER-BASED RECOMMENDATIONS                                      |
|                                                                         |
|  Treat user's interaction history as a SEQUENCE:                        |
|                                                                         |
|  [item_3, item_7, item_1, item_9, item_15, ???]                         |
|                                                                         |
|  Predict the NEXT item using self-attention.                            |
|                                                                         |
|  Models:                                                                |
|  - SASRec (Self-Attentive Sequential Recommendation)                    |
|  - BERT4Rec (Bidirectional Encoder for Recommendations)                 |
|  - Transformers4Rec (NVIDIA)                                            |
|                                                                         |
|  Architecture:                                                          |
|  +-----+  +-----+  +-----+  +-----+  +-----+                            |
|  |item3|  |item7|  |item1|  |item9|  |it.15|                            |
|  +--+--+  +--+--+  +--+--+  +--+--+  +--+--+                            |
|     |        |        |        |        |                               |
|     v        v        v        v        v                               |
|  +------------------------------------------------+                     |
|  |        Multi-Head Self-Attention                |                    |
|  |        (captures sequential patterns)           |                    |
|  +------------------------------------------------+                     |
|     |        |        |        |        |                               |
|     v        v        v        v        v                               |
|  +------------------------------------------------+                     |
|  |        Feed-Forward Network                     |                    |
|  +------------------------------------------------+                     |
|     |        |        |        |        |                               |
|     v        v        v        v        v                               |
|  [pred]  [pred]   [pred]   [pred]   [pred]                              |
|                                         |                               |
|                                         v                               |
|                                    Next Item Prediction                 |
|                                                                         |
|  ADVANTAGES:                                                            |
|  - Captures long-range dependencies in user behavior                    |
|  - Handles variable-length sequences                                    |
|  - State-of-the-art performance on sequential recommendation            |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 9. Recommendation Pipeline

### Candidate Generation -> Scoring -> Re-ranking

```
+--------------------------------------------------------------------------+
|                                                                          |
|  THREE-STAGE RECOMMENDATION PIPELINE                                     |
|                                                                          |
|  +--------------------+                                                  |
|  | STAGE 1:           |  100M items --> ~1000 candidates                 |
|  | CANDIDATE          |                                                  |
|  | GENERATION         |  Methods:                                        |
|  |                    |  - ANN search on embeddings (Two-Tower)          |
|  |                    |  - Item-based CF (similar to recent views)       |
|  |                    |  - Popular/trending items                        |
|  |                    |  - Category/topic-based retrieval                |
|  |                    |  - Social graph (friends' favorites)             |
|  |                    |                                                  |
|  |  Latency budget:   |  < 50ms                                          |
|  |  Model complexity:  |  LOW (must be fast)                             |
|  +--------+-----------+                                                  |
|           |                                                              |
|           v                                                              |
|  +--------------------+                                                  |
|  | STAGE 2:           |  ~1000 candidates --> ~50 scored items           |
|  | SCORING /          |                                                  |
|  | RANKING            |  Methods:                                        |
|  |                    |  - Deep neural network (user + item features)    |
|  |                    |  - Gradient-boosted trees (XGBoost, LightGBM)    |
|  |                    |  - Cross-features (user x item interactions)     |
|  |                    |  - Multi-objective: P(click), P(watch), P(buy)   |
|  |                    |                                                  |
|  |  Latency budget:   |  < 100ms                                         |
|  |  Model complexity:  |  HIGH (can afford more compute per item)        |
|  +--------+-----------+                                                  |
|           |                                                              |
|           v                                                              |
|  +--------------------+                                                  |
|  | STAGE 3:           |  ~50 items --> ~20 final recommendations         |
|  | RE-RANKING /       |                                                  |
|  | FILTERING          |  Rules:                                          |
|  |                    |  - Remove already-seen items                     |
|  |                    |  - Enforce diversity (no 5 action movies in row) |
|  |                    |  - Apply business rules (promote originals)      |
|  |                    |  - Freshness boost (mix in new content)          |
|  |                    |  - Content policy (age-appropriate, region)      |
|  |                    |  - Dedup (no same franchise back-to-back)        |
|  |                    |                                                  |
|  |  Latency budget:   |  < 20ms                                          |
|  |  Model complexity:  |  RULES + lightweight model                      |
|  +--------+-----------+                                                  |
|           |                                                              |
|           v                                                              |
|  +--------------------+                                                  |
|  | Final Response:    |                                                  |
|  | ~20 ranked items   |                                                  |
|  | with explanations  |                                                  |
|  +--------------------+                                                  |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 10. Feature Store Design

```
+--------------------------------------------------------------------------+
|                                                                          |
|  FEATURE STORE ARCHITECTURE                                              |
|                                                                          |
|  A feature store provides a centralized repository for storing,          |
|  serving, and managing ML features across training and serving.          |
|                                                                          |
|  +-------------------------------------------------------------+         |
|  |                    FEATURE STORE                              |       |
|  |                                                               |       |
|  |  +-------------------------+  +---------------------------+  |        |
|  |  | OFFLINE STORE           |  | ONLINE STORE              |  |        |
|  |  | (Training)              |  | (Serving)                 |  |        |
|  |  |                         |  |                           |  |        |
|  |  | Storage: S3 / HDFS      |  | Storage: Redis / DynamoDB |  |        |
|  |  | Format: Parquet         |  | Latency: < 5ms           |  |         |
|  |  | Latency: seconds-mins   |  | Keys: user_id, item_id   |  |         |
|  |  | Volume: full history    |  | Volume: latest values     |  |        |
|  |  +-------------------------+  +---------------------------+  |        |
|  |                                                               |       |
|  +-------------------------------------------------------------+         |
|                                                                          |
|  FEATURE TYPES:                                                          |
|                                                                          |
|  +--------------------+----------------------------------------+         |
|  | Category           | Examples                               |         |
|  +--------------------+----------------------------------------+         |
|  | User Features      | age, gender, country, signup_date,     |         |
|  |                    | avg_session_length, genre_preferences  |         |
|  +--------------------+----------------------------------------+         |
|  | User Behavior      | last_5_viewed, click_rate_7d,          |         |
|  | (aggregated)       | watch_time_30d, purchase_count_90d     |         |
|  +--------------------+----------------------------------------+         |
|  | Item Features      | category, price, rating, description   |         |
|  |                    | embedding, popularity_score             |        |
|  +--------------------+----------------------------------------+         |
|  | Context Features   | time_of_day, day_of_week, device_type, |         |
|  |                    | session_length, query_text              |        |
|  +--------------------+----------------------------------------+         |
|  | Cross Features     | user_category_affinity,                |         |
|  |                    | user_price_range_preference,           |         |
|  |                    | user_brand_interaction_count            |        |
|  +--------------------+----------------------------------------+         |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Feature Freshness

```
+-------------------------------------------------------------------------+
|                                                                         |
|  FEATURE UPDATE CADENCES                                                |
|                                                                         |
|  +------------------+------------------+-----------------------------+  |
|  | Freshness        | Update Frequency | Examples                    |  |
|  +------------------+------------------+-----------------------------+  |
|  | Static           | Rarely           | gender, country, genre      |  |
|  | Batch            | Daily            | avg rating, popularity      |  |
|  | Near-realtime    | Minutes          | click_rate_1h, trending     |  |
|  | Realtime         | Seconds          | current session items,      |  |
|  |                  |                  | last search query           |  |
|  +------------------+------------------+-----------------------------+  |
|                                                                         |
|  Pipeline:                                                              |
|  User clicks item --> Kafka event --> Flink aggregation -->             |
|  Update Redis (online store) --> User's next request sees               |
|  updated features within seconds                                        |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 11. Cold Start Problem

```
+--------------------------------------------------------------------------+
|                                                                          |
|  COLD START PROBLEM                                                      |
|                                                                          |
|  NEW USER COLD START:                                                    |
|  No interaction history -> cannot use collaborative filtering            |
|                                                                          |
|  Solutions:                                                              |
|  1. Onboarding questionnaire                                             |
|     "Select 5 movies you like" -> bootstrap user profile                 |
|                                                                          |
|  2. Demographic-based recommendations                                    |
|     Use age, location, device to find similar cohort                     |
|                                                                          |
|  3. Popular / trending items                                             |
|     Safe default: show what most people like                             |
|                                                                          |
|  4. Content-based (from first interaction)                               |
|     User views one item -> immediately recommend similar items           |
|                                                                          |
|  5. Contextual bandits (explore-exploit)                                 |
|     Show diverse items initially, learn preferences quickly              |
|                                                                          |
|  Transition: As user interacts more, gradually shift from                |
|  popularity -> content-based -> collaborative filtering                  |
|                                                                          |
+--------------------------------------------------------------------------+
|                                                                          |
|  NEW ITEM COLD START:                                                    |
|  No interaction data -> cannot compute item similarity                   |
|                                                                          |
|  Solutions:                                                              |
|  1. Content-based features                                               |
|     Use metadata (genre, description) to place in feature space          |
|                                                                          |
|  2. Exploration budget                                                   |
|     Show new items to a small % of users to collect feedback             |
|                                                                          |
|  3. Transfer learning                                                    |
|     Use pre-trained embeddings (e.g., BERT for text descriptions)        |
|                                                                          |
|  4. Similar item bootstrapping                                           |
|     Copy interactions from the most similar existing item                |
|                                                                          |
|  5. Editorial curation                                                   |
|     Human editors manually place high-quality new items                  |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 12. A/B Testing Framework

```
+--------------------------------------------------------------------------+
|                                                                          |
|  A/B TESTING FOR RECOMMENDATIONS                                         |
|                                                                          |
|  +--------+                                                              |
|  | User   |                                                              |
|  | Request|                                                              |
|  +---+----+                                                              |
|      |                                                                   |
|      v                                                                   |
|  +---+-------------------+                                               |
|  | Traffic Router         |                                              |
|  | (hash user_id % 100)  |                                               |
|  +---+---------+---------+                                               |
|      |         |                                                         |
|      v         v                                                         |
|  +-------+ +-------+                                                     |
|  |Control| | Test  |                                                     |
|  |  50%  | |  50%  |                                                     |
|  |Model A| |Model B|                                                     |
|  +---+---+ +---+---+                                                     |
|      |         |                                                         |
|      v         v                                                         |
|  +---+---------+---+                                                     |
|  | Metrics Logger   |                                                    |
|  | (clicks, views,  |                                                    |
|  |  watch time,     |                                                    |
|  |  purchases)      |                                                    |
|  +------------------+                                                    |
|                                                                          |
|  KEY METRICS:                                                            |
|  - CTR (Click-Through Rate): clicks / impressions                        |
|  - Engagement: time spent, videos watched, pages browsed                 |
|  - Conversion: purchases, sign-ups                                       |
|  - Diversity: number of unique categories in recommendations             |
|  - Coverage: % of catalog items ever recommended                         |
|  - Novelty: how surprising are the recommendations                       |
|  - Long-term retention: 7-day, 30-day return rate                        |
|                                                                          |
|  STATISTICAL RIGOR:                                                      |
|  - Run for at least 2 weeks (capture weekly patterns)                    |
|  - Minimum sample size for statistical significance (p < 0.05)           |
|  - Watch for novelty effects (new model gets clicks just for             |
|    being different)                                                      |
|  - Use interleaving for faster results (mix A and B in same list)        |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 13. Feedback Loops & Bias Handling

```
+--------------------------------------------------------------------------+
|                                                                          |
|  FEEDBACK LOOP PROBLEM                                                   |
|                                                                          |
|  1. Model recommends popular items                                       |
|  2. Users click on popular items (they're shown prominently)             |
|  3. Model learns: "popular items get more clicks"                        |
|  4. Model recommends popular items even more                             |
|  5. Rich get richer, niche items never get shown                         |
|                                                                          |
|  This is the POPULARITY BIAS loop.                                       |
|                                                                          |
|  +--------+     recommend     +--------+                                 |
|  | Model  | ----------------> | User   |                                 |
|  |        |                   |        |                                 |
|  |        | <---------------- |        |                                 |
|  +--------+     interaction   +--------+                                 |
|       ^              |                                                   |
|       |              |                                                   |
|       +----- train --+                                                   |
|                                                                          |
|  The model trains on data IT GENERATED. This is a closed loop.           |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Bias Types and Mitigations

```
+-------------------------------------------------------------------------+
|                                                                         |
|  TYPES OF BIAS IN RECOMMENDATIONS                                       |
|                                                                         |
|  +---------------------+---------------------------------------------+  |
|  | Bias Type           | Mitigation                                  |  |
|  +---------------------+---------------------------------------------+  |
|  | Position Bias       | Users click top results more. Use           |  |
|  |                     | position-aware training (learn position     |  |
|  |                     | bias and subtract it during ranking).       |  |
|  +---------------------+---------------------------------------------+  |
|  | Popularity Bias     | Add exploration: show some less-popular     |  |
|  |                     | items. Use inverse propensity scoring       |  |
|  |                     | (IPS) to correct for exposure bias.         |  |
|  +---------------------+---------------------------------------------+  |
|  | Selection Bias      | Users only rate items they choose to        |  |
|  |                     | interact with (missing not at random).      |  |
|  |                     | Use unbiased estimators in training.        |  |
|  +---------------------+---------------------------------------------+  |
|  | Exposure Bias       | Items not shown cannot be clicked.          |  |
|  |                     | Log what was shown and use counterfactual   |  |
|  |                     | learning to account for unseen items.       |  |
|  +---------------------+---------------------------------------------+  |
|  | Filter Bubble       | User only sees items similar to past        |  |
|  |                     | preferences. Inject diversity and           |  |
|  |                     | serendipity into recommendations.           |  |
|  +---------------------+---------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Exploration vs Exploitation

```
+--------------------------------------------------------------------------+
|                                                                          |
|  EXPLORE vs EXPLOIT                                                      |
|                                                                          |
|  EXPLOIT: Show items the model is CONFIDENT the user will like           |
|           (maximize immediate engagement)                                |
|                                                                          |
|  EXPLORE: Show items with UNCERTAIN predicted engagement                 |
|           (gather information to improve future recommendations)         |
|                                                                          |
|  Strategies:                                                             |
|  - Epsilon-greedy: 90% exploit, 10% random explore                       |
|  - Thompson Sampling: sample from posterior distribution                 |
|  - Upper Confidence Bound (UCB): optimism in uncertainty                 |
|  - Contextual Bandits: personalized exploration                          |
|                                                                          |
|  In practice: Reserve 5-10% of recommendation slots for exploration      |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 14. Storage Design

```
+-------------------------------------------------------------------------+
|                                                                         |
|  STORAGE ARCHITECTURE                                                   |
|                                                                         |
|  +--------------------------------------------------------------------+ |
|  |  USER PROFILE STORE                                                | |
|  |  Technology: Redis Cluster + DynamoDB (backup)                     | |
|  |  Key: user_id                                                      | |
|  |  Value: {demographics, preferences, embeddings, history}           | |
|  |  Access: ~50K reads/sec (low latency critical)                     | |
|  |  Size: 500GB (fits in Redis cluster)                               | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
|  +--------------------------------------------------------------------+ |
|  |  ITEM CATALOG                                                      | |
|  |  Technology: Elasticsearch + PostgreSQL                            | |
|  |  Key: item_id                                                      | |
|  |  Value: {title, description, category, metadata, features}         | |
|  |  Access: full-text search + structured queries                     | |
|  |  Size: 200GB                                                       | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
|  +--------------------------------------------------------------------+ |
|  |  EMBEDDING INDEX                                                   | |
|  |  Technology: FAISS (Facebook) or ScaNN (Google) or Pinecone        | |
|  |  Key: item_id -> 256-dim float vector                              | |
|  |  Operation: Approximate Nearest Neighbor search                    | |
|  |  Performance: query 100M vectors in < 10ms                         | |
|  |  Size: 100GB (in-memory for speed)                                 | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
|  +--------------------------------------------------------------------+ |
|  |  INTERACTION LOG                                                   | |
|  |  Technology: Kafka -> S3 (raw) / HDFS (processed)                  | |
|  |  Events: {user_id, item_id, action, timestamp, context}            | |
|  |  Volume: 10B events/day = ~1TB/day                                 | |
|  |  Retention: 90 days hot, 1 year cold                               | |
|  |  Used for: model training, analytics, feature computation          | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
|  +--------------------------------------------------------------------+ |
|  |  MODEL ARTIFACT STORE                                              | |
|  |  Technology: S3 + MLflow / Sagemaker Model Registry                | |
|  |  Contents: trained model weights, config, metrics                  | |
|  |  Versioned: each model version tracked with metadata               | |
|  +--------------------------------------------------------------------+ |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 15. Real-Time vs Batch Pipeline

```
+--------------------------------------------------------------------------+
|                                                                          |
|  BATCH PIPELINE (Offline)                                                |
|                                                                          |
|  Frequency: Daily or weekly                                              |
|                                                                          |
|  S3 (interaction logs)                                                   |
|       |                                                                  |
|       v                                                                  |
|  Spark / Databricks (feature engineering)                                |
|       |                                                                  |
|       v                                                                  |
|  Training Cluster (GPU) - train models on full dataset                   |
|       |                                                                  |
|       v                                                                  |
|  Model Registry (versioned artifacts)                                    |
|       |                                                                  |
|       v                                                                  |
|  Batch Inference: pre-compute top-K for each user                        |
|       |                                                                  |
|       v                                                                  |
|  Cache Store (Redis): user_id -> [top-K item recommendations]            |
|                                                                          |
|  PROS: Full dataset, complex models, fresh baselines                     |
|  CONS: Stale for hours/days, expensive compute, not personalized         |
|        to current session                                                |
|                                                                          |
+--------------------------------------------------------------------------+
|                                                                          |
|  NEAR-REALTIME PIPELINE                                                  |
|                                                                          |
|  Frequency: Minutes                                                      |
|                                                                          |
|  User action (click/view/purchase)                                       |
|       |                                                                  |
|       v                                                                  |
|  Kafka (event stream)                                                    |
|       |                                                                  |
|       v                                                                  |
|  Flink / Spark Streaming (update features)                               |
|       |                                                                  |
|       +---> Update Feature Store (latest user features)                  |
|       |                                                                  |
|       +---> Update User Embedding (incremental learning)                 |
|       |                                                                  |
|       +---> Trigger re-ranking (on next request, use updated features)   |
|                                                                          |
|  PROS: Fresh recommendations, captures session intent                    |
|  CONS: Complex infrastructure, harder to debug                           |
|                                                                          |
+--------------------------------------------------------------------------+
|                                                                          |
|  REAL-TIME SERVING PIPELINE                                              |
|                                                                          |
|  User request arrives:                                                   |
|       |                                                                  |
|       v                                                                  |
|  1. Fetch user features from Feature Store (Redis)        < 5ms          |
|  2. Compute user embedding (if not cached)                < 10ms         |
|  3. ANN search for candidates (FAISS)                     < 20ms         |
|  4. Fetch item features for candidates                    < 10ms         |
|  5. Score candidates with ranking model                   < 50ms         |
|  6. Re-rank with business rules                           < 10ms         |
|  7. Return response                                                      |
|                                                                          |
|  Total: < 100ms (well within 200ms budget)                               |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 16. Trade-offs Summary

```
+-------------------------------------------------------------------------+
|                                                                         |
|  KEY TRADE-OFFS IN RECOMMENDATION SYSTEM DESIGN                         |
|                                                                         |
|  +---------------------------+------------------------------------------+
|  | Trade-off                 | Analysis                                 |
|  +---------------------------+------------------------------------------+
|  | Relevance vs Diversity    | Highly relevant = similar to past.       |
|  |                           | Diverse = more exploration, less         |
|  |                           | predictable engagement.                  |
|  +---------------------------+------------------------------------------+
|  | Personalization vs Privacy| More user data = better recommendations  |
|  |                           | but higher privacy risk and regulatory   |
|  |                           | burden (GDPR).                           |
|  +---------------------------+------------------------------------------+
|  | Freshness vs Stability    | Real-time updates = fresh but noisy.     |
|  |                           | Batch updates = stable but stale.        |
|  +---------------------------+------------------------------------------+
|  | Model Complexity vs       | Deep learning = best accuracy but        |
|  | Latency                   | slower. Simple models = fast but less    |
|  |                           | accurate.                                |
|  +---------------------------+------------------------------------------+
|  | Exploitation vs           | Exploit = maximize short-term metrics.   |
|  | Exploration               | Explore = invest in long-term model      |
|  |                           | improvement. Need balance.               |
|  +---------------------------+------------------------------------------+
|  | Global vs Personal Models | One model for all = simpler, more data.  |
|  |                           | Per-user models = better fit, more       |
|  |                           | expensive, cold start issues.            |
|  +---------------------------+------------------------------------------+
|  | Short-term vs Long-term   | Optimize for clicks today vs user        |
|  | Engagement                | retention over months.                   |
|  +---------------------------+------------------------------------------+
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 17. Interview Q&A

### Q1: How would you design a recommendation system from scratch?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ANSWER:                                                                 |
|                                                                          |
|  Start with the three-stage pipeline:                                    |
|                                                                          |
|  1. Candidate Generation:                                                |
|     - Two-tower model for embedding-based retrieval                      |
|     - Item-based CF for "similar items"                                  |
|     - Trending/popular as fallback                                       |
|     - Reduce 100M items to ~1000 candidates                              |
|                                                                          |
|  2. Scoring/Ranking:                                                     |
|     - Feature-rich model (user features + item features + context)       |
|     - Gradient-boosted trees or deep neural network                      |
|     - Multi-objective: P(click) * w1 + P(purchase) * w2                  |
|                                                                          |
|  3. Re-ranking:                                                          |
|     - Business rules, diversity, freshness                               |
|     - Filter already-seen and policy-violating items                     |
|                                                                          |
|  Support with: Feature Store, A/B testing, feedback logging              |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q2: How do you handle the cold start problem?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ANSWER:                                                                 |
|                                                                          |
|  New Users:                                                              |
|  - Start with popular/trending items                                     |
|  - Use demographics (age, location) to match to cohorts                  |
|  - Onboarding flow: "pick 5 things you like"                             |
|  - Contextual bandits for fast personalization                           |
|  - Transition to CF after 10-20 interactions                             |
|                                                                          |
|  New Items:                                                              |
|  - Content-based features (category, description embeddings)             |
|  - Exploration budget: show to small random user sample                  |
|  - Transfer from similar existing items                                  |
|  - Editorial placement                                                   |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q3: How do you evaluate recommendation quality?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  OFFLINE METRICS (on historical data):                                  |
|  - Precision@K: of top K recommended, how many did user actually like   |
|  - Recall@K: of items user liked, how many were in top K                |
|  - NDCG: normalized discounted cumulative gain (rank-aware)             |
|  - MAP: mean average precision                                          |
|  - AUC-ROC: area under the receiver operating characteristic curve      |
|  - Hit Rate: did the user interact with any recommended item            |
|                                                                         |
|  ONLINE METRICS (in production):                                        |
|  - CTR (click-through rate)                                             |
|  - Watch time / session length                                          |
|  - Conversion rate                                                      |
|  - Revenue per user                                                     |
|  - User retention (7-day, 30-day)                                       |
|  - Catalog coverage                                                     |
|                                                                         |
|  IMPORTANT: Offline metrics don't always correlate with online          |
|  metrics. Always validate with A/B tests.                               |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q4: Explain collaborative filtering vs content-based filtering.

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  Collaborative Filtering:                                               |
|  - Uses interaction data (ratings, clicks, purchases)                   |
|  - "Users who liked X also liked Y"                                     |
|  - Can discover unexpected connections                                  |
|  - Suffers from cold start                                              |
|  - Needs large interaction dataset                                      |
|                                                                         |
|  Content-Based Filtering:                                               |
|  - Uses item features (genre, description, price)                       |
|  - "This item has similar features to items you liked"                  |
|  - No cold start for new items                                          |
|  - Tends toward over-specialization (filter bubble)                     |
|  - Requires good feature engineering                                    |
|                                                                         |
|  In practice, all major systems use HYBRID approaches combining both.   |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q5: How does the Two-Tower model work and why is it popular?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ANSWER:                                                                 |
|                                                                          |
|  Architecture: Two separate neural networks (towers).                    |
|  - User tower: maps user features -> user embedding (256-dim)            |
|  - Item tower: maps item features -> item embedding (256-dim)            |
|  - Score = dot_product(user_embedding, item_embedding)                   |
|                                                                          |
|  Why popular:                                                            |
|  1. SCALABLE: Item embeddings are pre-computed offline.                  |
|     At serving time, only compute user embedding once.                   |
|  2. FAST: Use ANN index (FAISS) to find top-K similar items in <10ms     |
|  3. FLEXIBLE: Each tower can use any features (text, images, etc.)       |
|  4. TRAINABLE: End-to-end with interaction data                          |
|                                                                          |
|  Limitation: Cannot model cross-features (user-item interactions)        |
|  directly. This is why it's used for candidate generation, not final     |
|  ranking.                                                                |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q6: How would you implement real-time personalization?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  1. Stream user events to Kafka (clicks, views, searches)               |
|                                                                         |
|  2. Flink/Spark Streaming processes events:                             |
|     - Updates user's session features in Feature Store                  |
|     - Computes real-time aggregates (clicks in last 5 min)              |
|     - Optionally updates user embedding incrementally                   |
|                                                                         |
|  3. On next recommendation request:                                     |
|     - Fetch UPDATED features from Feature Store                         |
|     - Include current session context in scoring model                  |
|     - Example: user just searched "sci-fi" -> boost sci-fi items        |
|                                                                         |
|  4. Latency: events reflected in recommendations within 1-5 minutes     |
|                                                                         |
|  5. For sub-second personalization:                                     |
|     - Client-side re-ranking using a lightweight model                  |
|     - Pre-fetch multiple recommendation lists for different contexts    |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q7: How do you prevent filter bubbles?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ANSWER:                                                                 |
|                                                                          |
|  1. Diversity constraints in re-ranking                                  |
|     - Max 2 items per category in a row                                  |
|     - MMR (Maximal Marginal Relevance): balance relevance and diversity  |
|                                                                          |
|  2. Exploration slots                                                    |
|     - Reserve 10% of slots for items outside user's usual preferences    |
|     - Use contextual bandits to explore efficiently                      |
|                                                                          |
|  3. Serendipity metric                                                   |
|     - Track and optimize for "surprising but liked" recommendations      |
|     - Reward model for successful novel suggestions                      |
|                                                                          |
|  4. Multi-objective optimization                                         |
|     - Don't optimize ONLY for engagement                                 |
|     - Include diversity, freshness, coverage in the objective            |
|                                                                          |
|  5. User controls                                                        |
|     - "Show me less like this" / "Explore something new" buttons         |
|     - Explicit interest settings                                         |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q8: How does Netflix's recommendation system work at a high level?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ANSWER:                                                                 |
|                                                                          |
|  Netflix uses a sophisticated multi-algorithm approach:                  |
|                                                                          |
|  1. Each "row" on the homepage is a different algorithm:                 |
|     - "Because you watched X" (item-based CF)                            |
|     - "Trending Now" (popularity + freshness)                            |
|     - "Top Picks for You" (personalized ranking)                         |
|     - Genre rows (personalized genre ranking)                            |
|                                                                          |
|  2. Row selection: Which rows to show and in what order                  |
|     This is a separate ranking problem (row-level personalization)       |
|                                                                          |
|  3. Within-row ranking: Order items within each row                      |
|                                                                          |
|  4. Artwork personalization: Different thumbnails for different users    |
|     (e.g., show comedy scene for comedy fans, action scene for           |
|     action fans, for the SAME movie)                                     |
|                                                                          |
|  5. Everything is A/B tested extensively                                 |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q9: What is the difference between implicit and explicit feedback?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ANSWER:                                                                 |
|                                                                          |
|  EXPLICIT FEEDBACK:                                                      |
|  - User explicitly states preference: 5-star rating, thumbs up/down      |
|  - High signal quality                                                   |
|  - Very sparse (most users don't rate)                                   |
|  - Example: Netflix star ratings (now removed)                           |
|                                                                          |
|  IMPLICIT FEEDBACK:                                                      |
|  - Inferred from behavior: views, clicks, watch time, purchases          |
|  - Lower signal quality (click != like)                                  |
|  - Very dense (every user generates it)                                  |
|  - Absence of signal is ambiguous (didn't click = dislike OR unseen?)    |
|  - Example: YouTube watch time, Amazon purchase history                  |
|                                                                          |
|  In modern systems: Almost exclusively use implicit feedback because     |
|  it is orders of magnitude more abundant. Explicit feedback is used      |
|  as supplementary signal when available.                                 |
|                                                                          |
|  Key difference in modeling:                                             |
|  - Explicit: predict rating (regression)                                 |
|  - Implicit: predict probability of interaction (classification)         |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q10: How do you handle scaling to 500M users and 100M items?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ANSWER:                                                                 |
|                                                                          |
|  1. Candidate generation is the bottleneck (100M items to search)        |
|     - Use ANN indexes (FAISS/ScaNN): query 100M vectors in <10ms         |
|     - Shard the index across multiple machines                           |
|     - Pre-filter by category/region to reduce search space               |
|                                                                          |
|  2. Feature Store must handle 50K reads/sec                              |
|     - Redis Cluster with read replicas                                   |
|     - Feature caching at the application layer                           |
|                                                                          |
|  3. Model serving at 50K QPS:                                            |
|     - Horizontal scaling with load balancers                             |
|     - Model quantization (FP16/INT8) for faster inference                |
|     - Batch inference: pre-compute for top users, real-time for rest     |
|     - GPU serving for ranking model                                      |
|                                                                          |
|  4. Training on 30TB+ data:                                              |
|     - Distributed training (Horovod, PyTorch DDP)                        |
|     - 100-1000 GPU cluster                                               |
|     - Incremental training (fine-tune on new data daily)                 |
|                                                                          |
|  5. Data pipeline: Kafka + Flink for real-time, Spark for batch          |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Q11: What is matrix factorization and when would you use it?

```
+-------------------------------------------------------------------------+
|                                                                         |
|  ANSWER:                                                                |
|                                                                         |
|  Matrix factorization decomposes the user-item interaction matrix       |
|  into two lower-dimensional matrices: U (users x k) and V (items x k).  |
|                                                                         |
|  Each user and item is represented as a k-dimensional vector            |
|  (embedding). The predicted rating is their dot product.                |
|                                                                         |
|  When to use:                                                           |
|  - Good baseline model (always start with this)                         |
|  - When you have rating/interaction data but limited item features      |
|  - When you need interpretable latent factors                           |
|  - Works well with ALS on Spark for distributed training                |
|                                                                         |
|  When NOT to use:                                                       |
|  - Severe cold start (no interactions for new users/items)              |
|  - When you have rich features (deep learning is better)                |
|  - When you need real-time adaptation to session context                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Q12: How would you design the system to support A/B testing?

```
+--------------------------------------------------------------------------+
|                                                                          |
|  ANSWER:                                                                 |
|                                                                          |
|  1. Traffic Router:                                                      |
|     - Hash user_id to deterministically assign to experiment groups      |
|     - Consistent: same user always sees same variant                     |
|     - Support nested experiments (multiple concurrent tests)             |
|                                                                          |
|  2. Experiment Config Service:                                           |
|     - Define experiments: model version, traffic %, duration             |
|     - Stored in a config store (feature flag service)                    |
|                                                                          |
|  3. Logging:                                                             |
|     - Log every recommendation shown and every interaction               |
|     - Include experiment_id and variant_id in every log                  |
|                                                                          |
|  4. Analysis Pipeline:                                                   |
|     - Compute metrics per variant                                        |
|     - Statistical significance testing                                   |
|     - Automated alerting if a variant is significantly worse             |
|                                                                          |
|  5. Guardrail metrics:                                                   |
|     - Even if CTR improves, check that revenue/retention don't drop      |
|     - Auto-stop experiments that violate guardrails                      |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## Quick Reference Card

```
+-------------------------------------------------------------------------+
|                                                                         |
|  RECOMMENDATION SYSTEM QUICK REFERENCE                                  |
|                                                                         |
|  PIPELINE: Candidate Gen -> Scoring -> Re-ranking                       |
|                                                                         |
|  ALGORITHMS:                                                            |
|  - CF:      User-based, Item-based, Matrix Factorization                |
|  - CB:      TF-IDF, feature vectors, cosine similarity                  |
|  - DL:      Two-Tower, Transformers, Wide & Deep                        |
|  - Hybrid:  Weighted, Switching, Cascade, Stacking                      |
|                                                                         |
|  COLD START:                                                            |
|  - New users: popular items, demographics, onboarding, bandits          |
|  - New items: content features, exploration budget, transfer            |
|                                                                         |
|  EVALUATION:                                                            |
|  - Offline: Precision@K, NDCG, Hit Rate                                 |
|  - Online: CTR, watch time, conversion, retention                       |
|                                                                         |
|  KEY STORES:                                                            |
|  - Feature Store (Feast/Tecton) for user & item features                |
|  - Vector Index (FAISS/ScaNN) for embedding search                      |
|  - Redis for online feature serving                                     |
|  - Kafka + S3 for interaction logging                                   |
|                                                                         |
|  BIASES: Position, popularity, selection, exposure, filter bubble       |
|  MITIGATIONS: Exploration, diversity, IPS, user controls                |
|                                                                         |
+-------------------------------------------------------------------------+
```
