"""
DevVault Pro V2.0: 20+ Cheat Sheets & Quick Reference Guides
"""
import os
import sys

CHEAT_SHEETS = {
    # === FRAMEWORKS ===
    "Next.js_15_App_Router_Complete_Guide.md": """# Next.js 15 App Router — Complete Guide

## Project Structure
```
app/
├── layout.tsx          # Root layout (wraps ALL pages)
├── page.tsx            # Home page (/)
├── loading.tsx         # Loading UI
├── error.tsx           # Error boundary
├── not-found.tsx       # 404 page
├── globals.css
├── dashboard/
│   ├── layout.tsx      # Dashboard layout
│   ├── page.tsx        # /dashboard
│   └── [id]/
│       └── page.tsx    # /dashboard/123
└── api/
    └── route.ts        # API route
```

## Server Components (Default)
```tsx
// app/page.tsx — runs on SERVER by default
async function Page() {
  const data = await fetch('https://api.example.com/data')
  const json = await data.json()
  return <div>{json.title}</div>
}
```

## Client Components
```tsx
'use client'
import { useState } from 'react'

export default function Counter() {
  const [count, setCount] = useState(0)
  return <button onClick={() => setCount(c => c+1)}>Count: {count}</button>
}
```

## Server Actions
```tsx
// app/actions.ts
'use server'
import { revalidatePath } from 'next/cache'

export async function createPost(formData: FormData) {
  const title = formData.get('title')
  await db.post.create({ data: { title } })
  revalidatePath('/posts')
}
```

## Dynamic Routes
```tsx
// app/blog/[slug]/page.tsx
export default function BlogPost({ params }: { params: { slug: string } }) {
  return <h1>Post: {params.slug}</h1>
}

// Generate static pages at build time
export async function generateStaticParams() {
  const posts = await getPosts()
  return posts.map(p => ({ slug: p.slug }))
}
```

## Metadata & SEO
```tsx
export const metadata = {
  title: 'My App',
  description: 'Built with DevVault Pro',
  openGraph: { images: ['/og.png'] }
}
```

## Middleware
```ts
// middleware.ts (root)
import { NextResponse } from 'next/server'

export function middleware(request) {
  if (!request.cookies.get('token')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
}
export const config = { matcher: ['/dashboard/:path*'] }
```
""",

    "React_Hooks_Cheat_Sheet.md": """# React Hooks — Complete Cheat Sheet

## useState
```tsx
const [count, setCount] = useState(0)
setCount(prev => prev + 1) // functional update
```

## useEffect
```tsx
useEffect(() => {
  // runs on mount + when deps change
  const sub = subscribe()
  return () => sub.unsubscribe() // cleanup
}, [dependency])
```

## useRef
```tsx
const inputRef = useRef<HTMLInputElement>(null)
inputRef.current?.focus()
```

## useMemo & useCallback
```tsx
const expensive = useMemo(() => compute(data), [data])
const handler = useCallback((e) => save(e), [save])
```

## useContext
```tsx
const ThemeCtx = createContext('dark')
const theme = useContext(ThemeCtx) // 'dark'
```

## Custom Hooks
```tsx
function useLocalStorage(key, initial) {
  const [value, setValue] = useState(() => {
    const stored = localStorage.getItem(key)
    return stored ? JSON.parse(stored) : initial
  })
  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value))
  }, [key, value])
  return [value, setValue]
}
```
""",

    "TypeScript_for_React_Cheat_Sheet.md": """# TypeScript for React — Quick Reference

## Component Props
```tsx
interface ButtonProps {
  label: string
  onClick: () => void
  variant?: 'primary' | 'secondary' // optional with union
  children?: React.ReactNode
}

const Button = ({ label, onClick, variant = 'primary' }: ButtonProps) => (
  <button className={variant} onClick={onClick}>{label}</button>
)
```

## Event Handlers
```tsx
const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {}
const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {}
const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {}
```

## API Response Types
```tsx
interface User {
  id: number
  name: string
  email: string
  role: 'admin' | 'user'
}

const [users, setUsers] = useState<User[]>([])
```

## Generic Components
```tsx
interface ListProps<T> {
  items: T[]
  renderItem: (item: T) => React.ReactNode
}

function List<T>({ items, renderItem }: ListProps<T>) {
  return <ul>{items.map(renderItem)}</ul>
}
```

## Utility Types
```tsx
Partial<User>    // all fields optional
Required<User>   // all fields required
Pick<User, 'id' | 'name'>  // only id & name
Omit<User, 'email'>        // everything except email
Record<string, User>        // { [key: string]: User }
```
""",

    # === UI LIBRARIES ===
    "Shadcn_UI_Complete_Guide.md": """# Shadcn/UI — Complete Component Guide

## Installation
```bash
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card dialog table
```

## Button Variants
```tsx
<Button variant="default">Primary</Button>
<Button variant="destructive">Delete</Button>
<Button variant="outline">Cancel</Button>
<Button variant="ghost">Ghost</Button>
<Button size="sm">Small</Button>
<Button size="lg">Large</Button>
<Button disabled>Disabled</Button>
```

## Dialog (Modal)
```tsx
<Dialog>
  <DialogTrigger asChild><Button>Open</Button></DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Are you sure?</DialogTitle>
      <DialogDescription>This action cannot be undone.</DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <Button variant="outline">Cancel</Button>
      <Button>Confirm</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

## Data Table
```tsx
const columns = [
  { accessorKey: "name", header: "Name" },
  { accessorKey: "email", header: "Email" },
  { accessorKey: "status", header: "Status",
    cell: ({ row }) => <Badge>{row.getValue("status")}</Badge>
  },
]
<DataTable columns={columns} data={users} />
```

## Form with React Hook Form + Zod
```tsx
const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
})

<Form {...form}>
  <FormField control={form.control} name="email" render={({ field }) => (
    <FormItem>
      <FormLabel>Email</FormLabel>
      <FormControl><Input {...field} /></FormControl>
      <FormMessage />
    </FormItem>
  )} />
</Form>
```
""",

    "Tailwind_CSS_Cheat_Sheet.md": """# Tailwind CSS — Complete Cheat Sheet

## Layout
```
flex items-center justify-between gap-4
grid grid-cols-3 gap-6
container mx-auto px-4
```

## Spacing
```
p-4 px-6 py-2 pt-8        (padding)
m-4 mx-auto my-2 mt-8     (margin)
space-x-4 space-y-2        (between children)
```

## Typography
```
text-sm text-base text-lg text-xl text-2xl
font-normal font-medium font-semibold font-bold
text-gray-500 text-white/80
leading-tight tracking-tight
```

## Colors
```
bg-white dark:bg-gray-900
text-gray-900 dark:text-white
border-gray-200 dark:border-gray-800
bg-gradient-to-r from-blue-500 to-purple-600
```

## Borders & Shadows
```
rounded-lg rounded-full rounded-xl
border border-gray-200
shadow-sm shadow-md shadow-xl
ring-2 ring-blue-500
```

## Responsive
```
sm: (640px)  md: (768px)  lg: (1024px)  xl: (1280px)
grid-cols-1 md:grid-cols-2 lg:grid-cols-3
hidden md:block
text-sm md:text-base lg:text-lg
```

## Dark Mode
```tsx
<div className="bg-white dark:bg-gray-900">
<html className="dark">  // or class-based toggle
```

## Animations
```
transition-all duration-300 ease-in-out
hover:scale-105 hover:shadow-lg
animate-pulse animate-spin animate-bounce
```
""",

    "Framer_Motion_Animations_Guide.md": """# Framer Motion — Animation Guide

## Basic Animation
```tsx
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.5 }}
/>
```

## Hover & Tap
```tsx
<motion.button
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
  transition={{ type: "spring", stiffness: 400 }}
/>
```

## Scroll Animations
```tsx
<motion.div
  initial={{ opacity: 0 }}
  whileInView={{ opacity: 1 }}
  viewport={{ once: true }}
/>
```

## Stagger Children
```tsx
const container = { hidden: {}, show: { transition: { staggerChildren: 0.1 } } }
const item = { hidden: { y: 20, opacity: 0 }, show: { y: 0, opacity: 1 } }

<motion.ul variants={container} initial="hidden" animate="show">
  {items.map(i => <motion.li key={i} variants={item} />)}
</motion.ul>
```

## Page Transitions
```tsx
<AnimatePresence mode="wait">
  <motion.div
    key={pathname}
    initial={{ opacity: 0, x: 20 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: -20 }}
  />
</AnimatePresence>
```

## Layout Animations
```tsx
<motion.div layout layoutId="card">
  {/* smoothly animates position and size changes */}
</motion.div>
```
""",

    # === BACKEND & INTEGRATIONS ===
    "Stripe_Integration_Complete_Guide.md": """# Stripe Integration — Complete Guide

## 1. Install
```bash
npm install stripe @stripe/stripe-js
```

## 2. Create Checkout Session (Server)
```ts
// app/api/checkout/route.ts
import Stripe from 'stripe'
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!)

export async function POST(req) {
  const session = await stripe.checkout.sessions.create({
    mode: 'payment', // or 'subscription'
    line_items: [{ price: 'price_xxx', quantity: 1 }],
    success_url: `${process.env.URL}/success`,
    cancel_url: `${process.env.URL}/cancel`,
  })
  return Response.json({ url: session.url })
}
```

## 3. Redirect to Checkout (Client)
```tsx
const handleCheckout = async () => {
  const res = await fetch('/api/checkout', { method: 'POST' })
  const { url } = await res.json()
  window.location.href = url
}
```

## 4. Webhook Handler
```ts
// app/api/webhook/route.ts
export async function POST(req) {
  const body = await req.text()
  const sig = req.headers.get('stripe-signature')
  const event = stripe.webhooks.constructEvent(body, sig, process.env.STRIPE_WEBHOOK_SECRET!)
  
  if (event.type === 'checkout.session.completed') {
    const session = event.data.object
    await db.user.update({ where: { email: session.customer_email }, data: { paid: true } })
  }
  return Response.json({ received: true })
}
```

## 5. Subscription Management
```ts
// Create portal for managing subscriptions
const portal = await stripe.billingPortal.sessions.create({
  customer: customerId,
  return_url: `${process.env.URL}/dashboard`,
})
```
""",

    "Supabase_Complete_Guide.md": """# Supabase — Complete Guide

## Setup
```bash
npm install @supabase/supabase-js
```
```ts
import { createClient } from '@supabase/supabase-js'
const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_ANON_KEY!)
```

## Auth
```ts
// Sign up
await supabase.auth.signUp({ email, password })

// Sign in
await supabase.auth.signInWithPassword({ email, password })

// OAuth (Google, GitHub)
await supabase.auth.signInWithOAuth({ provider: 'google' })

// Get current user
const { data: { user } } = await supabase.auth.getUser()

// Sign out
await supabase.auth.signOut()
```

## Database (CRUD)
```ts
// Read
const { data } = await supabase.from('posts').select('*').eq('published', true)

// Create
await supabase.from('posts').insert({ title: 'Hello', content: '...' })

// Update
await supabase.from('posts').update({ title: 'Updated' }).eq('id', 1)

// Delete
await supabase.from('posts').delete().eq('id', 1)

// Relationships
await supabase.from('posts').select('*, author:users(name, avatar)')
```

## Storage
```ts
// Upload
await supabase.storage.from('avatars').upload('user1.png', file)

// Get public URL
const { data } = supabase.storage.from('avatars').getPublicUrl('user1.png')
```

## Realtime
```ts
supabase.channel('posts').on('postgres_changes',
  { event: 'INSERT', schema: 'public', table: 'posts' },
  (payload) => console.log('New post:', payload.new)
).subscribe()
```
""",

    "Prisma_ORM_Cheat_Sheet.md": """# Prisma ORM — Cheat Sheet

## Schema
```prisma
// prisma/schema.prisma
model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  posts     Post[]
  createdAt DateTime @default(now())
}

model Post {
  id        String   @id @default(cuid())
  title     String
  content   String?
  published Boolean  @default(false)
  author    User     @relation(fields: [authorId], references: [id])
  authorId  String
}
```

## Commands
```bash
npx prisma init           # setup
npx prisma db push        # sync schema to DB (dev)
npx prisma migrate dev    # create migration
npx prisma studio         # visual DB browser
npx prisma generate       # regenerate client
```

## CRUD Operations
```ts
import { PrismaClient } from '@prisma/client'
const prisma = new PrismaClient()

// Create
const user = await prisma.user.create({ data: { email: 'a@b.com', name: 'Alice' } })

// Read
const users = await prisma.user.findMany({ where: { name: { contains: 'Ali' } }, include: { posts: true } })

// Update
await prisma.user.update({ where: { id: 'xxx' }, data: { name: 'Bob' } })

// Delete
await prisma.user.delete({ where: { id: 'xxx' } })

// Transactions
await prisma.$transaction([
  prisma.post.create({ data: ... }),
  prisma.user.update({ ... }),
])
```
""",

    "OpenAI_API_Integration_Guide.md": """# OpenAI API — Integration Guide

## Setup
```bash
npm install openai
```
```ts
import OpenAI from 'openai'
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY })
```

## Chat Completion
```ts
const completion = await openai.chat.completions.create({
  model: 'gpt-4o',
  messages: [
    { role: 'system', content: 'You are a helpful assistant.' },
    { role: 'user', content: 'Explain React hooks' },
  ],
  temperature: 0.7,
  max_tokens: 500,
})
console.log(completion.choices[0].message.content)
```

## Streaming
```ts
const stream = await openai.chat.completions.create({
  model: 'gpt-4o',
  messages: [{ role: 'user', content: 'Tell me a story' }],
  stream: true,
})
for await (const chunk of stream) {
  process.stdout.write(chunk.choices[0]?.delta?.content || '')
}
```

## With Vercel AI SDK (Recommended for Next.js)
```ts
// app/api/chat/route.ts
import { openai } from '@ai-sdk/openai'
import { streamText } from 'ai'

export async function POST(req) {
  const { messages } = await req.json()
  const result = streamText({ model: openai('gpt-4o'), messages })
  return result.toDataStreamResponse()
}
```

## Image Generation
```ts
const image = await openai.images.generate({
  model: 'dall-e-3',
  prompt: 'A futuristic dashboard UI',
  size: '1024x1024',
})
console.log(image.data[0].url)
```
""",

    # === AUTH ===
    "NextAuth_js_Auth_Guide.md": """# NextAuth.js (Auth.js) — Authentication Guide

## Setup
```bash
npm install next-auth @auth/prisma-adapter
```

## Configuration
```ts
// app/api/auth/[...nextauth]/route.ts
import NextAuth from 'next-auth'
import Google from 'next-auth/providers/google'
import GitHub from 'next-auth/providers/github'
import { PrismaAdapter } from '@auth/prisma-adapter'

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: PrismaAdapter(prisma),
  providers: [
    Google({ clientId: process.env.GOOGLE_ID!, clientSecret: process.env.GOOGLE_SECRET! }),
    GitHub({ clientId: process.env.GITHUB_ID!, clientSecret: process.env.GITHUB_SECRET! }),
  ],
})
export const { GET, POST } = handlers
```

## Protect Pages (Server)
```tsx
import { auth } from '@/auth'
export default async function Dashboard() {
  const session = await auth()
  if (!session) redirect('/login')
  return <h1>Hello {session.user.name}</h1>
}
```

## Client-Side
```tsx
'use client'
import { useSession, signIn, signOut } from 'next-auth/react'

export function LoginButton() {
  const { data: session } = useSession()
  if (session) return <button onClick={() => signOut()}>Sign Out</button>
  return <button onClick={() => signIn('google')}>Sign In</button>
}
```
""",

    # === STATE & DATA ===
    "Zustand_State_Management.md": """# Zustand — State Management

## Create Store
```ts
import { create } from 'zustand'

interface Store {
  count: number
  increment: () => void
  reset: () => void
}

const useStore = create<Store>((set) => ({
  count: 0,
  increment: () => set((s) => ({ count: s.count + 1 })),
  reset: () => set({ count: 0 }),
}))
```

## Use in Components
```tsx
function Counter() {
  const { count, increment } = useStore()
  return <button onClick={increment}>{count}</button>
}
```

## Persist to LocalStorage
```ts
import { persist } from 'zustand/middleware'

const useStore = create(persist((set) => ({
  theme: 'dark',
  setTheme: (t) => set({ theme: t }),
}), { name: 'app-storage' }))
```

## Async Actions
```ts
const useStore = create((set) => ({
  users: [],
  loading: false,
  fetchUsers: async () => {
    set({ loading: true })
    const res = await fetch('/api/users')
    const users = await res.json()
    set({ users, loading: false })
  },
}))
```
""",

    "React_Query_TanStack_Guide.md": """# TanStack Query (React Query) — Guide

## Setup
```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
const queryClient = new QueryClient()

<QueryClientProvider client={queryClient}>
  <App />
</QueryClientProvider>
```

## Fetch Data
```tsx
function Users() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: () => fetch('/api/users').then(r => r.json()),
    staleTime: 60_000, // cache for 1 min
  })
  if (isLoading) return <Spinner />
  return <ul>{data.map(u => <li key={u.id}>{u.name}</li>)}</ul>
}
```

## Mutations
```tsx
const mutation = useMutation({
  mutationFn: (newUser) => fetch('/api/users', {
    method: 'POST', body: JSON.stringify(newUser)
  }),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
})
```

## Infinite Scroll
```tsx
const { data, fetchNextPage, hasNextPage } = useInfiniteQuery({
  queryKey: ['posts'],
  queryFn: ({ pageParam = 1 }) => fetch(`/api/posts?page=${pageParam}`).then(r => r.json()),
  getNextPageParam: (last) => last.nextPage,
})
```
""",

    # === DEPLOYMENT ===
    "Vercel_Deployment_Guide.md": """# Vercel Deployment — Quick Guide

## CLI Deploy
```bash
npm i -g vercel
vercel          # preview deployment
vercel --prod   # production deployment
```

## Environment Variables
```bash
vercel env add STRIPE_SECRET_KEY production
# or via dashboard: Settings > Environment Variables
```

## vercel.json
```json
{
  "rewrites": [{ "source": "/api/:path*", "destination": "/api/:path*" }],
  "headers": [
    { "source": "/(.*)", "headers": [
      { "key": "X-Frame-Options", "value": "DENY" }
    ]}
  ]
}
```

## Domain Setup
```bash
vercel domains add yourdomain.com
```
Add CNAME record: `cname.vercel-dns.com`

## Edge Functions
```ts
export const runtime = 'edge' // in any route.ts or page.tsx
```
""",

    "Docker_Basics_for_Devs.md": """# Docker — Basics for Developers

## Dockerfile (Next.js)
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json .
EXPOSE 3000
CMD ["npm", "start"]
```

## Docker Compose
```yaml
version: '3.8'
services:
  app:
    build: .
    ports: ["3000:3000"]
    environment:
      - DATABASE_URL=postgres://user:pass@db:5432/mydb
    depends_on: [db]
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: mydb
    volumes: ["pgdata:/var/lib/postgresql/data"]
volumes:
  pgdata:
```

## Commands
```bash
docker build -t myapp .
docker run -p 3000:3000 myapp
docker-compose up -d
docker-compose down
docker logs <container>
```
""",

    # === TESTING & TOOLS ===
    "Git_Commands_Cheat_Sheet.md": """# Git Commands — Cheat Sheet

## Daily Workflow
```bash
git add .
git commit -m "feat: add user auth"
git push origin main
git pull origin main
```

## Branching
```bash
git checkout -b feat/auth    # create & switch
git merge feat/auth          # merge into current
git branch -d feat/auth      # delete branch
```

## Undo
```bash
git reset HEAD~1             # undo last commit (keep changes)
git reset --hard HEAD~1      # undo + delete changes
git stash                    # save changes temporarily
git stash pop                # restore stashed changes
```

## Commit Convention
```
feat:     new feature
fix:      bug fix
docs:     documentation
style:    formatting
refactor: code restructure
test:     tests
chore:    maintenance
```
""",

    "React_Native_Quick_Start.md": """# React Native — Quick Start

## Create App
```bash
npx create-expo-app@latest my-app
cd my-app && npx expo start
```

## Core Components
```tsx
import { View, Text, StyleSheet, Pressable, Image, ScrollView, FlatList, TextInput } from 'react-native'

export default function App() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Hello World</Text>
      <Pressable onPress={() => alert('Pressed!')}>
        <Text>Tap Me</Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 24, fontWeight: 'bold' },
})
```

## Navigation
```bash
npm install @react-navigation/native @react-navigation/stack
```
```tsx
<NavigationContainer>
  <Stack.Navigator>
    <Stack.Screen name="Home" component={HomeScreen} />
    <Stack.Screen name="Profile" component={ProfileScreen} />
  </Stack.Navigator>
</NavigationContainer>
```

## NativeWind (Tailwind for RN)
```bash
npm install nativewind tailwindcss
```
```tsx
<View className="flex-1 items-center justify-center bg-white dark:bg-gray-900">
  <Text className="text-2xl font-bold text-gray-900 dark:text-white">Hello</Text>
</View>
```
""",

    "Zod_Validation_Cheat_Sheet.md": """# Zod — Validation Cheat Sheet

## Basic Types
```ts
import { z } from 'zod'

const schema = z.object({
  name: z.string().min(2).max(50),
  email: z.string().email(),
  age: z.number().int().positive().max(120),
  role: z.enum(['admin', 'user', 'editor']),
  bio: z.string().optional(),
  tags: z.array(z.string()),
  metadata: z.record(z.string()),
})

type User = z.infer<typeof schema> // auto-generated type!
```

## Validation
```ts
const result = schema.safeParse(data)
if (result.success) {
  console.log(result.data) // typed!
} else {
  console.log(result.error.issues) // errors
}
```

## Transform & Refine
```ts
const schema = z.string()
  .transform(s => s.toLowerCase().trim())
  .refine(s => !s.includes('admin'), 'Cannot use admin')
```

## With React Hook Form
```ts
import { zodResolver } from '@hookform/resolvers/zod'
const form = useForm({ resolver: zodResolver(schema) })
```
""",

    "SEO_Checklist_for_Next_js.md": """# SEO Checklist for Next.js

## 1. Metadata
```tsx
// app/layout.tsx
export const metadata = {
  title: { default: 'My App', template: '%s | My App' },
  description: 'Build faster with DevVault Pro',
  keywords: ['nextjs', 'react', 'saas'],
  authors: [{ name: 'Your Name' }],
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://myapp.com',
    images: [{ url: '/og.png', width: 1200, height: 630 }],
  },
  twitter: { card: 'summary_large_image' },
}
```

## 2. Sitemap
```ts
// app/sitemap.ts
export default async function sitemap() {
  const posts = await getPosts()
  return [
    { url: 'https://myapp.com', lastModified: new Date() },
    ...posts.map(p => ({ url: `https://myapp.com/blog/${p.slug}`, lastModified: p.updatedAt })),
  ]
}
```

## 3. robots.txt
```ts
// app/robots.ts
export default function robots() {
  return { rules: { userAgent: '*', allow: '/' }, sitemap: 'https://myapp.com/sitemap.xml' }
}
```

## 4. Structured Data (JSON-LD)
```tsx
<script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({
  '@context': 'https://schema.org',
  '@type': 'WebSite',
  name: 'My App',
  url: 'https://myapp.com',
}) }} />
```
""",

    "React_Email_Templates_Guide.md": """# React Email — Templates Guide

## Setup
```bash
npm install @react-email/components resend
```

## Create Email Template
```tsx
import { Html, Head, Body, Container, Text, Button, Img } from '@react-email/components'

export default function WelcomeEmail({ name }: { name: string }) {
  return (
    <Html>
      <Head />
      <Body style={{ fontFamily: 'sans-serif', background: '#f4f4f5' }}>
        <Container style={{ maxWidth: 600, margin: '0 auto', padding: 20 }}>
          <Img src="https://myapp.com/logo.png" width={120} />
          <Text style={{ fontSize: 24, fontWeight: 'bold' }}>Welcome, {name}!</Text>
          <Text>Thanks for signing up. Here's what you can do next:</Text>
          <Button href="https://myapp.com/dashboard"
            style={{ background: '#6c63ff', color: '#fff', padding: '12px 24px', borderRadius: 8 }}>
            Go to Dashboard
          </Button>
        </Container>
      </Body>
    </Html>
  )
}
```

## Send with Resend
```ts
import { Resend } from 'resend'
const resend = new Resend(process.env.RESEND_API_KEY)

await resend.emails.send({
  from: 'onboarding@myapp.com',
  to: 'user@example.com',
  subject: 'Welcome!',
  react: WelcomeEmail({ name: 'Alice' }),
})
```
""",
}

