# SYSTEM DESIGN INTERVIEW QUESTIONS — COMPANY WISE

*Frequently asked system design questions mapped to companies, with links to detailed notes.*

> **How to use:** Each question links to the relevant notes file in this repo.
> Questions marked with ❌ don't have dedicated notes yet — use the brief solution hint provided.

---

## WALMART GLOBAL TECH (DETAILED)

Walmart interviews focus on **retail-scale, omnichannel, and high-throughput** systems.
System Design round appears for SDE-2+ roles. Expect questions rooted in real Walmart problems.

### Interview Focus Areas
- **Extreme scale:** Millions of daily transactions, thousands of stores + warehouses + online.
- **Omnichannel thinking:** Online + in-store + curbside pickup — not just web.
- **Peak traffic:** Black Friday / holiday flash sales with 10-50x normal traffic.
- **Real-time data:** Inventory sync, order tracking, pricing updates across regions.
- **Cost consciousness:** Frugality matters — justify infrastructure choices.

### Most Asked Questions

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design E-Commerce Platform (Walmart.com) | ★★★★★ | [E-Commerce/01-Requirements-And-Scale.md](E-Commerce/01-Requirements-And-Scale.md) |
| 2 | Design Inventory Management System | ★★★★★ | [Inventory-Management/01-Complete-Design.md](Inventory-Management/01-Complete-Design.md) |
| 3 | Design a Flash Sale / Black Friday System | ★★★★★ | [BookMyShow/03-Booking-Flow-And-Concurrency.md](BookMyShow/03-Booking-Flow-And-Concurrency.md) (concurrency patterns) + [E-Commerce/04-Inventory-Management.md](E-Commerce/04-Inventory-Management.md) |
| 4 | Design Order Fulfillment & Delivery System | ★★★★☆ | [Food-Delivery-App/03-Location-And-Delivery-Assignment.md](Food-Delivery-App/03-Location-And-Delivery-Assignment.md) (routing/assignment patterns) |
| 5 | Design a Recommendation Engine | ★★★★☆ | [Recommendation-System/01-Complete-Design.md](Recommendation-System/01-Complete-Design.md) |
| 6 | Design a Product Search System | ★★★★☆ | [Search-Engine-Typeahead/01-Complete-Design.md](Search-Engine-Typeahead/01-Complete-Design.md) |
| 7 | Design a Payment / Checkout System | ★★★★☆ | [Payment-Gateway/01-Requirements-And-Scale.md](Payment-Gateway/01-Requirements-And-Scale.md) |
| 8 | Design Dynamic Pricing & Promotions | ★★★☆☆ | ❌ *Key ideas: rule engine, regional price overrides, A/B testing pricing, coupon service, fairness compliance, price history audit trail* |
| 9 | Design Real-time Order Tracking | ★★★☆☆ | [Uber/04-ETA-And-Routing.md](Uber/04-ETA-And-Routing.md) (tracking/ETA patterns) |
| 10 | Design Curbside Pickup (BOPIS) System | ★★★☆☆ | ❌ *Key ideas: store inventory reservation, time-slot scheduling, geofence arrival detection, notification pipeline, order state machine (placed→picked→ready→collected)* |
| 11 | Design a Fraud Detection System | ★★★☆☆ | ❌ *Key ideas: ML scoring pipeline, real-time feature extraction, rule engine + ML ensemble, low-latency (<100ms) decision, feedback loop for model retraining* |
| 12 | Design Store IoT Monitoring Platform | ★★☆☆☆ | [Time-Series-Database/01-Complete-Design.md](Time-Series-Database/01-Complete-Design.md) (time-series storage patterns) |
| 13 | Design a Distributed Cache | ★★★☆☆ | [Distributed-Cache/01-Caching-Fundamentals.md](Distributed-Cache/01-Caching-Fundamentals.md) |
| 14 | Design a Notification System | ★★★☆☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 15 | Design a Rate Limiter | ★★★☆☆ | [Rate-Limiter/01-Requirements-And-Algorithms.md](Rate-Limiter/01-Requirements-And-Algorithms.md) |

### Walmart-Specific Prep Tips
- **Always mention omnichannel** — Walmart operates stores, warehouses, online, and marketplace. Interviewers want to see you think beyond pure web.
- **Black Friday is THE scenario** — every design should address "what happens at 50x traffic?" Auto-scaling, queue-based decoupling, graceful degradation.
- **Mention Kafka/event-driven** — Walmart uses event-driven microservices heavily. Bring up Kafka, CQRS, and event sourcing naturally.
- **Cost matters** — unlike pure-play tech companies, retail margins are thin. Justify cloud costs, mention spot instances, tiered storage.
- **Technologies Walmart uses:** Kafka, Cassandra, Elasticsearch, Redis, PostgreSQL, Kubernetes, React (Electrode.js), Node.js, Java/Spring Boot.

---

