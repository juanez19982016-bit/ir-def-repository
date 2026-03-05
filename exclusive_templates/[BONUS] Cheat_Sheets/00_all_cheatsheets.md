# 📋 DevVault Pro 2026 — 20 Developer Cheat Sheets

Quick-reference guides for the modern developer. Print them, bookmark them, or keep them open.

---

## 1. 🟨 JavaScript ES2026 Cheat Sheet

```javascript
// Destructuring
const { name, age = 25 } = user;
const [first, ...rest] = array;

// Optional chaining & nullish coalescing
const city = user?.address?.city ?? 'Unknown';

// Promises
const data = await Promise.allSettled([fetchA(), fetchB()]);
const results = data.filter(r => r.status === 'fulfilled').map(r => r.value);

// Array methods
arr.findLast(x => x > 5);        // Last match
arr.toSorted((a,b) => a-b);      // Immutable sort
arr.toReversed();                 // Immutable reverse
arr.with(2, 'new');               // Immutable replace at index
Object.groupBy(arr, item => item.category); // Group by

// Temporal API (replaces Date)
const now = Temporal.Now.plainDateTimeISO();
const duration = Temporal.Duration.from({ hours: 2, minutes: 30 });

// Symbols & WeakRef
const key = Symbol('unique');
const ref = new WeakRef(heavyObject);

// Structured clone (deep copy)
const copy = structuredClone(original);

// Iterator helpers
const first5 = iterator.take(5).toArray();
const mapped = iterator.map(x => x * 2).filter(x => x > 10);

// Pattern matching (Stage 3)
// match (value) { when (1): 'one'; when (2): 'two'; default: 'other' }
```

---

## 2. 🔷 TypeScript Cheat Sheet

```typescript
// Utility types
type Partial<T>     // All properties optional
type Required<T>    // All properties required
type Pick<T, K>     // Select specific keys
type Omit<T, K>     // Remove specific keys
type Record<K, V>   // Object with keys K and values V
type Exclude<T, U>  // Remove types from union
type Extract<T, U>  // Extract types from union
type NonNullable<T> // Remove null/undefined
type ReturnType<F>  // Get function return type
type Parameters<F>  // Get function parameters
type Awaited<T>     // Unwrap Promise type

// Conditional types
type IsString<T> = T extends string ? true : false;

// Template literal types
type Route = `/${string}`;
type EventName = `on${Capitalize<string>}`;

// Satisfies operator
const config = { port: 3000, host: 'localhost' } satisfies Config;

// const assertions
const colors = ['red', 'blue'] as const; // readonly tuple

// Discriminated unions
type Shape = 
  | { kind: 'circle'; radius: number }
  | { kind: 'rect'; width: number; height: number };

// Infer
type UnwrapArray<T> = T extends (infer U)[] ? U : T;

// Generic constraints
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] { return obj[key]; }
```

---

## 3. ⚛️ React 20 Cheat Sheet

```jsx
// Hooks
useState(initial)           // State management
useEffect(() => {}, [deps]) // Side effects
useRef(initial)             // Mutable ref
useMemo(() => val, [deps])  // Memoize value
useCallback(fn, [deps])     // Memoize function
useContext(Context)          // Consume context
useReducer(reducer, init)   // Complex state
useId()                      // Unique ID
useTransition()              // Non-blocking updates
useDeferredValue(value)      // Defer expensive renders
useOptimistic(state, fn)     // Optimistic updates
useActionState(fn, init)     // Form actions
use(promise)                 // Unwrap promise/context

// Server Components
async function Page() {
  const data = await db.query('SELECT * FROM posts');
  return <PostList posts={data} />;
}

// Client Components
'use client';
export function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}

// Server Actions
'use server';
async function createPost(formData: FormData) {
  await db.post.create({ data: { title: formData.get('title') } });
  revalidatePath('/posts');
}
```

---

## 4. 🟢 Next.js 15 Cheat Sheet

