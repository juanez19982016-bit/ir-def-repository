// ============================================================
// 🚀 NEXT.JS 15 SAAS STARTER — COMPLETE AUTH + PAYMENTS + DB
// ============================================================
// This is the EXACT code structure that products like ShipFast ($199)
// and Makerkit ($249) sell. You're getting it included in DevVault Pro.
//
// Stack: Next.js 15, Auth.js v5, Stripe, Prisma, Supabase
// Time saved: ~80-120 hours of development
// ============================================================

// ============ FILE: app/layout.tsx ============
// Root layout with providers
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Your SaaS App",
    description: "Built with the DevVault Pro SaaS Starter Kit",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body className={inter.className}>
                <Providers>{children}</Providers>
            </body>
        </html>
    );
}

// ============ FILE: components/providers.tsx ============
// All app providers in one place
"use client";
import { SessionProvider } from "next-auth/react";
import { ThemeProvider } from "next-themes";
import { Toaster } from "sonner";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient();

export function Providers({ children }: { children: React.ReactNode }) {
    return (
        <SessionProvider>
            <QueryClientProvider client={queryClient}>
                <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
                    {children}
                    <Toaster richColors position="bottom-right" />
                </ThemeProvider>
            </QueryClientProvider>
        </SessionProvider>
    );
}

// ============ FILE: auth.ts ============
// Auth.js v5 configuration — Google + GitHub + Email
import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import GitHub from "next-auth/providers/github";
import Resend from "next-auth/providers/resend";
import { PrismaAdapter } from "@auth/prisma-adapter";
import { prisma } from "@/lib/prisma";

export const { handlers, auth, signIn, signOut } = NextAuth({
    adapter: PrismaAdapter(prisma),
    providers: [
        Google({
            clientId: process.env.GOOGLE_CLIENT_ID,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET,
        }),
        GitHub({
            clientId: process.env.GITHUB_CLIENT_ID,
            clientSecret: process.env.GITHUB_CLIENT_SECRET,
        }),
        Resend({
            from: "noreply@yourdomain.com",
        }),
    ],
    pages: {
        signIn: "/login",
        error: "/login",
    },
    callbacks: {
        async session({ session, user }) {
            if (session.user) {
                session.user.id = user.id;
                // Attach subscription status to session
                const dbUser = await prisma.user.findUnique({
                    where: { id: user.id },
                    select: { plan: true, stripeCustomerId: true },
                });
                session.user.plan = dbUser?.plan ?? "free";
                session.user.stripeCustomerId = dbUser?.stripeCustomerId ?? null;
            }
            return session;
        },
    },
});

// ============ FILE: lib/prisma.ts ============
import { PrismaClient } from "@prisma/client";

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient };

export const prisma = globalForPrisma.prisma ?? new PrismaClient();

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;

// ============ FILE: prisma/schema.prisma ============
/*
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id              String    @id @default(cuid())
  name            String?
  email           String    @unique
  emailVerified   DateTime?
  image           String?
  plan            String    @default("free") // free, pro, enterprise
  stripeCustomerId String?  @unique
  accounts        Account[]
  sessions        Session[]
  projects        Project[]
  createdAt       DateTime  @default(now())
  updatedAt       DateTime  @updatedAt
}

model Account {
  id                String  @id @default(cuid())
  userId            String
  type              String
  provider          String
  providerAccountId String
  refresh_token     String?
  access_token      String?
  expires_at        Int?
  token_type        String?
  scope             String?
  id_token          String?
  session_state     String?
  user              User    @relation(fields: [userId], references: [id], onDelete: Cascade)
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
  tasks       Task[]
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
}

model Task {
  id          String   @id @default(cuid())
  title       String
  description String?
  status      String   @default("todo") // todo, in_progress, done
  priority    String   @default("medium") // low, medium, high, critical
  projectId   String
  project     Project  @relation(fields: [projectId], references: [id], onDelete: Cascade)
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
}

model Subscription {
  id                   String   @id @default(cuid())
  userId               String   @unique
  stripeSubscriptionId String   @unique
  stripePriceId        String
  stripeCustomerId     String
  status               String   // active, canceled, past_due
  currentPeriodEnd     DateTime
  createdAt            DateTime @default(now())
  updatedAt            DateTime @updatedAt
}
*/

// ============ FILE: app/api/auth/[...nextauth]/route.ts ============
import { handlers } from "@/auth";
export const { GET, POST } = handlers;

// ============ FILE: middleware.ts ============
// Protect routes that require authentication
import { auth } from "@/auth";
import { NextResponse } from "next/server";