## GOOGLE

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design YouTube / Video Streaming Platform | ★★★★★ | [Video-Streaming/01-Complete-Design.md](Video-Streaming/01-Complete-Design.md) |
| 2 | Design Google Drive / Dropbox (File Storage) | ★★★★★ | [File-Storage-System/01-Complete-Design.md](File-Storage-System/01-Complete-Design.md) |
| 3 | Design Google Maps / Location Service | ★★★★☆ | [Google-Maps/01-Complete-Design.md](Google-Maps/01-Complete-Design.md) |
| 4 | Design Web Crawler (Googlebot) | ★★★★☆ | [Web-Crawler/01-Complete-Design.md](Web-Crawler/01-Complete-Design.md) |
| 5 | Design Search Autocomplete / Typeahead | ★★★★☆ | [Search-Engine-Typeahead/01-Complete-Design.md](Search-Engine-Typeahead/01-Complete-Design.md) |
| 6 | Design Google Docs (Real-time Collaboration) | ★★★☆☆ | [Collaborative-Editor/01-Complete-Design.md](Collaborative-Editor/01-Complete-Design.md) |
| 7 | Design Gmail / Email Service | ★★★☆☆ | [Email-System/01-Complete-Design.md](Email-System/01-Complete-Design.md) |
| 8 | Design Distributed File System (GFS) | ★★★☆☆ | [Distributed-File-System/01-Complete-Design.md](Distributed-File-System/01-Complete-Design.md) |
| 9 | Design a Chat System | ★★★☆☆ | [Chat-System/01-Complete-Design.md](Chat-System/01-Complete-Design.md) |
| 10 | Design a Recommendation System | ★★★☆☆ | [Recommendation-System/01-Complete-Design.md](Recommendation-System/01-Complete-Design.md) |
| 11 | Design a Distributed Key-Value Store | ★★★☆☆ | [Key-Value-Store/01-Complete-Design.md](Key-Value-Store/01-Complete-Design.md) |
| 12 | Design a Global Load Balancer | ★★☆☆☆ | [Fundamentals/03-Load-Balancing.md](Fundamentals/03-Load-Balancing.md) |
| 13 | Design an Ad Click Aggregation System | ★★★☆☆ | [Ad-Click-Aggregator/01-Complete-Design.md](Ad-Click-Aggregator/01-Complete-Design.md) |
| 14 | Design Nearby Friends / Proximity Service | ★★★☆☆ | [Nearby-Friends/01-Complete-Design.md](Nearby-Friends/01-Complete-Design.md) + [Proximity-Service/01-Complete-Design.md](Proximity-Service/01-Complete-Design.md) |
| 15 | Design an Object Storage System (GCS) | ★★★☆☆ | [S3-Object-Storage/01-Complete-Design.md](S3-Object-Storage/01-Complete-Design.md) |
| 16 | Design a Unique ID Generator | ★★★☆☆ | [Unique-ID-Generator/01-Complete-Design.md](Unique-ID-Generator/01-Complete-Design.md) |
| 17 | Design a Metrics Monitoring System | ★★★☆☆ | [Metrics-Monitoring/01-Complete-Design.md](Metrics-Monitoring/01-Complete-Design.md) |

---

## AMAZON

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design an E-Commerce Platform (Amazon.com) | ★★★★★ | [E-Commerce/01-Requirements-And-Scale.md](E-Commerce/01-Requirements-And-Scale.md) |
| 2 | Design a URL Shortener (TinyURL) | ★★★★★ | [URL-Shortener/01-Complete-Design.md](URL-Shortener/01-Complete-Design.md) |
| 3 | Design a Notification System | ★★★★☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 4 | Design a Rate Limiter | ★★★★☆ | [Rate-Limiter/01-Requirements-And-Algorithms.md](Rate-Limiter/01-Requirements-And-Algorithms.md) |
| 5 | Design a Distributed Cache | ★★★★☆ | [Distributed-Cache/01-Caching-Fundamentals.md](Distributed-Cache/01-Caching-Fundamentals.md) |
| 6 | Design a Search/Product Search Engine | ★★★★☆ | [Search-Engine-Typeahead/01-Complete-Design.md](Search-Engine-Typeahead/01-Complete-Design.md) |
| 7 | Design a Payment System | ★★★★☆ | [Payment-Gateway/01-Requirements-And-Scale.md](Payment-Gateway/01-Requirements-And-Scale.md) |
| 8 | Design a Recommendation System | ★★★☆☆ | [Recommendation-System/01-Complete-Design.md](Recommendation-System/01-Complete-Design.md) |
| 9 | Design a Distributed Key-Value Store (DynamoDB) | ★★★☆☆ | [Key-Value-Store/01-Complete-Design.md](Key-Value-Store/01-Complete-Design.md) |
| 10 | Design a Video Streaming Platform (Prime Video) | ★★★☆☆ | [Video-Streaming/01-Complete-Design.md](Video-Streaming/01-Complete-Design.md) |
| 11 | Design a Task/Job Scheduler | ★★★☆☆ | [Distributed-Job-Scheduler/01-Complete-Design.md](Distributed-Job-Scheduler/01-Complete-Design.md) |
| 12 | Design an Order Processing System | ★★★☆☆ | [E-Commerce/03-Checkout-And-Saga.md](E-Commerce/03-Checkout-And-Saga.md) |
| 13 | Design S3 / Object Storage | ★★★☆☆ | [S3-Object-Storage/01-Complete-Design.md](S3-Object-Storage/01-Complete-Design.md) |
| 14 | Design an Inventory Management System | ★★★☆☆ | [Inventory-Management/01-Complete-Design.md](Inventory-Management/01-Complete-Design.md) |
| 15 | Design a Unique ID Generator | ★★★☆☆ | [Unique-ID-Generator/01-Complete-Design.md](Unique-ID-Generator/01-Complete-Design.md) |
| 16 | Design a Metrics Monitoring System | ★★★☆☆ | [Metrics-Monitoring/01-Complete-Design.md](Metrics-Monitoring/01-Complete-Design.md) |

---

