# 🧠 SYSTEM DESIGN INTERVIEW GUIDE — 2026 Edition

> This guide alone is worth $50+. Study this before your next senior dev interview.

---

## 📊 How to Approach Any System Design Question

### The 4-Step Framework (Use this EVERY time)

```
Step 1: CLARIFY (3-5 min)     → Ask questions, define scope
Step 2: ESTIMATE (3-5 min)    → Back-of-envelope calculations
Step 3: DESIGN (15-20 min)    → High-level → Deep dive
Step 4: WRAP UP (3-5 min)     → Tradeoffs, bottlenecks, scaling
```

---

## 🏗️ Architecture Patterns Cheat Sheet

### 1. Monolith vs Microservices

| Aspect | Monolith | Microservices |
|--------|----------|---------------|
| **When** | MVP, <10 devs, simple domain | Scale, >20 devs, complex domain |
| **Deploy** | Single unit | Independent services |
| **DB** | Shared database | Database per service |
| **Latency** | Lower (in-process) | Higher (network calls) |
| **Complexity** | Simple | Complex (service mesh, tracing) |
| **Cost** | Lower | Higher (infra overhead) |

**Rule:** Start monolith. Extract services only when you NEED to.

### 2. Database Selection Guide

```
SQL (PostgreSQL)    → Complex queries, ACID, relationships
                     Best for: SaaS, E-commerce, Finance

NoSQL (MongoDB)     → Flexible schema, rapid iteration
                     Best for: Content apps, catalogs

Redis               → Key-value, caching, sessions, queues
                     Best for: Cache layer, rate limiting

DynamoDB            → Auto-scaling, key-value, serverless
                     Best for: High-throughput, predictable access

Elasticsearch       → Full-text search, logs, analytics
                     Best for: Search features, log analysis

ClickHouse          → Analytics, time-series, OLAP
                     Best for: Dashboards, big data queries
```

### 3. Caching Strategies

```
Cache-Aside (Lazy Loading)
  Read:  App → Cache? → Hit: return | Miss: DB → write cache → return
  Best:  General purpose, read-heavy workloads
  
Write-Through
  Write: App → Cache + DB simultaneously
  Best:  Data consistency critical
  
Write-Behind (Write-Back)  
  Write: App → Cache → Async: batch write to DB
  Best:  Write-heavy, can tolerate eventual consistency
  
TTL-based Expiration
  Set:   cache.set(key, value, { ex: 3600 }) // 1 hour
  Best:  Simple invalidation, acceptable staleness
```

### 4. Load Balancing

```
Round Robin      → Equal distribution (default)
Weighted         → More traffic to powerful servers
Least Connection → Route to server with fewest connections
IP Hash          → Same user → same server (session affinity)
```

### 5. Message Queues

```
Redis Queues     → Simple, fast, good for <100K msg/sec
RabbitMQ         → Complex routing, DLQ, priorities  
Kafka            → Event streaming, replay, >1M msg/sec
SQS              → Serverless, auto-scaling, no management
```

---

## 🎯 Common System Design Questions (with Solutions)

### Design a URL Shortener (like bit.ly)

**Requirements:** Generate short URLs, redirect, analytics, 100M URLs/month

**Architecture:**
```
Client → Load Balancer → API Servers → Database
                              ↓
                          Cache (Redis)
                              ↓
                      Analytics Pipeline (Kafka)
```

**Key Decisions:**
- **ID Generation:** Base62 encoding of auto-increment ID or random hash
- **Database:** PostgreSQL for metadata, Redis for hot URLs
- **Read:Write ratio:** 100:1 → Heavy caching
- **Storage:** 100M × 1KB = 100GB/month → PostgreSQL handles this easily

**Schema:**
```sql
CREATE TABLE urls (
  id BIGSERIAL PRIMARY KEY,
  short_code VARCHAR(8) UNIQUE NOT NULL,
  original_url TEXT NOT NULL,
  user_id UUID,
  clicks BIGINT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ
);
CREATE INDEX idx_short_code ON urls(short_code);
```

---

### Design a Chat Application (like Slack)