export default auth((req) => {
    const isLoggedIn = !!req.auth;
    const isAuthPage = req.nextUrl.pathname.startsWith("/login");
    const isDashboard = req.nextUrl.pathname.startsWith("/dashboard");

    // Redirect logged-in users away from auth pages
    if (isAuthPage && isLoggedIn) {
        return NextResponse.redirect(new URL("/dashboard", req.url));
    }

    // Redirect unauthenticated users to login
    if (isDashboard && !isLoggedIn) {
        return NextResponse.redirect(new URL("/login", req.url));
    }

    return NextResponse.next();
});

export const config = {
    matcher: ["/dashboard/:path*", "/login"],
};

// ============ FILE: app/login/page.tsx ============
// Login page component
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { LoginForm } from "@/components/auth/login-form";

export default async function LoginPage() {
    const session = await auth();
    if (session) redirect("/dashboard");
    return <LoginForm />;
}

// ============ FILE: components/auth/login-form.tsx ============
"use client";
import { signIn } from "next-auth/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";

export function LoginForm() {
    const [email, setEmail] = useState("");
    const [loading, setLoading] = useState(false);

    const handleMagicLink = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            await signIn("resend", { email, callbackUrl: "/dashboard" });
            toast.success("Check your email for a magic link!");
        } catch {
            toast.error("Something went wrong. Try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-background">
            <Card className="w-full max-w-md">
                <CardHeader className="text-center">
                    <CardTitle className="text-2xl font-bold">Welcome back</CardTitle>
                    <CardDescription>Sign in to your account to continue</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                        <Button variant="outline" onClick={() => signIn("google", { callbackUrl: "/dashboard" })}>
                            Google
                        </Button>
                        <Button variant="outline" onClick={() => signIn("github", { callbackUrl: "/dashboard" })}>
                            GitHub
                        </Button>
                    </div>
                    <Separator />
                    <form onSubmit={handleMagicLink} className="space-y-3">
                        <Input
                            type="email"
                            placeholder="you@example.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                        <Button type="submit" className="w-full" disabled={loading}>
                            {loading ? "Sending..." : "Send Magic Link"}
                        </Button>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
}

// ============ FILE: app/dashboard/page.tsx ============
// Protected dashboard page
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { prisma } from "@/lib/prisma";
import { DashboardShell } from "@/components/dashboard/shell";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { ProjectsList } from "@/components/dashboard/projects-list";

export default async function DashboardPage() {
    const session = await auth();
    if (!session?.user) redirect("/login");

    const [projects, taskCount] = await Promise.all([
        prisma.project.findMany({
            where: { userId: session.user.id },
            include: { _count: { select: { tasks: true } } },
            orderBy: { updatedAt: "desc" },
        }),
        prisma.task.count({ where: { project: { userId: session.user.id } } }),
    ]);

    return (
        <DashboardShell>
            <StatsCards
                totalProjects={projects.length}
                totalTasks={taskCount}
                plan={session.user.plan}
            />
            <ProjectsList projects={projects} />
        </DashboardShell>
    );
}

// ============ FILE: app/api/projects/route.ts ============
// CRUD API for projects
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";
import { NextResponse } from "next/server";
import { z } from "zod";

const createSchema = z.object({
    name: z.string().min(1).max(100),
    description: z.string().max(500).optional(),
});

// GET /api/projects — list user's projects
export async function GET() {
    const session = await auth();
    if (!session?.user?.id) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const projects = await prisma.project.findMany({
        where: { userId: session.user.id },
        include: { _count: { select: { tasks: true } } },
        orderBy: { createdAt: "desc" },
    });

    return NextResponse.json(projects);
}

// POST /api/projects — create a project
export async function POST(req: Request) {
    const session = await auth();
    if (!session?.user?.id) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Check plan limits
    if (session.user.plan === "free") {
        const count = await prisma.project.count({ where: { userId: session.user.id } });
        if (count >= 3) {
            return NextResponse.json(
                { error: "Free plan limited to 3 projects. Upgrade to Pro!" },
                { status: 403 }
            );
        }
    }

    const body = await req.json();
    const result = createSchema.safeParse(body);
    if (!result.success) {
        return NextResponse.json({ error: result.error.flatten() }, { status: 400 });
    }

    const project = await prisma.project.create({
        data: { ...result.data, userId: session.user.id },
    });

    return NextResponse.json(project, { status: 201 });
}

// ============ FILE: lib/stripe.ts ============
// Stripe configuration
import Stripe from "stripe";

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
    apiVersion: "2024-12-18.acacia",
    typescript: true,
});