## META (FACEBOOK / INSTAGRAM)

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design Facebook/Instagram News Feed | ★★★★★ | [News-Feed-System/01-Complete-Design.md](News-Feed-System/01-Complete-Design.md) |
| 2 | Design WhatsApp / Messenger (Real-time Chat) | ★★★★★ | [Real-Time-Messaging/01-Requirements-And-Scale.md](Real-Time-Messaging/01-Requirements-And-Scale.md) |
| 3 | Design Instagram / Social Media Platform | ★★★★☆ | [Social-Media-Platform/01-Complete-Design.md](Social-Media-Platform/01-Complete-Design.md) |
| 4 | Design a Notification System | ★★★★☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 5 | Design Facebook Live / Live Video Streaming | ★★★☆☆ | [Video-Streaming/01-Complete-Design.md](Video-Streaming/01-Complete-Design.md) + [Video-Conferencing-Zoom/03-Meeting-Flow-And-WebRTC.md](Video-Conferencing-Zoom/03-Meeting-Flow-And-WebRTC.md) |
| 6 | Design a Content Moderation System | ★★★☆☆ | ❌ *Key ideas: ML classifiers, human review queue, priority scoring, appeals workflow, hash-based duplicate detection (PhotoDNA)* |
| 7 | Design a Real-time Ad Ranking System | ★★★☆☆ | ❌ *Key ideas: CTR prediction model, auction (second-price), feature store, real-time bidding pipeline, budget pacing* |
| 8 | Design Stories / Reels (Ephemeral Content) | ★★★☆☆ | [CDN-Edge-Computing/01-Complete-Design.md](CDN-Edge-Computing/01-Complete-Design.md) (CDN patterns) |
| 9 | Design a Rate Limiter | ★★★☆☆ | [Rate-Limiter/01-Requirements-And-Algorithms.md](Rate-Limiter/01-Requirements-And-Algorithms.md) |
| 10 | Design a Recommendation/People-You-May-Know System | ★★★☆☆ | [Recommendation-System/01-Complete-Design.md](Recommendation-System/01-Complete-Design.md) |
| 11 | Design Nearby Friends | ★★★☆☆ | [Nearby-Friends/01-Complete-Design.md](Nearby-Friends/01-Complete-Design.md) |
| 12 | Design an Ad Click Aggregation System | ★★★☆☆ | [Ad-Click-Aggregator/01-Complete-Design.md](Ad-Click-Aggregator/01-Complete-Design.md) |

---

## MICROSOFT

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design a Chat System (Teams) | ★★★★★ | [Chat-System/01-Complete-Design.md](Chat-System/01-Complete-Design.md) |
| 2 | Design a Video Conferencing System (Teams/Zoom) | ★★★★☆ | [Video-Conferencing-Zoom/01-Requirements-And-Scale.md](Video-Conferencing-Zoom/01-Requirements-And-Scale.md) |
| 3 | Design a File Storage System (OneDrive) | ★★★★☆ | [File-Storage-System/01-Complete-Design.md](File-Storage-System/01-Complete-Design.md) |
| 4 | Design a Distributed Cache | ★★★★☆ | [Distributed-Cache/01-Caching-Fundamentals.md](Distributed-Cache/01-Caching-Fundamentals.md) |
| 5 | Design a Notification System | ★★★☆☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 6 | Design a URL Shortener | ★★★☆☆ | [URL-Shortener/01-Complete-Design.md](URL-Shortener/01-Complete-Design.md) |
| 7 | Design a Search Engine / Bing | ★★★☆☆ | [Search-Engine-Typeahead/01-Complete-Design.md](Search-Engine-Typeahead/01-Complete-Design.md) + [Web-Crawler/01-Complete-Design.md](Web-Crawler/01-Complete-Design.md) |
| 8 | Design a Collaborative Editor (Office Online) | ★★★☆☆ | [Collaborative-Editor/01-Complete-Design.md](Collaborative-Editor/01-Complete-Design.md) |
| 9 | Design an API Gateway | ★★★☆☆ | [API-Gateway/01-Requirements-And-Architecture.md](API-Gateway/01-Requirements-And-Architecture.md) |
| 10 | Design a Distributed Lock Service | ★★☆☆☆ | [Distributed-Lock-Service/01-Complete-Design.md](Distributed-Lock-Service/01-Complete-Design.md) |
| 11 | Design an Object Storage System (Azure Blob) | ★★☆☆☆ | [S3-Object-Storage/01-Complete-Design.md](S3-Object-Storage/01-Complete-Design.md) |

---

## NETFLIX

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design Netflix / Video Streaming Platform | ★★★★★ | [Video-Streaming/01-Complete-Design.md](Video-Streaming/01-Complete-Design.md) |
| 2 | Design a Recommendation System | ★★★★★ | [Recommendation-System/01-Complete-Design.md](Recommendation-System/01-Complete-Design.md) |
| 3 | Design a CDN | ★★★★☆ | [CDN-Edge-Computing/01-Complete-Design.md](CDN-Edge-Computing/01-Complete-Design.md) |
| 4 | Design a Rate Limiter | ★★★☆☆ | [Rate-Limiter/01-Requirements-And-Algorithms.md](Rate-Limiter/01-Requirements-And-Algorithms.md) |
| 5 | Design a Distributed Tracing System | ★★★☆☆ | [Distributed-Tracing/01-Requirements-And-Scale.md](Distributed-Tracing/01-Requirements-And-Scale.md) |
| 6 | Design a Notification System | ★★★☆☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 7 | Design a Time Series Database (Monitoring) | ★★★☆☆ | [Time-Series-Database/01-Complete-Design.md](Time-Series-Database/01-Complete-Design.md) |
| 8 | Design a Distributed Job Scheduler | ★★☆☆☆ | [Distributed-Job-Scheduler/01-Complete-Design.md](Distributed-Job-Scheduler/01-Complete-Design.md) |
| 9 | Design a Metrics Monitoring System | ★★★☆☆ | [Metrics-Monitoring/01-Complete-Design.md](Metrics-Monitoring/01-Complete-Design.md) |