**Requirements:** 1:1 chat, group chat, online status, 10M DAU

**Architecture:**
```
Client ←WebSocket→ WebSocket Servers ← Load Balancer
                        ↓
                    Redis Pub/Sub (presence + routing)
                        ↓
                    Message Store (Cassandra / PostgreSQL)
                        ↓
                    Push Notification Service
```

**Key Decisions:**
- **Protocol:** WebSocket for real-time, HTTP fallback
- **Message Storage:** Write-optimized DB (Cassandra for scale, PostgreSQL for MVP)
- **Presence:** Redis SET with TTL (SADD online_users user_id)
- **Group Messages:** Fan-out on write (small groups) vs fan-out on read (large channels)

---

### Design a Rate Limiter

**Requirements:** Limit API calls per user, 1000 req/min

**Algorithm: Token Bucket (recommended)**
```python
# Redis implementation
def is_allowed(user_id, limit=1000, window=60):
    key = f"rate:{user_id}"
    current = redis.incr(key)
    if current == 1:
        redis.expire(key, window)
    return current <= limit
```

**Algorithm: Sliding Window**
```python
def is_allowed_sliding(user_id, limit=1000, window=60):
    now = time.time()
    key = f"rate:{user_id}"
    # Remove old entries
    redis.zremrangebyscore(key, 0, now - window)
    # Count current window
    count = redis.zcard(key)
    if count < limit:
        redis.zadd(key, {str(now): now})
        redis.expire(key, window)
        return True
    return False
```

---

## ⚡ Quick Reference: Numbers Every Dev Should Know

```
L1 cache reference                    0.5 ns
L2 cache reference                      7 ns
Main memory reference                 100 ns
SSD random read                   150,000 ns    (150 μs)
HDD seek                      10,000,000 ns    (10 ms)
Send 1K bytes over network        10,000 ns    (10 μs)
Read 1 MB from memory            250,000 ns    (250 μs)
Read 1 MB from SSD             1,000,000 ns    (1 ms)
Read 1 MB from HDD            20,000,000 ns    (20 ms)
Send packet CA → Netherlands  150,000,000 ns    (150 ms)
```

**Handy Estimations:**
```
QPS for web server:           ~1,000 (typical)
QPS for database:             ~10,000 (PostgreSQL)
QPS for cache:                ~100,000 (Redis)
QPS for message queue:        ~100,000 (Kafka per partition)

1 million users:              ~100 QPS (1 req/10sec average)
10 million users:             ~1,000 QPS
100 million users:            ~10,000 QPS
```

---

## 🔒 Security Checklist for Every Project

```
□ HTTPS everywhere (no HTTP)
□ Input validation & sanitization (Zod / Joi)
□ SQL injection prevention (parameterized queries / ORM)
□ XSS prevention (CSP headers, escape output)
□ CSRF tokens on forms
□ Rate limiting on auth endpoints
□ Password hashing (bcrypt, argon2 — NEVER plain text)
□ JWT in httpOnly cookies (not localStorage)
□ Environment variables for secrets (NEVER commit .env)
□ Dependency auditing (npm audit)
□ CORS configuration (whitelist specific origins)
□ Database backups (automated, tested)
```

---

## 📈 Scaling Cheat Sheet

```
Stage 1: Single Server (0 → 1K users)
  → One server, one database
  → Focus: Ship fast, validate idea

Stage 2: Separate DB (1K → 10K users)
  → App server + Dedicated DB server
  → Add: CDN for static assets

Stage 3: Cache Layer (10K → 100K users)
  → Add Redis for caching
  → Add: Load balancer, multiple app servers

Stage 4: Read Replicas (100K → 1M users)
  → Primary DB + Read replicas
  → Add: Database connection pooling (PgBouncer)

Stage 5: Horizontal Scale (1M → 10M users)
  → Sharding, microservices
  → Add: Message queues, service mesh, monitoring

Stage 6: Global (10M+ users)
  → Multi-region deployment
  → Add: Edge computing, geo-routing, eventual consistency
```

---

*DevVault Pro 2026 — System Design Interview Guide*
