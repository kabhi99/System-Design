# System Design Notes

Comprehensive system design notes covering fundamentals, real-world system designs, distributed systems, DevOps, and interview preparation.

## Fundamentals (22 chapters)

| # | Topic | Link |
|---|-------|------|
| 01 | Scalability | [Notes](md/Notes-Detailed/Fundamentals/01-Scalability.md) |
| 02 | CAP Theorem & Consistency | [Notes](md/Notes-Detailed/Fundamentals/02-CAP-And-Consistency.md) |
| 03 | Load Balancing | [Notes](md/Notes-Detailed/Fundamentals/03-Load-Balancing.md) |
| 04 | Caching | [Notes](md/Notes-Detailed/Fundamentals/04-Caching.md) |
| 05 | Databases | [Notes](md/Notes-Detailed/Fundamentals/05-Databases.md) |
| 06 | Sharding & Replication | [Notes](md/Notes-Detailed/Fundamentals/06-Sharding-And-Replication.md) |
| 07 | Message Queues | [Notes](md/Notes-Detailed/Fundamentals/07-Message-Queues.md) |
| 08 | API Design | [Notes](md/Notes-Detailed/Fundamentals/08-API-Design.md) |
| 09 | Distributed Transactions | [Notes](md/Notes-Detailed/Fundamentals/09-Distributed-Transactions.md) |
| 10 | Observability | [Notes](md/Notes-Detailed/Fundamentals/10-Observability.md) |
| 11 | Networking | [Notes](md/Notes-Detailed/Fundamentals/11-Networking.md) |
| 12 | Security | [Notes](md/Notes-Detailed/Fundamentals/12-Security.md) |
| 13 | Reverse Proxy & Processing Patterns | [Notes](md/Notes-Detailed/Fundamentals/13-Reverse-Proxy-And-Processing-Patterns.md) |
| 14 | Additional Networking | [Notes](md/Notes-Detailed/Fundamentals/14-Additional-Networking.md) |
| 15 | Architectural Patterns | [Notes](md/Notes-Detailed/Fundamentals/15-Architectural-Patterns.md) |
| 16 | Disaster Recovery & CDC | [Notes](md/Notes-Detailed/Fundamentals/16-Disaster-Recovery-And-CDC.md) |
| 17 | System Design Tradeoffs | [Notes](md/Notes-Detailed/Fundamentals/17-System-Design-Tradeoffs.md) |
| 18 | Backend Communication Patterns | [Notes](md/Notes-Detailed/Fundamentals/18-Backend-Communication-Patterns.md) |
| 19 | Protocols Deep Dive | [Notes](md/Notes-Detailed/Fundamentals/19-Protocols-Deep-Dive.md) |
| 20 | Database Internals Deep Dive | [Notes](md/Notes-Detailed/Fundamentals/20-Database-Internals-Deep-Dive.md) |
| 21 | Distributed Concurrency Control | [Notes](md/Notes-Detailed/Fundamentals/21-Distributed-Concurrency-Control.md) |
| 22 | Idempotent API Design | [Notes](md/Notes-Detailed/Fundamentals/22-Idempotent-API-Design.md) |

## System Design Problems

| System | Parts | Link |
|--------|-------|------|
| URL Shortener | 1 | [Design](md/Notes-Detailed/URL-Shortener/01-Complete-Design.md) |
| Rate Limiter | 3 | [Part 1](md/Notes-Detailed/Rate-Limiter/01-Requirements-And-Algorithms.md) |
| Notification System | 1 | [Design](md/Notes-Detailed/Notification-System/01-Complete-Design.md) |
| News Feed System | 1 | [Design](md/Notes-Detailed/News-Feed-System/01-Complete-Design.md) |
| Chat System | 1 | [Design](md/Notes-Detailed/Chat-System/01-Complete-Design.md) |
| Search / Typeahead | 1 | [Design](md/Notes-Detailed/Search-Engine-Typeahead/01-Complete-Design.md) |
| Web Crawler | 1 | [Design](md/Notes-Detailed/Web-Crawler/01-Complete-Design.md) |
| Social Media Platform | 1 | [Design](md/Notes-Detailed/Social-Media-Platform/01-Complete-Design.md) |
| Video Streaming (YouTube/Netflix) | 1 | [Design](md/Notes-Detailed/Video-Streaming/01-Complete-Design.md) |
| Video Conferencing (Zoom) | 5 | [Part 1](md/Notes-Detailed/Video-Conferencing-Zoom/01-Requirements-And-Scale.md) |
| BookMyShow (Ticket Booking) | 5 | [Part 1](md/Notes-Detailed/BookMyShow/01-Requirements-And-Scale.md) |
| Uber (Ride Sharing) | 6 | [Part 1](md/Notes-Detailed/Uber/01-Requirements-And-Scale.md) |
| Food Delivery App | 5 | [Part 1](md/Notes-Detailed/Food-Delivery-App/01-Requirements-And-Scale.md) |
| E-Commerce Platform | 4 | [Part 1](md/Notes-Detailed/E-Commerce/01-Requirements-And-Scale.md) |
| Payment Gateway | 4 | [Part 1](md/Notes-Detailed/Payment-Gateway/01-Requirements-And-Scale.md) |
| Stock Trading System | 1 | [Design](md/Notes-Detailed/Stock-Trading-System/01-Complete-Design.md) |
| Recommendation System | 1 | [Design](md/Notes-Detailed/Recommendation-System/01-Complete-Design.md) |
| File Storage System | 1 | [Design](md/Notes-Detailed/File-Storage-System/01-Complete-Design.md) |