```
app/                          # App Router
├── layout.tsx                # Root layout (wraps all pages)
├── page.tsx                  # Home page (/)
├── loading.tsx               # Loading UI (Suspense)
├── error.tsx                 # Error boundary
├── not-found.tsx             # 404 page
├── api/route.ts              # API route handler
├── blog/
│   ├── page.tsx              # /blog
│   ├── [slug]/page.tsx       # /blog/:slug (dynamic)
│   └── [...all]/page.tsx     # /blog/* (catch-all)
└── (auth)/                   # Route group (no URL segment)
    ├── login/page.tsx
    └── signup/page.tsx

// Metadata
export const metadata = { title: 'My App', description: '...' };

// Dynamic metadata
export async function generateMetadata({ params }) { ... }

// Static params (ISR)
export async function generateStaticParams() {
  return posts.map(p => ({ slug: p.slug }));
}

// Middleware
export function middleware(req) {
  if (!req.cookies.get('session')) return NextResponse.redirect('/login');
}
```

---

## 5. 🐘 PostgreSQL Cheat Sheet

```sql
-- CRUD
INSERT INTO users (name, email) VALUES ('John', 'john@dev.com') RETURNING *;
SELECT * FROM users WHERE age > 25 ORDER BY name LIMIT 10 OFFSET 20;
UPDATE users SET name = 'Jane' WHERE id = 1 RETURNING *;
DELETE FROM users WHERE id = 1;

-- Joins
SELECT u.name, p.title FROM users u
  INNER JOIN posts p ON u.id = p.user_id
  LEFT JOIN comments c ON p.id = c.post_id;

-- Aggregations
SELECT category, COUNT(*), AVG(price), SUM(quantity)
  FROM products GROUP BY category HAVING COUNT(*) > 5;

-- Window functions
SELECT name, salary, RANK() OVER (ORDER BY salary DESC) as rank,
  LAG(salary) OVER (ORDER BY salary) as prev_salary FROM employees;

-- CTEs
WITH active_users AS (
  SELECT * FROM users WHERE last_login > NOW() - INTERVAL '30 days'
) SELECT * FROM active_users WHERE plan = 'pro';

-- JSON
SELECT data->>'name' as name, data->'address'->>'city' as city FROM users;
INSERT INTO events (data) VALUES ('{"type":"click","page":"/home"}'::jsonb);

-- Full text search
SELECT * FROM posts WHERE to_tsvector(title || ' ' || body) @@ to_tsquery('react & hooks');

-- Indexes
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_posts_gin ON posts USING gin (to_tsvector('english', title));
```

---

## 6. 🐳 Docker Cheat Sheet

```bash
# Images
docker build -t myapp .           # Build image
docker pull node:20-alpine        # Pull image
docker images                     # List images
docker rmi <image>                # Remove image

# Containers
docker run -d -p 3000:3000 myapp  # Run detached
docker ps                         # List running
docker ps -a                      # List all
docker stop <id>                  # Stop container
docker rm <id>                    # Remove container
docker logs -f <id>               # Follow logs
docker exec -it <id> sh           # Shell into container

# Docker Compose
docker compose up -d              # Start all services
docker compose down               # Stop all
docker compose logs -f            # Follow all logs
docker compose build              # Rebuild images
docker compose exec app sh        # Shell into service

# Multi-stage Dockerfile
FROM node:20 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
CMD ["npm", "start"]
```

---

## 7. 🔄 Git Cheat Sheet

```bash
# Basics
git init / git clone <url>
git add . / git add -p             # Stage all / interactive
git commit -m "msg"
git push origin main

# Branches
git branch feature-x              # Create branch
git checkout -b feature-x         # Create & switch
git merge feature-x               # Merge into current
git rebase main                   # Rebase onto main
git branch -d feature-x           # Delete branch

# Undo
git reset HEAD~1                  # Undo last commit (keep changes)
git reset --hard HEAD~1           # Undo last commit (discard)
git revert <hash>                 # Create undo commit
git stash / git stash pop         # Stash changes

# History
git log --oneline -20             # Compact log
git log --graph --all             # Visual branches
git diff HEAD~1                   # Diff with previous
git blame <file>                  # Who changed what

# Advanced
git cherry-pick <hash>            # Apply specific commit
git bisect start / bad / good     # Find breaking commit
git reflog                        # Recovery log
```

---

## 8. 📦 npm/pnpm Cheat Sheet

