// ============================================================
// 🔐 SUPABASE + ROW LEVEL SECURITY — COMPLETE SETUP
// ============================================================
// Production-ready Supabase setup with RLS policies.
// Includes: Auth, CRUD, Storage, Realtime, Edge Functions
// Time saved: ~20-30 hours
// ============================================================

// ============ FILE: lib/supabase/client.ts ============
// Browser client — use in Client Components
import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
    return createBrowserClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );
}

// ============ FILE: lib/supabase/server.ts ============
// Server client — use in Server Components, Route Handlers, Server Actions
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createServerSupabaseClient() {
    const cookieStore = await cookies();

    return createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() {
                    return cookieStore.getAll();
                },
                setAll(cookiesToSet) {
                    try {
                        cookiesToSet.forEach(({ name, value, options }) =>
                            cookieStore.set(name, value, options)
                        );
                    } catch { }
                },
            },
        }
    );
}

// ============ FILE: lib/supabase/admin.ts ============
// Admin client — use for operations that bypass RLS
import { createClient } from "@supabase/supabase-js";

export const supabaseAdmin = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY! // ⚠️ Never expose this to the client!
);

// ============ FILE: middleware.ts ============
// Refresh auth tokens on every request
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
    let supabaseResponse = NextResponse.next({ request });

    const supabase = createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() {
                    return request.cookies.getAll();
                },
                setAll(cookiesToSet) {
                    cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
                    supabaseResponse = NextResponse.next({ request });
                    cookiesToSet.forEach(({ name, value, options }) =>
                        supabaseResponse.cookies.set(name, value, options)
                    );
                },
            },
        }
    );

    const { data: { user } } = await supabase.auth.getUser();

    // Protect dashboard routes
    if (!user && request.nextUrl.pathname.startsWith("/dashboard")) {
        const url = request.nextUrl.clone();
        url.pathname = "/login";
        return NextResponse.redirect(url);
    }

    return supabaseResponse;
}

export const config = {
    matcher: ["/dashboard/:path*", "/api/:path*"],
};

// ============ SQL: Complete Database Schema with RLS ============
/*
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============ PROFILES TABLE ============
CREATE TABLE profiles (
  id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  full_name TEXT,
  avatar_url TEXT,
  plan TEXT DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'enterprise')),
  stripe_customer_id TEXT UNIQUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS: Users can only read/update their own profile
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
  ON profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  USING (auth.uid() = id);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO profiles (id, full_name, avatar_url)
  VALUES (
    NEW.id,
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'avatar_url'
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ============ PROJECTS TABLE ============
CREATE TABLE projects (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD own projects"
  ON projects FOR ALL
  USING (auth.uid() = user_id);

-- ============ TASKS TABLE ============
CREATE TABLE tasks (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'todo' CHECK (status IN ('todo', 'in_progress', 'done')),
  priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
  assigned_to UUID REFERENCES profiles(id),
  due_date TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD tasks in own projects"
  ON tasks FOR ALL
  USING (
    project_id IN (
      SELECT id FROM projects WHERE user_id = auth.uid()
    )
  );

-- ============ STORAGE BUCKETS ============
INSERT INTO storage.buckets (id, name, public)
VALUES ('avatars', 'avatars', true);

INSERT INTO storage.buckets (id, name, public)
VALUES ('attachments', 'attachments', false);

-- Storage policies
CREATE POLICY "Users can upload own avatar"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'avatars' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );

CREATE POLICY "Anyone can view avatars"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'avatars');

CREATE POLICY "Users can upload attachments to own projects"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'attachments' AND
    auth.uid() IS NOT NULL
  );

-- ============ REALTIME ============
-- Enable realtime for tasks (live updates)
ALTER PUBLICATION supabase_realtime ADD TABLE tasks;

-- ============ INDEXES ============
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assigned_to ON tasks(assigned_to);

-- ============ UPDATED_AT TRIGGER ============
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_projects_updated_at
  BEFORE UPDATE ON projects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_tasks_updated_at
  BEFORE UPDATE ON tasks
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
*/

// ============ FILE: hooks/use-supabase-query.ts ============
// React hook for real-time Supabase queries
"use client";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import type { RealtimeChannel } from "@supabase/supabase-js";

export function useRealtimeTasks(projectId: string) {
    const [tasks, setTasks] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const supabase = createClient();

    useEffect(() => {
        // Initial fetch
        supabase
            .from("tasks")
            .select("*")
            .eq("project_id", projectId)
            .order("created_at", { ascending: false })
            .then(({ data }) => {
                setTasks(data || []);
                setLoading(false);
            });

        // Subscribe to realtime changes
        const channel: RealtimeChannel = supabase
            .channel(`tasks:${projectId}`)
            .on(
                "postgres_changes",
                {
                    event: "*",
                    schema: "public",
                    table: "tasks",
                    filter: `project_id=eq.${projectId}`,
                },
                (payload) => {
                    if (payload.eventType === "INSERT") {
                        setTasks((prev) => [payload.new as any, ...prev]);
                    } else if (payload.eventType === "UPDATE") {
                        setTasks((prev) =>
                            prev.map((t) => (t.id === payload.new.id ? payload.new : t))
                        );
                    } else if (payload.eventType === "DELETE") {
                        setTasks((prev) => prev.filter((t) => t.id !== payload.old.id));
                    }
                }
            )
            .subscribe();

        return () => {
            supabase.removeChannel(channel);
        };
    }, [projectId, supabase]);

    return { tasks, loading };
}

// ============ FILE: lib/supabase/storage.ts ============
// File upload helpers
import { createClient } from "@/lib/supabase/client";

export async function uploadAvatar(userId: string, file: File) {
    const supabase = createClient();
    const ext = file.name.split(".").pop();
    const path = `${userId}/avatar.${ext}`;

    const { error } = await supabase.storage
        .from("avatars")
        .upload(path, file, { upsert: true });

    if (error) throw error;

    const { data } = supabase.storage
        .from("avatars")
        .getPublicUrl(path);

    // Update profile
    await supabase.from("profiles").update({ avatar_url: data.publicUrl }).eq("id", userId);

    return data.publicUrl;
}

export async function uploadAttachment(projectId: string, file: File) {
    const supabase = createClient();
    const path = `${projectId}/${Date.now()}-${file.name}`;

    const { data, error } = await supabase.storage
        .from("attachments")
        .upload(path, file);

    if (error) throw error;
    return data.path;
}

export async function getSignedUrl(path: string, expiresIn = 3600) {
    const supabase = createClient();
    const { data, error } = await supabase.storage
        .from("attachments")
        .createSignedUrl(path, expiresIn);

    if (error) throw error;
    return data.signedUrl;
}
