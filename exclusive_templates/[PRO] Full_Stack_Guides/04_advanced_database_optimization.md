# 🗄️ Advanced Database & Architecture Optimization Guide

> **Estimated market value: $79** 
>
> Learn enterprise-grade database optimization, caching layers, and how to structure
> your backend to handle millions of requests without breaking a sweat.

---

## 1. Database Indexing Strategy (PostgreSQL + Prisma)

### Composite & Partial Indexes
```prisma
// Using B-Tree composite indexes for complex queries
model Transaction {
  id        String   @id
  userId    String
  status    String
  amount    Int
  createdAt DateTime

  // 1. Speeds up WHERE userId = ? AND status = ?
  @@index([userId, status])
  
  // 2. Speeds up recent history: WHERE userId = ? ORDER BY createdAt DESC
  @@index([userId, createdAt(sort: Desc)])
}

// B-Tree on Jsonb columns
model AuditLog {
  id      String @id
  event   String
  details Json

  // 3. PostgreSQL Gin index for searching inside JSON
  @@index([details], type: Gin)
}
```

---

## 2. Advanced Caching Layers (Redis + Next.js App Router)

### Layer 1: Next.js Data Cache (unstable_cache)
```typescript
import { unstable_cache } from 'next/cache'
import { db } from '@/lib/db'

export const getCachedUserProfile = unstable_cache(
  async (userId: string) => {
    return await db.user.findUnique({
      where: { id: userId },
      include: { preferences: true }
    })
  },
  ['user-profile'], // Cache key
  { revalidate: 3600, tags: ['user-data'] } // Cache for 1 hour
)
```

### Layer 2: Redis Query Result Caching (Upstash)
```typescript
import { Redis } from '@upstash/redis'
import { db } from '@/lib/db'

const redis = Redis.fromEnv()

export async function getLeaderboard() {
  const cacheKey = 'global_leaderboard:weekly'
  
  // Try Cache First
  const cached = await redis.get(cacheKey)
  if (cached) return cached
  
  // Cache Miss -> Database Query (Expensive)
  const leaderboard = await db.user.findMany({
    orderBy: { score: 'desc' },
    take: 100,
    select: { id: true, name: true, score: true }
  })
  
  // Write to Cache with 5-minute expiry (Stale-While-Revalidate pattern)
  await redis.setex(cacheKey, 300, JSON.stringify(leaderboard))
  
  return leaderboard
}
```

---

## 3. Handling Race Conditions (Distributed Locks)

When dealing with payments, point deductions, or inventory.

```typescript
// Prevent double-withdrawals using Redis Locks
import { Redis } from '@upstash/redis'

async function deductPoints(userId: string, points: number) {
  const redis = Redis.fromEnv()
  const lockKey = `lock:wallet:${userId}`
  
  // 1. Acquire Lock (expires in 5 seconds to prevent deadlocks)
  const acquired = await redis.set(lockKey, "LOCKED", { nx: true, ex: 5 })
  
  if (!acquired) {
    throw new Error("Transaction currently processing. Please try again.")
  }

  try {
    // 2. Perform safe read-modify-write inside the lock
    const u = await db.user.findUnique({ where: { id: userId } })
    if (u.walletBalance < points) throw new Error("Insufficient funds")
    
    // 3. Prisma transaction
    await db.user.update({
      where: { id: userId },
      data: { walletBalance: { decrement: points } }
    })
  } finally {
    // 4. Release Lock safely
    await redis.del(lockKey)
  }
}
```

---

## 4. Cursor-Based Pagination for Massive Datasets

Why? `LIMIT/OFFSET` degrades linearly as offsets grow. Cursor pagination is `O(1)`.

```typescript
// Fast endless scrolling for feeds/logs
export async function getFeed(cursorId?: string, limit = 20) {
  const feed = await db.post.findMany({
    take: limit + 1, // Take 1 extra to check for 'hasNextPage'
    ...(cursorId && {
      cursor: { id: cursorId },
      skip: 1, // Skip the actual cursor itself
    }),
    orderBy: { createdAt: 'desc' },
  })
  
  let nextCursor: string | undefined = undefined
  if (feed.length > limit) {
    const nextItem = feed.pop() // Remove the extra item
    nextCursor = nextItem!.id
  }
  
  return { data: feed, nextCursor }
}
```

**Saves: Countless debugging hours resolving N+1 queries and app crashes under load.**