---

## UBER / LYFT

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design a Ride-Hailing System (Uber) | ★★★★★ | [Uber/01-Requirements-And-Scale.md](Uber/01-Requirements-And-Scale.md) |
| 2 | Design Geospatial Indexing / Proximity Service | ★★★★★ | [Uber/02-Geospatial-Indexing.md](Uber/02-Geospatial-Indexing.md) |
| 3 | Design Surge Pricing | ★★★★☆ | [Uber/05-Pricing-And-Surge.md](Uber/05-Pricing-And-Surge.md) |
| 4 | Design ETA / Routing Service | ★★★★☆ | [Uber/04-ETA-And-Routing.md](Uber/04-ETA-And-Routing.md) |
| 5 | Design a Food Delivery System (Uber Eats) | ★★★★☆ | [Food-Delivery-App/01-Requirements-And-Scale.md](Food-Delivery-App/01-Requirements-And-Scale.md) |
| 6 | Design a Real-time Matching System | ★★★★☆ | [Uber/03-Real-Time-Matching.md](Uber/03-Real-Time-Matching.md) |
| 7 | Design a Notification System | ★★★☆☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 8 | Design a Payment System | ★★★☆☆ | [Payment-Gateway/01-Requirements-And-Scale.md](Payment-Gateway/01-Requirements-And-Scale.md) |
| 9 | Design Nearby Friends | ★★★☆☆ | [Nearby-Friends/01-Complete-Design.md](Nearby-Friends/01-Complete-Design.md) |

---

## STRIPE / PAYMENT COMPANIES

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design a Payment Gateway | ★★★★★ | [Payment-Gateway/01-Requirements-And-Scale.md](Payment-Gateway/01-Requirements-And-Scale.md) |
| 2 | Design Idempotent Payment API | ★★★★★ | [Payment-Gateway/03-Payment-Flow-And-Idempotency.md](Payment-Gateway/03-Payment-Flow-And-Idempotency.md) + [Fundamentals/22-Idempotent-API-Design.md](Fundamentals/22-Idempotent-API-Design.md) |
| 3 | Design a Rate Limiter | ★★★★☆ | [Rate-Limiter/01-Requirements-And-Algorithms.md](Rate-Limiter/01-Requirements-And-Algorithms.md) |
| 4 | Design a Distributed LRU Cache | ★★★★☆ | [Distributed-Cache/01-Caching-Fundamentals.md](Distributed-Cache/01-Caching-Fundamentals.md) |
| 5 | Design a Webhook Delivery System | ★★★★☆ | ❌ *Key ideas: at-least-once delivery, exponential backoff retry, dead-letter queue, idempotency key, event log, signature verification* |
| 6 | Design a Multi-Currency Ledger | ★★★☆☆ | ❌ *Key ideas: double-entry bookkeeping, immutable append-only log, currency conversion service, eventual consistency, audit trail* |
| 7 | Design an Application Monitoring System | ★★★☆☆ | [Distributed-Tracing/01-Requirements-And-Scale.md](Distributed-Tracing/01-Requirements-And-Scale.md) + [Time-Series-Database/01-Complete-Design.md](Time-Series-Database/01-Complete-Design.md) |

---

## APPLE

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design iMessage / Chat System | ★★★★★ | [Real-Time-Messaging/01-Requirements-And-Scale.md](Real-Time-Messaging/01-Requirements-And-Scale.md) |
| 2 | Design a Search Autocomplete / Typeahead | ★★★★☆ | [Search-Engine-Typeahead/01-Complete-Design.md](Search-Engine-Typeahead/01-Complete-Design.md) |
| 3 | Design iCloud / File Storage | ★★★★☆ | [File-Storage-System/01-Complete-Design.md](File-Storage-System/01-Complete-Design.md) |
| 4 | Design a Notification System (APNs) | ★★★★☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 5 | Design a CDN for App Store | ★★★☆☆ | [CDN-Edge-Computing/01-Complete-Design.md](CDN-Edge-Computing/01-Complete-Design.md) |
| 6 | Design a Distributed Key-Value Store | ★★★☆☆ | [Key-Value-Store/01-Complete-Design.md](Key-Value-Store/01-Complete-Design.md) |
| 7 | Design a Video Streaming Service (Apple TV+) | ★★★☆☆ | [Video-Streaming/01-Complete-Design.md](Video-Streaming/01-Complete-Design.md) |

---

## LINKEDIN

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design a News Feed / Activity Feed | ★★★★★ | [News-Feed-System/01-Complete-Design.md](News-Feed-System/01-Complete-Design.md) |
| 2 | Design a Recommendation System (People You May Know) | ★★★★☆ | [Recommendation-System/01-Complete-Design.md](Recommendation-System/01-Complete-Design.md) |
| 3 | Design a Search / Typeahead System | ★★★★☆ | [Search-Engine-Typeahead/01-Complete-Design.md](Search-Engine-Typeahead/01-Complete-Design.md) |
| 4 | Design a Notification System | ★★★☆☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 5 | Design a Messaging System | ★★★☆☆ | [Chat-System/01-Complete-Design.md](Chat-System/01-Complete-Design.md) |
| 6 | Design a Rate Limiter | ★★★☆☆ | [Rate-Limiter/01-Requirements-And-Algorithms.md](Rate-Limiter/01-Requirements-And-Algorithms.md) |
| 7 | Design Kafka / Event Streaming Platform | ★★★☆☆ | [Kafka/01-Fundamentals.md](Kafka/01-Fundamentals.md) |

---

