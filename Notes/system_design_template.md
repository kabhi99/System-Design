================================================================================
                         SYSTEM DESIGN NOTES TEMPLATE
================================================================================

================================================================================
1. FEATURE EXPECTATIONS [5 min]
================================================================================

(1) Use Cases
    - 
    - 
    - 

(2) Scenarios That Will Not Be Covered
    - 
    - 

(3) Who Will Use
    - 
    - 

(4) How Many Will Use
    - 

(5) Usage Patterns
    - 
    - 

================================================================================
2. ESTIMATIONS [5 min]
================================================================================

(1) Throughput
    - Queries per second (QPS) for read queries: 
    - Queries per second (QPS) for write queries: 

(2) Latency
    - Expected latency for read queries: 
    - Expected latency for write queries: 

(3) Read/Write Ratio
    - 

(4) Traffic Estimates
    - Write:
        * QPS: 
        * Volume of data: 
    - Read:
        * QPS: 
        * Volume of data: 

(5) Storage Estimates
    - 

(6) Memory Estimates
    - Cache data type: 
    - RAM required: 
    - Number of machines needed: 
    - Data to store on disk/SSD: 

================================================================================
3. DESIGN GOALS [5 min]
================================================================================

(1) Latency and Throughput Requirements
    - 

(2) Consistency vs. Availability
    - Consistency Model: [ ] Weak  [ ] Strong  [ ] Eventual
    - Availability Strategy:
        * Failover: 
        * Replication: 

================================================================================
4. HIGH-LEVEL DESIGN [5-8 min]
================================================================================

(1) APIs for Read/Write Scenarios for Crucial Components
    
    Read APIs:
    - 
    
    Write APIs:
    - 

(2) Database Schema
    
    Tables/Collections:
    - 

(3) Basic Algorithm
    - 

(4) High-Level Design for Read/Write Scenario
    
    Read Flow:
    - 
    
    Write Flow:
    - 

================================================================================
5. DEEP DIVE [10-12 min]
================================================================================

(1) Scaling the Algorithm
    - 

(2) Scaling Individual Components
    - Availability: 
    - Consistency: 
    - Scale story: 

(3) Components to Consider

    a) DNS
       - 

    b) CDN
       - Type: [ ] Push  [ ] Pull
       - Details: 

    c) Load Balancers
       - Type: [ ] Active-Passive  [ ] Active-Active
       - Layer: [ ] Layer 4  [ ] Layer 7
       - Details: 

    d) Reverse Proxy
       - 

    e) Application Layer Scaling
       - Microservices: 
       - Service Discovery: 

    f) Database Options
       
       RDBMS (ACID Properties)
       - Options: Postgres
       - Features: Primary-Secondary, Primary-Primary, Federation, Sharding, 
                   Denormalization, SQL Tuning
       - Use-cases: Structured data with relationships
       - Selection: 
       
       NoSQL
       - Options: MongoDB, DynamoDB
       - Types: Key-Value, Wide-Column, Document
       - Use-cases: Unstructured or semi-structured data
       - Selection: 
       
       Graph
       - Options: Neo4j, Amazon Neptune
       - Use-cases: Social networks, knowledge graphs, recommendation systems,
                    and bioinformatics
       - Selection: 
       
       NewSQL (Key-Value with ACID Properties)
       - Options: CockroachDB, Google Spanner, VoltDB
       - Use-cases: Transaction processing, real-time analytics, IoT device data
       - Selection: 
       
       Time Series
       - Options: InfluxDB, TimescaleDB, Prometheus
       - Use-cases: IoT sensor data, financial market data, system metrics, logs
       - Selection: 
       
       Vector (High-dimensional vector data)
       - Options: Pinecone, Weaviate, KDB.AI
       - Use-cases: Machine learning, similarity search, recommendation systems
       - Selection: 
       
       Fast Lookups:
       - RAM (Bounded size): Redis, Memcached
       - AP (Unbounded size): Cassandra, RIAK, Voldemort, DynamoDB (default mode)
       - CP (Unbounded size): HBase, MongoDB, Couchbase, DynamoDB (consistent read)
       - Selection: 

    g) Caches
       
       Caching Layers:
       - [ ] Client caching
       - [ ] CDN caching
       - [ ] Webserver caching
       - [ ] Database caching
       - [ ] Application caching
       - [ ] Cache at query level
       - [ ] Cache at object level
       
       Eviction/Update Policies:
       - [ ] Cache aside
       - [ ] Write through
       - [ ] Write behind
       - [ ] Refresh ahead
       
       Details: 

    h) Asynchronism
       - Message queues: 
       - Task queues: 
       - Back pressure: 

    i) Communication
       - [ ] TCP
       - [ ] UDP
       - [ ] REST
       - [ ] RPC
       - [ ] WebSockets
       
       Details: 

================================================================================
6. JUSTIFY [5 min]
================================================================================

(1) Throughput of Each Layer
    - 

(2) Latency Caused Between Each Layer
    - 

(3) Overall Latency Justification
    - 

================================================================================
7. KEY METRICS TO MEASURE [3 min]
================================================================================

(1) System Design Metrics
    - Availability: 
    - Latency: 
    - Throttling: 
    - Request Patterns/Volume: 
    - Customer Experience/Feature Specific Metrics: 

(2) Infrastructure and Resources Metrics
    - Tools: Grafana with Prometheus, AppDynamics, etc.
    - Details: 

================================================================================
8. SYSTEM HEALTH MONITORING [2 min]
================================================================================

(1) App Index and Latency of Microservices
    - 

(2) Monitoring Tools
    - Options: New Relic, AppDynamics, Grafana with Prometheus
    - Selection: 

(3) Canaries
    - Purpose: Simulate customer experience and pro-actively detect service 
               degradation
    - Implementation: 

================================================================================
9. LOG SYSTEMS [2 min]
================================================================================

(1) Metrics Gathering and Visualization
    - 

(2) Log Collection and Analysis
    - Tools: ELK (Elastic, Logstash, Kibana) or Splunk
    - Selection: 

================================================================================
10. SECURITY [2 min]
================================================================================

(1) Firewall
    - Encryptions at rest: 
    - Encryptions in transit: 

(2) TLS
    - 

(3) Authentication & Authorization (AuthN/Z)
    - Authentication: 
    - Authorization: 

(4) Limited Egress/Ingress
    - 

(5) Principle of Least Privilege
    - 

================================================================================
                              ADDITIONAL NOTES
================================================================================




================================================================================
                              DIAGRAM/SKETCH
================================================================================




================================================================================