```bash
# Project
npm init -y / pnpm init
npm install / pnpm install        # Install deps
npm run dev                       # Run script

# Dependencies
npm i express                     # Add dependency
npm i -D typescript               # Add dev dependency
npm un express                    # Remove
npm outdated                      # Check updates
npm update                        # Update all

# Scripts (package.json)
"scripts": {
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "eslint . --fix",
  "test": "vitest",
  "db:push": "prisma db push",
  "db:studio": "prisma studio"
}

# npx
npx create-next-app@latest my-app
npx prisma init
npx eslint --init
```

---

## 9. 🎨 CSS/Tailwind Cheat Sheet

```css
/* Flexbox */
display: flex;
justify-content: center;         /* Main axis */
align-items: center;             /* Cross axis */
gap: 1rem;
flex-wrap: wrap;
flex: 1;                         /* Grow to fill */

/* Grid */
display: grid;
grid-template-columns: repeat(3, 1fr);
grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
gap: 1rem;
place-items: center;             /* Both axes */

/* Modern CSS */
container-type: inline-size;     /* Container queries */
@container (min-width: 400px) { ... }

:has(.error)                     /* Parent selector */
color-mix(in srgb, blue 30%, white) /* Color mixing */
text-wrap: balance;              /* Balanced text */
view-transition-name: hero;      /* View transitions */

/* Tailwind shortcuts */
/* flex center: flex items-center justify-center */
/* grid 3 cols: grid grid-cols-3 gap-4 */
/* responsive: sm:flex md:grid lg:grid-cols-4 */
/* dark mode: dark:bg-gray-900 dark:text-white */
/* animations: animate-spin animate-pulse animate-bounce */
/* glass: bg-white/10 backdrop-blur-md border border-white/20 */
```

---

## 10. 🔐 Auth & Security Cheat Sheet

```
JWT Structure: header.payload.signature
  Header:  { "alg": "HS256", "typ": "JWT" }
  Payload: { "sub": "123", "iat": 1234567890, "exp": ... }

Password Hashing:
  ✅ bcrypt (cost 12+), argon2id
  ❌ MD5, SHA-1, SHA-256 (not for passwords)

OWASP Top 10:
  1. Broken Access Control
  2. Cryptographic Failures
  3. Injection (SQLi, XSS)
  4. Insecure Design
  5. Security Misconfiguration
  6. Vulnerable Components
  7. Auth Failures
  8. Data Integrity Failures
  9. Logging Failures
  10. SSRF

Security Headers:
  Content-Security-Policy: default-src 'self'
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Strict-Transport-Security: max-age=31536000
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=()

Rate Limiting: Token bucket, sliding window, fixed window
CORS: Access-Control-Allow-Origin, credentials, methods
CSRF: SameSite cookies, double-submit, synchronizer tokens
```

---

## 11. 🧪 Testing Cheat Sheet

```javascript
// Vitest / Jest
describe('Calculator', () => {
  it('adds numbers', () => {
    expect(add(1, 2)).toBe(3);
  });
  it('handles edge cases', () => {
    expect(add(0, 0)).toBe(0);
    expect(add(-1, 1)).toBe(0);
  });
});

// Matchers
expect(x).toBe(y)               // Exact equality
expect(x).toEqual(y)            // Deep equality
expect(x).toBeTruthy()          // Truthy
expect(x).toContain(y)          // Array/string contains
expect(fn).toThrow(Error)       // Throws
expect(fn).toHaveBeenCalledWith(args)

// React Testing Library
render(<Component />);
screen.getByText('Submit');
screen.getByRole('button', { name: 'Submit' });
await screen.findByText('Loaded');
fireEvent.click(screen.getByRole('button'));
await waitFor(() => expect(screen.getByText('Done')));

// Playwright (E2E)
test('login flow', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[name=email]', 'test@dev.com');
  await page.fill('[name=password]', 'pass123');
  await page.click('button[type=submit]');
  await expect(page).toHaveURL('/dashboard');
});
```

---

## 12. 🤖 AI/LLM API Cheat Sheet