## TWITTER (X)

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design Twitter Timeline / News Feed | ★★★★★ | [News-Feed-System/01-Complete-Design.md](News-Feed-System/01-Complete-Design.md) |
| 2 | Design a URL Shortener (t.co) | ★★★★☆ | [URL-Shortener/01-Complete-Design.md](URL-Shortener/01-Complete-Design.md) |
| 3 | Design a Rate Limiter | ★★★★☆ | [Rate-Limiter/01-Requirements-And-Algorithms.md](Rate-Limiter/01-Requirements-And-Algorithms.md) |
| 4 | Design a Social Media Platform | ★★★★☆ | [Social-Media-Platform/01-Complete-Design.md](Social-Media-Platform/01-Complete-Design.md) |
| 5 | Design a Notification System | ★★★☆☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 6 | Design Search / Trending Topics | ★★★☆☆ | [Search-Engine-Typeahead/01-Complete-Design.md](Search-Engine-Typeahead/01-Complete-Design.md) |
| 7 | Design a CDN | ★★☆☆☆ | [CDN-Edge-Computing/01-Complete-Design.md](CDN-Edge-Computing/01-Complete-Design.md) |
| 8 | Design an Ad Click Aggregation System | ★★★☆☆ | [Ad-Click-Aggregator/01-Complete-Design.md](Ad-Click-Aggregator/01-Complete-Design.md) |

---

## AIRBNB / BOOKING PLATFORMS

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design a Booking System (BookMyShow / Airbnb) | ★★★★★ | [BookMyShow/01-Requirements-And-Scale.md](BookMyShow/01-Requirements-And-Scale.md) |
| 2 | Design a Search / Proximity Service | ★★★★☆ | [Proximity-Service/01-Complete-Design.md](Proximity-Service/01-Complete-Design.md) |
| 3 | Design a Payment System | ★★★★☆ | [Payment-Gateway/01-Requirements-And-Scale.md](Payment-Gateway/01-Requirements-And-Scale.md) |
| 4 | Design a Recommendation System | ★★★☆☆ | [Recommendation-System/01-Complete-Design.md](Recommendation-System/01-Complete-Design.md) |
| 5 | Design a Notification System | ★★★☆☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 6 | Design a Chat System (Host-Guest Messaging) | ★★★☆☆ | [Chat-System/01-Complete-Design.md](Chat-System/01-Complete-Design.md) |
| 7 | Design a Hotel Reservation System | ★★★★☆ | [Hotel-Reservation/01-Complete-Design.md](Hotel-Reservation/01-Complete-Design.md) |
| 8 | Design an Auction / Bidding System | ★★★☆☆ | [Auction-System/01-Complete-Design.md](Auction-System/01-Complete-Design.md) |

---

## FLIPKART / MEESHO

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design an E-Commerce Platform | ★★★★★ | [E-Commerce/01-Requirements-And-Scale.md](E-Commerce/01-Requirements-And-Scale.md) |
| 2 | Design a Booking System (BookMyShow) | ★★★★☆ | [BookMyShow/01-Requirements-And-Scale.md](BookMyShow/01-Requirements-And-Scale.md) |
| 3 | Design a Recommendation System | ★★★★☆ | [Recommendation-System/01-Complete-Design.md](Recommendation-System/01-Complete-Design.md) |
| 4 | Design a URL Shortener | ★★★★☆ | [URL-Shortener/01-Complete-Design.md](URL-Shortener/01-Complete-Design.md) |
| 5 | Design a Notification System | ★★★☆☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 6 | Design a Rate Limiter | ★★★☆☆ | [Rate-Limiter/01-Requirements-And-Algorithms.md](Rate-Limiter/01-Requirements-And-Algorithms.md) |
| 7 | Design a Distributed Cache (Redis) | ★★★☆☆ | [Distributed-Cache/01-Caching-Fundamentals.md](Distributed-Cache/01-Caching-Fundamentals.md) + [Redis/01-Fundamentals-And-Data-Structures.md](Redis/01-Fundamentals-And-Data-Structures.md) |
| 8 | Design a CDN | ★★★☆☆ | [CDN-Edge-Computing/01-Complete-Design.md](CDN-Edge-Computing/01-Complete-Design.md) |
| 9 | Design an Inventory Management System | ★★★☆☆ | [Inventory-Management/01-Complete-Design.md](Inventory-Management/01-Complete-Design.md) |

---

## PAYTM / PHONEPE / RAZORPAY (FINTECH)

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design a Digital Wallet / UPI System | ★★★★★ | [Digital-Wallet/01-Complete-Design.md](Digital-Wallet/01-Complete-Design.md) + [Payment-Gateway/01-Requirements-And-Scale.md](Payment-Gateway/01-Requirements-And-Scale.md) |
| 2 | Design a Payment Gateway | ★★★★★ | [Payment-Gateway/01-Requirements-And-Scale.md](Payment-Gateway/01-Requirements-And-Scale.md) |
| 3 | Design Idempotent Transaction API | ★★★★☆ | [Payment-Gateway/03-Payment-Flow-And-Idempotency.md](Payment-Gateway/03-Payment-Flow-And-Idempotency.md) + [Fundamentals/22-Idempotent-API-Design.md](Fundamentals/22-Idempotent-API-Design.md) |
| 4 | Design a Fraud Detection System | ★★★★☆ | ❌ *Key ideas: ML scoring pipeline, real-time feature extraction, rule engine + ML, <100ms latency, feedback loop* |
| 5 | Design a Notification System (OTP/Alerts) | ★★★★☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 6 | Design a Rate Limiter | ★★★☆☆ | [Rate-Limiter/01-Requirements-And-Algorithms.md](Rate-Limiter/01-Requirements-And-Algorithms.md) |
| 7 | Design a Distributed Cache | ★★★☆☆ | [Distributed-Cache/01-Caching-Fundamentals.md](Distributed-Cache/01-Caching-Fundamentals.md) |
| 8 | Design a Ledger / Transaction Log | ★★★☆☆ | ❌ *Key ideas: double-entry bookkeeping, append-only log, ACID, idempotency, audit trail, reconciliation* |
| 9 | Design a Chat System | ★★★☆☆ | [Chat-System/01-Complete-Design.md](Chat-System/01-Complete-Design.md) |

