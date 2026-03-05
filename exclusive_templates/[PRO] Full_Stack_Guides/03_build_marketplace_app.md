# 🛍️ Build a Multi-Vendor Marketplace — Complete Guide

> **Estimated market value: $79** (Udemy marketplace courses: $49-$149)
>
> Learn how to build a complex two-sided marketplace (like Airbnb or Fiverr)
> handling multi-vendor payouts using Stripe Connect, Next.js 15, and Prisma.

---

## Table of Contents
1. [Architecture & Database Design](#1-architecture)
2. [Stripe Connect Express Setup](#2-stripe-connect)
3. [Vendor Onboarding Flow](#3-onboarding)
4. [Product/Listing Management](#4-listings)
5. [Shopping Cart & Checkout](#5-checkout)
6. [Split Payments & Payouts](#6-split-payments)
7. [Order Management Dashboard](#7-dashboard)

---

## 1. Architecture & Database Design

### Prisma Schema (Multi-Vendor)
```prisma
// prisma/schema.prisma

model User {
  id               String    @id @default(cuid())
  email            String    @unique
  role             Role      @default(BUYER)
  
  // Vendor specific
  stripeAccountId  String?   @unique
  onboardingStatus String?   // "pending", "completed"
  
  // Relations
  store            Store?
  orders           Order[]   // Orders placed by user
  reviews          Review[]
}

model Store {
  id          String    @id @default(cuid())
  name        String
  description String?
  userId      String    @unique
  user        User      @relation(fields: [userId], references: [id])
  products    Product[]
  orders      OrderLine[] // Orders received by store
}

model Product {
  id          String      @id @default(cuid())
  storeId     String
  store       Store       @relation(fields: [storeId], references: [id])
  name        String
  price       Int         // In cents
  inventory   Int
  images      String[]
  orderLines  OrderLine[]
}

model Order {
  id            String      @id @default(cuid())
  buyerId       String
  buyer         User        @relation(fields: [buyerId], references: [id])
  total         Int         // Total in cents
  stripeIntentId String     @unique
  status        OrderStatus @default(PENDING)
  orderLines    OrderLine[]
  createdAt     DateTime    @default(now())
}

model OrderLine {
  id        String  @id @default(cuid())
  orderId   String
  order     Order   @relation(fields: [orderId], references: [id])
  productId String
  product   Product @relation(fields: [productId], references: [id])
  storeId   String
  store     Store   @relation(fields: [storeId], references: [id])
  quantity  Int
  price     Int     // Price at time of purchase
}

enum Role { BUYER, VENDOR, ADMIN }
enum OrderStatus { PENDING, PAID, SHIPPED, DELIVERED, CANCELLED }
```

---

## 2. Stripe Connect Express Setup

Stripe Connect is required to accept payments on behalf of others and route funds to them.

### Initialize Stripe Connect
```typescript
// src/lib/stripe.ts
import Stripe from "stripe"

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: "2024-12-18",
  typescript: true,
})

// Platform fee percentage (e.g., 10%)
export const PLATFORM_FEE_PERCENT = 10
```

---

## 3. Vendor Onboarding Flow

```typescript
// src/app/api/vendor/onboarding/route.ts
import { stripe } from "@/lib/stripe"
import { db } from "@/lib/db"
import { NextResponse } from "next/server"

export async function POST(req: Request) {
  const { userId } = await auth()
  const user = await db.user.findUnique({ where: { id: userId } })

  let accountId = user?.stripeAccountId

  // 1. Create a Stripe Express account if it doesn't exist
  if (!accountId) {
    const account = await stripe.accounts.create({
      type: "express",
      country: "US", // or user's country
      email: user?.email,
      capabilities: {
        card_payments: { requested: true },
        transfers: { requested: true },
      },
    })
    accountId = account.id

    await db.user.update({
      where: { id: userId },
      data: { stripeAccountId: accountId, role: "VENDOR" },
    })
  }

  // 2. Create an onboarding link
  const accountLink = await stripe.accountLinks.create({
    account: accountId,
    refresh_url: `${process.env.NEXT_PUBLIC_URL}/vendor/onboarding?refresh=true`,
    return_url: `${process.env.NEXT_PUBLIC_URL}/vendor/dashboard`,
    type: "account_onboarding",
  })

  return NextResponse.json({ url: accountLink.url })
}
```

---

## 4. Split Payments & Checkout

### Creating a Destination Charge Checkout Session
When a buyer purchases items from a specific vendor.

```typescript
// src/app/api/checkout/route.ts
import { stripe, PLATFORM_FEE_PERCENT } from "@/lib/stripe"

export async function POST(req: Request) {
  const { items, storeId } = await req.json()
  
  const store = await db.store.findUnique({
    where: { id: storeId },
    include: { user: true }
  })
  
  const vendorStripeAccountId = store.user.stripeAccountId

  // Calculate total
  const totalAmount = items.reduce((sum, item) => sum + (item.price * item.quantity), 0)
  
  // Calculate platform fee
  const applicationFeeAmount = Math.round(totalAmount * (PLATFORM_FEE_PERCENT / 100))

  const session = await stripe.checkout.sessions.create({
    payment_method_types: ["card"],
    line_items: items.map(item => ({
      price_data: {
        currency: "usd",
        product_data: { name: item.name },
        unit_amount: item.price,
      },
      quantity: item.quantity,
    })),
    mode: "payment",
    success_url: `${process.env.NEXT_PUBLIC_URL}/success?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${process.env.NEXT_PUBLIC_URL}/cart`,
    payment_intent_data: {
      application_fee_amount: applicationFeeAmount,
      transfer_data: {
        destination: vendorStripeAccountId, // Route funds to vendor
      },
    },
  })

  return NextResponse.json({ url: session.url })
}
```

---

## 7. Webhook for Fulfilling Orders
```typescript
// src/app/api/webhooks/stripe/route.ts
export async function POST(req: Request) {
  const event = stripe.webhooks.constructEvent(...)

  if (event.type === "checkout.session.completed") {
    const session = event.data.object
    
    // Update order status
    await db.order.update({
      where: { stripeIntentId: session.payment_intent as string },
      data: { status: "PAID" }
    })
    
    // Notify vendor
    // sendEmail(...)
  }
}
```

**Saves: ~60 hours of Stripe Connect documentation reading and API integration.**
