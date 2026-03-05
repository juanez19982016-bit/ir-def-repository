# 👔 Tech Interview Cheat Sheet & Prep Kit

> **Estimated market value: $49**
>
> 50 high-frequency behavioral and technical interview questions for Front-End, 
> Back-End, and Full-Stack roles (React, Node.js, System Design).

---

## 1. System Design (The "Why")

### Q: "How would you design a URL shortener like Bitly?"
**Key Talking Points:**
1. **API:** Needs `POST /api/v1/data/shorten` (returns short URL) and `GET /:code` (redirects).
2. **Database:** Key-Value store (Redis or DynamoDB) or RDBMS with B-Tree index on short-code.
3. **Algorithm:** Base62 encoding (A-Z, a-z, 0-9) of an auto-incrementing ID.
4. **Scale:** Heavy reads, low writes. Put a Redis cache in front of read replica DBs.
5. **Collision:** If using random hash instead of Base62 ID, explain how you'd handle collisions (retry loop with DB unique constraint).

### Q: "Explain REST vs GraphQL"
**Key Talking Points:**
1. **REST:** Multiple endpoints, over/under-fetching data, standard HTTP verbs/caching.
2. **GraphQL:** Single endpoint (`/graphql`), client specifies exact data needs, no over/under-fetching, requires custom caching (Apollo/urql), harder to rate limit securely.

---

## 2. React & Frontend Core

### Q: "What's the difference between useMemo and useCallback?"
**Answer:** Both are for memoization to prevent unnecessary re-renders. 
`useMemo` caches the **result** of a computationally expensive function (like sorting an array). 
`useCallback` caches the **function instance itself**, useful when passing callbacks down as props to child components wrapped in `React.memo` (prevents child re-render because function reference stays the same).

### Q: "Explain the Virtual DOM"
**Answer:** It's a lightweight JavaScript representation of the actual DOM. When state changes, React creates a new Virtual DOM, compares it (diffs it) with the previous Virtual DOM, calculates the absolute minimum number of real DOM mutations needed, and applies them in a batch. Real DOM operations are slow; JS operations on the Virtual DOM are extremely fast.

### Q: "What are React Server Components (RSC)?"
**Answer:** Components that render exclusively on the server, sending zero compiled JavaScript to the client. This reduces bundle size drastically, allows direct database queries within components (bypassing API routes), and improves SEO and Initial Page Load (LCP). Only components needing interactivity (`onClick`, `useState`) need the `"use client"` directive.

---

## 3. Node.js & Backend

### Q: "Explain the Node.js Event Loop"
**Answer:** Node is single-threaded, but handles concurrency via the Event Loop. When synchronous code finishes, Node offloads async operations (I/O, database, network) to the system kernel (libuv worker threads). When those finish, they push callbacks to the Event Queue. The Event Loop constantly picks up callbacks from the queue and executes them on the main thread.

### Q: "How do you prevent SQL Injection?"
**Answer:** Never concatenate strings to build queries. Use an ORM/Query Builder (Prisma, Drizzle, Knex) which parameterizes queries by default. If writing raw SQL, always use parameterized queries (prepared statements) where the DB engine treats inputs strictly as data, never as executable code.

### Q: "What is an N+1 Query Problem?"
**Answer:** Occurs when you query a list of entities (1 query), and then execution loops over that list, executing an additional query for each entity's related data (N queries), totaling N+1.
*Solution:* Use JOINs in SQL, or data-loaders/includes in ORMs (e.g., `include: { comments: true }` in Prisma).

---

## 4. Behavior (STAR Method)
Use **S**ituation, **T**ask, **A**ction, **R**esult.

### Q: "Tell me about a time you disagreed with your lead or team."
*Bad Answer:* "I argued and forced them to use my tech."
*STAR Answer:* "In my last role, my lead wanted to use MongoDB for financial data (S/T). I knew we needed ACID transactions (A). I built a small proof of concept showing how Postgres handled the specific concurrency cases better, presented it objectively with metrics. The lead agreed, and we deployed it. The result (R) was zero data anomalies during peak traffic."