**Fintech-specific tips:** Expect deep questions on ACID, optimistic vs pessimistic locking, PCI-DSS compliance, tokenization, encryption at rest/transit, double-spend prevention, and reconciliation.

---

## ZEPTO / BLINKIT / SWIGGY (QUICK COMMERCE & FOOD DELIVERY)

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design a Food Delivery App (Swiggy/Zomato) | ★★★★★ | [Food-Delivery-App/01-Requirements-And-Scale.md](Food-Delivery-App/01-Requirements-And-Scale.md) |
| 2 | Design a Quick Commerce / 10-min Delivery System | ★★★★★ | [Food-Delivery-App/03-Location-And-Delivery-Assignment.md](Food-Delivery-App/03-Location-And-Delivery-Assignment.md) (delivery assignment) + ❌ *Key ideas: dark store inventory, hyperlocal geofencing, demand prediction per store, delivery slot management, real-time rider tracking* |
| 3 | Design Inventory Management (Dark Store) | ★★★★☆ | [Inventory-Management/01-Complete-Design.md](Inventory-Management/01-Complete-Design.md) |
| 4 | Design a Real-time Order Tracking System | ★★★★☆ | [Uber/04-ETA-And-Routing.md](Uber/04-ETA-And-Routing.md) (ETA/tracking patterns) |
| 5 | Design a Cart / Checkout System | ★★★★☆ | [E-Commerce/03-Checkout-And-Saga.md](E-Commerce/03-Checkout-And-Saga.md) |
| 6 | Design a Messaging System (WhatsApp) | ★★★☆☆ | [Real-Time-Messaging/01-Requirements-And-Scale.md](Real-Time-Messaging/01-Requirements-And-Scale.md) |
| 7 | Design a Notification System | ★★★☆☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 8 | Design a Recommendation System | ★★★☆☆ | [Recommendation-System/01-Complete-Design.md](Recommendation-System/01-Complete-Design.md) |
| 9 | Design a Rate Limiter | ★★★☆☆ | [Rate-Limiter/01-Requirements-And-Algorithms.md](Rate-Limiter/01-Requirements-And-Algorithms.md) |

**Quick commerce tips:** Think hyperlocal — dark stores, small delivery radius, sub-10-min SLA. Mention geofencing, delivery slot optimization, demand surge handling, and real-time rider allocation.

---

## ZETA (FINTECH INFRA)

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design a Payment Processing System | ★★★★★ | [Payment-Gateway/01-Requirements-And-Scale.md](Payment-Gateway/01-Requirements-And-Scale.md) |
| 2 | Design a Distributed Cache | ★★★★☆ | [Distributed-Cache/01-Caching-Fundamentals.md](Distributed-Cache/01-Caching-Fundamentals.md) |
| 3 | Design a Real-time Event Processing Pipeline | ★★★★☆ | [Kafka/01-Fundamentals.md](Kafka/01-Fundamentals.md) (Kafka patterns) |
| 4 | Design a Rate Limiter | ★★★☆☆ | [Rate-Limiter/01-Requirements-And-Algorithms.md](Rate-Limiter/01-Requirements-And-Algorithms.md) |
| 5 | Design a Notification System | ★★★☆☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 6 | Design a Distributed Job Scheduler | ★★★☆☆ | [Distributed-Job-Scheduler/01-Complete-Design.md](Distributed-Job-Scheduler/01-Complete-Design.md) |

**Zeta tips:** Banking-as-a-service infra. Expect questions on multi-tenancy, high-throughput event pipelines (Kafka/Spark), compliance (PCI-DSS, RBI), and white-label card platform design.

---

## HOTSTAR / DREAM11 (MEDIA & GAMING)

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design a Live Video Streaming System (Hotstar IPL) | ★★★★★ | [Video-Streaming/01-Complete-Design.md](Video-Streaming/01-Complete-Design.md) |
| 2 | Design a Real-time Leaderboard (Dream11) | ★★★★★ | ❌ *Key ideas: sorted set (Redis ZSET), real-time score ingestion via Kafka, sharded leaderboard, fan-out on update, pagination, contest-scoped ranking* |
| 3 | Design a CDN | ★★★★☆ | [CDN-Edge-Computing/01-Complete-Design.md](CDN-Edge-Computing/01-Complete-Design.md) |
| 4 | Design a Recommendation System | ★★★★☆ | [Recommendation-System/01-Complete-Design.md](Recommendation-System/01-Complete-Design.md) |
| 5 | Design a Notification System | ★★★☆☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 6 | Design a Stock Trading System (Zerodha) | ★★★☆☆ | [Stock-Trading-System/01-Complete-Design.md](Stock-Trading-System/01-Complete-Design.md) |
| 7 | Design a Chat System | ★★★☆☆ | [Chat-System/01-Complete-Design.md](Chat-System/01-Complete-Design.md) |
| 8 | Design a Rate Limiter | ★★★☆☆ | [Rate-Limiter/01-Requirements-And-Algorithms.md](Rate-Limiter/01-Requirements-And-Algorithms.md) |

