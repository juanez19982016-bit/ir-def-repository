# 🔐 Security Audit & Penetration Testing Kit

> **Estimated market value: $49** (Infosec checklists & scripts)
>
> A comprehensive guide and checklist for securing Next.js/Node.js applications
> before pushing them to production.

---

## 1. Application Security Checklist

### Authentication & Authorization
- [ ] No hardcoded credentials in source code (checked via `git-secrets`).
- [ ] Passwords hashed using bcrypt/Argon2 with appropriate salt rounds.
- [ ] JWTs use secure signing algorithms (e.g., RS256, not HS256 if public/private is needed).
- [ ] JWTs have short expiration times (e.g., 15 mins) with secure refresh token rotation.
- [ ] Refresh tokens are stored in `HttpOnly`, `Secure`, `SameSite=Strict` cookies.
- [ ] Rate limiting implemented on all login/password reset routes (e.g., 5 attempts / 15 mins).
- [ ] Role-Based Access Control (RBAC) enforced on the server-side, not just UI.

### Data Security
- [ ] Database credentials rotated and restricted by IP.
- [ ] PII (Personal Identifiable Information) encrypted at rest.
- [ ] ORM used (Prisma/Drizzle) to prevent SQL Injection, or parameterized queries for raw SQL.
- [ ] No sensitive data exposed in API responses (e.g., removing password hashes from user objects).

### Frontend Security
- [ ] Content Security Policy (CSP) headers implemented.
- [ ] X-Frame-Options set to `DENY` or `SAMEORIGIN` to prevent clickjacking.
- [ ] Strict-Transport-Security (HSTS) enabled.
- [ ] Next.js Image component domains strictly whitelisted in `next.config.js`.

---

## 2. Server Security Headers Implementation (Next.js)

```javascript
// next.config.js
const securityHeaders = [
  {
    key: 'X-DNS-Prefetch-Control',
    value: 'on'
  },
  {
    key: 'Strict-Transport-Security',
    value: 'max-age=63072000; includeSubDomains; preload'
  },
  {
    key: 'X-XSS-Protection',
    value: '1; mode=block'
  },
  {
    key: 'X-Frame-Options',
    value: 'SAMEORIGIN'
  },
  {
    key: 'Permissions-Policy',
    value: 'camera=(), microphone=(), geolocation=(), browsing-topics=()'
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff'
  },
  {
    key: 'Referrer-Policy',
    value: 'origin-when-cross-origin'
  }
]

module.exports = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: securityHeaders,
      },
    ]
  },
}
```

---

## 3. Rate Limiting Implementation (Upstash / Redis)

```typescript
// src/lib/rate-limit.ts
import { Ratelimit } from "@upstash/ratelimit"
import { Redis } from "@upstash/redis"

export const authRateLimit = new Ratelimit({
  redis: Redis.fromEnv(),
  limiter: Ratelimit.slidingWindow(5, "15 m"), // 5 requests per 15 minutes
  analytics: true,
})

// usage in API route:
// const { success } = await authRateLimit.limit(req.ip ?? "anonymous")
// if (!success) return new Response("Too Many Requests", { status: 429 })
```

---

## 4. Input Validation & SQLi Prevention

Always use Zod for API input validation to prevent NoSQL injection and payload tampering.

```typescript
import { z } from "zod"

const userUpdateSchema = z.object({
  email: z.string().email(),
  age: z.number().int().min(18).max(120),
  bio: z.string().max(500).transform(str => str.trim().replace(/[<>]/g, "")), // Basic XSS sanitize
})
```

**Saves: Countless hours recovering from basic vulnerability exploits.**