## Distributed Systems

| System | Parts | Link |
|--------|-------|------|
| Distributed Cache | 5 | [Part 1](md/Notes-Detailed/Distributed-Cache/01-Caching-Fundamentals.md) |
| Distributed Tracing | 5 | [Part 1](md/Notes-Detailed/Distributed-Tracing/01-Requirements-And-Scale.md) |
| Distributed Job Scheduler | 1 | [Design](md/Notes-Detailed/Distributed-Job-Scheduler/01-Complete-Design.md) |
| Distributed Lock Service | 1 | [Design](md/Notes-Detailed/Distributed-Lock-Service/01-Complete-Design.md) |
| Distributed File System (GFS/HDFS) | 1 | [Design](md/Notes-Detailed/Distributed-File-System/01-Complete-Design.md) |
| Key-Value Store | 1 | [Design](md/Notes-Detailed/Key-Value-Store/01-Complete-Design.md) |
| Time-Series Database | 1 | [Design](md/Notes-Detailed/Time-Series-Database/01-Complete-Design.md) |
| CDN & Edge Computing | 1 | [Design](md/Notes-Detailed/CDN-Edge-Computing/01-Complete-Design.md) |

## Technology Deep Dives

| Technology | Parts | Link |
|------------|-------|------|
| Apache Kafka | 5 | [Fundamentals](md/Notes-Detailed/Kafka/01-Fundamentals.md) / [Architecture](md/Notes-Detailed/Kafka/02-Architecture-Deep-Dive.md) / [Producers & Consumers](md/Notes-Detailed/Kafka/03-Producers-And-Consumers.md) / [Advanced Patterns](md/Notes-Detailed/Kafka/04-Advanced-Patterns.md) / [Interview QA](md/Notes-Detailed/Kafka/05-Interview-QA.md) |
| Redis | 5 | [Data Structures](md/Notes-Detailed/Redis/01-Fundamentals-And-Data-Structures.md) / [Advanced Features](md/Notes-Detailed/Redis/02-Advanced-Features.md) / [Persistence & Clustering](md/Notes-Detailed/Redis/03-Persistence-Replication-Clustering.md) / [System Design Patterns](md/Notes-Detailed/Redis/04-Redis-In-System-Design.md) / [Interview QA](md/Notes-Detailed/Redis/05-Interview-QA.md) |
| API Gateway | 3 | [Part 1](md/Notes-Detailed/API-Gateway/01-Requirements-And-Architecture.md) |
| Microservices Architecture | 6 | [Part 1](md/Notes-Detailed/Microservices-Architecture/01-Fundamentals-And-Patterns.md) |
| Real-Time Messaging | 5 | [Part 1](md/Notes-Detailed/Real-Time-Messaging/01-Requirements-And-Scale.md) |

## DevOps

| Topic | Parts | Link |
|-------|-------|------|
| Docker Complete | 9 | [Architecture](md/DevOps/Docker-Complete/01-Docker-Architecture.md) |
| Docker Networking | 3 | [Foundations](md/DevOps/Docker-Networking/01-Linux-Networking-Foundations.md) |
| Kubernetes Complete | 21 | [Architecture](md/DevOps/Kubernetes-Complete/01-Architecture.md) |
| Kubernetes Networking | 6 | [Fundamentals](md/DevOps/Kubernetes-Networking/01-Kubernetes-Networking-Fundamentals.md) |

## Deep Dive Case Studies

Full end-to-end system design notes with all components:

| Case Study | Link |
|------------|------|
| BookMyShow | [Full Notes](md/Notes/bookmyshow_system_design.md) |
| Uber | [Full Notes](md/Notes/uber_system_design.md) |
| E-Commerce | [Full Notes](md/Notes/ecommerce_system_design.md) |
| Distributed Cache | [Full Notes](md/Notes/distributed_cache_system_design.md) |
| System Design Template | [Template](md/Notes/system_design_template.md) |

## How to Use

1. **Start with Fundamentals** -- read chapters 1-12 for core concepts
2. **Pick a system design problem** -- practice with the design problems above
3. **Deep dive into technologies** -- read Kafka, Redis for interview depth
4. **Use the template** -- follow the [System Design Template](md/Notes/system_design_template.md) for structuring your answers

## Structure

```
md/
  Notes-Detailed/         # Detailed multi-part notes by topic
    Fundamentals/         # 22 chapters of core concepts
    Kafka/                # 5-part Kafka deep dive
    Redis/                # 5-part Redis deep dive
    BookMyShow/           # 5-part ticket booking system
    Uber/                 # 6-part ride sharing system
    ...                   # 30+ system design topics
  Notes/                  # Full case study notes
  DevOps/                 # Docker & Kubernetes notes
```