**Hotstar tips:** IPL-scale spike (25M+ concurrent users). Mention adaptive bitrate, CDN edge caching, pre-warming, graceful degradation.
**Dream11 tips:** Contest-based gaming. Real-time scoring, leaderboard at scale, concurrent contest creation, anti-fraud.

---

## CRED / GROWW

| # | Question | Frequency | Notes Link |
|---|----------|-----------|------------|
| 1 | Design a Payment Gateway | ★★★★★ | [Payment-Gateway/01-Requirements-And-Scale.md](Payment-Gateway/01-Requirements-And-Scale.md) |
| 2 | Design a Stock Trading / Portfolio System (Groww) | ★★★★☆ | [Stock-Trading-System/01-Complete-Design.md](Stock-Trading-System/01-Complete-Design.md) |
| 3 | Design a Reward / Cashback System (CRED) | ★★★★☆ | ❌ *Key ideas: event-driven reward calculation, rule engine, wallet service, expiry/clawback, idempotent credit* |
| 4 | Design a Notification System | ★★★☆☆ | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 5 | Design a Distributed Cache | ★★★☆☆ | [Distributed-Cache/01-Caching-Fundamentals.md](Distributed-Cache/01-Caching-Fundamentals.md) |
| 6 | Design a Rate Limiter | ★★★☆☆ | [Rate-Limiter/01-Requirements-And-Algorithms.md](Rate-Limiter/01-Requirements-And-Algorithms.md) |
| 7 | Design a Recommendation System | ★★★☆☆ | [Recommendation-System/01-Complete-Design.md](Recommendation-System/01-Complete-Design.md) |
| 8 | Design a Digital Wallet | ★★★☆☆ | [Digital-Wallet/01-Complete-Design.md](Digital-Wallet/01-Complete-Design.md) |

**CRED tips:** Credit card bill payments, reward points, merchant offers. Clean design culture.
**Groww tips:** Real-time market data ingestion, portfolio valuation, mutual fund SIP scheduling, regulatory compliance (SEBI).

---

## CROSS-COMPANY: MOST UNIVERSAL QUESTIONS

These questions are asked at **almost every** top company:

| # | Question | Companies | Notes Link |
|---|----------|-----------|------------|
| 1 | Design a URL Shortener | Google, Amazon, Microsoft, Twitter | [URL-Shortener/01-Complete-Design.md](URL-Shortener/01-Complete-Design.md) |
| 2 | Design a Rate Limiter | All companies | [Rate-Limiter/01-Requirements-And-Algorithms.md](Rate-Limiter/01-Requirements-And-Algorithms.md) |
| 3 | Design a Notification System | All companies | [Notification-System/01-Complete-Design.md](Notification-System/01-Complete-Design.md) |
| 4 | Design a Distributed Cache | Amazon, Microsoft, Stripe, Netflix | [Distributed-Cache/01-Caching-Fundamentals.md](Distributed-Cache/01-Caching-Fundamentals.md) |
| 5 | Design a Chat/Messaging System | Meta, Apple, Microsoft, Airbnb | [Real-Time-Messaging/01-Requirements-And-Scale.md](Real-Time-Messaging/01-Requirements-And-Scale.md) |
| 6 | Design a News Feed | Meta, Twitter, LinkedIn | [News-Feed-System/01-Complete-Design.md](News-Feed-System/01-Complete-Design.md) |
| 7 | Design a Video Streaming Platform | Google, Netflix, Apple, Hotstar | [Video-Streaming/01-Complete-Design.md](Video-Streaming/01-Complete-Design.md) |
| 8 | Design a Payment System | Amazon, Uber, Stripe, Airbnb | [Payment-Gateway/01-Requirements-And-Scale.md](Payment-Gateway/01-Requirements-And-Scale.md) |
| 9 | Design a Recommendation System | Google, Amazon, Netflix, LinkedIn | [Recommendation-System/01-Complete-Design.md](Recommendation-System/01-Complete-Design.md) |
| 10 | Design a Web Crawler | Google, Amazon, Microsoft | [Web-Crawler/01-Complete-Design.md](Web-Crawler/01-Complete-Design.md) |
| 11 | Design a Unique ID Generator | All companies (building block) | [Unique-ID-Generator/01-Complete-Design.md](Unique-ID-Generator/01-Complete-Design.md) |
| 12 | Design a Proximity Service | Uber, Airbnb, Swiggy, Google | [Proximity-Service/01-Complete-Design.md](Proximity-Service/01-Complete-Design.md) |
| 13 | Design an Object Storage System (S3) | Amazon, Google, Microsoft | [S3-Object-Storage/01-Complete-Design.md](S3-Object-Storage/01-Complete-Design.md) |
| 14 | Design an Ad Click Aggregation System | Google, Meta, Twitter | [Ad-Click-Aggregator/01-Complete-Design.md](Ad-Click-Aggregator/01-Complete-Design.md) |
| 15 | Design a Metrics Monitoring System | Netflix, Google, Amazon | [Metrics-Monitoring/01-Complete-Design.md](Metrics-Monitoring/01-Complete-Design.md) |

---

## FUNDAMENTALS TO REVIEW BEFORE ANY INTERVIEW

These apply regardless of which company you're interviewing at:

