// ============================================================
// 🔌 NEXT.JS API ROUTE PATTERNS — Production-Ready Templates
// DevVault Pro 2026 — 10 essential API patterns
// ============================================================
// All patterns use Next.js 15 App Router (Route Handlers).
// Each pattern is copy-paste ready with full TypeScript types.
// ============================================================

import { NextRequest, NextResponse } from 'next/server'

// ─────────────────────────────────────────────
// 1. CRUD Operations with Validation
// ─────────────────────────────────────────────
// app/api/posts/route.ts

import { z } from 'zod'
import { db } from '@/lib/db'

const postSchema = z.object({
    title: z.string().min(3).max(120),
    content: z.string().min(10),
    category: z.enum(['tech', 'design', 'business']),
    tags: z.array(z.string()).max(5).optional(),
    published: z.boolean().default(false),
})

// GET /api/posts?page=1&limit=10&category=tech
export async function GET(req: NextRequest) {
    try {
        const { searchParams } = new URL(req.url)
        const page = Math.max(1, Number(searchParams.get('page')) || 1)
        const limit = Math.min(50, Math.max(1, Number(searchParams.get('limit')) || 10))
        const category = searchParams.get('category')

        const where = {
            published: true,
            ...(category && { category }),
        }

        const [posts, total] = await Promise.all([
            db.post.findMany({
                where,
                skip: (page - 1) * limit,
                take: limit,
                orderBy: { createdAt: 'desc' },
                select: { id: true, title: true, category: true, createdAt: true },
            }),
            db.post.count({ where }),
        ])

        return NextResponse.json({
            data: posts,
            pagination: {
                page,
                limit,
                total,
                totalPages: Math.ceil(total / limit),
                hasMore: page * limit < total,
            },
        })
    } catch (error) {
        return NextResponse.json({ error: 'Failed to fetch posts' }, { status: 500 })
    }
}

// POST /api/posts
export async function POST(req: NextRequest) {
    try {
        const body = await req.json()
        const validated = postSchema.parse(body)

        const post = await db.post.create({ data: validated })
        return NextResponse.json(post, { status: 201 })
    } catch (error) {
        if (error instanceof z.ZodError) {
            return NextResponse.json(
                { error: 'Validation failed', details: error.errors },
                { status: 400 }
            )
        }
        return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
    }
}


// ─────────────────────────────────────────────
// 2. Authentication Middleware
// ─────────────────────────────────────────────
// middleware.ts

import { getToken } from 'next-auth/jwt'

const protectedPaths = ['/dashboard', '/api/user', '/api/admin']
const adminPaths = ['/api/admin']

export async function middleware(req: NextRequest) {
    const token = await getToken({ req })

    // Check if path requires auth
    const isProtected = protectedPaths.some(p => req.nextUrl.pathname.startsWith(p))
    if (!isProtected) return NextResponse.next()

    // Not authenticated
    if (!token) {
        if (req.nextUrl.pathname.startsWith('/api/')) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
        }
        return NextResponse.redirect(new URL('/login', req.url))
    }

    // Check admin access
    const isAdmin = adminPaths.some(p => req.nextUrl.pathname.startsWith(p))
    if (isAdmin && token.role !== 'admin') {
        return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
    }

    // Add user info to headers for downstream use
    const headers = new Headers(req.headers)
    headers.set('x-user-id', token.sub as string)
    headers.set('x-user-role', token.role as string)

    return NextResponse.next({ request: { headers } })
}

export const config = {
    matcher: ['/dashboard/:path*', '/api/:path*'],
}


// ─────────────────────────────────────────────
// 3. Rate Limiting
// ─────────────────────────────────────────────
// lib/rate-limit.ts (works with Upstash Redis or in-memory)

const rateLimitMap = new Map<string, { count: number; resetAt: number }>()

export function rateLimit(key: string, limit: number, windowMs: number) {
    const now = Date.now()
    const entry = rateLimitMap.get(key)

    if (!entry || now > entry.resetAt) {
        rateLimitMap.set(key, { count: 1, resetAt: now + windowMs })
        return { allowed: true, remaining: limit - 1 }
    }

    if (entry.count >= limit) {
        return { allowed: false, remaining: 0, retryAfter: Math.ceil((entry.resetAt - now) / 1000) }
    }

    entry.count++
    return { allowed: true, remaining: limit - entry.count }
}