def generate_cheat_sheets(vault_dir):
    bonus = os.path.join(vault_dir, "[BONUS] Cheat_Sheets_2026")
    os.makedirs(bonus, exist_ok=True)
    
    for filename, content in CHEAT_SHEETS.items():
        fpath = os.path.join(bonus, filename)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content.strip())
    
    # Create index
    idx = f"# 📚 Cheat Sheets & Quick Reference Guides\n\n"
    idx += f"**{len(CHEAT_SHEETS)} professional guides** included.\n\n"
    idx += "| # | Guide | Topic |\n|---|-------|-------|\n"
    
    for i, fname in enumerate(sorted(CHEAT_SHEETS.keys()), 1):
        topic = fname.replace("_", " ").replace(".md", "")
        idx += f"| {i} | [{topic}]({fname}) | Quick Reference |\n"
    
    idx += "\n---\n*DevVault Pro 2026*\n"
    
    with open(os.path.join(bonus, "INDICE.md"), 'w', encoding='utf-8') as f:
        f.write(idx)
    
    print(f"Generated {len(CHEAT_SHEETS)} cheat sheets + index.")

if __name__ == "__main__":
    vault = sys.argv[1] if len(sys.argv) > 1 else "God_Tier_Dev_Vault"
    generate_cheat_sheets(vault)
