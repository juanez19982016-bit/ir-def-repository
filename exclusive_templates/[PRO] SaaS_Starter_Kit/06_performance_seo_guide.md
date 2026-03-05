# 🚀 PERFORMANCE & SEO OPTIMIZATION GUIDE — 2026 Edition

> This guide covers the techniques used by top-performing sites.
> Apply these and watch your Lighthouse score hit 95+.

---

## 📊 Core Web Vitals — The Only Metrics That Matter

| Metric | Target | What it measures |
|--------|--------|-----------------|
| **LCP** (Largest Contentful Paint) | < 2.5s | Loading speed |
| **INP** (Interaction to Next Paint) | < 200ms | Responsiveness |
| **CLS** (Cumulative Layout Shift) | < 0.1 | Visual stability |

---

## ⚡ Performance Checklist

### Images (usually 50%+ of page weight)
```tsx
// ✅ ALWAYS use next/image — automatic WebP/AVIF, lazy loading, responsive
import Image from 'next/image'

<Image
  src="/hero.jpg"
  alt="Hero"
  width={1200}
  height={630}
  priority          // Add for above-the-fold images (fixes LCP)
  placeholder="blur" // Shows blurred preview while loading
  blurDataURL={shimmer(1200, 630)}
/>
```

**Rules:**
- `priority` on hero/banner images only
- All other images load lazily by default
- Use `sizes` prop to avoid downloading oversized images
- AVIF saves 50% over JPEG, WebP saves 30%

### Fonts
```tsx
// ✅ Use next/font — zero layout shift, self-hosted
import { Inter } from 'next/font/google'

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',       // No invisible text
  variable: '--font-inter',
})
```

### JavaScript Bundle
```tsx
// ✅ Dynamic imports for heavy components
const Chart = dynamic(() => import('./Chart'), {
  loading: () => <Skeleton className="h-64" />,
  ssr: false,  // Skip SSR for client-only components
})

// ✅ Lazy load below-the-fold sections
const Testimonials = dynamic(() => import('./Testimonials'))
```

### Data Fetching
```tsx
// ✅ Server Components fetch data on the server (zero client JS)
async function Dashboard() {
  const stats = await db.stats.findMany()  // Runs on server
  return <StatsGrid data={stats} />
}

// ✅ Parallel data fetching (don't await sequentially)
const [users, projects, tasks] = await Promise.all([
  getUsers(),
  getProjects(),
  getTasks(),
])
```

### Caching
```tsx
// ✅ Cache expensive operations
import { unstable_cache } from 'next/cache'

const getCachedStats = unstable_cache(
  async () => db.stats.aggregate(),
  ['dashboard-stats'],
  { revalidate: 60 }  // Refresh every 60 seconds
)

// ✅ Set proper headers for API routes
export async function GET() {
  return Response.json(data, {
    headers: {
      'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=300',
    },
  })
}
```

---

## 🔍 SEO Checklist

### Metadata (Next.js 15)
```tsx
// app/layout.tsx
export const metadata: Metadata = {
  title: {
    template: '%s | YourApp',
    default: 'YourApp — Build Faster',
  },
  description: 'Production-ready SaaS starter with auth, payments, and more.',
  keywords: ['saas', 'nextjs', 'starter'],
  authors: [{ name: 'Your Name' }],

  openGraph: {
    type: 'website',
    siteName: 'YourApp',
    title: 'YourApp — Build Faster',
    description: 'Ship your SaaS in days, not months.',
    images: [{ url: '/og.png', width: 1200, height: 630 }],
  },

  twitter: {
    card: 'summary_large_image',
    creator: '@yourhandle',
  },

  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
}
```

### Sitemap & Robots
```tsx
// app/sitemap.ts
export default async function sitemap(): MetadataRoute.Sitemap {
  const posts = await db.post.findMany({ select: { slug: true, updatedAt: true } })

  return [
    { url: 'https://yourapp.com', lastModified: new Date(), changeFrequency: 'weekly', priority: 1 },
    { url: 'https://yourapp.com/pricing', lastModified: new Date(), priority: 0.8 },
    ...posts.map(post => ({
      url: `https://yourapp.com/blog/${post.slug}`,
      lastModified: post.updatedAt,
      priority: 0.6,
    })),
  ]
}

// app/robots.ts
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: '*', allow: '/', disallow: ['/api/', '/dashboard/'] },
    sitemap: 'https://yourapp.com/sitemap.xml',
  }
}
```

### Structured Data (JSON-LD)
```tsx
// For product/pricing pages (shows star ratings in Google)
<script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "YourApp",
  "applicationCategory": "DeveloperApplication",
  "offers": { "@type": "Offer", "price": "29", "priceCurrency": "USD" },
  "aggregateRating": { "@type": "AggregateRating", "ratingValue": "4.9", "reviewCount": "142" },
}) }} />
```

---

## 🛡️ Security Headers

```tsx
// next.config.ts
const securityHeaders = [
  { key: 'X-DNS-Prefetch-Control', value: 'on' },
  { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-XSS-Protection', value: '1; mode=block' },
  { key: 'Referrer-Policy', value: 'origin-when-cross-origin' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
]

const nextConfig = {
  async headers() {
    return [{ source: '/(.*)', headers: securityHeaders }]
  },
}
```

---

## 📏 Quick Wins Cheat Sheet

| Action | Impact | Effort |
|--------|--------|--------|
| Add `priority` to hero image | LCP -40% | 1 min |
| Use `next/font` | CLS = 0 | 5 min |
| Dynamic import heavy components | JS -30% | 10 min |
| Add `loading.tsx` skeletons | Perceived speed +50% | 15 min |
| Enable Brotli compression | Size -25% | 5 min |
| Add proper meta + OG tags | SEO + social shares | 10 min |
| Implement `sitemap.ts` | Google indexing speed | 5 min |
| Cache API responses | Server load -80% | 10 min |
| Add security headers | Security score A+ | 5 min |
| Lazy load below-the-fold | TTI -20% | 10 min |

---

**Apply this guide and your app will load faster than 95% of the web.** ⚡