// Usage in API route:
export async function POST(req: NextRequest) {
    const ip = req.headers.get('x-forwarded-for') || 'anonymous'
    const { allowed, remaining, retryAfter } = rateLimit(ip, 10, 60_000) // 10 req/min

    if (!allowed) {
        return NextResponse.json(
            { error: 'Too many requests' },
            { status: 429, headers: { 'Retry-After': String(retryAfter) } }
        )
    }

    const res = NextResponse.json({ success: true })
    res.headers.set('X-RateLimit-Remaining', String(remaining))
    return res
}


// ─────────────────────────────────────────────
// 4. File Upload with Presigned URLs
// ─────────────────────────────────────────────
// app/api/upload/route.ts

import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3'
import { getSignedUrl } from '@aws-sdk/s3-request-presigner'

const s3 = new S3Client({
    region: process.env.AWS_REGION!,
    credentials: {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
    },
})

export async function POST(req: NextRequest) {
    const { fileName, fileType, fileSize } = await req.json()

    // Validate
    const maxSize = 10 * 1024 * 1024 // 10 MB
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf']

    if (fileSize > maxSize) {
        return NextResponse.json({ error: 'File too large (max 10MB)' }, { status: 400 })
    }
    if (!allowedTypes.includes(fileType)) {
        return NextResponse.json({ error: 'File type not allowed' }, { status: 400 })
    }

    const key = `uploads/${Date.now()}-${fileName}`
    const command = new PutObjectCommand({
        Bucket: process.env.S3_BUCKET!,
        Key: key,
        ContentType: fileType,
        ContentLength: fileSize,
    })

    const presignedUrl = await getSignedUrl(s3, command, { expiresIn: 300 })

    return NextResponse.json({
        uploadUrl: presignedUrl,
        fileUrl: `https://${process.env.S3_BUCKET}.s3.amazonaws.com/${key}`,
    })
}


// ─────────────────────────────────────────────
// 5. Webhook Handler (Stripe)
// ─────────────────────────────────────────────
// app/api/webhooks/stripe/route.ts

import Stripe from 'stripe'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!)
const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET!

export async function POST(req: NextRequest) {
    const body = await req.text()
    const signature = req.headers.get('stripe-signature')!

    let event: Stripe.Event

    try {
        event = stripe.webhooks.constructEvent(body, signature, webhookSecret)
    } catch {
        return NextResponse.json({ error: 'Invalid signature' }, { status: 400 })
    }

    switch (event.type) {
        case 'checkout.session.completed': {
            const session = event.data.object as Stripe.Checkout.Session
            await db.user.update({
                where: { stripeCustomerId: session.customer as string },
                data: { plan: 'pro', subscriptionId: session.subscription as string },
            })
            break
        }
        case 'customer.subscription.deleted': {
            const subscription = event.data.object as Stripe.Subscription
            await db.user.update({
                where: { subscriptionId: subscription.id },
                data: { plan: 'free', subscriptionId: null },
            })
            break
        }
        case 'invoice.payment_failed': {
            const invoice = event.data.object as Stripe.Invoice
            // Send email notification about failed payment
            await sendEmail(invoice.customer_email!, 'payment-failed')
            break
        }
    }

    return NextResponse.json({ received: true })
}


// ─────────────────────────────────────────────
// 6. Server-Sent Events (SSE) for Real-time
// ─────────────────────────────────────────────
// app/api/stream/route.ts