export const PLANS = {
    free: { name: "Free", price: 0, features: ["3 projects", "Basic support"] },
    pro: {
        name: "Pro",
        price: 29,
        priceId: process.env.STRIPE_PRO_PRICE_ID!,
        features: ["Unlimited projects", "Priority support", "API access", "Team collaboration"],
    },
    enterprise: {
        name: "Enterprise",
        price: 99,
        priceId: process.env.STRIPE_ENTERPRISE_PRICE_ID!,
        features: ["Everything in Pro", "SLA", "Custom integrations", "Dedicated support", "SSO"],
    },
};

// ============ FILE: app/api/stripe/checkout/route.ts ============
// Create Stripe Checkout session
import { auth } from "@/auth";
import { stripe, PLANS } from "@/lib/stripe";
import { prisma } from "@/lib/prisma";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
    const session = await auth();
    if (!session?.user?.id) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { plan } = await req.json();
    const planConfig = PLANS[plan as keyof typeof PLANS];
    if (!planConfig || !("priceId" in planConfig)) {
        return NextResponse.json({ error: "Invalid plan" }, { status: 400 });
    }

    // Get or create Stripe customer
    let customerId = session.user.stripeCustomerId;
    if (!customerId) {
        const customer = await stripe.customers.create({
            email: session.user.email!,
            name: session.user.name ?? undefined,
            metadata: { userId: session.user.id },
        });
        customerId = customer.id;
        await prisma.user.update({
            where: { id: session.user.id },
            data: { stripeCustomerId: customerId },
        });
    }

    const checkoutSession = await stripe.checkout.sessions.create({
        customer: customerId,
        mode: "subscription",
        payment_method_types: ["card"],
        line_items: [{ price: planConfig.priceId, quantity: 1 }],
        success_url: `${process.env.NEXTAUTH_URL}/dashboard?success=true`,
        cancel_url: `${process.env.NEXTAUTH_URL}/pricing`,
        metadata: { userId: session.user.id },
    });

    return NextResponse.json({ url: checkoutSession.url });
}

// ============ FILE: app/api/stripe/webhook/route.ts ============
// Handle Stripe webhook events
import { stripe } from "@/lib/stripe";
import { prisma } from "@/lib/prisma";
import { NextResponse } from "next/server";
import { headers } from "next/headers";

export async function POST(req: Request) {
    const body = await req.text();
    const headersList = await headers();
    const signature = headersList.get("stripe-signature")!;

    let event;
    try {
        event = stripe.webhooks.constructEvent(body, signature, process.env.STRIPE_WEBHOOK_SECRET!);
    } catch (err) {
        console.error("Webhook signature verification failed:", err);
        return NextResponse.json({ error: "Invalid signature" }, { status: 400 });
    }

    switch (event.type) {
        case "checkout.session.completed": {
            const session = event.data.object;
            const userId = session.metadata?.userId;
            if (userId) {
                const subscription = await stripe.subscriptions.retrieve(session.subscription as string);
                await prisma.user.update({
                    where: { id: userId },
                    data: { plan: "pro" },
                });
                await prisma.subscription.upsert({
                    where: { userId },
                    update: {
                        stripeSubscriptionId: subscription.id,
                        stripePriceId: subscription.items.data[0].price.id,
                        stripeCustomerId: subscription.customer as string,
                        status: subscription.status,
                        currentPeriodEnd: new Date(subscription.current_period_end * 1000),
                    },
                    create: {
                        userId,
                        stripeSubscriptionId: subscription.id,
                        stripePriceId: subscription.items.data[0].price.id,
                        stripeCustomerId: subscription.customer as string,
                        status: subscription.status,
                        currentPeriodEnd: new Date(subscription.current_period_end * 1000),
                    },
                });
            }
            break;
        }

        case "customer.subscription.deleted": {
            const subscription = event.data.object;
            await prisma.subscription.update({
                where: { stripeSubscriptionId: subscription.id },
                data: { status: "canceled" },
            });
            const sub = await prisma.subscription.findUnique({
                where: { stripeSubscriptionId: subscription.id },
            });
            if (sub) {
                await prisma.user.update({
                    where: { id: sub.userId },
                    data: { plan: "free" },
                });
            }
            break;
        }

        case "invoice.payment_failed": {
            const invoice = event.data.object;
            const customerId = invoice.customer as string;
            const user = await prisma.user.findFirst({
                where: { stripeCustomerId: customerId },
            });
            if (user) {
                // TODO: Send email notification about failed payment
                console.log(`Payment failed for user ${user.id}`);
            }
            break;
        }
    }

    return NextResponse.json({ received: true });
}

// ============ FILE: .env.example ============
/*
# Auth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-here-generate-with-openssl-rand-base64-32

# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# GitHub OAuth
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# Database (Supabase)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_ENTERPRISE_PRICE_ID=price_...

# Resend (Email)
RESEND_API_KEY=re_...
*/
