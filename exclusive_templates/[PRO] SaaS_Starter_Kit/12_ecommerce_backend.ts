// ============================================================
// 🛒 E-COMMERCE BACKEND — Complete Production System
// DevVault Pro 2026 — Cart, Orders, Inventory, Stripe Checkout
// ============================================================

// ── 1. Product Management ───────────────────────

// lib/products.ts
import { db } from '@/lib/db'
import { z } from 'zod'

const ProductSchema = z.object({
    name: z.string().min(1).max(200),
    description: z.string().max(5000),
    price: z.number().positive(),
    compareAtPrice: z.number().positive().optional(),
    images: z.array(z.string().url()),
    category: z.string(),
    tags: z.array(z.string()),
    variants: z.array(z.object({
        name: z.string(),
        sku: z.string(),
        price: z.number().positive(),
        stock: z.number().int().min(0),
        attributes: z.record(z.string()),
    })).optional(),
    metadata: z.record(z.string()).optional(),
})

export async function createProduct(data: z.infer<typeof ProductSchema>) {
    const validated = ProductSchema.parse(data)

    return db.product.create({
        data: {
            ...validated,
            slug: generateSlug(validated.name),
            status: 'draft',
            variants: validated.variants ? { create: validated.variants } : undefined,
        },
        include: { variants: true },
    })
}

export async function getProducts(filters: {
    category?: string
    minPrice?: number
    maxPrice?: number
    search?: string
    sort?: 'price_asc' | 'price_desc' | 'newest' | 'popular'
    page?: number
    limit?: number
}) {
    const { category, minPrice, maxPrice, search, sort = 'newest', page = 1, limit = 20 } = filters

    const where: any = { status: 'active' }
    if (category) where.category = category
    if (minPrice || maxPrice) where.price = { ...(minPrice && { gte: minPrice }), ...(maxPrice && { lte: maxPrice }) }
    if (search) where.OR = [
        { name: { contains: search, mode: 'insensitive' } },
        { description: { contains: search, mode: 'insensitive' } },
        { tags: { hasSome: [search] } },
    ]

    const orderBy: any = {
        price_asc: { price: 'asc' },
        price_desc: { price: 'desc' },
        newest: { createdAt: 'desc' },
        popular: { soldCount: 'desc' },
    }[sort]

    const [products, total] = await Promise.all([
        db.product.findMany({ where, orderBy, skip: (page - 1) * limit, take: limit, include: { variants: true } }),
        db.product.count({ where }),
    ])

    return { products, total, pages: Math.ceil(total / limit), page }
}


// ── 2. Shopping Cart ────────────────────────────

// lib/cart.ts

interface CartItem {
    productId: string
    variantId?: string
    quantity: number
}

export async function getCart(userId: string) {
    const cart = await db.cart.findUnique({
        where: { userId },
        include: {
            items: {
                include: {
                    product: true,
                    variant: true,
                },
            },
        },
    })

    if (!cart) return { items: [], subtotal: 0, itemCount: 0 }

    const items = cart.items.map(item => ({
        ...item,
        price: item.variant?.price ?? item.product.price,
        total: (item.variant?.price ?? item.product.price) * item.quantity,
    }))

    return {
        items,
        subtotal: items.reduce((sum, item) => sum + item.total, 0),
        itemCount: items.reduce((sum, item) => sum + item.quantity, 0),
    }
}

export async function addToCart(userId: string, item: CartItem) {
    // Ensure cart exists
    const cart = await db.cart.upsert({
        where: { userId },
        create: { userId },
        update: {},
    })

    // Check stock
    const product = await db.product.findUnique({
        where: { id: item.productId },
        include: { variants: true },
    })

    if (!product) throw new Error('Product not found')

    const variant = item.variantId
        ? product.variants.find(v => v.id === item.variantId)
        : null

    const stock = variant?.stock ?? product.stock
    if (stock < item.quantity) throw new Error('Insufficient stock')

    // Upsert cart item
    const existing = await db.cartItem.findFirst({
        where: { cartId: cart.id, productId: item.productId, variantId: item.variantId ?? null },
    })

    if (existing) {
        const newQty = existing.quantity + item.quantity
        if (newQty > stock) throw new Error('Insufficient stock')

        return db.cartItem.update({
            where: { id: existing.id },
            data: { quantity: newQty },
        })
    }

    return db.cartItem.create({
        data: { cartId: cart.id, productId: item.productId, variantId: item.variantId, quantity: item.quantity },
    })
}

