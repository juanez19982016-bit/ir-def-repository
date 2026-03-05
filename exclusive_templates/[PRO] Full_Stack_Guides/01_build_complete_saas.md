# 🚀 Build a Complete SaaS App from Scratch — Step-by-Step Guide

> **Estimated market value: $79** (Udemy full-stack courses: $49-$149)
>
> This guide walks you through building a production-ready SaaS application
> using Next.js 15, Auth.js v5, Stripe, Prisma, and PostgreSQL.

---

## Table of Contents
1. [Project Setup & Architecture](#1-project-setup)
2. [Database Design with Prisma](#2-database)
3. [Authentication System](#3-auth)
4. [Subscription & Billing with Stripe](#4-stripe)
5. [Dashboard & Admin Panel](#5-dashboard)
6. [API Routes & Middleware](#6-api)
7. [Email System](#7-email)
8. [Deployment to Production](#8-deploy)

---

## 1. Project Setup & Architecture

### Initialize the Project
```bash
npx create-next-app@latest my-saas --typescript --tailwind --eslint --app --src-dir
cd my-saas
npm install prisma @prisma/client @auth/prisma-adapter
npm install stripe @stripe/stripe-js
npm install resend @react-email/components
npm install zod react-hook-form @hookform/resolvers
npm install lucide-react class-variance-authority clsx tailwind-merge
```

### Recommended Folder Structure
```
src/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   └── layout.tsx
│   ├── (dashboard)/
│   │   ├── dashboard/page.tsx
│   │   ├── settings/page.tsx
│   │   ├── billing/page.tsx
│   │   └── layout.tsx
│   ├── (marketing)/
│   │   ├── page.tsx          # Landing page
│   │   ├── pricing/page.tsx
│   │   └── layout.tsx
│   ├── api/
│   │   ├── auth/[...nextauth]/route.ts
│   │   ├── webhooks/stripe/route.ts
│   │   └── trpc/[trpc]/route.ts
│   └── layout.tsx
├── components/
│   ├── ui/                   # Reusable UI components
│   ├── forms/                # Form components
│   └── layouts/              # Layout components
├── lib/
│   ├── auth.ts               # Auth configuration
│   ├── db.ts                 # Database client
│   ├── stripe.ts             # Stripe client
│   ├── email.ts              # Email client
│   └── utils.ts              # Utilities
├── prisma/
│   └── schema.prisma
└── types/
    └── index.ts
```

### Environment Variables
```env
# Database
DATABASE_URL="postgresql://user:pass@localhost:5432/saas_db"

# Auth
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-secret-here"  # openssl rand -base64 32
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""
GITHUB_ID=""
GITHUB_SECRET=""

# Stripe
STRIPE_SECRET_KEY="sk_test_..."
STRIPE_PUBLISHABLE_KEY="pk_test_..."
STRIPE_WEBHOOK_SECRET="whsec_..."
STRIPE_PRO_PRICE_ID="price_..."
STRIPE_BUSINESS_PRICE_ID="price_..."

# Email
RESEND_API_KEY="re_..."
EMAIL_FROM="noreply@yourdomain.com"
```

---

## 2. Database Design with Prisma

### Schema Definition
```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id            String    @id @default(cuid())
  name          String?
  email         String    @unique
  emailVerified DateTime?
  image         String?
  password      String?   // For credentials auth
  role          Role      @default(USER)
  
  // Subscription
  stripeCustomerId     String?   @unique
  stripeSubscriptionId String?   @unique
  stripePriceId        String?
  stripeCurrentPeriodEnd DateTime?
  
  // Relations
  accounts      Account[]
  sessions      Session[]
  projects      Project[]
  
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}

enum Role {
  USER
  PRO
  ADMIN
}

model Account {
  id                String  @id @default(cuid())
  userId            String
  type              String
  provider          String
  providerAccountId String
  refresh_token     String? @db.Text
  access_token      String? @db.Text
  expires_at        Int?
  token_type        String?
  scope             String?
  id_token          String? @db.Text
  session_state     String?
  
  user User @relation(fields: [userId], references: [id], onDelete: Cascade)
  
  @@unique([provider, providerAccountId])
}

model Session {
  id           String   @id @default(cuid())
  sessionToken String   @unique
  userId       String
  expires      DateTime
  user         User     @relation(fields: [userId], references: [id], onDelete: Cascade)
}

model Project {
  id          String   @id @default(cuid())
  name        String
  description String?
  userId      String
  user        User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
  
  @@index([userId])
}
```

### Database Client Singleton
```typescript
// src/lib/db.ts
import { PrismaClient } from '@prisma/client'

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

export const db = globalForPrisma.prisma ?? new PrismaClient()

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = db
```

### Migration Commands
```bash
npx prisma generate        # Generate client
npx prisma db push         # Push schema (dev)
npx prisma migrate dev     # Create migration (dev)
npx prisma migrate deploy  # Apply migrations (prod)
npx prisma studio          # Visual DB editor
```

---

## 3. Authentication System

### Auth.js v5 Configuration
```typescript
// src/lib/auth.ts
import NextAuth from "next-auth"
import { PrismaAdapter } from "@auth/prisma-adapter"
import Google from "next-auth/providers/google"
import GitHub from "next-auth/providers/github"
import Credentials from "next-auth/providers/credentials"
import bcrypt from "bcryptjs"
import { db } from "./db"

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: PrismaAdapter(db),
  session: { strategy: "jwt" },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    }),
    GitHub({
      clientId: process.env.GITHUB_ID,
      clientSecret: process.env.GITHUB_SECRET,
    }),
    Credentials({
      async authorize(credentials) {
        const { email, password } = credentials as {
          email: string; password: string
        }
        
        const user = await db.user.findUnique({ where: { email } })
        if (!user?.password) return null
        
        const isValid = await bcrypt.compare(password, user.password)
        if (!isValid) return null
        
        return user
      },
    }),
  ],
  callbacks: {
    async session({ token, session }) {
      if (token.sub && session.user) {
        session.user.id = token.sub
        session.user.role = token.role as string
      }
      return session
    },
    async jwt({ token }) {
      if (!token.sub) return token
      const user = await db.user.findUnique({ where: { id: token.sub } })
      if (user) token.role = user.role
      return token
    },
  },
})
```

### Protected Route Middleware
```typescript
// src/middleware.ts
import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export default auth((req) => {
  const isLoggedIn = !!req.auth
  const isOnDashboard = req.nextUrl.pathname.startsWith("/dashboard")
  const isOnAuth = req.nextUrl.pathname.startsWith("/login") || 
                   req.nextUrl.pathname.startsWith("/register")

  if (isOnDashboard && !isLoggedIn) {
    return NextResponse.redirect(new URL("/login", req.nextUrl))
  }
  
  if (isOnAuth && isLoggedIn) {
    return NextResponse.redirect(new URL("/dashboard", req.nextUrl))
  }
  
  return NextResponse.next()
})

export const config = {
  matcher: ["/dashboard/:path*", "/login", "/register"],
}
```

---

## 4. Subscription & Billing with Stripe

### Stripe Client Setup
```typescript
// src/lib/stripe.ts
import Stripe from "stripe"

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: "2024-12-18.acacia",
  typescript: true,
})

export const PLANS = {
  free: { name: "Free", price: 0, features: ["3 projects", "Basic support"] },
  pro: {
    name: "Pro",
    price: 19,
    priceId: process.env.STRIPE_PRO_PRICE_ID!,
    features: ["Unlimited projects", "Priority support", "API access", "Analytics"],
  },
  business: {
    name: "Business",
    price: 49,
    priceId: process.env.STRIPE_BUSINESS_PRICE_ID!,
    features: ["Everything in Pro", "Team collaboration", "Custom domain", "SLA"],
  },
}
```

### Checkout Session Creation
```typescript
// src/app/api/stripe/checkout/route.ts
import { auth } from "@/lib/auth"
import { stripe } from "@/lib/stripe"
import { db } from "@/lib/db"
import { NextResponse } from "next/server"

export async function POST(req: Request) {
  const session = await auth()
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const { priceId } = await req.json()
  const user = await db.user.findUnique({ where: { id: session.user.id } })

  // Create or retrieve Stripe customer
  let customerId = user?.stripeCustomerId
  if (!customerId) {
    const customer = await stripe.customers.create({
      email: session.user.email!,
      metadata: { userId: session.user.id },
    })
    customerId = customer.id
    await db.user.update({
      where: { id: session.user.id },
      data: { stripeCustomerId: customerId },
    })
  }

  const checkoutSession = await stripe.checkout.sessions.create({
    customer: customerId,
    mode: "subscription",
    payment_method_types: ["card"],
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: `${process.env.NEXTAUTH_URL}/dashboard/billing?success=true`,
    cancel_url: `${process.env.NEXTAUTH_URL}/pricing`,
    metadata: { userId: session.user.id },
  })

  return NextResponse.json({ url: checkoutSession.url })
}
```

### Stripe Webhook Handler
```typescript
// src/app/api/webhooks/stripe/route.ts
import { stripe } from "@/lib/stripe"
import { db } from "@/lib/db"
import { headers } from "next/headers"
import Stripe from "stripe"

export async function POST(req: Request) {
  const body = await req.text()
  const signature = headers().get("Stripe-Signature")!

  let event: Stripe.Event
  try {
    event = stripe.webhooks.constructEvent(
      body, signature, process.env.STRIPE_WEBHOOK_SECRET!
    )
  } catch {
    return new Response("Webhook Error", { status: 400 })
  }

  switch (event.type) {
    case "checkout.session.completed": {
      const session = event.data.object as Stripe.Checkout.Session
      const subscription = await stripe.subscriptions.retrieve(
        session.subscription as string
      )
      await db.user.update({
        where: { id: session.metadata!.userId },
        data: {
          stripeSubscriptionId: subscription.id,
          stripeCustomerId: subscription.customer as string,
          stripePriceId: subscription.items.data[0].price.id,
          stripeCurrentPeriodEnd: new Date(subscription.current_period_end * 1000),
          role: "PRO",
        },
      })
      break
    }
    
    case "invoice.payment_succeeded": {
      const invoice = event.data.object as Stripe.Invoice
      const subscription = await stripe.subscriptions.retrieve(
        invoice.subscription as string
      )
      await db.user.update({
        where: { stripeSubscriptionId: subscription.id },
        data: {
          stripePriceId: subscription.items.data[0].price.id,
          stripeCurrentPeriodEnd: new Date(subscription.current_period_end * 1000),
        },
      })
      break
    }
    
    case "customer.subscription.deleted": {
      const subscription = event.data.object as Stripe.Subscription
      await db.user.update({
        where: { stripeSubscriptionId: subscription.id },
        data: {
          stripeSubscriptionId: null,
          stripePriceId: null,
          stripeCurrentPeriodEnd: null,
          role: "USER",
        },
      })
      break
    }
  }

  return new Response(null, { status: 200 })
}
```

---

## 5. Dashboard & Admin Panel

### Dashboard Layout with Sidebar
```typescript
// src/app/(dashboard)/layout.tsx
import { auth } from "@/lib/auth"
import { redirect } from "next/navigation"
import { Sidebar } from "@/components/layouts/sidebar"

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const session = await auth()
  if (!session) redirect("/login")

  return (
    <div className="flex h-screen">
      <Sidebar user={session.user} />
      <main className="flex-1 overflow-y-auto p-6">
        {children}
      </main>
    </div>
  )
}
```

### Server Component with Data Fetching
```typescript
// src/app/(dashboard)/dashboard/page.tsx
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { StatsCards } from "@/components/dashboard/stats-cards"
import { RecentProjects } from "@/components/dashboard/recent-projects"

export default async function DashboardPage() {
  const session = await auth()
  
  const [projectCount, recentProjects] = await Promise.all([
    db.project.count({ where: { userId: session!.user.id } }),
    db.project.findMany({
      where: { userId: session!.user.id },
      orderBy: { createdAt: "desc" },
      take: 5,
    }),
  ])

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome back, {session!.user.name}
        </p>
      </div>
      <StatsCards projectCount={projectCount} />
      <RecentProjects projects={recentProjects} />
    </div>
  )
}
```

---

## 6. API Routes & Middleware

### Type-Safe API with Zod Validation
```typescript
// src/lib/validations/project.ts
import { z } from "zod"

export const createProjectSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
})

export type CreateProjectInput = z.infer<typeof createProjectSchema>
```

```typescript
// src/app/api/projects/route.ts
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { createProjectSchema } from "@/lib/validations/project"
import { NextResponse } from "next/server"

export async function POST(req: Request) {
  const session = await auth()
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const json = await req.json()
  const body = createProjectSchema.safeParse(json)
  
  if (!body.success) {
    return NextResponse.json({ error: body.error.issues }, { status: 422 })
  }

  // Check plan limits
  const projectCount = await db.project.count({
    where: { userId: session.user.id },
  })
  
  const user = await db.user.findUnique({ where: { id: session.user.id } })
  const limit = user?.role === "USER" ? 3 : Infinity
  
  if (projectCount >= limit) {
    return NextResponse.json(
      { error: "Project limit reached. Upgrade to Pro." },
      { status: 403 }
    )
  }

  const project = await db.project.create({
    data: { ...body.data, userId: session.user.id },
  })

  return NextResponse.json(project, { status: 201 })
}

export async function GET() {
  const session = await auth()
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const projects = await db.project.findMany({
    where: { userId: session.user.id },
    orderBy: { createdAt: "desc" },
  })

  return NextResponse.json(projects)
}
```

---

## 7. Email System

### Transactional Email with Resend
```typescript
// src/lib/email.ts
import { Resend } from "resend"

const resend = new Resend(process.env.RESEND_API_KEY)

export async function sendWelcomeEmail(email: string, name: string) {
  await resend.emails.send({
    from: process.env.EMAIL_FROM!,
    to: email,
    subject: "Welcome to Our SaaS! 🎉",
    html: `
      <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
        <h1 style="color:#333">Welcome, ${name}!</h1>
        <p>Thanks for signing up. Here's what you can do next:</p>
        <ul>
          <li>Create your first project</li>
          <li>Explore the dashboard</li>
          <li>Invite team members</li>
        </ul>
        <a href="${process.env.NEXTAUTH_URL}/dashboard" 
           style="display:inline-block;background:#6366f1;color:#fff;padding:12px 24px;
                  border-radius:8px;text-decoration:none;font-weight:600;margin-top:16px">
          Go to Dashboard →
        </a>
      </div>
    `,
  })
}

export async function sendSubscriptionEmail(email: string, plan: string) {
  await resend.emails.send({
    from: process.env.EMAIL_FROM!,
    to: email,
    subject: `You're now on the ${plan} plan! 🚀`,
    html: `
      <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
        <h1>Upgrade Complete! 🎉</h1>
        <p>You now have access to all ${plan} features.</p>
      </div>
    `,
  })
}
```

---

## 8. Deployment to Production

### Vercel Deployment
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod

# Set environment variables
vercel env add DATABASE_URL
vercel env add NEXTAUTH_SECRET
vercel env add STRIPE_SECRET_KEY
# ... etc
```

### Production Checklist
- [ ] Set all environment variables in Vercel dashboard
- [ ] Configure Stripe webhook endpoint: `https://yourdomain.com/api/webhooks/stripe`
- [ ] Enable Stripe live mode and update keys
- [ ] Set up custom domain
- [ ] Configure email domain with Resend
- [ ] Run `prisma migrate deploy` on production database
- [ ] Set up error monitoring (Sentry)
- [ ] Enable rate limiting on API routes
- [ ] Test all payment flows in live mode
- [ ] Set up database backups

### Docker Production Setup
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npx prisma generate
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

---

## Summary

This guide covers the complete stack for a production SaaS:

| Component | Technology | Status |
|-----------|-----------|--------|
| Framework | Next.js 15 (App Router) | ✅ |
| Auth | Auth.js v5 (Google, GitHub, Credentials) | ✅ |
| Database | PostgreSQL + Prisma ORM | ✅ |
| Payments | Stripe (subscriptions, webhooks) | ✅ |
| Email | Resend + React Email | ✅ |
| Validation | Zod + React Hook Form | ✅ |
| Deployment | Vercel / Docker | ✅ |

**Time saved: ~80-120 hours of development.**