```javascript
// OpenAI Chat Completion
const response = await openai.chat.completions.create({
  model: 'gpt-4o',
  messages: [
    { role: 'system', content: 'You are a helpful assistant.' },
    { role: 'user', content: 'Explain React hooks' }
  ],
  temperature: 0.7,
  max_tokens: 1000,
  stream: true,
});

// Streaming
for await (const chunk of response) {
  process.stdout.write(chunk.choices[0]?.delta?.content || '');
}

// Embeddings (for RAG)
const embedding = await openai.embeddings.create({
  model: 'text-embedding-3-small',
  input: 'Your text here',
});

// Function calling
tools: [{
  type: 'function',
  function: {
    name: 'get_weather',
    parameters: { type: 'object', properties: { city: { type: 'string' } } }
  }
}]

// Image generation
const image = await openai.images.generate({
  model: 'dall-e-3',
  prompt: 'A futuristic city',
  size: '1024x1024',
});
```

---

## 13. 💳 Stripe Cheat Sheet

```javascript
// Checkout Session
const session = await stripe.checkout.sessions.create({
  mode: 'subscription', // or 'payment'
  line_items: [{ price: 'price_xxx', quantity: 1 }],
  success_url: 'https://app.com/success?session_id={CHECKOUT_SESSION_ID}',
  cancel_url: 'https://app.com/cancel',
});

// Webhook handling
const event = stripe.webhooks.constructEvent(body, sig, secret);
switch (event.type) {
  case 'checkout.session.completed': /* activate */ break;
  case 'invoice.payment_succeeded': /* renew */ break;
  case 'customer.subscription.deleted': /* cancel */ break;
}

// Customer Portal
const portal = await stripe.billingPortal.sessions.create({
  customer: 'cus_xxx',
  return_url: 'https://app.com/account',
});
```

---

## 14. 🗄️ Prisma ORM Cheat Sheet

```prisma
// Schema
model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  posts     Post[]
  createdAt DateTime @default(now())
}

model Post {
  id       String @id @default(cuid())
  title    String
  author   User   @relation(fields: [authorId], references: [id])
  authorId String
}
```

```javascript
// Queries
await prisma.user.findUnique({ where: { email } });
await prisma.user.findMany({ where: { name: { contains: 'john' } }, take: 10 });
await prisma.user.create({ data: { email, name } });
await prisma.user.update({ where: { id }, data: { name } });
await prisma.user.delete({ where: { id } });

// Relations
await prisma.user.findUnique({
  where: { id },
  include: { posts: { orderBy: { createdAt: 'desc' }, take: 5 } }
});

// Transactions
await prisma.$transaction([
  prisma.user.update({ ... }),
  prisma.post.create({ ... }),
]);

// CLI
npx prisma init           # Initialize
npx prisma db push         # Sync schema → DB
npx prisma generate        # Generate client
npx prisma studio          # Visual editor
npx prisma migrate dev     # Create migration
```

---

## 15. 🌐 HTTP & REST API Cheat Sheet

```
Methods:
  GET    /api/users          → List users
  GET    /api/users/:id      → Get single user
  POST   /api/users          → Create user
  PUT    /api/users/:id      → Replace user
  PATCH  /api/users/:id      → Partial update
  DELETE /api/users/:id      → Delete user

Status Codes:
  200 OK                    → Success
  201 Created               → Resource created
  204 No Content            → Deleted successfully
  400 Bad Request           → Invalid input
  401 Unauthorized          → Not authenticated
  403 Forbidden             → Not authorized
  404 Not Found             → Resource not found
  409 Conflict              → Duplicate/conflict
  422 Unprocessable         → Validation failed
  429 Too Many Requests     → Rate limited
  500 Internal Server Error → Server error

Headers:
  Content-Type: application/json
  Authorization: Bearer <token>
  Accept: application/json
  Cache-Control: max-age=3600
  X-Request-ID: uuid

Pagination:
  GET /api/posts?page=2&limit=20
  Response: { data: [...], meta: { total: 100, page: 2, pages: 5 } }
```

---

## 16. 🔧 Linux/CLI Cheat Sheet