export async function removeFromCart(userId: string, cartItemId: string) {
    const cart = await db.cart.findUnique({ where: { userId } })
    if (!cart) throw new Error('Cart not found')

    return db.cartItem.deleteMany({ where: { id: cartItemId, cartId: cart.id } })
}


// ── 3. Stripe Checkout ──────────────────────────

// lib/checkout.ts
import Stripe from 'stripe'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, { apiVersion: '2024-12-18.acacia' })

export async function createCheckoutSession(userId: string, options?: {
    couponCode?: string
    successUrl?: string
    cancelUrl?: string
}) {
    const { items, subtotal } = await getCart(userId)
    if (items.length === 0) throw new Error('Cart is empty')

    const user = await db.user.findUnique({ where: { id: userId } })

    // Apply coupon if provided
    let couponId: string | undefined
    if (options?.couponCode) {
        const coupon = await db.coupon.findUnique({ where: { code: options.couponCode } })
        if (coupon && coupon.active && coupon.expiresAt > new Date()) {
            couponId = coupon.stripeCouponId
        }
    }

    const session = await stripe.checkout.sessions.create({
        customer_email: user?.email ?? undefined,
        line_items: items.map(item => ({
            price_data: {
                currency: 'usd',
                product_data: {
                    name: item.product.name,
                    images: item.product.images.slice(0, 1),
                    metadata: {
                        productId: item.productId,
                        variantId: item.variantId ?? '',
                    },
                },
                unit_amount: Math.round(item.price * 100),
            },
            quantity: item.quantity,
        })),
        mode: 'payment',
        ...(couponId && { discounts: [{ coupon: couponId }] }),
        shipping_address_collection: { allowed_countries: ['US', 'CA', 'GB', 'AU'] },
        metadata: { userId },
        success_url: options?.successUrl || `${process.env.NEXT_PUBLIC_URL}/checkout/success?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: options?.cancelUrl || `${process.env.NEXT_PUBLIC_URL}/cart`,
    })

    return { sessionId: session.id, url: session.url }
}


// ── 4. Order Management ─────────────────────────

// lib/orders.ts

export async function createOrderFromCheckout(sessionId: string) {
    const session = await stripe.checkout.sessions.retrieve(sessionId, {
        expand: ['line_items', 'payment_intent'],
    })

    const userId = session.metadata!.userId
    const { items } = await getCart(userId)

    // Create order
    const order = await db.order.create({
        data: {
            userId,
            status: 'confirmed',
            stripeSessionId: sessionId,
            stripePaymentIntentId: (session.payment_intent as Stripe.PaymentIntent).id,
            subtotal: session.amount_subtotal! / 100,
            total: session.amount_total! / 100,
            currency: session.currency!,
            shippingAddress: session.shipping_details?.address as any,
            items: {
                create: items.map(item => ({
                    productId: item.productId,
                    variantId: item.variantId,
                    name: item.product.name,
                    price: item.price,
                    quantity: item.quantity,
                })),
            },
        },
        include: { items: true },
    })

    // Reduce stock
    for (const item of items) {
        if (item.variantId) {
            await db.productVariant.update({
                where: { id: item.variantId },
                data: { stock: { decrement: item.quantity } },
            })
        } else {
            await db.product.update({
                where: { id: item.productId },
                data: { stock: { decrement: item.quantity }, soldCount: { increment: item.quantity } },
            })
        }
    }

    // Clear cart
    const cart = await db.cart.findUnique({ where: { userId } })
    if (cart) await db.cartItem.deleteMany({ where: { cartId: cart.id } })

    // Send confirmation email
    await sendOrderConfirmation(order)

    return order
}

export async function getOrders(userId: string, page = 1) {
    return db.order.findMany({
        where: { userId },
        orderBy: { createdAt: 'desc' },
        skip: (page - 1) * 10,
        take: 10,
        include: { items: { include: { product: true } } },
    })
}

export async function updateOrderStatus(
    orderId: string,
    status: 'processing' | 'shipped' | 'delivered' | 'refunded' | 'cancelled',
    trackingNumber?: string
) {
    const order = await db.order.update({
        where: { id: orderId },
        data: {
            status,
            ...(trackingNumber && { trackingNumber }),
            ...(status === 'shipped' && { shippedAt: new Date() }),
            ...(status === 'delivered' && { deliveredAt: new Date() }),
        },
        include: { user: true },
    })

    // Send status update email
    await sendStatusUpdate(order)

    return order
}


// ── 5. Inventory Management ─────────────────────

export async function getLowStockProducts(threshold = 10) {
    return db.product.findMany({
        where: { stock: { lte: threshold }, status: 'active' },
        orderBy: { stock: 'asc' },
    })
}

export async function bulkUpdateStock(
    updates: Array<{ productId: string; variantId?: string; stock: number }>
) {
    return db.$transaction(
        updates.map(({ productId, variantId, stock }) =>
            variantId
                ? db.productVariant.update({ where: { id: variantId }, data: { stock } })
                : db.product.update({ where: { id: productId }, data: { stock } })
        )
    )
}


// ── 6. Coupon System ────────────────────────────

const CouponSchema = z.object({
    code: z.string().min(3).max(20).toUpperCase(),
    type: z.enum(['percentage', 'fixed']),
    value: z.number().positive(),
    minOrderValue: z.number().min(0).optional(),
    maxUses: z.number().int().positive().optional(),
    expiresAt: z.date(),
})

export async function createCoupon(data: z.infer<typeof CouponSchema>) {
    const validated = CouponSchema.parse(data)

    // Create Stripe coupon
    const stripeCoupon = await stripe.coupons.create({
        ...(validated.type === 'percentage'
            ? { percent_off: validated.value }
            : { amount_off: Math.round(validated.value * 100), currency: 'usd' }),
        max_redemptions: validated.maxUses,
        redeem_by: Math.floor(validated.expiresAt.getTime() / 1000),
    })

    return db.coupon.create({
        data: { ...validated, stripeCouponId: stripeCoupon.id, active: true, usedCount: 0 },
    })
}

export async function applyCoupon(code: string, cartSubtotal: number) {
    const coupon = await db.coupon.findUnique({ where: { code: code.toUpperCase() } })

    if (!coupon) return { valid: false, error: 'Coupon not found' }
    if (!coupon.active) return { valid: false, error: 'Coupon is no longer active' }
    if (coupon.expiresAt < new Date()) return { valid: false, error: 'Coupon has expired' }
    if (coupon.maxUses && coupon.usedCount >= coupon.maxUses) return { valid: false, error: 'Coupon usage limit reached' }
    if (coupon.minOrderValue && cartSubtotal < coupon.minOrderValue) return { valid: false, error: `Minimum order: $${coupon.minOrderValue}` }

    const discount = coupon.type === 'percentage'
        ? cartSubtotal * (coupon.value / 100)
        : coupon.value

    return { valid: true, discount: Math.min(discount, cartSubtotal), coupon }
}


// ── Helper Functions ────────────────────────────

function generateSlug(name: string): string {
    return name.toLowerCase().replace(/[^\w\s-]/g, '').replace(/[\s_-]+/g, '-').replace(/^-+|-+$/g, '')
}

async function sendOrderConfirmation(order: any) {
    // Integrate with your email service (Resend, SendGrid, etc.)
    console.log(`📧 Order confirmation sent for #${order.id}`)
}

async function sendStatusUpdate(order: any) {
    console.log(`📧 Status update sent for #${order.id}: ${order.status}`)
}
