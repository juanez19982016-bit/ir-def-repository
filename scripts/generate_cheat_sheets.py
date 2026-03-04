"""
DevVault Pro V3: Generates a BONUS folder with developer cheat sheets.
"""
import os

CHEAT_SHEETS = {
    "Next.js_15_App_Router_Cheat_Sheet.md": """# 🚀 Next.js 15 App Router — Cheat Sheet

## Estructura de Carpetas
```
app/
├── layout.tsx          # Layout principal (se hereda)
├── page.tsx            # Página principal (/)
├── loading.tsx         # UI de carga automático
├── error.tsx           # Manejo de errores
├── not-found.tsx       # Página 404
├── api/
│   └── route.ts        # API Routes (GET, POST)
├── dashboard/
│   ├── layout.tsx      # Layout anidado
│   └── page.tsx        # /dashboard
```

## Server Components vs Client Components
```tsx
// Server Component (default - NO 'use client')
async function ServerPage() {
  const data = await fetch('https://api.example.com/data');
  return <div>{data}</div>;
}

// Client Component (interactividad)
'use client'
import { useState } from 'react';
export default function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(count + 1)}>{count}</button>;
}
```

## Server Actions (Formularios sin API)
```tsx
async function createUser(formData: FormData) {
  'use server'
  const name = formData.get('name');
  await db.user.create({ data: { name } });
}

export default function Form() {
  return (
    <form action={createUser}>
      <input name="name" />
      <button type="submit">Crear</button>
    </form>
  );
}
```

## Metadata SEO
```tsx
export const metadata = {
  title: 'Mi App',
  description: 'Descripción para Google',
  openGraph: { title: 'Mi App', images: ['/og.png'] },
};
```

## Rutas Dinámicas
```
app/blog/[slug]/page.tsx     →  /blog/mi-post
app/shop/[...slug]/page.tsx  →  /shop/a/b/c (catch-all)
```

## Middleware (Auth, Redirects)
```ts
// middleware.ts (raíz del proyecto)
import { NextResponse } from 'next/server';
export function middleware(request) {
  if (!request.cookies.get('token')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
}
export const config = { matcher: ['/dashboard/:path*'] };
```
""",

    "Shadcn_UI_Components_Guide.md": """# 🎨 Shadcn/UI — Guía Completa de Componentes

## Instalación
```bash
npx shadcn@latest init
npx shadcn@latest add button card dialog table
```

## Componentes Más Usados

### Button
```tsx
import { Button } from "@/components/ui/button"
<Button variant="default">Default</Button>
<Button variant="destructive">Eliminar</Button>
<Button variant="outline">Outline</Button>
<Button variant="ghost">Ghost</Button>
```

### Card
```tsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
<Card>
  <CardHeader><CardTitle>Título</CardTitle></CardHeader>
  <CardContent>Contenido aquí</CardContent>
</Card>
```

### Dialog (Modal)
```tsx
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
<Dialog>
  <DialogTrigger asChild><Button>Abrir</Button></DialogTrigger>
  <DialogContent>
    <DialogHeader><DialogTitle>Título del Modal</DialogTitle></DialogHeader>
    <p>Contenido del modal</p>
  </DialogContent>
</Dialog>
```

### Data Table (con TanStack)
```tsx
import { DataTable } from "@/components/ui/data-table"
const columns = [
  { accessorKey: "name", header: "Nombre" },
  { accessorKey: "email", header: "Email" },
];
<DataTable columns={columns} data={users} />
```

### Form (con react-hook-form + zod)
```tsx
const formSchema = z.object({ email: z.string().email() });
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

## Temas y Personalización
Edita `globals.css` para cambiar colores:
```css
:root {
  --primary: 222.2 47.4% 11.2%;
  --primary-foreground: 210 40% 98%;
}
```
""",

    "Tailwind_CSS_Cheat_Sheet.md": """# 🎯 Tailwind CSS — Clases Más Usadas (2026)

## Layout
| Clase | CSS |
|-------|-----|
| `flex` | display: flex |
| `grid` | display: grid |
| `grid-cols-3` | grid-template-columns: repeat(3, 1fr) |
| `gap-4` | gap: 1rem |
| `justify-center` | justify-content: center |
| `items-center` | align-items: center |
| `container mx-auto` | max-width + centrado |

## Spacing (Padding & Margin)
| Clase | Valor |
|-------|-------|
| `p-4` | padding: 1rem |
| `px-6` | padding-left/right: 1.5rem |
| `my-8` | margin-top/bottom: 2rem |
| `space-y-4` | gap vertical entre hijos |

## Typography
| Clase | Uso |
|-------|-----|
| `text-sm/base/lg/xl/2xl` | Tamaño de fuente |
| `font-bold/semibold/medium` | Peso de fuente |
| `text-gray-500` | Color de texto |
| `leading-relaxed` | Interlineado |
| `tracking-tight` | Letter spacing |

## Borders & Rounded
| Clase | Uso |
|-------|-----|
| `rounded-lg` | border-radius: 0.5rem |
| `rounded-full` | Completamente redondo |
| `border border-gray-200` | Borde fino |
| `shadow-lg` | Sombra grande |

## Responsive
```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
  <!-- 1 col mobile, 2 tablet, 3 desktop -->
</div>
```

## Dark Mode
```html
<div class="bg-white dark:bg-gray-900 text-black dark:text-white">
  Funciona automáticamente con class="dark" en <html>
</div>
```

## Animaciones
| Clase | Efecto |
|-------|--------|
| `animate-spin` | Rotación infinita |
| `animate-pulse` | Pulso suave |
| `animate-bounce` | Rebote |
| `transition-all duration-300` | Transición suave |
| `hover:scale-105` | Zoom al hover |
""",

    "Stripe_Integration_Quick_Start.md": """# 💳 Stripe Integration — Quick Start (Next.js)

## 1. Instalar
```bash
npm install stripe @stripe/stripe-js
```

## 2. Variables de Entorno
```env
STRIPE_SECRET_KEY=sk_test_xxx
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
```

## 3. Crear Checkout Session (API Route)
```ts
// app/api/checkout/route.ts
import Stripe from 'stripe';
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function POST(req: Request) {
  const session = await stripe.checkout.sessions.create({
    payment_method_types: ['card'],
    line_items: [{
      price_data: {
        currency: 'usd',
        product_data: { name: 'DevVault Pro' },
        unit_amount: 14900, // $149.00
      },
      quantity: 1,
    }],
    mode: 'payment',
    success_url: `${process.env.NEXT_PUBLIC_URL}/success`,
    cancel_url: `${process.env.NEXT_PUBLIC_URL}/cancel`,
  });
  return Response.json({ url: session.url });
}
```

## 4. Botón de Pago (Client)
```tsx
'use client'
export default function BuyButton() {
  const handleClick = async () => {
    const res = await fetch('/api/checkout', { method: 'POST' });
    const { url } = await res.json();
    window.location.href = url;
  };
  return <button onClick={handleClick}>Comprar $149</button>;
}
```

## 5. Webhook (Confirmar pagos)
```ts
// app/api/webhook/route.ts
export async function POST(req: Request) {
  const body = await req.text();
  const sig = req.headers.get('stripe-signature')!;
  const event = stripe.webhooks.constructEvent(body, sig, process.env.STRIPE_WEBHOOK_SECRET!);
  
  if (event.type === 'checkout.session.completed') {
    const session = event.data.object;
    // Grant access to user
    await grantAccess(session.customer_email);
  }
  return Response.json({ received: true });
}
```
""",

    "Supabase_Auth_Quick_Start.md": """# 🔐 Supabase Auth — Quick Start (Next.js)

## 1. Instalar
```bash
npm install @supabase/supabase-js @supabase/ssr
```

## 2. Variables de Entorno
```env
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJxxx
```

## 3. Cliente Supabase
```ts
// lib/supabase.ts
import { createBrowserClient } from '@supabase/ssr';
export const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);
```

## 4. Login con Email
```tsx
const { error } = await supabase.auth.signInWithPassword({
  email: 'user@email.com',
  password: 'password123',
});
```

## 5. Login con Google OAuth
```tsx
const { error } = await supabase.auth.signInWithOAuth({
  provider: 'google',
  options: { redirectTo: `${window.location.origin}/auth/callback` },
});
```

## 6. Proteger Rutas (Middleware)
```ts
// middleware.ts
import { createServerClient } from '@supabase/ssr';
import { NextResponse } from 'next/server';

export async function middleware(req) {
  const supabase = createServerClient(/* config */);
  const { data: { user } } = await supabase.auth.getUser();
  
  if (!user && req.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', req.url));
  }
  return NextResponse.next();
}
```
""",
}

def generate_cheat_sheets(vault_dir):
    bonus_dir = os.path.join(vault_dir, "[BONUS] Cheat_Sheets_2026")
    os.makedirs(bonus_dir, exist_ok=True)
    
    for filename, content in CHEAT_SHEETS.items():
        filepath = os.path.join(bonus_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content.strip())
        print(f"  ✅ {filename}")
    
    print(f"\nGenerated {len(CHEAT_SHEETS)} bonus cheat sheets.")

if __name__ == "__main__":
    import sys
    vault = sys.argv[1] if len(sys.argv) > 1 else "God_Tier_Dev_Vault"
    generate_cheat_sheets(vault)