```bash
# Files
ls -la                    # List with details
find . -name "*.ts"       # Find files
grep -rn "TODO" src/      # Search in files
wc -l src/**/*.ts         # Count lines
du -sh node_modules/      # Folder size
tar -czf backup.tar.gz .  # Compress
chmod 755 script.sh       # Permissions

# Network
curl -X POST url -d '{}' -H 'Content-Type: application/json'
wget https://example.com/file.zip
netstat -tlnp             # Open ports
ss -tlnp                  # Modern alternative

# Process
ps aux | grep node        # Find process
kill -9 <pid>             # Force kill
htop                      # System monitor
lsof -i :3000             # What's using port 3000

# Text
cat file | head -20       # First 20 lines
tail -f log.txt           # Follow log
sed 's/old/new/g' file    # Replace text
awk '{print $1}' file     # Extract column
jq '.data[0].name' f.json # Parse JSON
```

---

## 17. 🏗️ System Design Cheat Sheet

```
Load Balancer → App Servers → Cache → Database
                    ↓
               Message Queue → Workers

Scaling:
  Vertical: Bigger server (CPU, RAM)
  Horizontal: More servers + load balancer

Databases:
  PostgreSQL: ACID, relations, JSON support
  MongoDB: Documents, flexible schema
  Redis: Cache, sessions, rate limiting
  DynamoDB: Serverless, auto-scaling

Caching:
  CDN → Edge cache → Application cache → DB cache
  Cache-aside: Read from cache, miss → DB → write cache
  TTL: Time-based expiration

CAP Theorem: Choose 2 of 3:
  Consistency, Availability, Partition tolerance

Estimates:
  1 mil daily users ≈ 12 req/sec average
  1 KB × 1 mil = 1 GB storage/day
  Read:Write ratio typically 100:1
```

---

## 18. ⚡ Performance Cheat Sheet

```
Core Web Vitals:
  LCP (Largest Contentful Paint) < 2.5s
  FID (First Input Delay) < 100ms
  CLS (Cumulative Layout Shift) < 0.1

Next.js Optimization:
  ✅ Use Image component (auto WebP, lazy loading)
  ✅ Use dynamic() for heavy components
  ✅ Use Suspense boundaries
  ✅ Server Components (zero JS shipped)
  ✅ Route-based code splitting (automatic)

Bundle:
  ✅ Tree shaking (ES modules)
  ✅ import { specific } from 'lodash-es'
  ✅ Lazy load below-the-fold content
  ❌ import _ from 'lodash' (imports everything)

Database:
  ✅ Add indexes on WHERE/JOIN columns
  ✅ Use SELECT specific columns (not *)
  ✅ Paginate results (LIMIT/OFFSET)
  ✅ Use connection pooling
  ✅ Cache frequent queries (Redis)
```

---

## 19. 📧 Email Development Cheat Sheet

```html
<!-- Email-safe HTML structure -->
<table role="presentation" width="600" cellpadding="0" cellspacing="0">
  <tr><td style="padding: 20px; font-family: Arial, sans-serif;">
    <!-- Content here -->
  </td></tr>
</table>

<!-- Safe for email: -->
✅ Tables for layout
✅ Inline styles
✅ System fonts (Arial, Georgia, Verdana)
✅ Background colors
✅ Alt text on images
✅ width/height attributes on images

<!-- NOT safe for email: -->
❌ CSS Grid/Flexbox
❌ <div> for layout
❌ External stylesheets
❌ JavaScript
❌ Custom fonts
❌ Video/audio
❌ SVG (limited support)

<!-- Responsive -->
@media screen and (max-width: 600px) {
  .container { width: 100% !important; }
}
```

---

## 20. 🚀 Deployment Cheat Sheet

```
Vercel (Frontend/Next.js):
  vercel                    # Deploy
  vercel --prod             # Production
  vercel env pull           # Pull env vars

AWS (Full control):
  EC2: Virtual servers
  S3: File storage
  RDS: Managed PostgreSQL
  CloudFront: CDN
  Lambda: Serverless functions

CI/CD Pipeline:
  1. Push to main
  2. Run linter (eslint)
  3. Run tests (vitest)
  4. Build (next build)
  5. Deploy (vercel/aws)

Environment Variables:
  .env.local        → Local dev (git-ignored)
  .env.production   → Production defaults
  Vercel/AWS UI     → Actual secrets (never in git)

DNS:
  A Record:     domain.com → IP address
  CNAME:        www.domain.com → domain.com
  SSL:          Always use HTTPS (Let's Encrypt)
```

---

*Part of DevVault Pro 2026 — The Ultimate Developer Toolkit*