| Topic | Notes Link |
|-------|------------|
| Scalability & Back-of-Envelope | [Fundamentals/01-Scalability.md](Fundamentals/01-Scalability.md) |
| CAP Theorem & Consistency | [Fundamentals/02-CAP-And-Consistency.md](Fundamentals/02-CAP-And-Consistency.md) |
| Load Balancing | [Fundamentals/03-Load-Balancing.md](Fundamentals/03-Load-Balancing.md) |
| Caching Strategies | [Fundamentals/04-Caching.md](Fundamentals/04-Caching.md) |
| Databases (SQL vs NoSQL) | [Fundamentals/05-Databases.md](Fundamentals/05-Databases.md) |
| Sharding & Replication | [Fundamentals/06-Sharding-And-Replication.md](Fundamentals/06-Sharding-And-Replication.md) |
| Message Queues | [Fundamentals/07-Message-Queues.md](Fundamentals/07-Message-Queues.md) |
| API Design & Spec-Driven Dev | [Fundamentals/08-API-Design.md](Fundamentals/08-API-Design.md) |
| Distributed Transactions | [Fundamentals/09-Distributed-Transactions.md](Fundamentals/09-Distributed-Transactions.md) |
| Observability | [Fundamentals/10-Observability.md](Fundamentals/10-Observability.md) |
| Networking | [Fundamentals/11-Networking.md](Fundamentals/11-Networking.md) |
| Security | [Fundamentals/12-Security.md](Fundamentals/12-Security.md) |
| Reverse Proxy & Processing Patterns | [Fundamentals/13-Reverse-Proxy-And-Processing-Patterns.md](Fundamentals/13-Reverse-Proxy-And-Processing-Patterns.md) |
| Additional Networking | [Fundamentals/14-Additional-Networking.md](Fundamentals/14-Additional-Networking.md) |
| Architectural Patterns | [Fundamentals/15-Architectural-Patterns.md](Fundamentals/15-Architectural-Patterns.md) |
| Disaster Recovery & CDC | [Fundamentals/16-Disaster-Recovery-And-CDC.md](Fundamentals/16-Disaster-Recovery-And-CDC.md) |
| System Design Tradeoffs | [Fundamentals/17-System-Design-Tradeoffs.md](Fundamentals/17-System-Design-Tradeoffs.md) |
| Backend Communication Patterns | [Fundamentals/18-Backend-Communication-Patterns.md](Fundamentals/18-Backend-Communication-Patterns.md) |
| Protocols Deep Dive | [Fundamentals/19-Protocols-Deep-Dive.md](Fundamentals/19-Protocols-Deep-Dive.md) |
| Database Internals Deep Dive | [Fundamentals/20-Database-Internals-Deep-Dive.md](Fundamentals/20-Database-Internals-Deep-Dive.md) |
| Distributed Concurrency Control | [Fundamentals/21-Distributed-Concurrency-Control.md](Fundamentals/21-Distributed-Concurrency-Control.md) |
| Idempotent API Design | [Fundamentals/22-Idempotent-API-Design.md](Fundamentals/22-Idempotent-API-Design.md) |
| Interview Followup Questions | [Fundamentals/23-Interview-Followup-Questions.md](Fundamentals/23-Interview-Followup-Questions.md) |
| Production Issues & Solutions | [Fundamentals/24-Production-Issues-And-Solutions.md](Fundamentals/24-Production-Issues-And-Solutions.md) |
| Microservices Architecture | [Microservices-Architecture/01-Fundamentals-And-Patterns.md](Microservices-Architecture/01-Fundamentals-And-Patterns.md) |
| Kafka Deep Dive | [Kafka/01-Fundamentals.md](Kafka/01-Fundamentals.md) |
| Redis Deep Dive | [Redis/01-Fundamentals-And-Data-Structures.md](Redis/01-Fundamentals-And-Data-Structures.md) |

---

## COVERAGE GAPS (Questions Not Yet in Notes)

| Question | Asked At | Brief Solution Hint |
|----------|----------|---------------------|
| Design Dynamic Pricing & Promotions | Walmart, Amazon, Airbnb | Rule engine, regional overrides, A/B testing, coupon service, fairness compliance, price history audit |
| Design a Curbside Pickup (BOPIS) System | Walmart | Store inventory reservation, time-slot scheduling, geofence arrival, notification pipeline, order state machine |
| Design a Fraud Detection System | Walmart, Stripe, Amazon | ML scoring pipeline, real-time feature extraction, rule engine + ML, <100ms latency, feedback loop |
| Design a Content Moderation System | Meta, Twitter | ML classifiers (text + image + video), human review queue, priority scoring, hash-matching (PhotoDNA/pDNA), appeals workflow, audit log |
| Design a Real-time Ad Ranking System | Meta, Google | CTR prediction (ML), second-price auction, feature store, real-time bidding pipeline, budget pacing, A/B testing |
| Design a Webhook Delivery System | Stripe, Shopify | At-least-once delivery, exponential backoff retry, DLQ, idempotency key, event log, HMAC signature verification |
| Design a Multi-Currency Ledger | Stripe, Payment cos. | Double-entry bookkeeping, immutable append-only log, FX conversion service, eventual consistency, audit trail |
| Design a Code Deployment System | Google, Amazon, Netflix | Rolling/blue-green/canary deploy, artifact store, health checks, rollback, feature flags, deploy pipeline |
| Design a Real-time Leaderboard | Dream11, Hotstar, Gaming cos. | Redis ZSET, real-time score ingestion via Kafka, sharded leaderboard, fan-out on update, pagination |
| Design a Reward / Cashback System | CRED, Paytm, Flipkart | Event-driven reward calculation, rule engine, wallet service, expiry/clawback, idempotent credit |

---

*Last updated: Mar 2026*
*Sources: Exponent, DesignGurus, SystemDesignHandbook, Educative, InterviewKickstart, Glassdoor, AmbitionBox, Prepfully, PlacementPreparation.io, HackerPrep*