export async function GET(req: NextRequest) {
    const encoder = new TextEncoder()

    const stream = new ReadableStream({
        async start(controller) {
            const send = (data: any) => {
                controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`))
            }

            // Initial data
            send({ type: 'connected', timestamp: Date.now() })

            // Simulated events (replace with actual DB polling or pub/sub)
            const interval = setInterval(() => {
                send({
                    type: 'update',
                    data: { metric: 'users_online', value: Math.floor(Math.random() * 100) },
                })
            }, 5000)

            // Cleanup on disconnect
            req.signal.addEventListener('abort', () => {
                clearInterval(interval)
                controller.close()
            })
        },
    })

    return new Response(stream, {
        headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            Connection: 'keep-alive',
        },
    })
}


// ─────────────────────────────────────────────
// 7. Error Handling Wrapper
// ─────────────────────────────────────────────
// lib/api-handler.ts

type ApiHandler = (req: NextRequest, context?: any) => Promise<NextResponse>

export function withErrorHandler(handler: ApiHandler): ApiHandler {
    return async (req, context) => {
        try {
            return await handler(req, context)
        } catch (error) {
            console.error(`[API Error] ${req.method} ${req.url}:`, error)

            if (error instanceof z.ZodError) {
                return NextResponse.json(
                    { error: 'Validation Error', details: error.flatten().fieldErrors },
                    { status: 400 }
                )
            }

            if (error instanceof Error && error.message === 'NOT_FOUND') {
                return NextResponse.json({ error: 'Resource not found' }, { status: 404 })
            }

            return NextResponse.json(
                { error: 'Internal Server Error' },
                { status: 500 }
            )
        }
    }
}

// Usage:
// export const GET = withErrorHandler(async (req) => { ... })


// ─────────────────────────────────────────────
// 8. CORS Configuration
// ─────────────────────────────────────────────
// lib/cors.ts

const allowedOrigins = [
    'http://localhost:3000',
    'https://yourdomain.com',
    'https://app.yourdomain.com',
]

export function withCors(response: NextResponse, origin: string | null) {
    if (origin && allowedOrigins.includes(origin)) {
        response.headers.set('Access-Control-Allow-Origin', origin)
        response.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.set('Access-Control-Max-Age', '86400')
    }
    return response
}

// OPTIONS handler for preflight
export async function OPTIONS(req: NextRequest) {
    const origin = req.headers.get('origin')
    return withCors(new NextResponse(null, { status: 204 }), origin)
}


// ─────────────────────────────────────────────
// 9. Background Jobs with Queue
// ─────────────────────────────────────────────
// app/api/jobs/route.ts

// Simple in-memory queue (use BullMQ + Redis in production)
const jobQueue: Array<{ id: string; type: string; payload: any; status: string }> = []

export async function POST(req: NextRequest) {
    const { type, payload } = await req.json()

    const job = {
        id: crypto.randomUUID(),
        type,
        payload,
        status: 'queued',
    }

    jobQueue.push(job)

    // Process async (fire-and-forget)
    processJob(job).catch(console.error)

    return NextResponse.json({ jobId: job.id, status: 'queued' }, { status: 202 })
}

async function processJob(job: typeof jobQueue[0]) {
    job.status = 'processing'

    switch (job.type) {
        case 'send-email':
            await sendEmail(job.payload.to, job.payload.template)
            break
        case 'generate-report':
            await generateReport(job.payload.reportId)
            break
        case 'resize-image':
            await resizeImage(job.payload.imageUrl, job.payload.sizes)
            break
    }

    job.status = 'completed'
}


// ─────────────────────────────────────────────
// 10. API Key Authentication
// ─────────────────────────────────────────────
// lib/api-key-auth.ts

export async function validateApiKey(req: NextRequest) {
    const apiKey = req.headers.get('x-api-key') || req.headers.get('authorization')?.replace('Bearer ', '')

    if (!apiKey) {
        return { valid: false, error: 'Missing API key' }
    }

    // Hash the key for security (store hashed keys in DB)
    const keyHash = await crypto.subtle.digest(
        'SHA-256',
        new TextEncoder().encode(apiKey)
    )
    const hashHex = Array.from(new Uint8Array(keyHash))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('')

    const key = await db.apiKey.findUnique({
        where: { keyHash: hashHex },
        include: { organization: true },
    })

    if (!key) return { valid: false, error: 'Invalid API key' }
    if (key.expiresAt && key.expiresAt < new Date()) return { valid: false, error: 'API key expired' }

    // Update last used timestamp
    await db.apiKey.update({
        where: { id: key.id },
        data: { lastUsedAt: new Date() },
    })

    return { valid: true, orgId: key.organization.id, scopes: key.scopes }
}

// Usage in route:
export async function GET(req: NextRequest) {
    const auth = await validateApiKey(req)
    if (!auth.valid) {
        return NextResponse.json({ error: auth.error }, { status: 401 })
    }

    // auth.orgId and auth.scopes are now available
    const data = await db.resource.findMany({ where: { orgId: auth.orgId } })
    return NextResponse.json(data)
}
